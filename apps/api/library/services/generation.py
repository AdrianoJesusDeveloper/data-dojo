import json
import re

from django.conf import settings


SYSTEM_PROMPT = """Você é o Diretor de Conteúdo e Mentor de Engenharia do Data Driven Dojô.
Crie um roteiro prático em português do Brasil, fundamentado exclusivamente no contexto fornecido.
O aluno deve pensar e estruturar o problema antes de usar IA. A IA atua como pair programmer, nunca como substituta do julgamento humano.
Responda somente com JSON válido, sem markdown, com as chaves:
titulo_video, problema_resolvido, ganho_negocio e estrutura.
estrutura deve conter arquitetura_mental, parceria_ia, revisao_critica e formato_youtube.
Inclua pseudocódigo/diagramas textuais, prompts estratégicos, testes, segurança, Clean Code e validação de resultados.
Não invente fatos ausentes nas fontes; indique limitações quando necessário."""


def _extract_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("A IA não retornou um JSON válido.")
        data = json.loads(match.group(0))
    required = {"titulo_video", "problema_resolvido", "ganho_negocio", "estrutura"}
    if not isinstance(data, dict) or not required.issubset(data) or not isinstance(data["estrutura"], dict):
        raise ValueError("O roteiro retornado não segue a estrutura esperada.")
    return data


def gerar_roteiro(tema: str, trilha, chunks) -> tuple[dict, str]:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY não está configurada.")
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("Instale a dependência anthropic para gerar roteiros.") from exc

    sources = "\n\n".join(
        f"[Livro: {chunk.book.title} | página: {chunk.page_number or 'n/d'}]\n{chunk.content}"
        for chunk in chunks
    )
    prompt = (
        f"Trilha: {trilha.nome}\nFoco da trilha: {trilha.foco}\nTema solicitado: {tema}\n\n"
        f"FONTES RECUPERADAS:\n{sources}"
    )
    response = Anthropic(api_key=settings.ANTHROPIC_API_KEY).messages.create(
        model=settings.ANTHROPIC_LIBRARY_MODEL,
        max_tokens=4096,
        temperature=0.2,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    return _extract_json(raw), raw
