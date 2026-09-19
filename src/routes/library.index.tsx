import { createFileRoute } from "@tanstack/react-router";
import Library from "@/pages/Library";
import { requireAdministrativeAccess } from "@/lib/admin-access";
export const Route = createFileRoute("/library/")({ beforeLoad: requireAdministrativeAccess, component: Library });
