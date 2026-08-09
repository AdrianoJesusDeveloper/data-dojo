import { createFileRoute } from "@tanstack/react-router";
import AiSales from "../pages/AiSales";

export const Route = createFileRoute("/ai-sales")({
  component: AiSales,
});