import { createFileRoute } from "@tanstack/react-router";
import ResetPassword from "../pages/ResetPassword";

export const Route = createFileRoute("/reset-password")({
  validateSearch: (search: Record<string, unknown>) => ({
    uid: String(search.uid ?? ""),
    token: String(search.token ?? ""),
  }),
  component: ResetPassword,
});
