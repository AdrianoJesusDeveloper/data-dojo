import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import type { ComponentPropsWithoutRef } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: apiMocks }));
vi.mock("@/components/DojoHeader", () => ({ DojoHeader: () => <div>Header</div> }));
vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => () => ({}),
  Link: ({ to, ...props }: ComponentPropsWithoutRef<"a"> & { to?: string }) => <a href={to} {...props} />,
}));

import { HomePage } from "../routes/index";
import { useAuthStore } from "../lib/auth-store";

const course = { id: 7, title: "Python para Dados", description: "Formação" };
const lesson = { id: 11, title: "DataFrames", module: { title: "Pandas" } };
const progress = { percentage: "42.00", academic_state: "in_progress", completed_at: null };

describe("Home academic next step", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    useAuthStore.setState({ token: "token", isAuthenticated: true, isStaff: false, isSuperuser: false, accessLoaded: true });
  });

  it("shows loading then the first-course empty state", async () => {
    let resolve!: (value: unknown) => void;
    apiMocks.get.mockReturnValue(new Promise((done) => { resolve = done; }));
    render(<HomePage />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando sua jornada");
    resolve({ data: { type: "no_enrollment" } });
    expect(await screen.findByText("Escolha sua primeira formação")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Escolher um curso" })).toHaveAttribute("href", "/workspace");
  });

  it.each([
    ["start_course", "Comece sua formação", "Começar curso"],
    ["continue_lesson", "Continue sua aula", "Continuar aula"],
    ["next_lesson", "Continue aprendendo", "Continuar aprendendo"],
    ["course_completed", "Formação concluída", "Voltar ao Workspace"],
  ])("presents %s using the backend destination", async (type, heading, action) => {
    apiMocks.get.mockResolvedValue({ data: { type, course, lesson, course_progress: progress } });
    render(<HomePage />);
    expect(await screen.findByText(heading)).toBeInTheDocument();
    expect(screen.getByText("42%")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: action })).toHaveAttribute(
      "href", "/workspace?course=7&lesson=11",
    );
  });

  it("uses the semantic endpoint to finalize an eligible course", async () => {
    apiMocks.get
      .mockResolvedValueOnce({ data: { type: "complete_course", course, course_progress: { ...progress, percentage: "100.00" } } })
      .mockResolvedValueOnce({ data: { type: "course_completed", course, course_progress: { ...progress, percentage: "100.00", academic_state: "completed" } } });
    apiMocks.post.mockResolvedValue({ data: {} });
    render(<HomePage />);
    fireEvent.click(await screen.findByRole("button", { name: "Finalizar curso" }));
    await waitFor(() => expect(apiMocks.post).toHaveBeenCalledWith("/api/course-progress/by-course/7/complete/", {}));
    expect(await screen.findByText("Formação concluída")).toBeInTheDocument();
  });

  it("shows a non-destructive API error with retry and Workspace fallback", async () => {
    apiMocks.get.mockRejectedValue(new Error("network"));
    render(<HomePage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível carregar seu próximo passo");
    expect(screen.getByRole("link", { name: "Ir ao Workspace" })).toHaveAttribute("href", "/workspace");
  });

  it("does not create a false academic journey for administrators", async () => {
    useAuthStore.setState({ isStaff: true });
    apiMocks.get.mockResolvedValue({ data: { type: "administrative" } });
    render(<HomePage />);
    expect(await screen.findByText("Acesso administrativo")).toBeInTheDocument();
    expect(screen.queryByText("Progresso persistente")).not.toBeInTheDocument();
  });
});
