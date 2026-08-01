import { createFileRoute } from "@tanstack/react-router";
import { HomePage } from "../pages/HomePage";
import { About } from "../components/About";

export const Route = createFileRoute("/")({
  component: HomePage,
});