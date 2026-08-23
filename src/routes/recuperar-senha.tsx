import { createFileRoute } from "@tanstack/react-router";
import ForgotPassword from "../pages/ForgotPassword";

export const Route = createFileRoute("/recuperar-senha")({
  component: ForgotPassword,
});
