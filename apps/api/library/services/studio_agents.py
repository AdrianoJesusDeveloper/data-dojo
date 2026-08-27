import json
import re

from django.conf import settings

from ai.services import chat_with_provider


def _json(raw: str, required: set[str]) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("O agente não retornou JSON válido.")
        data = json.loads(match.group(0))
    if not isinstance(data, dict) or not required.issubset(data):
        raise ValueError("O agente não retornou todos os campos obrigatórios.")
    return data


def _context(chunks) -> str:
    return "\n\n".join(
        f"[Fonte {index} | {chunk.book.title} | página {chunk.page_number or 'n/d'}]\n{chunk.content}"
        for index, chunk in enumerate(chunks, start=1)
    )


def generate_modernization_plan(project, chunks) -> tuple[dict, str]:
    system = """Você é o Arquiteto de Modernização do DDJ Content Studio.
Use apenas as fontes fornecidas para descrever o projeto original. Diferencie fatos da fonte e recomendações atuais.
Não copie extensamente o livro. Produza uma arquitetura nova, segura, testável e pedagogicamente útil.
Responda somente em JSON com: source_summary, original_architecture, proposed_architecture, replacements,
requirements, acceptance_criteria, test_strategy, risks e business_value."""
    user = f"Projeto: {project.title}\nTema: {project.theme}\nObjetivo: {project.objective}\n\nFontes:\n{_context(chunks)}"
    raw = chat_with_provider(settings.CONTENT_STUDIO_PROVIDER, [{"role": "system", "content": system}, {"role": "user", "content": user}])
    required = {"source_summary", "original_architecture", "proposed_architecture", "replacements", "requirements", "acceptance_criteria", "test_strategy", "risks", "business_value"}
    return _json(raw, required), raw


def generate_content_package(project, plan) -> tuple[dict, str]:
    system = """Você é o Designer Educacional e Diretor de Conteúdo do Data Driven Dojô.
Transforme somente o plano aprovado em um pacote pedagógico prático. Preserve o princípio: humano pensa, IA potencializa, desenvolvedor valida.
Responda somente em JSON com: study_plan, lesson, kata, video_script, article e linkedin_post."""
    user = json.dumps({"project": {"title": project.title, "theme": project.theme, "objective": project.objective}, "approved_plan": {"source_summary": plan.source_summary, "proposed_architecture": plan.proposed_architecture, "requirements": plan.requirements, "acceptance_criteria": plan.acceptance_criteria, "test_strategy": plan.test_strategy, "risks": plan.risks, "business_value": plan.business_value}}, ensure_ascii=False)
    raw = chat_with_provider(settings.CONTENT_STUDIO_PROVIDER, [{"role": "system", "content": system}, {"role": "user", "content": user}])
    return _json(raw, {"study_plan", "lesson", "kata", "video_script", "article", "linkedin_post"}), raw
