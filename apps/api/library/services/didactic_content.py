import json

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from ai.services import AIProviderError, chat_with_provider
from ..models import DidacticLesson, DidacticLessonSection, SenseiCompetencyProgress, SenseiLearningActivity, SenseiStudyUnit, SenseiUnitSource
from .sensei_learning import SenseiLearningError, resolve_provider


SECTION_TYPES = {choice for choice, _ in DidacticLessonSection.SectionType.choices}

LESSON_SCHEMA = {
    "type": "object",
    "properties": {
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section_type": {"type": "string", "enum": sorted(SECTION_TYPES)},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "additionalProperties": False,
                    },
                },
                "required": ["section_type", "title", "content", "metadata"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["sections"],
    "additionalProperties": False,
}


class DidacticContentError(RuntimeError):
    pass


def get_authorship_section(lesson):
    return lesson.sections.filter(
        section_type=DidacticLessonSection.SectionType.AUTHORSHIP_CHALLENGE
    ).order_by("order", "id").first()


def get_authorship_activity(lesson, section, user):
    return SenseiLearningActivity.objects.filter(
        user=user,
        unit_id=lesson.learning_target_id,
        pedagogical_context__didactic_lesson_id=lesson.id,
        pedagogical_context__didactic_section_id=section.id,
        pedagogical_context__kind="AUTHORSHIP_CHALLENGE",
    ).prefetch_related("attempts").order_by("-created_at", "-id").first()


@transaction.atomic
def start_authorship_challenge(lesson, section, user):
    unit = lesson.learning_target
    plan = getattr(unit, "study_plan", None)
    competency = plan.related_competencies.order_by("order", "id").first() if plan else None
    if plan is None or competency is None:
        raise DidacticContentError("O desafio não possui contexto pedagógico suficiente.")
    activity = get_authorship_activity(lesson, section, user)
    if activity:
        return activity, False
    activity = SenseiLearningActivity.objects.create(
        user=user,
        unit=unit,
        competency=competency,
        activity_type=SenseiLearningActivity.ActivityType.PRACTICAL_CHALLENGE,
        prompt=section.content,
        difficulty_level=max(1, min(competency.expected_level, 6)),
        pedagogical_context={
            "kind": "AUTHORSHIP_CHALLENGE",
            "didactic_lesson_id": lesson.id,
            "didactic_section_id": section.id,
            "audience": lesson.audience,
        },
    )
    return activity, True


def build_didactic_context(unit):
    plan = getattr(unit, "study_plan", None)
    if plan is None:
        raise DidacticContentError("A unidade não possui plano de estudo configurado.")
    competencies = list(plan.related_competencies.order_by("order", "id"))
    if not competencies:
        raise DidacticContentError("A unidade não possui competência relacionada.")

    formation = unit.module.formation
    sources = list(
        unit.curated_sources.filter(
            editorial_status=SenseiUnitSource.EditorialStatus.APPROVED
        ).order_by("priority", "id")
    )
    if not sources and formation.source_policy == formation.SourcePolicy.REQUIRE_APPROVED_SOURCE:
        raise DidacticContentError("NEEDS_SOURCE: a aula exige ao menos uma fonte aprovada por revisão humana.")

    source_mode = (
        DidacticLesson.SourceMode.APPROVED_SOURCES
        if sources
        else DidacticLesson.SourceMode.AI_GENERATED_UNSOURCED
    )

    return {
        "formation": formation.title,
        "module": unit.module.title,
        "unit": unit.title,
        "unit_objective": unit.objective,
        "learning_objectives": plan.learning_objectives,
        "competencies": [{"title": item.title, "description": item.description, "expected_level": item.expected_level, "mastery_criteria": item.mastery_criteria} for item in competencies],
        "prerequisites": list(plan.prerequisites.values_list("title", flat=True)),
        "practices": plan.practices,
        "expected_evidence": plan.expected_evidence,
        "completion_criteria": plan.completion_criteria,
        "approved_sources": [{"id": source.id, "title": source.title, "reference": source.reference, "category": source.category, "source_type": source.source_type, "priority": source.priority, "location": source.location, "objective": source.objective} for source in sources],
        "source_policy": formation.source_policy,
        "source_mode": source_mode,
        "audience": DidacticLesson.Audience.SENSEI,
    }, sources, source_mode


def _parse_response(raw, provider):
    try:
        payload = raw if isinstance(raw, dict) else json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AIProviderError("invalid_response", provider) from exc
    sections = payload.get("sections") if isinstance(payload, dict) else None
    if not isinstance(sections, list) or not sections:
        raise AIProviderError("invalid_response", provider)
    normalized = []
    for item in sections:
        if not isinstance(item, dict) or item.get("section_type") not in SECTION_TYPES or not str(item.get("title", "")).strip() or not str(item.get("content", "")).strip() or not isinstance(item.get("metadata", {}), dict):
            raise AIProviderError("invalid_response", provider)
        normalized.append({"section_type": item["section_type"], "title": item["title"].strip(), "content": item["content"].strip(), "metadata": item.get("metadata", {})})
    if not any(item["section_type"] == DidacticLessonSection.SectionType.AUTHORSHIP_CHALLENGE for item in normalized):
        raise DidacticContentError("A aula precisa conter um desafio de autoria.")
    return normalized


@transaction.atomic
def generate_didactic_lesson(unit: SenseiStudyUnit, user):
    context, sources, source_mode = build_didactic_context(unit)
    content_type = ContentType.objects.get_for_model(unit)
    lesson, created = DidacticLesson.objects.select_for_update().get_or_create(
        learning_target_type=content_type, learning_target_id=unit.id, audience=DidacticLesson.Audience.SENSEI,
        defaults={"title": unit.title, "author": user},
    )
    if not created and lesson.status != DidacticLesson.Status.ARCHIVED:
        return lesson, False
    provider, model, _ = resolve_provider(user, unit.module.formation)
    allowed_section_types = ", ".join(sorted(SECTION_TYPES))
    if source_mode == DidacticLesson.SourceMode.APPROVED_SOURCES:
        grounding_instruction = (
            "Use somente o contexto confiável e as fontes aprovadas fornecidas. "
            "Não invente referências, autores, links, documentos ou citações."
        )
    else:
        grounding_instruction = (
            "Não há fonte aprovada disponível para esta unidade. A política da formação permite gerar um rascunho "
            "assistido por IA com conhecimento geral do modelo. Não apresente conhecimento do modelo como se viesse "
            "de uma fonte aprovada. Não invente referências, autores, livros, artigos, links, documentos ou citações. "
            "Não crie uma seção REFERENCES com referências fictícias. O conteúdo permanecerá DRAFT e exigirá revisão humana."
        )

    messages = [
        {
            "role": "system",
            "content": (
                "Você é um motor universal de conteúdo didático. Produza uma aula estruturada, não um resumo. "
                f"{grounding_instruction} "
                "Cada seção deve usar EXATAMENTE um dos valores permitidos em section_type: "
                f"{allowed_section_types}. "
                "Não crie, traduza, pluralize, abrevie ou adapte nomes de section_type. "
                "O campo metadata deve ser sempre um objeto JSON vazio: {}. "
                "Inclua obrigatoriamente uma seção com section_type AUTHORSHIP_CHALLENGE, exigindo compreensão, "
                "aplicação, explicação, reflexão e artefato quando adequado."
            ),
        },
        {
            "role": "user",
            "content": (
                "Gere uma aula completa e densa para o público Sensei. "
                "Respeite rigorosamente os valores de section_type definidos pelo sistema. "
                "Contexto pedagógico:\n" + json.dumps(context, ensure_ascii=False)
            ),
        },
    ]
    sections = _parse_response(chat_with_provider(provider, messages, response_schema=LESSON_SCHEMA), provider)
    lesson.title = unit.title
    lesson.status = DidacticLesson.Status.DRAFT
    lesson.source_mode = source_mode
    lesson.ai_provider = provider
    lesson.ai_model = model
    lesson.generated_at = timezone.now()
    lesson.author = user
    lesson.reviewed_by = None
    lesson.reviewed_at = None
    lesson.published_at = None
    lesson.save()
    lesson.sources.set(sources)
    lesson.sections.all().delete()
    DidacticLessonSection.objects.bulk_create([DidacticLessonSection(lesson=lesson, section_type=item["section_type"], title=item["title"], content=item["content"], order=index, metadata=item["metadata"]) for index, item in enumerate(sections)])
    return lesson, True


def update_human_lesson(lesson, user, validated_data):
    sections = validated_data.pop("sections", None)
    if "title" in validated_data:
        lesson.title = validated_data["title"]
    if "status" in validated_data:
        lesson.status = validated_data["status"]
        if lesson.status == DidacticLesson.Status.APPROVED:
            lesson.reviewed_by = user
            lesson.reviewed_at = timezone.now()
        elif lesson.status == DidacticLesson.Status.PUBLISHED:
            lesson.published_at = timezone.now()
    lesson.author = lesson.author or user
    update_fields = ["title", "status", "author", "updated_at"]
    if lesson.status == DidacticLesson.Status.APPROVED:
        update_fields.extend(["reviewed_by", "reviewed_at"])
    if lesson.status == DidacticLesson.Status.PUBLISHED:
        update_fields.append("published_at")
    lesson.save(update_fields=update_fields)
    if sections is not None:
        lesson.sections.all().delete()
        DidacticLessonSection.objects.bulk_create([DidacticLessonSection(lesson=lesson, **item) for item in sections])
    return lesson
