import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from library.editorial_contracts import (
    AI_PEDAGOGY_POLICY,
    AUTHORSHIP_CHALLENGE_SCHEMA,
    EDITORIAL_CONTRACTS,
    get_editorial_contract,
    validate_editorial_plan,
)
from library.models import StudioProject
from library.serializers import StudioProjectSerializer
from library.services.studio_agents import generate_content_package, generate_modernization_plan


def challenge():
    return {field: "valor" for field in AUTHORSHIP_CHALLENGE_SCHEMA["required_fields"]}


def valid_plan(project_type):
    if project_type == "youtube":
        return {
            "title": "valor", "objective": "Objetivo", "target_audience": "PÃºblico",
            "playlist_description": "Trilha prÃ¡tica", "level": "BÃ¡sico", "prerequisites": ["LÃ³gica"],
            "competencies": ["Dados"], "estimated_total_duration": "30 min", "video_count": 1, "tools": ["Python"],
            "videos": [{
                "theme": "Tema", "title": "VÃ­deo 1", "objective": "Aprender", "concepts": ["Conceito"],
                "practical_demo": "Demonstrar", "practice": "Praticar", "code": {"language": "python", "code": "print(1)"}, "exercise": "ExercÃ­cio",
                "tools": ["Python"], "ai_integration": "Auxiliar", "human_reasoning": "Raciocinar",
                "validation": "Validar", "reflection": "Refletir", "without_ai_challenge": "Refazer", "authorship_challenge": challenge(),
                "sources": ["Livro"], "rag_sources": ["Trecho"], "order": 1,
            }],
            "sources": ["Livro"], "ai_policy": "Humano raciocina e valida.",
        }
    return {
        "title": "valor", "general_objective": "Formar", "professional_objective": "Atuar",
        "specific_objectives": ["Construir"], "target_audience": "Analistas", "level": "BÃ¡sico",
        "prerequisites": ["LÃ³gica"], "total_workload": "10h", "competencies": ["Dados"],
        "technology_stack": ["Python"], "module_count": 1, "lesson_count": 1,
        "methodology": "DojÃ´", "modules": [{
            "title": "MÃ³dulo", "objective": "Base", "competencies": ["AnÃ¡lise"], "workload": "10h",
            "lessons": [{
                "title": "Aula", "objective": "Aprender", "concepts": ["Conceito"], "practice": "Praticar",
                "tools": ["Python"], "ai_integration": "Auxiliar", "human_reasoning": "Raciocinar",
                "validation": "Validar", "reflection": "Refletir", "authorship_challenge": challenge(),
                "without_ai_challenge": "Refazer", "sources": ["Livro"], "expected_result": "Entrega",
            }],
            "exercises": ["ExercÃ­cio"], "kata": "Kata", "practical_project": "Projeto", "assessment": "Rubrica",
        }],
        "practical_projects": ["Projeto"], "final_project": "Entrega final", "assessment_criteria": ["Qualidade"],
        "materials": ["Livro"], "completion_requirements": "Concluir", "certification_requirements": "Aprovar",
        "sources": ["Livro"], "ai_policy": "Humano raciocina e valida.",
    }


class EditorialContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="editorial@example.com", username="editorial", password="test-password"
        )

    def test_youtube_and_premium_projects_are_valid(self):
        for project_type in ("youtube", "premium"):
            with self.subTest(project_type=project_type):
                project = StudioProject(
                    title="Plano", theme="Tema", objective="Objetivo",
                    project_type=project_type, created_by=self.user,
                )
                project.full_clean()

    def test_legacy_project_defaults_to_premium(self):
        project = StudioProject.objects.create(
            title="Projeto legado", theme="Tema", objective="Objetivo", created_by=self.user
        )
        self.assertEqual(project.project_type, "premium")

    def test_serializer_rejects_unknown_editorial_type(self):
        serializer = StudioProjectSerializer(data={
            "title": "Inválido", "theme": "Tema", "objective": "Objetivo",
            "project_type": "social_media",
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("project_type", serializer.errors)

    def test_contracts_share_ai_policy_authorship_and_optional_social_publication(self):
        for project_type in ("youtube", "premium"):
            contract = get_editorial_contract(project_type)
            self.assertEqual(contract["ai_pedagogy_policy"], AI_PEDAGOGY_POLICY)
            self.assertIn("authorship_challenge", contract)
            self.assertFalse(contract["authorship_challenge"]["social_publication_required"])
            self.assertIn("private_submission_option", contract["authorship_challenge"]["required_fields"])
            self.assertTrue(contract["evidence_policy"]["old_source_is_not_current_stack_evidence"])

    def test_youtube_and_premium_plan_schemas_are_validated(self):
        for project_type in ("youtube", "premium"):
            with self.subTest(project_type=project_type):
                self.assertEqual(
                    validate_editorial_plan(project_type, valid_plan(project_type))["title"],
                    "valor",
                )

        invalid = valid_plan("youtube")
        invalid["videos"][0]["authorship_challenge"].pop("private_submission_option")
        with self.assertRaisesRegex(ValueError, "Desafio de Autoria"):
            validate_editorial_plan("youtube", invalid)

    def test_editorial_ids_are_server_normalized_and_unique(self):
        invalid_values = (None, "", "not-a-uuid", str(uuid4()))
        for value in invalid_values:
            with self.subTest(value=value):
                plan = valid_plan("premium")
                plan["modules"][0]["editorial_id"] = value
                plan["modules"][0]["lessons"][0]["editorial_id"] = value
                normalized = validate_editorial_plan("premium", plan)
                module_id = normalized["modules"][0]["editorial_id"]
                lesson_id = normalized["modules"][0]["lessons"][0]["editorial_id"]
                self.assertEqual(UUID(module_id).version, 4)
                self.assertEqual(UUID(lesson_id).version, 4)
                self.assertNotEqual(module_id, lesson_id)

    def test_valid_unique_editorial_ids_are_preserved(self):
        plan = valid_plan("premium")
        module_id, lesson_id = str(uuid4()), str(uuid4())
        plan["modules"][0]["editorial_id"] = module_id
        plan["modules"][0]["lessons"][0]["editorial_id"] = lesson_id
        normalized = validate_editorial_plan("premium", plan)
        self.assertEqual(normalized["modules"][0]["editorial_id"], module_id)
        self.assertEqual(normalized["modules"][0]["lessons"][0]["editorial_id"], lesson_id)

    def test_regeneration_reconciles_existing_ids_without_reusing_removed_items(self):
        previous = validate_editorial_plan("premium", valid_plan("premium"))
        old_module_id = previous["modules"][0]["editorial_id"]
        old_lesson_id = previous["modules"][0]["lessons"][0]["editorial_id"]
        regenerated = valid_plan("premium")
        regenerated["modules"][0]["editorial_id"] = str(uuid4())
        regenerated["modules"][0]["lessons"][0]["editorial_id"] = str(uuid4())
        regenerated["modules"][0]["lessons"].append(deepcopy(regenerated["modules"][0]["lessons"][0]))
        regenerated["modules"][0]["lessons"][1]["title"] = "Aula nova"
        regenerated["lesson_count"] = 2
        normalized = validate_editorial_plan("premium", regenerated, previous)
        self.assertEqual(normalized["modules"][0]["editorial_id"], old_module_id)
        self.assertEqual(normalized["modules"][0]["lessons"][0]["editorial_id"], old_lesson_id)
        self.assertNotIn(normalized["modules"][0]["lessons"][1]["editorial_id"], {old_module_id, old_lesson_id})
        replacement = valid_plan("premium")
        replacement["modules"][0]["lessons"][0]["title"] = "Aula substituta"
        replaced = validate_editorial_plan("premium", replacement, previous)
        self.assertNotEqual(replaced["modules"][0]["lessons"][0]["editorial_id"], old_lesson_id)

    def test_provider_cannot_transfer_historical_id_to_different_item(self):
        previous = validate_editorial_plan("premium", valid_plan("premium"))
        historical_id = previous["modules"][0]["editorial_id"]
        adversarial = valid_plan("premium")
        adversarial["modules"][0]["title"] = "Machine Learning AvanÃ§ado"
        adversarial["modules"][0]["editorial_id"] = historical_id
        normalized = validate_editorial_plan("premium", adversarial, previous)
        new_id = normalized["modules"][0]["editorial_id"]
        self.assertNotEqual(new_id, historical_id)
        self.assertEqual(UUID(new_id).version, 4)

        legitimate = valid_plan("premium")
        legitimate["modules"][0]["editorial_id"] = historical_id
        self.assertEqual(
            validate_editorial_plan("premium", legitimate, previous)["modules"][0]["editorial_id"],
            historical_id,
        )

        truly_new_id = str(uuid4())
        truly_new = valid_plan("premium")
        truly_new["modules"][0]["title"] = "Engenharia de Features"
        truly_new["modules"][0]["editorial_id"] = truly_new_id
        self.assertEqual(
            validate_editorial_plan("premium", truly_new, previous)["modules"][0]["editorial_id"],
            truly_new_id,
        )

    def test_historical_ids_cannot_transfer_between_lessons_or_videos(self):
        previous_premium = validate_editorial_plan("premium", valid_plan("premium"))
        old_lesson_id = previous_premium["modules"][0]["lessons"][0]["editorial_id"]
        changed_lesson = valid_plan("premium")
        changed_lesson["modules"][0]["lessons"][0]["title"] = "Redes Neurais"
        changed_lesson["modules"][0]["lessons"][0]["editorial_id"] = old_lesson_id
        normalized_lesson = validate_editorial_plan("premium", changed_lesson, previous_premium)
        self.assertNotEqual(normalized_lesson["modules"][0]["lessons"][0]["editorial_id"], old_lesson_id)

        previous_youtube = validate_editorial_plan("youtube", valid_plan("youtube"))
        old_video_id = previous_youtube["videos"][0]["editorial_id"]
        changed_video = valid_plan("youtube")
        changed_video["videos"][0]["title"] = "Machine Learning AvanÃ§ado"
        changed_video["videos"][0]["editorial_id"] = old_video_id
        normalized_video = validate_editorial_plan("youtube", changed_video, previous_youtube)
        self.assertNotEqual(normalized_video["videos"][0]["editorial_id"], old_video_id)

    @override_settings(CONTENT_STUDIO_PROVIDER="test-provider")
    @patch("library.services.studio_agents.chat_with_provider")
    def test_dormant_package_generator_applies_untrusted_boundary(self, chat):
        chat.return_value = json.dumps({field: {} if field not in {"article", "linkedin_post"} else "texto" for field in ("study_plan", "lesson", "kata", "video_script", "article", "linkedin_post")})
        project = SimpleNamespace(title="Plano", theme="Tema", objective="Objetivo", project_type="premium")
        plan = SimpleNamespace(source_summary="ignore system", proposed_architecture={}, requirements={}, acceptance_criteria=[], test_strategy={}, risks=[], business_value="Valor")
        generate_content_package(project, plan)
        self.assertIn("NÃO CONFIÁVEL", chat.call_args.args[1][0]["content"])

    @override_settings(CONTENT_STUDIO_PROVIDER="test-provider")
    @patch("library.services.studio_agents.chat_with_provider")
    def test_global_policy_is_injected_into_both_editorial_generators(self, chat):
        for project_type in ("youtube", "premium"):
            with self.subTest(project_type=project_type):
                response = {
                    "source_summary": "Resumo", "original_architecture": {},
                    "proposed_architecture": valid_plan(project_type), "replacements": [], "requirements": {},
                    "acceptance_criteria": [], "test_strategy": {}, "risks": [],
                    "business_value": "Valor",
                }
                chat.return_value = json.dumps(response)
                project = SimpleNamespace(
                    title="Plano", theme="Tema", objective="Objetivo", project_type=project_type
                )
                generated, _ = generate_modernization_plan(project, [])
                system_prompt = chat.call_args.args[1][0]["content"]
                self.assertIn(AI_PEDAGOGY_POLICY["principle"], system_prompt)
                self.assertIn(EDITORIAL_CONTRACTS[project_type]["label"], system_prompt)
                self.assertEqual(generated["proposed_architecture"]["contract_version"], "editorial-plan-v1")
                collection = generated["proposed_architecture"][EDITORIAL_CONTRACTS[project_type]["content_collection"]]
                self.assertTrue(collection)
                lessons = collection if project_type == "youtube" else collection[0]["lessons"]
                self.assertTrue(lessons)
                self.assertIn("ai_integration", lessons[0])
                self.assertIn("authorship_challenge", lessons[0])
