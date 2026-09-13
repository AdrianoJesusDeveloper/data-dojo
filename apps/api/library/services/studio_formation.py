from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.text import slugify

from ..models import SenseiCompetency, SenseiFormation, SenseiFormationModule, SenseiStudyUnit, SenseiUnitStudyPlan, StudioFormationLink
from ..editorial_contracts import normalize_project_type


class StudioFormationError(RuntimeError):
    pass


@transaction.atomic
def materialize_premium_formation(project, user):
    if (
        normalize_project_type(project.project_type) != "formation"
        or not hasattr(project, "modernization_plan")
        or project.modernization_plan.status != "approved"
    ):
        raise StudioFormationError("Somente um plano Premium aprovado pode ser materializado.")
    plan = project.modernization_plan.proposed_architecture
    link = StudioFormationLink.objects.select_for_update().filter(project=project).select_related("formation").first()
    if link and link.synced_plan_version == project.modernization_plan.version:
        return link, False
    if link:
        formation = link.formation
    else:
        base_slug = slugify(plan.get("title") or project.title)[:230] or f"studio-{project.pk}"
        slug = base_slug if not SenseiFormation.objects.filter(slug=base_slug).exists() else f"{base_slug}-{project.pk}"
        formation = SenseiFormation.objects.create(title=project.title, slug=slug, objective=project.objective, created_by=user)
        link = StudioFormationLink.objects.create(project=project, formation=formation)
    formation.title = str(plan.get("title") or project.title)[:255]
    formation.description = str(plan.get("general_objective") or project.objective)
    formation.objective = str(plan.get("professional_objective") or project.objective)
    formation.level = str(plan.get("level") or "")[:80]
    formation.save(update_fields=["title", "description", "objective", "level", "updated_at"])
    identity = dict(link.identity_map or {})
    formation.modules.update(order=F("order") + 10000)
    active_unit_ids = []
    for module_order, module_data in enumerate(plan.get("modules", [])):
        editorial_id = str(module_data["editorial_id"])
        module = SenseiFormationModule.objects.filter(pk=identity.get("modules", {}).get(editorial_id), formation=formation).first()
        if not module:
            module = SenseiFormationModule.objects.create(formation=formation, title=module_data["title"], order=module_order)
        module.title, module.description, module.order = module_data["title"], module_data.get("objective", ""), module_order
        module.save()
        identity.setdefault("modules", {})[editorial_id] = module.pk
        module.study_units.update(order=F("order") + 10000)
        for unit_order, lesson_data in enumerate(module_data.get("lessons", [])):
            lesson_id = str(lesson_data["editorial_id"])
            unit = SenseiStudyUnit.objects.filter(pk=identity.get("units", {}).get(lesson_id), module__formation=formation).first()
            if not unit:
                unit = SenseiStudyUnit.objects.create(module=module, title=lesson_data["title"], objective=lesson_data["objective"], order=unit_order)
            unit.module, unit.title, unit.objective, unit.order, unit.status = module, lesson_data["title"], lesson_data["objective"], unit_order, SenseiStudyUnit.Status.ACTIVE
            unit.reference_links = [{"kind": "EDITORIAL_SOURCE", "reference": source} for source in lesson_data.get("sources", [])]
            unit.save()
            SenseiUnitStudyPlan.objects.update_or_create(unit=unit, defaults={
                "learning_objectives": [lesson_data["objective"]], "practices": [lesson_data.get("practice", "")],
                "expected_evidence": [lesson_data.get("expected_result", "")],
                "completion_criteria": [lesson_data.get("validation", "")], "guidance": lesson_data.get("human_reasoning", ""),
            })
            identity.setdefault("units", {})[lesson_id] = unit.pk
            active_unit_ids.append(unit.pk)
    SenseiStudyUnit.objects.filter(module__formation=formation).exclude(pk__in=active_unit_ids).update(status=SenseiStudyUnit.Status.ARCHIVED)
    for order, title in enumerate(plan.get("competencies", [])):
        value = title if isinstance(title, str) else title.get("title", "Competência")
        key = slugify(str(value)) or f"competency-{order}"
        competency, _ = SenseiCompetency.objects.update_or_create(
            pk=identity.get("competencies", {}).get(key), formation=formation,
            defaults={"title": str(value)[:255], "description": str(value), "mastery_criteria": ["Demonstrar e justificar a competência em evidência revisada."], "order": order},
        )
        identity.setdefault("competencies", {})[key] = competency.pk
    link.synced_plan_version = project.modernization_plan.version
    link.identity_map = identity
    link.synced_at = timezone.now()
    link.save(update_fields=["synced_plan_version", "identity_map", "synced_at", "updated_at"])
    return link, True
