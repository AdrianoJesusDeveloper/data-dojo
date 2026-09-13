import json
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from library.editorial_contracts import AUTHORSHIP_CHALLENGE_SCHEMA
from library.models import ModernizationPlan, StudioArtifact
from library.services.editorial_council import _safe_json
from library.services.studio_scripts import recording_fields, spoken_text, validate_recording_script
from library.tests.test_content_studio_multiformat import ContentStudioMultiformatTests
from library.tests.test_editorial_contracts import valid_plan
from library.editorial_contracts import validate_editorial_plan


def script(project_type):
    fields = recording_fields(project_type) | {
        "objective", "explanatory_text", "concepts", "code", "guided_exercise", "kata",
        "challenge", "mini_project", "ai_partnership", "without_ai_challenge", "sources",
        "supplementary_material", "theme", "script", "demonstration", "exercise", "conclusion",
        "description", "timestamps", "thumbnail_idea", "keywords", "narrative_structure",
        "thumbnail_text", "slide_suggestions", "slides", "visual_assets", "b_roll", "derived_shorts",
    }
    content = {key: "Conteúdo autoral a validar" for key in fields}
    content["estimated_duration"] = "8 minutos"
    content["teleprompter_text"] = "Antes de consultar a IA, formule sua hipótese.\nAgora vamos testar juntos."
    content["authorship_challenge"] = {key: "Explique e valide sua decisão; entrega privada permitida." for key in AUTHORSHIP_CHALLENGE_SCHEMA["required_fields"]}
    return content


class RecordingContractTests(SimpleTestCase):
    def test_export_normalizes_invisible_and_nonbreaking_hyphens(self):
        from library.services.studio_plan_export import clean_text
        self.assertEqual(clean_text("reescrevê\u2011la"), "reescrevê-la")
    def test_council_accepts_only_safe_json_wrapping(self):
        payload = {"summary": "Revisão", "findings": ["Achado"], "recommendations": [], "risks": []}
        self.assertEqual(_safe_json("```json\n" + json.dumps(payload) + "\n```"), payload)
        for raw in ("Prefixo " + json.dumps(payload), '{"summary": null}', json.dumps({**payload, "risks": "alto"}), json.dumps({**payload, "findings": [{}]})):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                _safe_json(raw)

    def test_scripts_require_all_fields_and_spoken_text(self):
        for kind in ("youtube", "premium"):
            content = script(kind)
            self.assertEqual(validate_recording_script(content, kind), content)
            for field in recording_fields(kind):
                with self.subTest(kind=kind, field=field), self.assertRaises(ValueError):
                    validate_recording_script({key: value for key, value in content.items() if key != field}, kind)
        for text in (None, {}, "", "{\"script\": \"fala\"}", "```python\nprint(1)\n```"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                spoken_text({"teleprompter_text": text})


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class RecordingWorkflowTests(APITestCase):
    setUp = ContentStudioMultiformatTests.setUp
    project = ContentStudioMultiformatTests.project
    @patch("library.services.studio_agents.chat_with_provider")
    def test_youtube_and_premium_recording_lifecycle(self, chat):
        from library.services.studio_formation import materialize_premium_formation
        self.client.force_authenticate(self.admin)
        for kind in ("youtube", "premium"):
            project = self.project("WEB_ONLY", kind)
            plan = ModernizationPlan.objects.create(project=project, proposed_architecture=validate_editorial_plan(kind, valid_plan(kind)), status="approved", version=1, source_summary="Rascunho sem fontes verificadas.")
            if kind == "premium":
                link, _ = materialize_premium_formation(project, self.admin)
            chat.return_value = json.dumps({"content": script(kind)})
            generated = self.client.post(reverse("library-studio-generate-content", kwargs={"pk": project.pk}), {"target_type": "video" if kind == "youtube" else "lesson", "target_index": 0}, format="json", REMOTE_ADDR="127.0.0.1")
            self.assertEqual(generated.status_code, 200, generated.data)
            artifact = StudioArtifact.objects.get(pk=generated.data["artifact"]["id"])
            self.assertEqual(artifact.content["script_contract_version"], "recording-script-v1")
            self.assertEqual(artifact.content["source_summary"], plan.source_summary)
            if kind == "premium":
                self.assertEqual(artifact.linked_formation_id, link.formation_id)
                self.assertIsNotNone(artifact.linked_unit_id)
            url = reverse("library-studio-artifact-export", kwargs={"pk": artifact.pk, "export_format": "teleprompter"})
            self.assertEqual(self.client.get(url, REMOTE_ADDR="127.0.0.1").status_code, 409)
            transition = reverse("library-studio-artifact-transition", kwargs={"pk": artifact.pk})
            self.assertEqual(self.client.post(transition, {"status": "APPROVED"}, format="json", REMOTE_ADDR="127.0.0.1").status_code, 400)
            for state in ("REVIEW", "APPROVED", "REVIEW", "DRAFT"):
                response = self.client.post(transition, {"status": state}, format="json", REMOTE_ADDR="127.0.0.1")
                self.assertEqual(response.status_code, 200)
                if state != "DRAFT":
                    exported = self.client.get(url, REMOTE_ADDR="127.0.0.1")
                    self.assertEqual(exported.status_code, 200)
                    self.assertIn("Antes de consultar a IA", exported.content.decode())
                    self.assertNotIn("thumbnail", exported.content.decode())
            from core.models import Course
            self.assertEqual(Course.objects.count(), 0)

    @patch("library.services.studio_agents.chat_with_provider", return_value='{"content": {}}')
    def test_invalid_script_does_not_persist(self, chat):
        project = self.project("WEB_ONLY")
        ModernizationPlan.objects.create(project=project, proposed_architecture=valid_plan("youtube"), status="approved")
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse("library-studio-generate-content", kwargs={"pk": project.pk}), {"target_type": "video", "target_index": 0}, format="json", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(project.artifacts.exists())

    def test_artifact_ownership_and_legacy_teleprompter_fail_closed(self):
        project = self.project("WEB_ONLY")
        artifact = StudioArtifact.objects.create(project=project, artifact_type="YOUTUBE_PACKAGE", target_type="video", target_id="legacy", plan_version=1, content={"script": "Plano não é fala"}, status="REVIEW", created_by=self.admin)
        export_url = reverse("library-studio-artifact-export", kwargs={"pk": artifact.pk, "export_format": "teleprompter"})
        transition_url = reverse("library-studio-artifact-transition", kwargs={"pk": artifact.pk})
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(export_url, REMOTE_ADDR="127.0.0.1").status_code, 409)
        self.student.is_staff = True
        self.student.save(update_fields=["is_staff"])
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get(export_url, REMOTE_ADDR="127.0.0.1").status_code, 404)
        self.assertEqual(self.client.post(transition_url, {"status": "APPROVED"}, format="json", REMOTE_ADDR="127.0.0.1").status_code, 404)

    def test_plan_export_formats_and_permissions(self):
        project = self.project("WEB_ONLY")
        ModernizationPlan.objects.create(project=project, proposed_architecture=valid_plan("youtube"))
        self.client.force_authenticate(self.admin)
        for format in ("pdf", "docx", "pptx"):
            url = reverse("library-studio-plan-export", kwargs={"pk": project.pk, "export_format": format})
            response = self.client.get(url, REMOTE_ADDR="127.0.0.1")
            self.assertEqual(response.status_code, 200)
            self.assertIn(f'.{format}', response["Content-Disposition"])
            self.assertTrue(response.content.startswith(b"%PDF") if format == "pdf" else response.content.startswith(b"PK"))
            self.assertEqual(self.client.get(url, REMOTE_ADDR="8.8.8.8").status_code, 403)
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get(url, REMOTE_ADDR="127.0.0.1").status_code, 403)
        self.student.is_staff = True
        self.student.save(update_fields=["is_staff"])
        self.assertEqual(self.client.get(url, REMOTE_ADDR="127.0.0.1").status_code, 404)
