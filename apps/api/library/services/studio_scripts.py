"""Recording contracts shared by generation and teleprompter exports."""
from library.editorial_contracts import AUTHORSHIP_CHALLENGE_SCHEMA, normalize_project_type


COMMON_FIELDS = {
    "title", "opening", "examples", "ai_usage", "human_reasoning", "validation",
    "reflection", "estimated_duration", "teleprompter_text", "authorship_challenge",
}
YOUTUBE_FIELDS = COMMON_FIELDS | {
    "hook", "promise", "context", "sections", "transitions", "practical_demo",
    "code_demo", "cta", "closing",
}
PREMIUM_FIELDS = COMMON_FIELDS | {
    "learning_objectives", "prerequisites", "explanation_blocks", "demonstration",
    "guided_practice", "exercise", "common_mistakes", "summary", "next_lesson_bridge",
}


def recording_fields(project_type):
    semantic_project_type = normalize_project_type(project_type)
    return PREMIUM_FIELDS if semantic_project_type == "formation" else YOUTUBE_FIELDS


def spoken_text(content):
    text = content.get("teleprompter_text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("O roteiro precisa de teleprompter_text falável; gere um novo roteiro.")
    text = text.strip()
    if text.startswith(("{", "[", "```")):
        raise ValueError("O teleprompter deve conter fala, não JSON ou código.")
    return text


def validate_recording_script(content, project_type):
    if not isinstance(content, dict) or not recording_fields(project_type).issubset(content):
        raise ValueError("O roteiro de gravação está incompleto.")
    for field in recording_fields(project_type):
        value = content[field]
        if value is None or isinstance(value, (bool, int, float)) or not isinstance(value, (str, list, dict)) or not value:
            raise ValueError(f"Campo de roteiro inválido: {field}.")
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"Campo de roteiro vazio: {field}.")
    for field in ("title", "opening", "estimated_duration"):
        if not isinstance(content[field], str):
            raise ValueError(f"Campo de roteiro deve ser texto: {field}.")
    spoken_text(content)
    challenge = content["authorship_challenge"]
    if not isinstance(challenge, dict) or any(
        not isinstance(challenge.get(field), str) or not challenge[field].strip()
        for field in AUTHORSHIP_CHALLENGE_SCHEMA["required_fields"]
    ):
        raise ValueError("Desafio de Autoria incompleto no roteiro.")
    return content
