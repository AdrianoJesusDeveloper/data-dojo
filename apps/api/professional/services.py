import json
import logging
import os

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from library.models import SenseiCompetency
from library.serializers import SenseiCompetencyEvidenceSerializer

from .models import OpportunityExecutionArtifact, OpportunityExecutionEvidenceLink

from ai.agent_registry import get_agent
from ai.services import AIProviderError, agent_runtime_status, chat_with_provider, get_provider_model

logger = logging.getLogger("professional")


@transaction.atomic
def submit_execution_artifacts_as_competency_evidence(
    *, user, artifact_ids, competency, evidence_type, demonstrated_level,
    description, content="", reference_url="",
):
    artifact_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False,
    ).run_validation(artifact_ids)
    artifact_ids = list(dict.fromkeys(artifact_ids))
    artifacts = list(OpportunityExecutionArtifact.objects.filter(
        pk__in=artifact_ids, created_by=user, opportunity__created_by=user,
    ))
    if len(artifacts) != len(artifact_ids):
        raise NotFound("Artefatos não encontrados.")
    competency = SenseiCompetency.objects.filter(
        Q(formation__created_by=user) | Q(formation__created_by__isnull=True),
        pk=competency.pk,
    ).first()
    if competency is None:
        raise NotFound("Competência não encontrada.")
    serializer = SenseiCompetencyEvidenceSerializer(data={
        "evidence_type": evidence_type,
        "description": description,
        "content": content,
        "reference_url": reference_url,
        "demonstrated_level": demonstrated_level,
    })
    serializer.is_valid(raise_exception=True)
    evidence = serializer.save(competency=competency, submitted_by=user)
    for artifact in artifacts:
        OpportunityExecutionEvidenceLink.objects.create(artifact=artifact, evidence=evidence)
    return evidence


NARRATIVE_FIELDS = ("problem", "objective", "target_audience")
LIST_FIELDS = (
    "deliverables", "functional_requirements", "non_functional_requirements",
    "integrations", "data_requirements", "infrastructure_requirements", "constraints",
    "dependencies", "assumptions", "scope_risks", "ambiguities", "client_questions",
    "acceptance_criteria",
)
EXPECTED_FIELDS = NARRATIVE_FIELDS + LIST_FIELDS


class InvalidBriefingResponse(ValueError):
    pass


class InvalidProfessionalResponse(ValueError):
    pass


def configured_briefing_provider():
    explicit = os.getenv("PROFESSIONAL_BRIEFING_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    return agent_runtime_status(get_agent("data"))["provider"]


def validate_briefing_payload(raw_response):
    try:
        payload = json.loads(raw_response)
    except (TypeError, json.JSONDecodeError) as exc:
        raise InvalidBriefingResponse("invalid_json") from exc
    if not isinstance(payload, dict) or set(payload) != set(EXPECTED_FIELDS):
        raise InvalidBriefingResponse("invalid_schema")
    if any(not isinstance(payload[field], str) for field in NARRATIVE_FIELDS):
        raise InvalidBriefingResponse("invalid_narrative")
    if any(not isinstance(payload[field], list) or any(not isinstance(item, str) for item in payload[field]) for field in LIST_FIELDS):
        raise InvalidBriefingResponse("invalid_list")
    return {field: payload[field] for field in EXPECTED_FIELDS}


def generate_intelligent_briefing(opportunity, additional_context=""):
    provider = configured_briefing_provider()
    system_prompt = """Você é um analista profissional de requisitos. Transforme o texto fornecido em JSON estrito, sem markdown, com exatamente estas chaves: problem, objective, target_audience, deliverables, functional_requirements, non_functional_requirements, integrations, data_requirements, infrastructure_requirements, constraints, dependencies, assumptions, scope_risks, ambiguities, client_questions, acceptance_criteria. problem, objective e target_audience são strings. Todos os outros campos são listas de strings. Extraia somente fatos sustentados pelo texto. Não apresente inferências como requisitos confirmados. Registre incertezas em ambiguities, inferências apenas em assumptions e informações ausentes relevantes como perguntas em client_questions. Use listas vazias e strings vazias quando não houver evidência."""
    user_prompt = f"Título: {opportunity.title}\nDescrição bruta:\n{opportunity.description.strip()}"
    if opportunity.modalities.exists():
        user_prompt += "\nModalidades informadas: " + ", ".join(opportunity.modalities.values_list("name", flat=True))
    if additional_context:
        user_prompt += f"\nContexto adicional fornecido pelo usuário:\n{additional_context.strip()}"
    raw_response = chat_with_provider(provider, [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    return validate_briefing_payload(raw_response), provider, get_provider_model(provider)


ANALYSIS_FIELDS = {
    "decision", "score", "problem_summary", "client_need", "likely_deliverables",
    "technologies", "required_competencies", "complexity", "technical_risks",
    "commercial_risks", "ambiguities", "missing_information", "client_questions",
    "external_dependencies", "estimated_deadline", "estimated_effort", "ai_execution_fit",
    "competency_gap", "score_breakdown", "pricing", "limitations",
}
ANALYSIS_LIST_FIELDS = {
    "likely_deliverables", "technologies", "required_competencies", "technical_risks",
    "commercial_risks", "ambiguities", "missing_information", "client_questions",
    "external_dependencies", "limitations",
}


def _object_schema(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


STRING_SCHEMA = {"type": "string"}
STRING_LIST_SCHEMA = {"type": "array", "items": STRING_SCHEMA}
ANALYSIS_RESPONSE_SCHEMA = _object_schema({
    "decision": {"type": "string", "enum": ["GO", "CAUTION", "NO_GO"]},
    "score": {"type": "integer", "minimum": 0, "maximum": 100},
    "problem_summary": STRING_SCHEMA, "client_need": STRING_SCHEMA,
    "likely_deliverables": STRING_LIST_SCHEMA, "technologies": STRING_LIST_SCHEMA,
    "required_competencies": STRING_LIST_SCHEMA, "complexity": STRING_SCHEMA,
    "technical_risks": STRING_LIST_SCHEMA, "commercial_risks": STRING_LIST_SCHEMA,
    "ambiguities": STRING_LIST_SCHEMA, "missing_information": STRING_LIST_SCHEMA,
    "client_questions": STRING_LIST_SCHEMA, "external_dependencies": STRING_LIST_SCHEMA,
    "estimated_deadline": STRING_SCHEMA,
    "estimated_effort": _object_schema({
        "minimum": STRING_SCHEMA, "probable": STRING_SCHEMA, "with_margin": STRING_SCHEMA,
        "suggested_deadline": STRING_SCHEMA, "schedule_risks": STRING_LIST_SCHEMA,
    }),
    "ai_execution_fit": STRING_SCHEMA,
    "competency_gap": _object_schema({
        "can_execute": STRING_LIST_SCHEMA, "with_ai_support": STRING_LIST_SCHEMA,
        "study_first": STRING_LIST_SCHEMA, "do_not_assume": STRING_LIST_SCHEMA,
    }),
    "score_breakdown": _object_schema({
        "scope_clarity": {"type": "integer", "minimum": 0},
        "technical_domain": {"type": "integer", "minimum": 0},
        "risk": {"type": "integer", "minimum": 0},
        "deadline": {"type": "integer", "minimum": 0},
        "dependencies": {"type": "integer", "minimum": 0},
        "validation": {"type": "integer", "minimum": 0},
        "ai_fit": {"type": "integer", "minimum": 0},
    }),
    "pricing": _object_schema({
        "insufficient_data": {"type": "boolean"}, "suggested_range": STRING_SCHEMA,
        "minimum_recommended": STRING_SCHEMA, "target": STRING_SCHEMA,
        "justification": STRING_SCHEMA, "change_factors": STRING_LIST_SCHEMA,
    }),
    "limitations": STRING_LIST_SCHEMA,
})


def _strict_object(raw_response, expected_fields):
    try:
        payload = json.loads(raw_response)
    except (TypeError, json.JSONDecodeError) as exc:
        raise InvalidProfessionalResponse("invalid_json") from exc
    if not isinstance(payload, dict) or set(payload) != set(expected_fields):
        raise InvalidProfessionalResponse("invalid_schema")
    return payload


def validate_analysis_payload(raw_response):
    payload = _strict_object(raw_response, ANALYSIS_FIELDS)
    if payload["decision"] not in {"GO", "CAUTION", "NO_GO"}:
        raise InvalidProfessionalResponse("invalid_decision")
    if type(payload["score"]) is not int or not 0 <= payload["score"] <= 100:
        raise InvalidProfessionalResponse("invalid_score")
    if any(not isinstance(payload[field], list) or any(not isinstance(item, str) for item in payload[field]) for field in ANALYSIS_LIST_FIELDS):
        raise InvalidProfessionalResponse("invalid_lists")
    for field in ("estimated_effort", "competency_gap", "score_breakdown", "pricing"):
        if not isinstance(payload[field], dict):
            raise InvalidProfessionalResponse(f"invalid_{field}")
    expected_score = {"scope_clarity", "technical_domain", "risk", "deadline", "dependencies", "validation", "ai_fit"}
    if set(payload["score_breakdown"]) != expected_score or any(type(value) is not int or value < 0 for value in payload["score_breakdown"].values()):
        raise InvalidProfessionalResponse("invalid_score_breakdown")
    calculated_score = sum(payload["score_breakdown"].values())
    if not 0 <= calculated_score <= 100:
        raise InvalidProfessionalResponse("invalid_score_breakdown_total")
    if payload["score"] != calculated_score:
        logger.info(
            "OpportunityAnalysis score normalizado pelo servidor: provider_score=%s calculated_score=%s",
            payload["score"],
            calculated_score,
        )
    payload["score"] = calculated_score
    expected_gap = {"can_execute", "with_ai_support", "study_first", "do_not_assume"}
    if set(payload["competency_gap"]) != expected_gap or any(not isinstance(payload["competency_gap"][key], list) for key in expected_gap):
        raise InvalidProfessionalResponse("invalid_competency_gap")
    expected_effort = {"minimum", "probable", "with_margin", "suggested_deadline", "schedule_risks"}
    if set(payload["estimated_effort"]) != expected_effort or not isinstance(payload["estimated_effort"]["schedule_risks"], list):
        raise InvalidProfessionalResponse("invalid_effort")
    expected_pricing = {"insufficient_data", "suggested_range", "minimum_recommended", "target", "justification", "change_factors"}
    if set(payload["pricing"]) != expected_pricing or type(payload["pricing"]["insufficient_data"]) is not bool or not isinstance(payload["pricing"]["change_factors"], list):
        raise InvalidProfessionalResponse("invalid_pricing")
    if not payload["limitations"]:
        payload["limitations"] = ["A análise não utiliza uma matriz persistente de competências; exige revisão humana."]
    return payload


def generate_opportunity_analysis(opportunity):
    provider = configured_briefing_provider()
    model = get_provider_model(provider)
    logger.info("OpportunityAnalysis iniciada: provider=%s model=%s phase=provider_call", provider, model)
    system_prompt = """Você analisa oportunidades freelancer. Retorne JSON estrito, sem markdown, com exatamente: decision, score, problem_summary, client_need, likely_deliverables, technologies, required_competencies, complexity, technical_risks, commercial_risks, ambiguities, missing_information, client_questions, external_dependencies, estimated_deadline, estimated_effort, ai_execution_fit, competency_gap, score_breakdown, pricing, limitations. decision: GO, CAUTION ou NO_GO. score: inteiro 0-100 explicável por score_breakdown. Campos plurais principais são listas de strings. estimated_effort tem exatamente minimum, probable, with_margin, suggested_deadline, schedule_risks. competency_gap tem exatamente can_execute, with_ai_support, study_first, do_not_assume, todos listas. pricing tem exatamente insufficient_data (boolean), suggested_range, minimum_recommended, target, justification, change_factors (lista). Não finja conhecer competências do usuário. Registre essa limitação. Não invente fatos, experiência, orçamento ou precisão. Quando faltarem dados, sinalize explicitamente."""
    user_prompt = _opportunity_context(opportunity)
    raw = chat_with_provider(
        provider,
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        response_schema=ANALYSIS_RESPONSE_SCHEMA,
    )
    try:
        payload = validate_analysis_payload(raw)
    except InvalidProfessionalResponse as error:
        logger.warning(
            "OpportunityAnalysis rejeitada: provider=%s model=%s phase=validation code=%s",
            provider,
            model,
            str(error),
        )
        raise
    logger.info("OpportunityAnalysis concluída: provider=%s model=%s phase=persist_ready", provider, model)
    return payload, provider, model


PROPOSAL_FIELDS = {"greeting", "understanding", "approach", "deliverables", "deadline", "suggested_price", "currency", "essential_questions", "differentiators", "closing"}
PROPOSAL_RESPONSE_SCHEMA = _object_schema({
    "greeting": STRING_SCHEMA,
    "understanding": STRING_SCHEMA,
    "approach": STRING_SCHEMA,
    "deliverables": STRING_LIST_SCHEMA,
    "deadline": STRING_SCHEMA,
    "suggested_price": {"type": ["number", "null"], "minimum": 0},
    "currency": STRING_SCHEMA,
    "essential_questions": STRING_LIST_SCHEMA,
    "differentiators": STRING_LIST_SCHEMA,
    "closing": STRING_SCHEMA,
})


def validate_proposal_payload(raw_response):
    payload = _strict_object(raw_response, PROPOSAL_FIELDS)
    for field in ("deliverables", "essential_questions", "differentiators"):
        if not isinstance(payload[field], list) or any(not isinstance(item, str) for item in payload[field]):
            raise InvalidProfessionalResponse("invalid_proposal_lists")
    if payload["suggested_price"] is not None and (type(payload["suggested_price"]) not in {int, float} or payload["suggested_price"] < 0):
        raise InvalidProfessionalResponse("invalid_price")
    if not isinstance(payload["currency"], str) or len(payload["currency"]) != 3:
        raise InvalidProfessionalResponse("invalid_currency")
    return payload


def generate_opportunity_proposal(opportunity, analysis, version):
    provider = configured_briefing_provider()
    model = get_provider_model(provider)
    logger.info(
        "OpportunityProposal iniciada: provider=%s model=%s version=%s phase=provider_call",
        provider,
        model,
        version,
    )
    system_prompt = f"""Crie uma proposta comercial {version} para uma oportunidade freelancer. Retorne JSON estrito com exatamente: greeting, understanding, approach, deliverables, deadline, suggested_price, currency, essential_questions, differentiators, closing. Listas: deliverables, essential_questions, differentiators. suggested_price deve ser número ou null. Demonstre entendimento concreto usando somente a oportunidade e a análise fornecidas. Não invente nem insinue experiência profissional do usuário, clientes anteriores, certificações, cases, portfólio, resultados, métricas, formação ou qualquer informação inexistente sobre o usuário. Não afirme como certo o que é ambíguo. Se um diferencial pessoal não estiver sustentado pelos dados, use diferenciais da abordagem proposta, como validação incremental, comunicação e critérios de aceite. A proposta será DRAFT e revisada por humano."""
    context = _opportunity_context(opportunity) + "\nAnálise validada:\n" + json.dumps({
        "decision": analysis.decision, "problem_summary": analysis.problem_summary,
        "client_need": analysis.client_need, "likely_deliverables": analysis.likely_deliverables,
        "client_questions": analysis.client_questions, "pricing": analysis.pricing,
    }, ensure_ascii=False)
    raw = chat_with_provider(
        provider,
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": context}],
        response_schema=PROPOSAL_RESPONSE_SCHEMA,
    )
    try:
        payload = validate_proposal_payload(raw)
    except InvalidProfessionalResponse as error:
        logger.warning(
            "OpportunityProposal rejeitada: provider=%s model=%s version=%s phase=validation code=%s",
            provider,
            model,
            version,
            str(error),
        )
        raise
    logger.info(
        "OpportunityProposal concluída: provider=%s model=%s version=%s phase=persist_ready",
        provider,
        model,
        version,
    )
    return payload, provider, model


PLAN_FIELDS = {"project", "phases", "risks", "validation", "delivery"}
TASK_FIELDS = {"objective", "description", "dependencies", "tools", "expected_result", "validation", "ai_help", "human_validation"}


EXECUTION_PLAN_RESPONSE_SCHEMA = _object_schema({
    "project": STRING_SCHEMA,
    "phases": {
        "type": "array",
        "items": _object_schema({
            "name": STRING_SCHEMA,
            "acceptance_criteria": STRING_SCHEMA,
            "tasks": {
                "type": "array",
                "items": _object_schema({
                    "objective": STRING_SCHEMA,
                    "description": STRING_SCHEMA,
                    "dependencies": STRING_SCHEMA,
                    "tools": STRING_SCHEMA,
                    "expected_result": STRING_SCHEMA,
                    "validation": STRING_SCHEMA,
                    "ai_help": STRING_SCHEMA,
                    "human_validation": STRING_SCHEMA,
                }),
            },
        }),
    },
    "risks": STRING_LIST_SCHEMA,
    "validation": STRING_LIST_SCHEMA,
    "delivery": STRING_LIST_SCHEMA,
})



def validate_execution_plan_payload(raw_response):
    payload = _strict_object(raw_response, PLAN_FIELDS)
    if not isinstance(payload["phases"], list):
        raise InvalidProfessionalResponse("invalid_phases")
    for phase in payload["phases"]:
        if not isinstance(phase, dict) or set(phase) != {"name", "acceptance_criteria", "tasks"} or not isinstance(phase["tasks"], list):
            raise InvalidProfessionalResponse("invalid_phase")
        for task in phase["tasks"]:
            if not isinstance(task, dict) or set(task) != TASK_FIELDS:
                raise InvalidProfessionalResponse("invalid_task")
    for field in ("risks", "validation", "delivery"):
        if not isinstance(payload[field], list):
            raise InvalidProfessionalResponse("invalid_plan_lists")
    return payload


def generate_opportunity_execution_plan(opportunity, proposal):
    provider = configured_briefing_provider()
    model = get_provider_model(provider)
    system_prompt = """Crie um plano inicial de execução OBJETIVO E CONCISO e retorne JSON estrito com exatamente project, phases, risks, validation, delivery. phases é uma lista com no máximo 4 fases. Cada fase possui exatamente name, acceptance_criteria e tasks. Cada fase deve ter no máximo 4 tasks. Cada task possui exatamente objective, description, dependencies, tools, expected_result, validation, ai_help, human_validation. Use strings curtas e diretas, evitando explicações longas e repetição. risks, validation e delivery devem conter no máximo 5 itens cada. Não invente requisitos; transforme ambiguidades em validações. Explicite de forma breve onde IA ajuda e o que exige revisão humana."""
    retry_prompt = system_prompt + " IMPORTANTE: respeite exatamente o schema solicitado, sem chaves extras, sem omitir chaves e sem envolver o JSON em markdown."
    context = _opportunity_context(opportunity) + "\nProposta aprovada:\n" + json.dumps({
        "understanding": proposal.understanding, "approach": proposal.approach,
        "deliverables": proposal.deliverables, "deadline": proposal.deadline,
    }, ensure_ascii=False)

    logger.info(
        "OpportunityExecutionPlan iniciada: provider=%s model=%s phase=provider_call",
        provider,
        model,
    )

    for attempt, prompt in enumerate((system_prompt, retry_prompt), start=1):
        raw = chat_with_provider(
            provider,
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": context},
            ],
            response_schema=EXECUTION_PLAN_RESPONSE_SCHEMA,
        )
        try:
            payload = validate_execution_plan_payload(raw)
        except InvalidProfessionalResponse as error:
            logger.warning(
                "OpportunityExecutionPlan rejeitado: provider=%s model=%s attempt=%s phase=validation code=%s",
                provider,
                model,
                attempt,
                str(error),
            )
            if attempt == 2:
                raise
            continue

        logger.info(
            "OpportunityExecutionPlan concluído: provider=%s model=%s attempt=%s phase=persist_ready",
            provider,
            model,
            attempt,
        )
        return payload, provider, model


def _opportunity_context(opportunity):
    return json.dumps({
        "title": opportunity.title, "description": opportunity.description,
        "source": opportunity.source, "source_url": opportunity.source_url,
        "budget_min": str(opportunity.budget_min) if opportunity.budget_min is not None else None,
        "budget_max": str(opportunity.budget_max) if opportunity.budget_max is not None else None,
        "currency": opportunity.currency, "deadline": str(opportunity.deadline) if opportunity.deadline else None,
        "notes": opportunity.notes,
    }, ensure_ascii=False)
