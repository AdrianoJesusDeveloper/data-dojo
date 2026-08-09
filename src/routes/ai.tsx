import { createFileRoute } from "@tanstack/react-router";
import Ai from "../pages/Ai";

export const Route = createFileRoute("/ai")({
  component: Ai,
});