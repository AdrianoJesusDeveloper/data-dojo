"""Internal persistence operations. No research, providers, publication or API."""
from copy import deepcopy

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from core.permissions import is_administrative_user
from library.dossier_contracts import SCHEMA_VERSION
from library.models import SourceCitation, StudioDossierVersion, StudioProject, StudioResearchEvidence


def _owned_project(project_id, actor):
    if not actor or not actor.is_active or not is_administrative_user(actor):
        raise PermissionDenied("O Dossiê exige acesso administrativo.")
    project = StudioProject.objects.select_for_update().filter(pk=project_id, created_by=actor).first()
    if project is None:
        raise PermissionDenied("Projeto indisponível para este usuário.")
    return project


def _evidence_reference(evidence, captured_at):
    chunk = evidence.chunk
    book = chunk.book if chunk else None
    return {
        "id": f"evidence:{evidence.pk}", "source_kind": evidence.source_kind,
        "evidence_id": evidence.pk, "context_id": evidence.context_id,
        "chunk_id": evidence.chunk_id, "book_id": book.pk if book else None,
        "source_id": book.source_id if book else None,
        "title": evidence.title[:500], "page_number": chunk.page_number if chunk else None,
        "url": evidence.url, "excerpt": evidence.excerpt[:1500],
        "captured_at": captured_at, "retrieved_at": evidence.retrieved_at.isoformat(),
    }


def _citation_reference(citation, captured_at):
    chunk = citation.chunk
    return {
        "id": f"citation:{citation.pk}", "source_kind": "ACERVO", "citation_id": citation.pk,
        "chunk_id": citation.chunk_id, "book_id": chunk.book_id if chunk else None,
        "source_id": citation.source_id or (chunk.book.source_id if chunk else None),
        "title": citation.book_title[:500], "page_number": citation.page_number,
        "url": "", "excerpt": citation.excerpt[:1500],
        "captured_at": captured_at, "recorded_at": citation.created_at.isoformat(),
    }


def _reference_rows(project_id, evidence_ids, citation_ids):
    for ids in (evidence_ids, citation_ids):
        if not isinstance(ids, (list, tuple)) or any(type(value) is not int or value < 1 for value in ids) or len(set(ids)) != len(ids):
            raise ValidationError("Seleção de referências inválida ou duplicada.")
    evidence = list(StudioResearchEvidence.objects.filter(context__project_id=project_id, pk__in=evidence_ids).select_related("chunk__book"))
    citations = list(SourceCitation.objects.filter(project_id=project_id, pk__in=citation_ids).select_related("chunk__book"))
    if len(evidence) != len(evidence_ids) or len(citations) != len(citation_ids):
        raise ValidationError("Referências inexistentes ou pertencentes a outro projeto.")
    return evidence, citations


def validate_reference_origins(project_id, references, based_on):
    """Accept exact inherited snapshots or metadata derived from this project's rows."""
    inherited = {ref["id"]: ref for ref in based_on.references_snapshot} if based_on else {}
    new = [ref for ref in references if inherited.get(ref["id"]) != ref]
    evidence, citations = _reference_rows(
        project_id, [ref["evidence_id"] for ref in new if ref.get("evidence_id")],
        [ref["citation_id"] for ref in new if ref.get("citation_id")],
    )
    rows = {f"evidence:{row.pk}": (row, _evidence_reference) for row in evidence}
    rows.update({f"citation:{row.pk}": (row, _citation_reference) for row in citations})
    for ref in new:
        row, build = rows[ref["id"]]
        if ref != build(row, ref["captured_at"]):
            raise ValidationError("A proveniência deve corresponder à fonte persistida.")


@transaction.atomic
def create_dossier_version(*, project_id, actor, content, expected_version,
                           evidence_ids=(), citation_ids=(), inherit_references=True,
                           origin=StudioDossierVersion.Origin.HUMAN_EDIT):
    """Append against the caller's last observed version (0 means no dossier).

    Content is supplied by the caller, never generated here. Example:
    {"facts": [{"text": "...", "reference_ids": ["evidence:12"]}]}.
    Snapshots inherit unchanged historical references, including deleted sources;
    explicitly selected rows refresh only the new version's corresponding entry.
    Set inherit_references=False to explicitly replace the selection.
    """
    project = _owned_project(project_id, actor)
    latest = project.dossier_versions.first()
    if type(expected_version) is not int or expected_version != (latest.version if latest else 0):
        raise ValidationError("Versão base desatualizada; recarregue o Dossiê.")
    if type(inherit_references) is not bool:
        raise ValidationError("A opção de herdar referências deve ser booleana.")
    references = {ref["id"]: deepcopy(ref) for ref in latest.references_snapshot} if latest and inherit_references else {}
    evidence, citations = _reference_rows(project.pk, evidence_ids, citation_ids)
    captured_at = timezone.now().isoformat()
    for row in evidence:
        ref = _evidence_reference(row, captured_at)
        references[ref["id"]] = ref
    for row in citations:
        ref = _citation_reference(row, captured_at)
        references[ref["id"]] = ref
    return StudioDossierVersion.objects.create(
        project=project, version=expected_version + 1, based_on=latest,
        content=deepcopy(content), schema_version=SCHEMA_VERSION,
        research_policy=project.research_policy, references_snapshot=list(references.values()),
        created_by=actor, origin=origin,
    )


@transaction.atomic
def transition_dossier_version(*, project_id, actor, version_id, expected_version, status):
    """Review metadata changes explicitly; approved content is never rewritten."""
    project = _owned_project(project_id, actor)
    latest = project.dossier_versions.first()
    if latest is None or type(expected_version) is not int or latest.version != expected_version or latest.pk != version_id:
        raise ValidationError("A revisão deve usar a versão atual deste projeto.")
    if status not in StudioDossierVersion.Status.values:
        raise ValidationError("Status do Dossiê inválido.")
    if latest.status == status:
        return latest  # A repeated approval must not rewrite the reviewer/time.
    latest.status = status
    if status == StudioDossierVersion.Status.APPROVED:
        latest.reviewed_by = actor
        latest.reviewed_at = timezone.now()
    latest.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    return latest
