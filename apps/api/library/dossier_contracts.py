"""Persistence contract for human-curated master dossiers (no generation)."""
from datetime import datetime
from urllib.parse import urlparse

from django.core.exceptions import ValidationError


SCHEMA_VERSION = "master-dossier-v1"
SECTIONS = {
    "fundamental_concepts", "facts", "limitations", "examples",
    "editorial_insights", "didactic_opportunities", "research_gaps",
}
REFERENCE_FIELDS = {
    "id", "source_kind", "evidence_id", "citation_id", "context_id", "chunk_id",
    "book_id", "source_id", "title", "page_number", "url", "excerpt", "captured_at",
    "retrieved_at", "recorded_at",
}


def validate_dossier(content, references, policy, schema_version):
    if schema_version != SCHEMA_VERSION:
        raise ValidationError("Versão de estrutura do Dossiê não suportada.")
    allowed = {"ACERVO_ONLY": {"ACERVO", "GAP"}, "WEB_ONLY": {"WEB", "GAP"}, "HYBRID": {"ACERVO", "WEB", "GAP"}}
    if not isinstance(policy, str) or policy not in allowed or not isinstance(references, list):
        raise ValidationError("Política ou referências do Dossiê inválidas.")
    reference_map = {}
    for ref in references:
        if not isinstance(ref, dict) or set(ref) - REFERENCE_FIELDS:
            raise ValidationError("Snapshot deve conter somente metadados de proveniência.")
        key, kind = ref.get("id"), ref.get("source_kind")
        if not isinstance(key, str) or not key or key in reference_map or not isinstance(kind, str) or kind not in allowed[policy]:
            raise ValidationError("Referência duplicada, inválida ou incompatível com a política.")
        for field in ("title", "excerpt", "url", "captured_at"):
            if not isinstance(ref.get(field), str):
                raise ValidationError("Metadado de referência inválido.")
        if len(ref["title"]) > 500 or len(ref["excerpt"]) > 1500 or len(ref["url"]) > 2000:
            raise ValidationError("Snapshot excede o limite de metadados históricos.")
        date_field = "retrieved_at" if ref.get("evidence_id") else "recorded_at"
        for field in ("captured_at", date_field):
            if not isinstance(ref.get(field), str):
                raise ValidationError("Data de proveniência ausente.")
            try:
                stamp = datetime.fromisoformat(ref[field])
            except ValueError as exc:
                raise ValidationError("Data de proveniência inválida.") from exc
            if stamp.tzinfo is None:
                raise ValidationError("Data de proveniência deve incluir fuso horário.")
        ids = ("evidence_id", "citation_id", "context_id", "chunk_id", "book_id", "source_id", "page_number")
        for field in ids:
            value = ref.get(field)
            if value is not None and (type(value) is not int or value < 1):
                raise ValidationError("Identificador de proveniência inválido.")
        evidence_id, citation_id = ref.get("evidence_id"), ref.get("citation_id")
        if bool(evidence_id) == bool(citation_id):
            raise ValidationError("Referência deve identificar uma evidência ou citação existente.")
        expected_key = f"evidence:{evidence_id}" if evidence_id else f"citation:{citation_id}"
        if key != expected_key:
            raise ValidationError("Identidade da referência incompatível com a origem.")
        if kind == "WEB":
            try:
                url = urlparse(ref["url"])
            except ValueError as exc:
                raise ValidationError("URL de referência web inválida.") from exc
            if not evidence_id or url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
                raise ValidationError("Referência web precisa de URL HTTP(S) rastreável.")
        elif ref["url"]:
            raise ValidationError("Referência do acervo ou lacuna não deve se apresentar como fonte web.")
        reference_map[key] = kind

    if not isinstance(content, dict) or set(content) - (SECTIONS | {"executive_summary"}):
        raise ValidationError("Conteúdo do Dossiê não segue a estrutura suportada.")
    if "executive_summary" in content and not isinstance(content["executive_summary"], str):
        raise ValidationError("Síntese executiva deve ser texto.")
    for section in SECTIONS & content.keys():
        if not isinstance(content[section], list):
            raise ValidationError("Seções do Dossiê devem ser listas.")
        for item in content[section]:
            if not isinstance(item, dict) or set(item) - {"text", "reference_ids"}:
                raise ValidationError("Item do Dossiê inválido.")
            if not isinstance(item.get("text"), str) or not item["text"].strip():
                raise ValidationError("Item do Dossiê precisa de texto.")
            keys = item.get("reference_ids", [])
            if not isinstance(keys, list) or any(not isinstance(key, str) or key not in reference_map for key in keys):
                raise ValidationError("Item cita referência inexistente no snapshot.")
            if section == "facts" and not keys:
                raise ValidationError("Fatos precisam de referências rastreáveis.")
            if section != "research_gaps" and any(reference_map[key] == "GAP" for key in keys):
                raise ValidationError("GAP representa lacuna, nunca evidência factual.")
