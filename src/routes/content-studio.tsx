import { createFileRoute } from "@tanstack/react-router";
import ContentStudio from "../pages/ContentStudio";

export const Route = createFileRoute("/content-studio")({
  component: ContentStudio,
});
