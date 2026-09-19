import { createFileRoute } from "@tanstack/react-router";
import LibraryMedia from "@/pages/LibraryMedia";
import { requireAdministrativeAccess } from "@/lib/admin-access";
export const Route = createFileRoute("/library/media")({ beforeLoad: requireAdministrativeAccess, component: LibraryMedia });
