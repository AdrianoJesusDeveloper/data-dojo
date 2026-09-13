import { createFileRoute } from "@tanstack/react-router";
import ContentStudio from "../pages/ContentStudio";
import { requireAdministrativeAccess } from "../lib/admin-access";

export const Route = createFileRoute("/content-studio")({
  beforeLoad: requireAdministrativeAccess,
  component: ContentStudio,
});
