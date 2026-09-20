"""Claim grounding V1: exact evidence identity and conservative extractive support.

This is not a semantic entailment classifier. Only verbatim source statements are
marked source-derived; pedagogical prose is explicitly not certified by a source.
"""
from copy import deepcopy


class ClaimGroundingError(ValueError):
    pass


PEDAGOGICAL_TYPES = {
    "LEARNING_OBJECTIVES", "GUIDED_PRACTICE", "EXERCISE", "AUTHORSHIP_CHALLENGE",
    "PROJECT", "REFLECTION", "SELF_ASSESSMENT", "MASTERY_CRITERIA",
}
IDENTITY_FIELDS = ("source_id", "book_id", "chunk_id", "pdf_page")
EVIDENCE_SCHEMA = {
    "type": "object",
    "properties": {**{field: {"type": "integer"} for field in IDENTITY_FIELDS}, "quote": {"type": "string"}},
    "required": [*IDENTITY_FIELDS, "quote"],
    "additionalProperties": False,
}
CLAIMS_METADATA_SCHEMA = {
    "type": "object",
    "properties": {"claims": {"type": "array", "items": {
        "type": "object", "properties": {
            "text": {"type": "string"},
            "evidence": {"type": "array", "items": EVIDENCE_SCHEMA},
        }, "required": ["text", "evidence"], "additionalProperties": False,
    }}},
    "required": ["claims"], "additionalProperties": False,
}


def grounded_schema(schema):
    result = deepcopy(schema)
    result["properties"]["sections"]["items"]["properties"]["metadata"] = CLAIMS_METADATA_SCHEMA
    return result


def _fail(reason):
    raise ClaimGroundingError(f"CLAIM_GROUNDING_INVALID: {reason} A aula não foi salva.")


def ground_sections(sections, context):
    """Validate against precisely the excerpts sent on this generation, not live RAG."""
    sources = {source["id"] for source in context.get("approved_sources", [])}
    excerpts = {item["chunk_id"]: item for item in context.get("approved_source_excerpts", [])}
    if not excerpts:
        _fail("As fontes aprovadas não possuem evidência textual verificável nesta geração.")
    result, used = [], {}
    claim_count = 0
    for section in deepcopy(sections):
        kind = section["section_type"]
        claims = section["metadata"].get("claims", [])
        if not isinstance(claims, list) or len(claims) > 100:
            _fail("Lista de afirmações inválida.")
        validated = []
        for claim in claims:
            if not isinstance(claim, dict) or not isinstance(claim.get("text"), str) or not claim["text"].strip():
                _fail("Afirmação vazia ou inválida.")
            text = claim["text"].strip()
            evidence = claim.get("evidence")
            if not isinstance(evidence, list) or not evidence or len(evidence) > 8:
                _fail("Cada afirmação factual precisa de evidência.")
            canonical = []
            for ref in evidence:
                if not isinstance(ref, dict) or any(type(ref.get(field)) is not int for field in IDENTITY_FIELDS):
                    _fail("Identificadores de evidência inválidos.")
                excerpt = excerpts.get(ref["chunk_id"])
                if excerpt is None or excerpt["source_id"] not in sources or any(ref[field] != excerpt.get(field) for field in IDENTITY_FIELDS):
                    _fail("Chunk, fonte, livro ou página não pertence ao grounding atual.")
                quote = ref.get("quote")
                # Identity alone cannot support arbitrary prose. V1 accepts only exact,
                # contiguous quotations of the excerpt actually supplied to the provider.
                if not isinstance(quote, str) or not quote.strip() or quote != text or quote not in excerpt["content"]:
                    _fail("A afirmação não corresponde a uma citação literal da evidência fornecida.")
                canonical.append({**{field: excerpt[field] for field in IDENTITY_FIELDS}, "quote": quote})
                used[excerpt["chunk_id"]] = excerpt
            validated.append({"text": text, "evidence": canonical})
        if kind == "REFERENCES":
            # Never trust model-written bibliography, even if it contains valid IDs.
            continue
        if kind not in PEDAGOGICAL_TYPES and not validated:
            _fail(f"A seção {kind} não possui afirmações factuais sustentadas.")
        if validated and section["content"] != "\n\n".join(claim["text"] for claim in validated):
            _fail("A seção contém texto factual não coberto pelas afirmações verificadas.")
        claim_count += len(validated)
        section["metadata"] = {"claim_grounding": {
            "version": 1,
            "kind": "source_derived" if validated else "pedagogical",
            "validation": "extractive_snapshot_match" if validated else "not_source_assertion",
            "claims": validated,
        }}
        result.append(section)
    if not claim_count:
        _fail("A aula baseada em fontes não contém evidência factual suficiente.")
    references = sorted(used.values(), key=lambda item: (item["source_id"], item["book_id"], item["pdf_page"], item["chunk_id"]))
    result.append({"section_type": "REFERENCES", "title": "Evidências do snapshot", "content": "\n".join(
        f"{item['book_title']} · PDF p.{item['pdf_page']} · chunk #{item['chunk_id']} · fonte #{item['source_id']}" for item in references
    ), "metadata": {"claim_grounding": {"version": 1, "kind": "references", "validation": "backend_derived", "claims": [], "evidence": [{field: item[field] for field in IDENTITY_FIELDS} for item in references]}}})
    return result


def has_editorial_claim_state(lesson):
    """Check stored state, never trust claim metadata supplied in an editorial PATCH.

    Human revisions remain explicitly uncertified. Source-derived sections are
    rechecked against the immutable snapshot, not today's corpus or source ranges.
    """
    sections = list(lesson.sections.all())
    if not sections:
        return False
    snapshot = lesson.grounding_snapshot or {}
    context = {"approved_sources": snapshot.get("sources", []), "approved_source_excerpts": snapshot.get("excerpts", [])}
    try:
        for section in sections:
            state = section.metadata.get("claim_grounding") if isinstance(section.metadata, dict) else None
            if not isinstance(state, dict) or type(state.get("version")) is not int or state["version"] != 1:
                return False
            kind = state.get("kind")
            if kind in {"human_edited", "pedagogical"}:
                if state.get("validation") != "not_source_assertion" or state.get("claims") != []:
                    return False
                if kind == "pedagogical" and section.section_type not in PEDAGOGICAL_TYPES:
                    return False
            elif kind == "source_derived":
                if state.get("validation") != "extractive_snapshot_match" or not state.get("claims") or section.section_type == "REFERENCES":
                    return False
                checked = ground_sections([{
                    "section_type": section.section_type, "title": section.title,
                    "content": section.content, "metadata": {"claims": state["claims"]},
                }], context)
                if checked[0]["metadata"]["claim_grounding"] != state:
                    return False
            elif kind == "references":
                if section.section_type != "REFERENCES" or state.get("validation") != "backend_derived" or state.get("claims") != []:
                    return False
                evidence = state.get("evidence")
                if not isinstance(evidence, list) or not evidence:
                    return False
                sources = {source["id"] for source in context["approved_sources"]}
                excerpts = {item["chunk_id"]: item for item in context["approved_source_excerpts"]}
                for ref in evidence:
                    if not isinstance(ref, dict) or any(type(ref.get(field)) is not int for field in IDENTITY_FIELDS):
                        return False
                    excerpt = excerpts.get(ref["chunk_id"])
                    if not excerpt or excerpt["source_id"] not in sources or any(ref[field] != excerpt.get(field) for field in IDENTITY_FIELDS):
                        return False
            else:
                return False
    except (ClaimGroundingError, KeyError, TypeError, AttributeError):
        return False
    return True


GROUNDING_INSTRUCTION = (
    "Claim-Level Grounding V1: metadata deve conter claims, uma lista de objetos "
    "{text, evidence: [{source_id, book_id, chunk_id, pdf_page, quote}]}. "
    "Use SOMENTE identidades de approved_source_excerpts desta geração. "
    "Nesta V1 conservadora, text e quote devem ser IDÊNTICOS a um trecho literal contínuo do excerpt; "
    "não use paráfrases, inferências nem conhecimento externo nas afirmações factuais. "
    "Em seções factuais, content deve ser EXATAMENTE os textos dos claims unidos por duas quebras de linha. "
    "Instruções, exercícios, reflexão e autoria podem ter claims: [] e texto pedagógico livre, "
    "mas não devem afirmar fatos nem atribuir novas conclusões à fonte. Separe suas premissas factuais em seções com claims. "
    "Os tipos pedagógicos são: " + ", ".join(sorted(PEDAGOGICAL_TYPES)) + ". "
    "Todos os outros tipos (exceto REFERENCES) exigem claims. "
    "Não gere REFERENCES: o backend deriva as referências das evidências verificadas. "
    "Se faltar evidência para o objetivo, não preencha a lacuna com conhecimento do modelo."
)
