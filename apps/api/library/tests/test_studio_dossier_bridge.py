from copy import deepcopy
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from library.models import Book, BookChunk, StudioDossierVersion, StudioProject, StudioResearchContext, StudioResearchEvidence
from library.services.studio_dossier import (
    create_dossier_version, prepare_dossier_from_research, transition_dossier_version,
)
from library.services.studio_research import WebResearchResult, build_research_context


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True)
class StudioDossierBridgeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username="bridge", email="bridge@example.com", is_staff=True)
        cls.other = get_user_model().objects.create_user(username="bridge-other", email="bridge-other@example.com", is_staff=True)
        cls.student = get_user_model().objects.create_user(username="bridge-student", email="bridge-student@example.com")
        cls.project = StudioProject.objects.create(title="Ponte", theme="Dados", objective="Ensinar",
                                                   research_policy="WEB_ONLY", created_by=cls.owner)
        other_project = StudioProject.objects.create(title="Privado", created_by=cls.other)
        other_context = StudioResearchContext.objects.create(project=other_project, policy="WEB_ONLY")
        cls.foreign = StudioResearchEvidence.objects.create(context=other_context, source_kind="WEB",
            url="https://example.com/private", retrieved_at=timezone.now())

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        self.research_url = f"/api/library/studio/projects/{self.project.pk}/research/"
        self.dossier_url = f"/api/library/studio/projects/{self.project.pk}/dossier/"

    def research(self, dossier=None, results=None):
        provider = Mock()
        provider.search.return_value = results if results is not None else [
            WebResearchResult(url="https://example.com/source", title="Fonte", excerpt="Trecho documental")]
        return build_research_context(self.project, provider,
            dossier_builder=lambda project, evidence: (dossier or {"thesis": "Uma hipótese"}, []))

    def prepare(self, **kwargs):
        return prepare_dossier_from_research(project_id=self.project.pk, actor=self.owner, **kwargs)

    def save_proposal(self, proposal):
        return create_dossier_version(project_id=self.project.pk, actor=self.owner, **proposal)

    def approve(self, version):
        for status in ("REVIEW", "APPROVED"):
            transition_dossier_version(project_id=self.project.pk, actor=self.owner,
                version_id=version.pk, expected_version=version.version, status=status)
        version.refresh_from_db()

    def test_preparation_maps_only_supported_editorial_text(self):
        research = {"thesis": "Hipótese", "arguments": [{"text": "Argumento", "evidence_id": 1}],
                    "counterpoints": ["Contraponto"], "interpretation_risks": ["Risco"],
                    "examples": ["Exemplo"], "possible_demonstrations": ["Demonstração"],
                    "dojo_connections": ["Conexão"], "title_proposal": "Não mapear",
                    "evidence": [{"text": "Inferência não é fato", "evidence_id": 1}]}
        context = self.research(research)
        proposal = self.prepare()
        self.assertEqual(proposal, self.prepare())
        self.assertEqual(proposal["content"], {
            "editorial_insights": [{"text": "Hipótese da pesquisa a revisar: Hipótese"},
                                   {"text": "Argumento sugerido pela pesquisa a revisar: Argumento"}],
            "limitations": [{"text": "Contraponto sugerido pela pesquisa a revisar: Contraponto"},
                            {"text": "Risco sugerido pela pesquisa a revisar: Risco"}],
            "examples": [{"text": "Exemplo sugerido pela pesquisa a validar: Exemplo"}],
            "didactic_opportunities": [{"text": "Demonstração sugerida pela pesquisa a validar: Demonstração"},
                                       {"text": "Conexão didática sugerida pela pesquisa a revisar: Conexão"}],
        })
        self.assertEqual(proposal["evidence_ids"], [context.evidence.get().pk])
        self.assertEqual(proposal["expected_version"], 0)
        self.assertFalse(proposal["inherit_references"])
        self.assertFalse(StudioDossierVersion.objects.exists())
        context.refresh_from_db()
        self.assertEqual(context.dossier, research)

    def test_persistent_ids_are_not_research_ordinals(self):
        context = self.research({"arguments": [{"text": "Sugestão [1]", "evidence_id": 1,
                                                "reference_ids": ["evidence:1"]}]})
        real_id = context.evidence.get().pk
        self.assertNotEqual(real_id, 1)
        proposal = self.prepare()
        self.assertEqual(proposal["evidence_ids"], [real_id])
        self.assertNotIn("reference_ids", proposal["content"]["editorial_insights"][0])
        version = self.save_proposal(proposal)
        self.assertEqual(version.references_snapshot[0]["id"], f"evidence:{real_id}")
        self.assertEqual(version.references_snapshot[0]["context_id"], context.pk)

    def test_missing_and_foreign_selection_rejected(self):
        self.research()
        for ids in ([999999], [self.foreign.pk]):
            with self.subTest(ids=ids), self.assertRaises(ValidationError):
                self.prepare(evidence_ids=ids)
        self.assertFalse(StudioDossierVersion.objects.exists())

    def test_current_policy_and_source_origins_are_enforced(self):
        context = self.research()
        self.project.research_policy = "ACERVO_ONLY"
        self.project.save(update_fields=["research_policy"])
        with self.assertRaises(ValidationError):
            self.prepare()
        context.policy = "ACERVO_ONLY"
        context.save(update_fields=["policy"])
        with self.assertRaises(ValidationError):
            self.prepare()
        context.evidence.update(source_kind="UNKNOWN")
        with self.assertRaises(ValidationError):
            self.prepare()

    @patch("library.services.studio_research.buscar_chunks_relevantes")
    def test_acervo_and_hybrid_preparations_keep_persisted_origins(self, retrieve):
        book = Book.objects.create(title="Livro", file="books/bridge.pdf", status="ready")
        chunk = BookChunk.objects.create(book=book, chunk_index=0, page_number=3, content="Trecho do livro")
        self.project.books.add(book)
        retrieve.return_value = [chunk]
        for policy, kinds in (("ACERVO_ONLY", {"ACERVO"}), ("HYBRID", {"ACERVO", "WEB"})):
            with self.subTest(policy=policy):
                self.project.research_policy = policy
                self.project.save(update_fields=["research_policy"])
                context = self.research()
                proposal = self.prepare()
                self.assertEqual(set(proposal["evidence_ids"]), set(context.evidence.values_list("pk", flat=True)))
                version = self.save_proposal(proposal)
                self.assertEqual({ref["source_kind"] for ref in version.references_snapshot}, kinds)
                reference = next(ref for ref in version.references_snapshot if ref["source_kind"] == "ACERVO")
                self.assertEqual((reference["chunk_id"], reference["book_id"], reference["page_number"]),
                                 (chunk.pk, book.pk, 3))

    def test_no_documentary_content_or_references_are_invented(self):
        self.research({"facts": [{"text": "Inventado", "reference_ids": ["evidence:999"]}],
                       "evidence": [{"text": "Inventado", "evidence_id": 999}],
                       "arguments": [42, {"unsupported": "Não converter"}],
                       "thesis": ["Forma desconhecida"]})
        proposal = self.prepare(evidence_ids=[])
        self.assertEqual(proposal["content"], {})
        self.assertEqual(proposal["evidence_ids"], [])

    def test_human_edits_proposal_then_explicit_post_creates_draft(self):
        context = self.research()
        response = self.client.get(self.research_url)
        self.assertEqual(response.status_code, 200, response.data)
        proposal = deepcopy(response.data["dossier_preparation"])
        self.assertEqual(response.data["evidence"][0]["id"], context.evidence.get().pk)
        self.assertFalse(StudioDossierVersion.objects.exists())
        proposal["content"] = {"executive_summary": "Texto decidido pelo humano",
            "facts": [{"text": "Fato revisado pelo humano",
                       "reference_ids": [f"evidence:{context.evidence.get().pk}"]}]}
        response = self.client.post(self.dossier_url, proposal, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["content"], proposal["content"])
        self.assertEqual(response.data["status"], "DRAFT")
        self.assertEqual(response.data["origin"], "human_edit")
        self.assertIsNone(response.data["reviewed_by"])

    @patch("library.services.studio_research.WikipediaWebResearchProvider.search")
    @patch("library.views.generate_grounded_dossier")
    def test_research_post_alone_never_creates_human_version(self, builder, search):
        search.return_value = [WebResearchResult("https://example.com/source", "Fonte", "Trecho")]
        builder.return_value = ({"thesis": "Sugestão automática"}, [])
        response = self.client.post(self.research_url, {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(self.project.research_context.evidence.exists())
        self.assertFalse(StudioDossierVersion.objects.exists())

    def test_new_research_preserves_draft_and_approved_history(self):
        self.research()
        version = self.save_proposal(self.prepare())
        for status in ("DRAFT", "APPROVED"):
            if status == "APPROVED":
                self.approve(version)
            before = StudioDossierVersion.objects.values().get(pk=version.pk)
            self.research({"thesis": "Nova pesquisa"})
            self.prepare()
            self.assertEqual(StudioDossierVersion.objects.values().get(pk=version.pk), before)
            self.assertEqual(self.project.dossier_versions.count(), 1)

    def test_incorporation_after_approval_creates_new_draft_and_preserves_history(self):
        self.research()
        first = self.save_proposal(self.prepare())
        self.approve(first)
        before = StudioDossierVersion.objects.values().get(pk=first.pk)
        self.research({"thesis": "Nova pesquisa"})
        proposal = self.prepare()
        self.assertEqual(proposal["expected_version"], 1)
        proposal["content"]["executive_summary"] = "Revisão humana"
        response = self.client.post(self.dossier_url, proposal, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data["version"], response.data["status"], response.data["based_on"]),
                         (2, "DRAFT", first.pk))
        self.assertEqual(StudioDossierVersion.objects.values().get(pk=first.pk), before)
        first.content = {"executive_summary": "Não sobrescrever"}
        with self.assertRaises(ValidationError):
            first.save()
        history = self.client.get(self.dossier_url)
        self.assertEqual([row["version"] for row in history.data], [2, 1])

    def test_proposal_stale_version_and_replaced_evidence_are_rejected(self):
        self.research()
        stale = self.prepare()
        first = self.save_proposal(stale)
        response = self.client.post(self.dossier_url, stale, format="json")
        self.assertEqual(response.status_code, 400)
        stale["expected_version"] = first.version
        self.research()
        response = self.client.post(self.dossier_url, stale, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.project.dossier_versions.count(), 1)

    def test_selection_can_be_reduced_by_human(self):
        self.research(results=[WebResearchResult("https://example.com/a", "A", "Trecho A"),
                               WebResearchResult("https://example.com/b", "B", "Trecho B")])
        proposal = self.prepare()
        proposal["evidence_ids"] = proposal["evidence_ids"][-1:]
        response = self.client.post(self.dossier_url, proposal, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual([ref["evidence_id"] for ref in response.data["references_snapshot"]], proposal["evidence_ids"])

    def test_get_and_service_preserve_owner_isolation(self):
        self.research()
        for actor, expected in ((self.other, 404), (self.student, 403)):
            self.client.force_authenticate(actor)
            response = self.client.get(self.research_url)
            self.assertEqual(response.status_code, expected)
            with self.assertRaises(PermissionDenied):
                prepare_dossier_from_research(project_id=self.project.pk, actor=actor)
        self.assertFalse(StudioDossierVersion.objects.exists())

    def test_missing_or_unfinished_research_returns_validation_error(self):
        self.assertEqual(self.client.get(self.research_url).status_code, 400)
        context = self.research()
        for status in ("draft", "failed"):
            context.status = status
            context.save(update_fields=["status"])
            self.assertEqual(self.client.get(self.research_url).status_code, 400)

    def test_gap_is_only_a_gap_and_can_be_reviewed_without_sources(self):
        context = self.research(results=[])
        proposal = self.prepare()
        self.assertNotIn("facts", proposal["content"])
        self.assertEqual(proposal["content"]["research_gaps"], [{
            "text": context.evidence.get().excerpt,
            "reference_ids": [f"evidence:{context.evidence.get().pk}"],
        }])
        version = self.save_proposal(proposal)
        self.assertEqual(version.status, "DRAFT")
        self.assertEqual(version.references_snapshot[0]["source_kind"], "GAP")
