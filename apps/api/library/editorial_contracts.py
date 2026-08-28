import json
import re
from copy import deepcopy
from uuid import UUID, uuid4


PROJECT_TYPES = ("youtube", "premium")

AI_PEDAGOGY_POLICY = {
    "principle": "A IA é amplificador cognitivo e nunca substitui o raciocínio do aluno.",
    "learning_sequence": [
        "understand_problem", "reason_first", "structure_hypotheses", "use_ai_as_partner",
        "critically_review", "technically_validate", "implement", "explain_in_own_words",
    ],
    "lesson_dimensions": [
        "human_reasoning", "ai_assistance", "validation", "reflection", "without_ai_challenge",
    ],
    "must_not_delegate": [
        "fundamentals", "critical_thinking", "problem_formulation", "decision_making",
        "validation", "understanding",
    ],
}

LEARNING_METHOD = {
    "name": "Aprender → Fazer → Ensinar",
    "cycle": ["learn", "practice", "build", "explain", "share_optionally", "receive_feedback", "improve_kaizen"],
}

AUTHORSHIP_CHALLENGE_SCHEMA = {
    "required_fields": [
        "independent_explanation", "practical_challenge", "portfolio_artifact",
        "reflection_question", "comprehension_criteria", "responsible_ai_use",
        "must_not_delegate_to_ai", "expected_result", "private_submission_option",
    ],
    "optional_fields": ["publication_suggestion", "suggested_channels"],
    "social_publication_required": False,
    "supported_channels": ["ddj_community", "linkedin", "instagram", "youtube", "github"],
}

EVIDENCE_POLICY = {
    "bibliographic_foundation": "Library, BookChunk e citações RAG fundamentam conceitos.",
    "current_technology_stack": "Versões e práticas atuais exigem fontes recentes; pesquisa externa não ocorre neste marco.",
    "old_source_is_not_current_stack_evidence": True,
}

EDITORIAL_CONTRACTS = {
    "youtube": {
        "label": "Trilha YouTube",
        "plan_required_fields": [
            "title", "objective", "target_audience", "level", "prerequisites",
            "playlist_description", "competencies", "tools", "video_count",
            "estimated_total_duration", "sources", "videos",
            "ai_policy",
        ],
        "content_collection": "videos",
        "content_required_fields": [
            "order", "theme", "title", "objective", "concepts", "tools",
            "practical_demo", "practice", "code", "exercise", "ai_integration", "human_reasoning",
            "validation", "reflection", "without_ai_challenge", "authorship_challenge", "rag_sources",
        ],
        "future_production_fields": [
            "hook", "script", "cta", "seo_title", "youtube_description",
            "timestamps", "thumbnail", "keywords",
        ],
    },
    "premium": {
        "label": "Formação Premium",
        "plan_required_fields": [
            "title", "general_objective", "professional_objective", "specific_objectives",
            "target_audience", "level", "prerequisites", "total_workload", "competencies",
            "technology_stack", "module_count", "lesson_count", "methodology", "modules",
            "practical_projects", "final_project", "assessment_criteria", "materials",
            "completion_requirements", "certification_requirements", "sources",
            "ai_policy",
        ],
        "content_collection": "modules",
        "content_required_fields": [
            "title", "objective", "competencies", "workload", "lessons", "exercises",
            "kata", "practical_project", "assessment",
        ],
        "lesson_required_fields": [
            "objective", "concepts", "practice", "tools", "ai_integration",
            "human_reasoning", "validation", "reflection", "authorship_challenge",
            "without_ai_challenge", "sources", "expected_result",
        ],
    },
}


def get_editorial_contract(project_type: str) -> dict:
    if project_type not in EDITORIAL_CONTRACTS:
        raise ValueError("Tipo editorial inválido.")
    contract = deepcopy(EDITORIAL_CONTRACTS[project_type])
    contract["ai_pedagogy_policy"] = deepcopy(AI_PEDAGOGY_POLICY)
    contract["learning_method"] = deepcopy(LEARNING_METHOD)
    contract["authorship_challenge"] = deepcopy(AUTHORSHIP_CHALLENGE_SCHEMA)
    contract["evidence_policy"] = deepcopy(EVIDENCE_POLICY)
    return contract


def validate_editorial_plan(project_type: str, payload: dict, previous_plan: dict | None = None) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("O plano editorial deve ser um objeto JSON.")
    contract = get_editorial_contract(project_type)
    missing = set(contract["plan_required_fields"]) - payload.keys()
    if missing:
        raise ValueError(f"Campos obrigatórios ausentes: {sorted(missing)}")
    string_fields = ["title", "level", "target_audience", "ai_policy"]
    string_fields += ["objective", "playlist_description", "estimated_total_duration"] if project_type == "youtube" else ["general_objective", "professional_objective", "total_workload", "methodology", "final_project", "completion_requirements", "certification_requirements"]
    _require_non_empty_strings(payload, string_fields, "Plano editorial")
    list_fields = ["prerequisites", "competencies", "sources"]
    list_fields += ["tools"] if project_type == "youtube" else ["specific_objectives", "technology_stack", "practical_projects", "assessment_criteria", "materials"]
    _require_non_empty_lists(payload, list_fields, "Plano editorial")
    collection = payload[contract["content_collection"]]
    if not isinstance(collection, list) or not collection:
        raise ValueError(f"{contract['content_collection']} deve ser uma lista não vazia.")
    _reconcile_editorial_ids(project_type, collection, previous_plan or {})
    required = set(contract["content_required_fields"])
    seen_editorial_ids = set()
    for item in collection:
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError("Item editorial incompleto.")
        _claim_editorial_id(item, seen_editorial_ids)
        _require_non_empty_strings(item, ["title", "objective"], "Item editorial")
        if project_type == "premium":
            _require_non_empty_strings(item, ["workload"], "MÃ³dulo editorial")
            _require_non_empty_lists(item, ["competencies", "exercises"], "MÃ³dulo editorial")
            _require_present_content(item, ["kata", "practical_project", "assessment"], "MÃ³dulo editorial")
        lessons = [item] if project_type == "youtube" else item["lessons"]
        if not isinstance(lessons, list) or not lessons:
            raise ValueError("O item editorial deve conter aulas.")
        lesson_required = set(contract.get("lesson_required_fields", contract["content_required_fields"]))
        challenge_required = set(AUTHORSHIP_CHALLENGE_SCHEMA["required_fields"])
        for lesson in lessons:
            if not isinstance(lesson, dict) or not lesson_required.issubset(lesson):
                raise ValueError("Aula editorial incompleta.")
            if project_type != "youtube":
                _claim_editorial_id(lesson, seen_editorial_ids)
            _require_non_empty_strings(lesson, ["title", "objective", "ai_integration", "human_reasoning", "validation", "reflection", "without_ai_challenge"], "Aula editorial")
            _require_non_empty_lists(lesson, ["concepts", "tools"], "Aula editorial")
            if project_type == "youtube":
                _require_non_empty_strings(lesson, ["theme", "practical_demo", "practice", "exercise"], "VÃ­deo editorial")
                _require_non_empty_lists(lesson, ["rag_sources"], "VÃ­deo editorial")
                order = lesson.get("order")
                if not isinstance(order, int) or isinstance(order, bool) or order < 0:
                    raise ValueError("A ordem do vÃ­deo deve ser um inteiro nÃ£o negativo.")
            else:
                _require_non_empty_strings(lesson, ["practice", "expected_result"], "Aula editorial")
                _require_non_empty_lists(lesson, ["sources"], "Aula editorial")
            challenge = lesson["authorship_challenge"]
            if not isinstance(challenge, dict) or not challenge_required.issubset(challenge):
                raise ValueError("Desafio de Autoria incompleto.")
            _require_non_empty_strings(challenge, challenge_required, "Desafio de Autoria")
    if project_type == "premium":
        _require_count(payload, "module_count", len(collection))
        _require_count(payload, "lesson_count", sum(len(module["lessons"]) for module in collection))
    else:
        _require_count(payload, "video_count", len(collection))
    return payload


def _reconcile_editorial_ids(project_type: str, collection: list, previous_plan: dict):
    """Preserve identity only for deterministic, unambiguous structural matches."""
    previous_collection = previous_plan.get("videos" if project_type == "youtube" else "modules", [])
    historical_editorial_ids = _historical_editorial_ids(project_type, previous_collection)
    used = set()
    for index, item in enumerate(collection):
        previous_item = _match_previous(item, index, previous_collection, used)
        item["editorial_id"] = _safe_editorial_id(
            item.get("editorial_id"), previous_item, used, historical_editorial_ids
        )
        used.add(item["editorial_id"])
        if project_type == "premium":
            previous_lessons = previous_item.get("lessons", []) if previous_item else []
            for lesson_index, lesson in enumerate(item.get("lessons", [])):
                previous_lesson = _match_previous(lesson, lesson_index, previous_lessons, used)
                lesson["editorial_id"] = _safe_editorial_id(
                    lesson.get("editorial_id"), previous_lesson, used, historical_editorial_ids
                )
                used.add(lesson["editorial_id"])


def _historical_editorial_ids(project_type: str, collection: list) -> set[str]:
    historical = set()
    for item in collection:
        editorial_id = _valid_editorial_id(item.get("editorial_id"))
        if editorial_id:
            historical.add(editorial_id)
        if project_type == "premium":
            for lesson in item.get("lessons", []):
                lesson_id = _valid_editorial_id(lesson.get("editorial_id"))
                if lesson_id:
                    historical.add(lesson_id)
    return historical


def _match_previous(item: dict, index: int, candidates: list, used: set) -> dict | None:
    title = _normalized_title(item.get("title", ""))
    if index < len(candidates):
        candidate = candidates[index]
        if _normalized_title(candidate.get("title", "")) == title and _valid_editorial_id(candidate.get("editorial_id")) not in used:
            return candidate
    matches = [candidate for candidate in candidates if _normalized_title(candidate.get("title", "")) == title and _valid_editorial_id(candidate.get("editorial_id")) not in used]
    return matches[0] if len(matches) == 1 else None


def _safe_editorial_id(value, previous: dict | None, used: set, historical_editorial_ids: set) -> str:
    explicit = _valid_editorial_id(value)
    previous_id = _valid_editorial_id(previous.get("editorial_id")) if previous else None
    if explicit and previous_id and explicit == previous_id and explicit not in used:
        return explicit
    if previous_id and previous_id not in used:
        return previous_id
    if explicit and explicit not in used and explicit not in historical_editorial_ids:
        return explicit
    return str(uuid4())


def _valid_editorial_id(value) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = UUID(value.strip())
    except (ValueError, AttributeError):
        return None
    return str(parsed) if parsed.version == 4 else None


def _normalized_title(value) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold()) if isinstance(value, str) else ""


def _claim_editorial_id(item: dict, seen: set):
    editorial_id = _valid_editorial_id(item.get("editorial_id"))
    if not editorial_id or editorial_id in seen:
        raise ValueError("Identidade editorial invÃ¡lida ou duplicada apÃ³s normalizaÃ§Ã£o.")
    item["editorial_id"] = editorial_id
    seen.add(editorial_id)


def _require_non_empty_strings(payload: dict, fields, label: str):
    invalid = [field for field in fields if not isinstance(payload.get(field), str) or not payload[field].strip()]
    if invalid:
        raise ValueError(f"{label}: textos obrigatÃ³rios invÃ¡lidos: {sorted(invalid)}")


def _require_non_empty_lists(payload: dict, fields, label: str):
    invalid = [field for field in fields if not isinstance(payload.get(field), list) or not payload[field]]
    if invalid:
        raise ValueError(f"{label}: listas obrigatÃ³rias invÃ¡lidas: {sorted(invalid)}")


def _require_count(payload: dict, field: str, actual: int):
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value != actual:
        raise ValueError(f"{field} deve ser um inteiro nÃ£o negativo igual a {actual}.")


def _require_present_content(payload: dict, fields, label: str):
    invalid = [field for field in fields if payload.get(field) in (None, "", [], {})]
    if invalid:
        raise ValueError(f"{label}: conteÃºdo obrigatÃ³rio invÃ¡lido: {sorted(invalid)}")


def editorial_prompt_context(project_type: str) -> str:
    return json.dumps(get_editorial_contract(project_type), ensure_ascii=False)
