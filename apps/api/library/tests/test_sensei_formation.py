from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import (
    LibrarySource, SenseiCompetency, SenseiCompetencyEvidence,
    SenseiCompetencyProgress, SenseiFormation, SenseiFormationModule,
    SenseiProgress, SenseiStudyNote, SenseiStudyUnit, SenseiUnitSource,
    SenseiUnitStudyPlan, SenseiUnitStudyProgress,
)


@override_settings(DDJ_CONTENT_STUDIO_ENABLED=True, DDJ_CONTENT_STUDIO_LOCAL_ONLY=True)
class SenseiFormationApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_user(email="sensei@example.com", username="sensei", password="test", is_staff=True)
        self.other = users.objects.create_user(email="other-sensei@example.com", username="other-sensei", password="test", is_staff=True)
        self.student = users.objects.create_user(email="student-sensei@example.com", username="student-sensei", password="test")
        self.client.force_authenticate(self.admin)

    def request(self, method, url, data=None):
        return getattr(self.client, method)(url, data=data, format="json" if data is not None else None, REMOTE_ADDR="127.0.0.1")

    def create_formation(self, slug="formation-test"):
        response = self.request("post", reverse("library-sensei-formations"), {
            "title": "Formação de teste", "slug": slug, "description": "Fundação",
            "objective": "Demonstrar competência", "status": "DRAFT", "level": "Progressivo",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return SenseiFormation.objects.get(pk=response.data["id"])

    def create_competency(self, formation, expected_level=6):
        response = self.request("post", reverse("library-sensei-formation-competencies", kwargs={"formation_pk": formation.pk}), {
            "title": "Arquitetura de agentes", "description": "Projetar e defender decisões.",
            "expected_level": expected_level, "mastery_criteria": ["Implementa", "Justifica", "Ensina"], "order": 0,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return SenseiCompetency.objects.get(pk=response.data["id"])

    def test_seed_create_update_and_persistence(self):
        seeded = SenseiFormation.objects.get(slug="engenharia-ia-arquitetura-sistemas-inteligentes")
        self.assertEqual(seeded.title, "Engenharia de IA Aplicada e Arquitetura de Sistemas Inteligentes")
        self.assertEqual(seeded.status, "DRAFT")
        self.assertIsNone(seeded.created_by)
        self.assertEqual(seeded.modules.count(), 22)
        self.assertEqual(SenseiStudyUnit.objects.filter(module__formation=seeded).count(), 66)
        self.assertEqual(seeded.competencies.count(), 44)
        self.assertEqual(list(seeded.modules.values_list("order", flat=True)), list(range(22)))
        self.assertFalse(SenseiProgress.objects.filter(formation=seeded).exists())
        self.assertFalse(SenseiCompetencyProgress.objects.filter(competency__formation=seeded).exists())
        self.assertFalse(SenseiCompetencyEvidence.objects.filter(competency__formation=seeded).exists())
        pilot = seeded.modules.get(order=0).study_units.get(order=0)
        self.assertTrue(SenseiUnitStudyPlan.objects.filter(unit=pilot).exists())
        transformer = seeded.modules.get(title="Transformers e LLMs")
        self.assertEqual(
            list(transformer.study_units.values_list("title", flat=True)),
            ["Tokenização, embeddings posicionais e contexto", "Q/K/V, self-attention e multi-head attention", "Blocos Transformer, pré-treino e inferência de LLMs"],
        )

        formation = self.create_formation()
        self.assertEqual(formation.created_by, self.admin)
        updated = self.request("patch", reverse("library-sensei-formation-detail", kwargs={"pk": formation.pk}), {"status": "ACTIVE", "level": "Avançado"})
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        formation.refresh_from_db()
        self.assertEqual((formation.status, formation.level), ("ACTIVE", "Avançado"))

    def test_modules_units_multiple_sources_and_invalid_states(self):
        formation = self.create_formation("formation-structure")
        module_response = self.request("post", reverse("library-sensei-formation-modules", kwargs={"formation_pk": formation.pk}), {"title": "Fundamentos", "description": "Base", "order": 0})
        self.assertEqual(module_response.status_code, status.HTTP_201_CREATED)
        module = SenseiFormationModule.objects.get(pk=module_response.data["id"])
        sources = [LibrarySource.objects.create(relative_path=f"source-{index}.pdf", filename=f"source-{index}.pdf", extension="pdf") for index in range(2)]
        unit_response = self.request("post", reverse("library-sensei-module-units", kwargs={"module_pk": module.pk}), {
            "title": "Embeddings", "objective": "Implementar recuperação vetorial", "order": 0,
            "status": "ACTIVE", "sources": [source.id for source in sources],
            "reference_links": [{"type": "official_documentation", "url": "https://example.com/docs"}],
        })
        self.assertEqual(unit_response.status_code, status.HTTP_201_CREATED, unit_response.data)
        self.assertEqual(SenseiStudyUnit.objects.get(pk=unit_response.data["id"]).sources.count(), 2)
        invalid = self.request("post", reverse("library-sensei-module-units", kwargs={"module_pk": module.pk}), {"title": "Inválida", "objective": "Teste", "order": 1, "status": "COMPLETED"})
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_competency_levels_relationships_and_invalid_level(self):
        formation = self.create_formation("formation-competency")
        competency = self.create_competency(formation)
        self.assertEqual(list(SenseiCompetency.MasteryLevel.values), [1, 2, 3, 4, 5, 6])
        self.assertEqual(competency.get_expected_level_display(), "Ensina")
        invalid = self.request("post", reverse("library-sensei-formation-competencies", kwargs={"formation_pk": formation.pk}), {"title": "Inválida", "expected_level": 7, "mastery_criteria": ["Critério"]})
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

        other_formation = self.create_formation("other-formation")
        foreign_module = SenseiFormationModule.objects.create(formation=other_formation, title="Outro", order=0)
        cross_relation = self.request("post", reverse("library-sensei-formation-competencies", kwargs={"formation_pk": formation.pk}), {"title": "Cruzada", "module": foreign_module.pk, "expected_level": 2, "mastery_criteria": ["Explicar"]})
        self.assertEqual(cross_relation.status_code, status.HTTP_400_BAD_REQUEST)

    def test_evidence_requires_human_validation_before_mastery(self):
        formation = self.create_formation("formation-evidence")
        competency = self.create_competency(formation)
        progress_url = reverse("library-sensei-competency-progress", kwargs={"pk": competency.pk})
        blocked = self.request("patch", progress_url, {"current_level": 6, "state": "TEACHING_READY"})
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)

        evidence = self.request("post", reverse("library-sensei-competency-evidences", kwargs={"competency_pk": competency.pk}), {
            "evidence_type": "TAUGHT_CLASS", "description": "Aula ministrada e defendida",
            "content": "Registro produzido e revisado por uma pessoa.", "demonstrated_level": 6,
            "validation_status": "VALIDATED",
        })
        self.assertEqual(evidence.status_code, status.HTTP_201_CREATED, evidence.data)
        self.assertEqual(evidence.data["validation_status"], "PENDING")
        reviewed = self.request("patch", reverse("library-sensei-evidence-review", kwargs={"pk": evidence.data["id"]}), {"validation_status": "VALIDATED", "feedback": "Defesa técnica aceita."})
        self.assertEqual(reviewed.status_code, status.HTTP_200_OK)
        stored = SenseiCompetencyEvidence.objects.get(pk=evidence.data["id"])
        self.assertEqual(stored.validated_by, self.admin)
        self.assertIsNotNone(stored.validated_at)

        promoted = self.request("patch", progress_url, {"current_level": 6, "state": "TEACHING_READY"})
        self.assertEqual(promoted.status_code, status.HTTP_200_OK, promoted.data)
        formation_progress = self.request("get", reverse("library-sensei-formation-progress", kwargs={"formation_pk": formation.pk}))
        self.assertEqual(formation_progress.data["percentage"], "100.00")
        self.assertEqual(formation_progress.data["state"], "COMPLETED")
        self.assertTrue(SenseiProgress.objects.filter(formation=formation, user=self.admin).exists())

    def test_studied_state_does_not_imply_demonstrated_competency(self):
        formation = self.create_formation("formation-study")
        competency = self.create_competency(formation, expected_level=2)
        response = self.request("patch", reverse("library-sensei-competency-progress", kwargs={"pk": competency.pk}), {"current_level": 0, "state": "STUDYING"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        progress = SenseiCompetencyProgress.objects.get(competency=competency, user=self.admin)
        self.assertEqual(progress.current_level, 0)
        overall = SenseiProgress.objects.get(formation=formation, user=self.admin)
        self.assertEqual(overall.percentage, 0)
        self.assertEqual(overall.state, "IN_PROGRESS")

    def test_permissions_local_only_and_private_formation_isolation(self):
        formation = self.create_formation("private-formation")
        detail = reverse("library-sensei-formation-detail", kwargs={"pk": formation.pk})
        self.client.force_authenticate(self.student)
        self.assertEqual(self.request("get", reverse("library-sensei-formations")).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.request("get", detail).status_code, status.HTTP_404_NOT_FOUND)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(detail, REMOTE_ADDR="198.51.100.10").status_code, status.HTTP_403_FORBIDDEN)

    def test_unit_study_plan_curated_sources_notes_and_study_do_not_grant_mastery(self):
        formation = self.create_formation("study-plan-domain")
        module = SenseiFormationModule.objects.create(formation=formation, title="Base", order=0)
        prerequisite = SenseiStudyUnit.objects.create(module=module, title="Vetores", objective="Compreender vetores", order=0)
        unit = SenseiStudyUnit.objects.create(module=module, title="Produto escalar", objective="Aplicar similaridade", order=1)
        competency = SenseiCompetency.objects.create(formation=formation, module=module, title="Aplicar similaridade", expected_level=4, mastery_criteria=["Calcula", "Implementa", "Justifica"], order=0)
        plan = SenseiUnitStudyPlan.objects.create(unit=unit, learning_objectives=["Compreender"], practices=["Calcular"], expected_evidence=["Notebook"], completion_criteria=["Explica e implementa"])
        plan.prerequisites.add(prerequisite)
        plan.related_competencies.add(competency)
        sources = [LibrarySource.objects.create(relative_path=f"curated-{index}.pdf", filename=f"Fonte {index}.pdf", extension="pdf") for index in range(2)]
        for index, source in enumerate(sources):
            response = self.request("post", reverse("library-sensei-unit-sources", kwargs={"unit_pk": unit.pk}), {
                "source": source.pk, "category": "PRIMARY" if index == 0 else "FOUNDATIONAL",
                "source_type": "PAPER" if index == 0 else "TECHNICAL_BOOK", "title": f"Fonte {index}",
                "reference": "Referência curada", "location": "Seção verificada — PDF p.1 a 1", "objective": "Apoiar o estudo",
                "priority": index + 1, "is_required": index == 0, "justification": "Fonte adequada à unidade.",
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
            reviewed = self.request("patch", reverse("library-sensei-unit-source-review", kwargs={"pk": response.data["id"]}), {"editorial_status": "APPROVED"})
            self.assertEqual(reviewed.status_code, status.HTTP_200_OK, reviewed.data)
        self.assertEqual(SenseiUnitSource.objects.filter(unit=unit).count(), 2)
        detail = self.request("get", reverse("library-sensei-unit-study-plan", kwargs={"pk": unit.pk}))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detail.data["curated_sources"]), 2)
        self.assertEqual(detail.data["prerequisites"][0]["id"], prerequisite.id)

        note_url = reverse("library-sensei-unit-notes", kwargs={"unit_pk": unit.pk})
        created_note = self.request("post", note_url, {"note_type": "QUESTION", "content": "Por que normalizar?"})
        self.assertEqual(created_note.status_code, status.HTTP_201_CREATED)
        SenseiStudyNote.objects.create(unit=unit, author=self.other, note_type="DISCOVERY", content="Nota privada")
        self.assertEqual(len(self.request("get", note_url).data), 1)

        studied = self.request("patch", reverse("library-sensei-unit-study-progress", kwargs={"pk": unit.pk}), {"status": "STUDIED"})
        self.assertEqual(studied.status_code, status.HTTP_200_OK)
        self.assertEqual(SenseiUnitStudyProgress.objects.get(unit=unit, user=self.admin).status, "STUDIED")
        self.assertFalse(SenseiCompetencyProgress.objects.filter(competency=competency, user=self.admin).exists())
        self.assertFalse(SenseiProgress.objects.filter(formation=formation, user=self.admin).exists())
        self.assertFalse(SenseiCompetencyEvidence.objects.filter(competency=competency).exists())

        foreign = self.create_formation("foreign-study-plan")
        foreign_module = SenseiFormationModule.objects.create(formation=foreign, title="Outro", order=0)
        foreign_unit = SenseiStudyUnit.objects.create(module=foreign_module, title="Outra", objective="Outra", order=0)
        invalid = self.request("patch", reverse("library-sensei-unit-study-plan", kwargs={"pk": unit.pk}), {"prerequisite_ids": [foreign_unit.id]})
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
