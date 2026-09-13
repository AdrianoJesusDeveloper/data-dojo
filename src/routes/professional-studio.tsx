import { createFileRoute } from "@tanstack/react-router";
import ProfessionalStudio from "../pages/ProfessionalStudio";
import { requireAdministrativeAccess } from "../lib/admin-access";

export const Route = createFileRoute("/professional-studio")({
  beforeLoad: requireAdministrativeAccess,
  component: ProfessionalStudio,
});
