from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from core.models import Course, Lesson, Module
from ..models import DidacticLesson, DidacticLessonSection, DidacticPublication, SenseiStudyUnit


class DidacticPublicationError(RuntimeError):
    pass


def create_preview(anchor_unit, scope, user):
    scope = str(scope or "").upper()
    units = _scope_units(anchor_unit, scope)
    eligibility, lessons = _classify_units(units)
    payload = [_adapt_lesson(lesson) for lesson in lessons]
    snapshot = _snapshot(eligibility)
    publication = DidacticPublication.objects.create(
        scope=scope,
        formation=anchor_unit.module.formation,
        module=anchor_unit.module if scope in {DidacticPublication.Scope.LESSON, DidacticPublication.Scope.MODULE} else None,
        unit=anchor_unit if scope == DidacticPublication.Scope.LESSON else None,
        preview_token=uuid4(),
        source_snapshot=snapshot,
        preview_payload=payload,
        created_by=user,
    )
    publication.eligibility_items = eligibility
    publication.summary = _summary(eligibility)
    return publication


@transaction.atomic
def publish_preview(preview_token, user, formation_id):
    # Keep publication/formation locked without joining optional scope relations.
    publication = DidacticPublication.objects.select_for_update().select_related("formation").prefetch_related("module", "unit").filter(
        preview_token=preview_token, created_by=user, formation_id=formation_id, status=DidacticPublication.Status.PREVIEW,
    ).first()
    if not publication:
        raise DidacticPublicationError("Prévia inválida, já publicada ou pertencente a outro usuário.")
    current_units = _publication_units(publication)
    current_eligibility, current_lessons = _classify_units(current_units, lock=True)
    if _snapshot(current_eligibility) != publication.source_snapshot:
        raise DidacticPublicationError("A origem SENSEI mudou após a prévia. Gere uma nova prévia antes de publicar.")
    if not current_lessons:
        raise DidacticPublicationError("Nenhuma unidade elegível para publicação. Gere uma nova prévia após aprovar uma aula didática.")
    sources = {item.pk: item for item in current_lessons}

    formation = publication.formation
    if not formation.workspace_course_id:
        formation.workspace_course = Course.objects.create(title=formation.title, description=formation.description or formation.objective)
        formation.save(update_fields=["workspace_course", "updated_at"])

    published = []
    for adapted in publication.preview_payload:
        source = sources[adapted["source_lesson_id"]]
        unit = source.learning_target
        sensei_module = unit.module
        if not sensei_module.workspace_module_id:
            sensei_module.workspace_module = Module.objects.create(course=formation.workspace_course, title=sensei_module.title, order=sensei_module.order)
            sensei_module.save(update_fields=["workspace_module"])
        student, _ = DidacticLesson.objects.update_or_create(
            learning_target_type=source.learning_target_type,
            learning_target_id=source.learning_target_id,
            audience=DidacticLesson.Audience.STUDENT,
            defaults={
                "title": adapted["title"], "status": DidacticLesson.Status.PUBLISHED,
                "source_mode": source.source_mode, "origin_lesson": source,
                "origin_updated_at": source.updated_at, "author": user, "reviewed_by": user,
                "reviewed_at": timezone.now(), "published_at": timezone.now(),
                "ai_provider": source.ai_provider, "ai_model": source.ai_model, "generated_at": source.generated_at,
            },
        )
        student.sections.all().delete()
        DidacticLessonSection.objects.bulk_create([
            DidacticLessonSection(lesson=student, section_type=item["section_type"], title=item["title"], content=item["content"], order=index, metadata=item["metadata"])
            for index, item in enumerate(adapted["sections"])
        ])
        student.sources.set(source.sources.all())
        body = "\n\n".join(f"## {item['title']}\n\n{item['content']}" for item in adapted["sections"])
        workspace, _ = Lesson.objects.update_or_create(
            pk=student.workspace_lesson_id,
            defaults={"module": sensei_module.workspace_module, "title": student.title, "content_type": "ARTICLE", "body": body, "order": unit.order},
        ) if student.workspace_lesson_id else (Lesson.objects.create(module=sensei_module.workspace_module, title=student.title, content_type="ARTICLE", body=body, order=unit.order), True)
        student.workspace_lesson = workspace
        student.save(update_fields=["workspace_lesson", "updated_at"])
        published.append({"source_lesson_id": source.pk, "student_lesson_id": student.pk, "workspace_lesson_id": workspace.pk, "stale": False})

    publication.status = DidacticPublication.Status.PUBLISHED
    publication.published_at = timezone.now()
    publication.save(update_fields=["status", "published_at", "updated_at"])
    return publication, published


def _scope_units(anchor_unit, scope):
    if scope not in DidacticPublication.Scope.values:
        raise DidacticPublicationError("Escopo inválido. Use LESSON, MODULE ou FORMATION.")
    units = anchor_unit.__class__.objects.filter(pk=anchor_unit.pk)
    if scope == DidacticPublication.Scope.MODULE:
        units = anchor_unit.module.study_units.all()
    elif scope == DidacticPublication.Scope.FORMATION:
        units = anchor_unit.__class__.objects.filter(module__formation=anchor_unit.module.formation)
    return units.select_related("module", "module__formation").order_by("module__order", "module_id", "order", "id")


def _publication_units(publication):
    if publication.scope == DidacticPublication.Scope.LESSON:
        return SenseiStudyUnit.objects.filter(pk=publication.unit_id).select_related("module", "module__formation")
    if publication.scope == DidacticPublication.Scope.MODULE:
        return publication.module.study_units.select_related("module", "module__formation").order_by("order", "id")
    return SenseiStudyUnit.objects.filter(module__formation=publication.formation).select_related("module", "module__formation").order_by("module__order", "module_id", "order", "id")


def _classify_units(units, lock=False):
    units = list(units)
    if not units:
        return [], []
    content_type = ContentType.objects.get_for_model(units[0])
    query = DidacticLesson.objects.filter(
        learning_target_type=content_type, learning_target_id__in=[unit.pk for unit in units],
    ).select_related().prefetch_related("sections", "sources")
    if lock:
        query = query.select_for_update()
    lessons_by_unit = {lesson.learning_target_id: lesson for lesson in query if lesson.audience == DidacticLesson.Audience.SENSEI}
    incompatible_units = {lesson.learning_target_id for lesson in query if lesson.audience != DidacticLesson.Audience.SENSEI}
    eligibility = []
    eligible_lessons = []
    for unit in units:
        lesson = lessons_by_unit.get(unit.pk)
        if lesson is None and unit.pk in incompatible_units:
            code, reason = "INELIGIBLE_INCOMPATIBLE_AUDIENCE", "Aula sem origem SENSEI compatível — não será publicada"
        elif lesson is None:
            code, reason = "INELIGIBLE_NO_DIDACTIC_LESSON", "Sem aula didática — não será publicada"
        elif lesson.status == DidacticLesson.Status.APPROVED:
            code, reason = "ELIGIBLE", "APPROVED — será publicada"
            eligible_lessons.append(lesson)
        else:
            code = f"INELIGIBLE_{lesson.status}"
            reason = f"{lesson.get_status_display()} ({lesson.status}) — não será publicada"
        existing_student = DidacticLesson.objects.filter(origin_lesson=lesson).only("id", "origin_updated_at").first() if lesson else None
        eligibility.append({
            "unit_id": unit.pk, "unit_title": unit.title, "unit_status": unit.status,
            "unit_order": unit.order, "module_id": unit.module_id, "module_title": unit.module.title,
            "module_order": unit.module.order, "eligibility": code, "reason": reason,
            "source_lesson_id": lesson.pk if lesson else None,
            "source_status": lesson.status if lesson else None,
            "source_updated_at": lesson.updated_at.isoformat() if lesson else None,
            "source_ids": sorted(source.pk for source in lesson.sources.all()) if lesson else [],
            "existing_student_lesson_id": existing_student.pk if existing_student else None,
            "student_is_stale": bool(lesson and existing_student and existing_student.origin_updated_at != lesson.updated_at),
        })
    return eligibility, eligible_lessons


def _snapshot(eligibility):
    return [{key: item[key] for key in (
        "unit_id", "unit_title", "unit_status", "unit_order", "module_id", "module_title", "module_order",
        "eligibility", "source_lesson_id", "source_status", "source_updated_at", "source_ids",
    )} for item in eligibility]


def _summary(eligibility):
    eligible = sum(item["eligibility"] == "ELIGIBLE" for item in eligibility)
    return {"total": len(eligibility), "eligible": eligible, "ineligible": len(eligibility) - eligible}


def _adapt_lesson(source):
    unit = source.learning_target
    plan = getattr(unit, "study_plan", None)
    completion = list(plan.completion_criteria) if plan else []
    sections = []
    for item in source.sections.all():
        guidance = _guidance(item.section_type)
        sections.append({
            "section_type": item.section_type,
            "title": item.title,
            "content": f"{guidance}\n\n{item.content}" if guidance else item.content,
            "metadata": {**item.metadata, "adapted_for": "STUDENT", "source_section_id": item.pk, "requires_human_publication": True},
        })
    if completion:
        sections.append({
            "section_type": DidacticLessonSection.SectionType.MASTERY_CRITERIA,
            "title": "Critérios de conclusão",
            "content": "Conclua esta aula quando conseguir:\n" + "\n".join(f"- {criterion}" for criterion in completion),
            "metadata": {"adapted_for": "STUDENT", "derived_from": "study_plan", "does_not_grant_mastery": True},
        })
    existing_student = DidacticLesson.objects.filter(origin_lesson=source).only("id", "origin_updated_at").first()
    return {
        "source_lesson_id": source.pk, "source_updated_at": source.updated_at.isoformat(),
        "unit_id": unit.pk, "module_id": unit.module_id, "title": source.title,
        "audience": "STUDENT", "sections": sections,
        "existing_student_lesson_id": existing_student.pk if existing_student else None,
        "student_is_stale": bool(existing_student and existing_student.origin_updated_at != source.updated_at),
        "adaptation": {"profile": "guided-student-v1", "human_publication_required": True, "does_not_grant_mastery": True},
    }


def _guidance(section_type):
    return {
        "PREREQUISITES": "Antes de avançar, confirme cada pré-requisito e registre dúvidas.",
        "CONCEPT": "Leia buscando explicar o conceito com suas próprias palavras.",
        "EXAMPLE": "Analise o exemplo e identifique as decisões tomadas.",
        "GUIDED_PRACTICE": "Execute cada passo, valide o resultado e anote o que mudou.",
        "EXERCISE": "Resolva antes de consultar uma resposta e justifique sua estratégia.",
        "AUTHORSHIP_CHALLENGE": "Produza uma resposta autoral; esta atividade não concede domínio automaticamente.",
        "PROJECT": "Construa o artefato incrementalmente e valide-o pelos critérios apresentados.",
        "REFLECTION": "Registre o que aprendeu, o que ainda precisa testar e como ensinaria este ponto.",
    }.get(section_type, "")
