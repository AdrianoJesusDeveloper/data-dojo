import { createFileRoute } from "@tanstack/react-router";
import AboutSensey from "../pages/AboutSensey";

export const Route = createFileRoute("/conheca-sensey")({
  component: AboutSensey,
});
