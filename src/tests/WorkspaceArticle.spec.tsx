import { fireEvent, render, screen, within } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: apiMocks }));
vi.mock("@/components/DojoHeader", () => ({ DojoHeader: () => null }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() }, Toaster: () => null }));
vi.mock("@tanstack/react-router", () => ({ createFileRoute: vi.fn() }));

import Workspace from "../pages/Workspace";

// Keep the real LessonPlayer, CourseTree and CodeEditor to exercise both selection paths.
const article = { id: 1, title: "Material técnico", content_type: "ARTICLE", body: "## Conceito técnico\n\nMaterial complementar.", exercise: null };

async function openWorkspace(lessons: Array<{ id: number; title: string; content_type: string; body?: string; exercise: null }>) {
  const course = { id: 1, title: "SQL", description: "Curso", modules: [{ id: 1, title: "Módulo", lessons }] };
  apiMocks.get.mockImplementation((url: string) => Promise.resolve({ data: url === "/api/enrollments/access/"
    ? { access_type: "administrative", courses: [course] }
    : { results: [course] } }));
  render(<Workspace />);
  return screen.findByRole("textbox");
}

describe("Workspace ARTICLE editor isolation", () => {
  beforeEach(() => { vi.resetAllMocks(); });

  it("opens ARTICLE with an empty editor while retaining its material in LessonPlayer", async () => {
    const editor = await openWorkspace([article]);
    expect(editor).toHaveValue("");
    expect(within(screen.getByRole("article", { name: "Material didático" })).getByRole("heading", { name: "Conceito técnico" })).toBeInTheDocument();
  });

  it.each(["VIDEO", "LAB"])("clears edited %s content on ARTICLE selection and restores that lesson's body on return", async (content_type) => {
    const practice = { id: 2, title: "Prática", content_type, body: "SELECT id FROM customers", exercise: null };
    const editor = await openWorkspace([practice, article]);
    expect(editor).toHaveValue(practice.body);
    fireEvent.change(editor, { target: { value: "Resposta em edição" } });
    fireEvent.click(screen.getByRole("button", { name: /Material técnico/ }));
    expect(editor).toHaveValue("");
    expect(screen.getByRole("heading", { name: "Conceito técnico" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Prática/ }));
    expect(editor).toHaveValue(practice.body);
    expect(screen.queryByRole("article", { name: "Material didático" })).not.toBeInTheDocument();
  });

  it.each(["VIDEO", "LAB"])("loads %s body when leaving an initially selected ARTICLE", async (content_type) => {
    const editor = await openWorkspace([article, { id: 2, title: "Prática", content_type, body: "SELECT 1", exercise: null }]);
    fireEvent.click(screen.getByRole("button", { name: /Prática/ }));
    expect(editor).toHaveValue("SELECT 1");
  });

  it.each([
    ["VIDEO", undefined], ["VIDEO", ""], ["LAB", undefined], ["LAB", ""],
  ])("clears residual content when selecting %s with body %j", async (content_type, body) => {
    const editor = await openWorkspace([
      { id: 2, title: "Prática", content_type: "LAB", body: "SELECT 1", exercise: null },
      { id: 3, title: "Sem conteúdo", content_type: content_type!, body, exercise: null },
    ]);
    expect(editor).toHaveValue("SELECT 1");
    fireEvent.click(screen.getByRole("button", { name: /Sem conteúdo/ }));
    expect(editor).toHaveValue("");
  });
});
