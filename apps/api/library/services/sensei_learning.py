import json
import os

from django.db import transaction
from django.utils import timezone

from ai.agent_registry import get_agent
from ai.services import AIProviderError, available_sensei_providers, canonical_provider_name, chat_with_provider, get_provider_model, provider_is_available
from library.models import SenseiCompetencyProgress, SenseiLearningActivity, SenseiLearningAttempt, SenseiLearningProviderPreference, SenseiUnitSource

ACTIVITY_SCHEMA = {
    "type": "object",
    "properties": {
        "activity_type": {"type": "string", "enum": [choice for choice, _ in SenseiLearningActivity.ActivityType.choices]},
        "prompt": {"type": "string"},
    },
    "required": ["activity_type", "prompt"],
    "additionalProperties": False,
}
FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "feedback": {"type": "string"},
        "gap_type": {"type": "string"},
        "outcome": {"type": "string", "enum": ["RETRY", "DEEPEN", "EVIDENCE_CANDIDATE"]},
        "next_activity_suggestion": {"type": "string"},
    },
    "required": ["feedback", "gap_type", "outcome", "next_activity_suggestion"],
    "additionalProperties": False,
}


class SenseiLearningError(RuntimeError):
    pass


def _configured_provider_names():
    agent = get_agent("sensei")
    return (
        os.getenv(agent["provider_env"], "").strip().lower(),
        os.getenv("AI_DEFAULT_PROVIDER", "").strip().lower(),
        agent["default_provider"],
    )


def available_providers():
    return available_sensei_providers()


def resolve_provider(user, formation):
    preference = SenseiLearningProviderPreference.objects.filter(user=user, formation=formation).first()
    candidates = ([preference.provider] if preference else []) + list(_configured_provider_names())
    for candidate in candidates:
        provider = canonical_provider_name(candidate)
        if provider and provider_is_available(provider):
            return provider, get_provider_model(provider), "preference" if preference and candidate == preference.provider else "default"
    raise SenseiLearningError("Nenhum provedor de IA configurado está disponível para esta formação.")


def _parse_json(raw, provider):
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AIProviderError("invalid_response", provider) from exc
    if not isinstance(value, dict):
        raise AIProviderError("invalid_response", provider)
    return value


def build_context(unit, user, competency=None):
    plan = getattr(unit, "study_plan", None)
    if plan is None:
        raise SenseiLearningError("A unidade não possui plano de estudo configurado.")
    competency = competency or plan.related_competencies.order_by("order", "id").first()
    if competency is None:
        raise SenseiLearningError("A unidade não possui competência relacionada.")
    progress = SenseiCompetencyProgress.objects.filter(user=user, competency=competency).first()
    sources = unit.curated_sources.filter(editorial_status=SenseiUnitSource.EditorialStatus.APPROVED).order_by("priority", "id")
    history = []
    for activity in unit.learning_activities.filter(user=user).prefetch_related("attempts").order_by("created_at", "id")[:20]:
        history.append({
            "activity_type": activity.activity_type,
            "prompt": activity.prompt,
            "state": activity.state,
            "attempts": [{"attempt_number": attempt.attempt_number, "answer": attempt.answer, "feedback": attempt.feedback, "outcome": attempt.outcome, "identified_gap": attempt.identified_gap, "next_step": attempt.next_step} for attempt in activity.attempts.all()],
        })
    return {
        "formation": unit.module.formation.title,
        "module": unit.module.title,
        "unit": unit.title,
        "unit_objective": unit.objective,
        "learning_objectives": plan.learning_objectives,
        "competency": {"id": competency.id, "title": competency.title, "description": competency.description, "mastery_criteria": competency.mastery_criteria},
        "current_level": progress.current_level if progress else 0,
        "expected_level": competency.expected_level,
        "practices": plan.practices,
        "completion_criteria": plan.completion_criteria,
        "approved_sources": [{"title": source.title, "reference": source.reference, "location": source.location, "objective": source.objective, "priority": source.priority, "required": source.is_required} for source in sources],
        "history": history,
    }, competency


def generate_activity(unit, user, competency=None):
    context, competency = build_context(unit, user, competency)
    provider, model, _ = resolve_provider(user, unit.module.formation)
    messages = [
        {"role": "system", "content": "Você é um motor pedagógico. Gere uma atividade, não uma aula nem a solução. Use somente o contexto fornecido e nunca invente referências bibliográficas."},
        {"role": "user", "content": "Gere uma atividade progressiva para o Sensei tentar antes de receber ajuda. Contexto confiável:\n" + json.dumps(context, ensure_ascii=False)},
    ]
    data = _parse_json(chat_with_provider(provider, messages, response_schema=ACTIVITY_SCHEMA), provider)
    if data.get("activity_type") not in SenseiLearningActivity.ActivityType.values or not str(data.get("prompt", "")).strip():
        raise AIProviderError("invalid_response", provider)
    return SenseiLearningActivity.objects.create(
        user=user, unit=unit, competency=competency, activity_type=data["activity_type"],
        prompt=data["prompt"].strip(), difficulty_level=max(1, min(context["current_level"] + 1, context["expected_level"])),
        pedagogical_context=context, ai_provider=provider, ai_model=model,
    )


@transaction.atomic
def review_response(activity, response):
    # Load the optional study plan separately: PostgreSQL cannot lock an outer join.
    activity = SenseiLearningActivity.objects.select_for_update().select_related("unit", "competency").prefetch_related("unit__study_plan").get(pk=activity.pk)
    provider, model, _ = resolve_provider(activity.user, activity.unit.module.formation)
    previous_attempts = list(activity.attempts.order_by("attempt_number", "id"))
    progress = SenseiCompetencyProgress.objects.filter(user=activity.user, competency=activity.competency).first()
    approved_sources = activity.unit.curated_sources.filter(editorial_status=SenseiUnitSource.EditorialStatus.APPROVED).order_by("priority", "id")
    evaluation_context = {
        "original_context": activity.pedagogical_context,
        "competency": {"title": activity.competency.title, "mastery_criteria": activity.competency.mastery_criteria},
        "current_level": progress.current_level if progress else 0,
        "approved_sources": [{"title": source.title, "reference": source.reference, "location": source.location, "objective": source.objective} for source in approved_sources],
        "previous_attempts": [{"attempt_number": item.attempt_number, "answer": item.answer, "feedback": item.feedback, "outcome": item.outcome, "identified_gap": item.identified_gap, "next_step": item.next_step} for item in previous_attempts],
    }
    messages = [
        {"role": "system", "content": "Avalie pedagogicamente sem declarar domínio. Não entregue imediatamente a solução completa; identifique lacuna, dê pista e proponha nova tentativa ou aprofundamento. EVIDENCE_CANDIDATE nunca significa evidência validada."},
        {"role": "user", "content": json.dumps({"context": evaluation_context, "original_activity": activity.prompt, "new_attempt": response, "instruction": "Compare a nova tentativa com o histórico e reconheça evolução quando houver."}, ensure_ascii=False)},
    ]
    data = _parse_json(chat_with_provider(provider, messages, response_schema=FEEDBACK_SCHEMA), provider)
    if not str(data.get("feedback", "")).strip() or data.get("outcome") not in {"RETRY", "DEEPEN", "EVIDENCE_CANDIDATE"}:
        raise AIProviderError("invalid_response", provider)
    now = timezone.now()
    SenseiLearningAttempt.objects.create(
        activity=activity,
        user=activity.user,
        attempt_number=len(previous_attempts) + 1,
        answer=response,
        feedback=data["feedback"].strip(),
        outcome=data["outcome"],
        identified_gap=data.get("gap_type", ""),
        next_step=data.get("next_activity_suggestion", ""),
        metadata={"difficulty_level": activity.difficulty_level}, ai_provider=provider, ai_model=model,
    )
    update_fields = ["state", "updated_at"]
    if not activity.learner_response:
        activity.learner_response = response
        activity.feedback = data["feedback"].strip()
        activity.feedback_metadata = {"gap_type": data.get("gap_type", ""), "outcome": data["outcome"], "next_activity_suggestion": data.get("next_activity_suggestion", "")}
        activity.answered_at = now
        activity.reviewed_at = now
        update_fields.extend(["learner_response", "feedback", "feedback_metadata", "answered_at", "reviewed_at"])
    activity.state = SenseiLearningActivity.State.REVIEWED
    activity.save(update_fields=update_fields)
    return activity
