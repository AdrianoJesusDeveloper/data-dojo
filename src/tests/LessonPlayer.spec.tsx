import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({ post: vi.fn() }));
const toastMocks = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));

vi.mock("@/lib/api", () => ({ api: apiMocks }));
vi.mock("sonner", () => ({ toast: toastMocks }));
vi.mock("@/components/workspace/ExerciseCard", () => ({ ExerciseCard: () => null }));
vi.mock("@/components/workspace/CourseTree", () => ({ CourseTree: () => null }));

import { LessonPlayer } from "../components/workspace/LessonPlayer";

const course = { id: 1, title: "SQL", description: "Curso", modules: [] };
const lesson = {
  id: 3,
  title: "Consultas",
  content_type: "ARTICLE",
  file_upload: null,
  video_url: null,
  exercise: null,
};

function progress(status: "in_progress" | "completed", percentage = "0.00") {
  return { data: { status, course_progress_percentage: percentage } };
}

function renderPlayer(
  accessType: "enrollment" | "administrative" = "enrollment",
  onCourseProgressChange = vi.fn(),
) {
  render(
    <LessonPlayer
      course={course}
      currentLesson={lesson}
      setCurrentLesson={vi.fn()}
      setCode={vi.fn()}
      accessType={accessType}
      onCourseProgressChange={onCourseProgressChange}
    />,
  );
  return onCourseProgressChange;
}

describe("LessonPlayer academic activity", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("starts the lesson idempotently when an enrolled student opens it", async () => {
    apiMocks.post.mockResolvedValue(progress("in_progress"));
    renderPlayer();

    expect(await screen.findByText("Aula em andamento")).toBeInTheDocument();
    expect(apiMocks.post).toHaveBeenCalledWith(
      "/api/lesson-progress/by-lesson/3/start/",
      {},
    );
  });

  it("completes through the semantic endpoint and reports recalculated progress", async () => {
    apiMocks.post
      .mockResolvedValueOnce(progress("in_progress"))
      .mockResolvedValueOnce(progress("completed", "50.00"));
    const onCourseProgressChange = renderPlayer();
    fireEvent.click(await screen.findByRole("button", { name: "Marcar como concluída" }));

    expect(await screen.findByText("Aula concluída")).toBeInTheDocument();
    expect(apiMocks.post).toHaveBeenLastCalledWith(
      "/api/lesson-progress/by-lesson/3/complete/",
      {},
    );
    expect(onCourseProgressChange).toHaveBeenLastCalledWith("50.00");
  });

  it("shows an activity error without breaking the lesson", async () => {
    apiMocks.post.mockRejectedValue(new Error("unavailable"));
    renderPlayer();

    expect(await screen.findByText("Atividade não registrada")).toBeInTheDocument();
    expect(screen.getByText("Consultas")).toBeInTheDocument();
    expect(toastMocks.error).toHaveBeenCalled();
  });

  it("does not register academic activity for administrative access", async () => {
    renderPlayer("administrative");
    await waitFor(() => expect(apiMocks.post).not.toHaveBeenCalled());
    expect(screen.queryByText("Marcar como concluída")).not.toBeInTheDocument();
  });
});

describe("LessonPlayer content", () => {
  function renderContent(overrides: Record<string, unknown> = {}) {
    return render(<LessonPlayer course={course} currentLesson={{ ...lesson, ...overrides }} setCurrentLesson={vi.fn()} setCode={vi.fn()} accessType="administrative" onCourseProgressChange={vi.fn()} />);
  }

  it("renders ARTICLE headings, paragraphs, lists, links and code as read-only material", () => {
    const { container } = renderContent({ body: "## Objetivos\n\nAprenda consultas SQL.\n\n- Ler dados\n- Filtrar dados\n\n1. Abra o terminal\n2. Execute a consulta\n\nUse `SELECT` e consulte a [documentação](https://example.com/docs).\n\n```sql\nSELECT *\nFROM customers;\n```" });
    expect(screen.getByRole("article", { name: "Material didático" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Objetivos" })).toBeInTheDocument();
    expect(screen.getByText("Aprenda consultas SQL.").tagName).toBe("P");
    expect(screen.getAllByRole("list")).toHaveLength(2);
    expect(screen.getAllByRole("listitem")).toHaveLength(4);
    expect(screen.getByRole("link", { name: "documentação" })).toHaveAttribute("href", "https://example.com/docs");
    expect(screen.getByText("SELECT", { selector: "code" })).toBeInTheDocument();
    expect(container.querySelector("pre code")?.textContent).toBe("SELECT *\nFROM customers;\n");
    expect(container.querySelector("textarea, input, [contenteditable=true]")).toBeNull();
    expect(screen.queryByText("Nenhum vídeo disponível.")).not.toBeInTheDocument();
  });

  it.each([undefined, "", "  \n\t "])("shows a textual empty state for ARTICLE body %j", (body) => {
    renderContent({ body });
    expect(screen.getByText("Material desta aula ainda não disponível.")).toBeInTheDocument();
    expect(screen.queryByText("Nenhum vídeo disponível.")).not.toBeInTheDocument();
  });

  it("does not insert raw HTML, scripts or event handlers", () => {
    const { container } = renderContent({ body: '<script>alert(1)</script>\n\n<img src="x" onerror="alert(1)">\n\n<iframe src="https://example.com"></iframe>\n\nTexto seguro.' });
    expect(screen.getByText("Texto seguro.")).toBeInTheDocument();
    expect(container.querySelector("script, img, iframe, [onerror]")).toBeNull();
  });

  it.each(["javascript:alert%281%29", "data:text/html,test", "vbscript:msgbox%281%29"])("does not make unsafe URL %s navigable", (url) => {
    renderContent({ body: `[Perigoso](${url})` });
    expect(screen.getByText("Perigoso")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Perigoso" })).not.toBeInTheDocument();
  });

  it("preserves the VIDEO YouTube embed and its priority over uploaded media", () => {
    const { container } = renderContent({ content_type: "VIDEO", video_url: "https://youtu.be/example", file_upload: "/lesson.mp4", body: "Texto de outra modalidade" });
    expect(screen.getByTitle("Consultas")).toHaveAttribute("src", "https://www.youtube.com/embed/example");
    expect(container.querySelector("video")).toBeNull();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it.each(["VIDEO", "LAB"])("preserves uploaded media for %s", (content_type) => {
    const { container } = renderContent({ content_type, file_upload: "/lesson.mp4" });
    expect(container.querySelector("video")).toHaveAttribute("src", "/lesson.mp4");
    expect(container.querySelector("video")).toHaveAttribute("controls");
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it.each(["VIDEO", "LAB"])("preserves the missing media message for %s", (content_type) => {
    renderContent({ content_type });
    expect(screen.getByText("Nenhum vídeo disponível.")).toBeInTheDocument();
    expect(screen.queryByText("Material desta aula ainda não disponível.")).not.toBeInTheDocument();
  });
});
