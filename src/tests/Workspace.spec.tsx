import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: apiMocks }));
vi.mock("@/components/DojoHeader", () => ({ DojoHeader: () => <div>Header</div> }));
vi.mock("@/components/workspace/LessonPlayer", () => ({
  LessonPlayer: ({ course, setCurrentLesson, setCode, onCourseProgressChange }: {
    course: typeof courseResponse.data.results[number] | null;
    setCurrentLesson: (lesson: unknown) => void;
    setCode: (code: string) => void;
    onCourseProgressChange: (percentage: string) => void;
  }) => {
    const alternative = course?.modules[0]?.lessons[1];
    return <div>{alternative ? (
      <button onClick={() => {
        setCurrentLesson(alternative);
        setCode(alternative.body);
      }}>
        {alternative.title}
      </button>
    ) : <div>Lesson</div>}<button onClick={() => onCourseProgressChange("50.00")}>Simular conclusão</button></div>;
  },
}));
vi.mock("@/components/workspace/DojoTerminal", () => ({
  DojoTerminal: ({ lines }: { lines: string[] }) => (
    <div>{lines.map((line, index) => <div key={`${index}:${line}`}>{line}</div>)}</div>
  ),
}));
vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
  Toaster: () => null,
}));
vi.mock("@tanstack/react-router", () => ({ createFileRoute: vi.fn() }));

import Workspace from "../pages/Workspace";
import { ExerciseCard } from "../components/workspace/ExerciseCard";

const courseResponse = {
  data: {
    count: 1,
    next: null,
    previous: null,
    results: [
      {
        id: 1,
        title: "SQL",
        description: "Curso",
        modules: [
          {
            id: 2,
            title: "Módulo",
            order: 1,
            lessons: [
              {
                id: 3,
                title: "Consulta",
                content_type: "LAB",
                file_upload: null,
                video_url: null,
                body: "SELECT id FROM customers",
                order: 1,
                exercise: {
                  id: 4,
                  lesson: 3,
                  title: "Selecione nomes",
                  statement: "Escreva a consulta",
                  answer_type: "SQL",
                  points: 100,
                  submission: {
                    format: "text",
                    max_length: 20_000,
                    automated_evaluation: true,
                  },
                },
              },
              {
                id: 5,
                title: "Consulta alternativa",
                content_type: "LAB",
                file_upload: null,
                video_url: null,
                body: "SELECT id FROM customers",
                order: 2,
                exercise: {
                  id: 6,
                  lesson: 5,
                  title: "Selecione novamente",
                  statement: "Escreva outra consulta",
                  answer_type: "SQL",
                  points: 100,
                  submission: {
                    format: "text",
                    max_length: 20_000,
                    automated_evaluation: true,
                  },
                },
              },
            ],
          },
        ],
      },
    ],
  },
};

const enrolledAccessResponse = {
  data: {
    access_type: "enrollment",
    courses: courseResponse.data.results,
  },
};

const defaultProgressResponse = {
  data: {
    id: 20,
    enrollment: 9,
    course: courseResponse.data.results[0],
    percentage: "0.00",
    academic_state: "not_started",
    first_activity_at: null,
    last_activity_at: null,
    created_at: "2026-08-31T12:00:00Z",
    updated_at: "2026-08-31T12:00:00Z",
  },
};

function attempt(passed: boolean, message: string, attemptNumber = 1) {
  return {
    data: {
      id: 10,
      exercise: 4,
      attempt_number: attemptNumber,
      passed,
      feedback: { code: passed ? "accepted" : "not_accepted", message },
      evaluation_version: "v1",
      created_at: "2026-08-30T12:00:00Z",
    },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function renderWorkspace() {
  render(<Workspace />);
  return screen.findByRole("button", { name: "⚔ Compilar desafio" });
}

describe("Workspace server-side exercise submission", () => {
  let uuidIndex = 0;

  beforeEach(() => {
    vi.resetAllMocks();
    uuidIndex = 0;
    vi.stubGlobal("crypto", {
      randomUUID: vi.fn(() => `00000000-0000-4000-8000-${String(++uuidIndex).padStart(12, "0")}`),
    });
    apiMocks.get.mockImplementation((url: string) => {
      if (url === "/api/enrollments/access/") return Promise.resolve(enrolledAccessResponse);
      if (url.startsWith("/api/course-progress/")) return Promise.resolve(defaultProgressResponse);
      return Promise.resolve(courseResponse);
    });
  });

  it("sends the edited code and shows analyzing while preventing duplicate clicks", async () => {
    const pending = deferred<ReturnType<typeof attempt>>();
    apiMocks.post.mockReturnValue(pending.promise);
    const button = await renderWorkspace();
    const editor = screen.getByRole("textbox");
    fireEvent.change(editor, { target: { value: "SELECT name FROM customers" } });
    fireEvent.click(button);
    fireEvent.click(button);

    expect(screen.getByRole("button", { name: "Analisando..." })).toBeDisabled();
    expect(apiMocks.post).toHaveBeenCalledTimes(1);
    expect(apiMocks.post).toHaveBeenCalledWith(
      "/api/exercises/4/attempts/",
      expect.objectContaining({ submitted_answer: "SELECT name FROM customers" }),
    );
    expect(apiMocks.post.mock.calls[0][1]).not.toHaveProperty("passed");
    expect(apiMocks.post.mock.calls[0][1]).not.toHaveProperty("correct");
    expect(apiMocks.post.mock.calls[0][1]).not.toHaveProperty("score");

    pending.resolve(attempt(true, "Resposta aprovada."));
    expect(await screen.findByText("✓ DESAFIO APROVADO")).toBeInTheDocument();
    expect(screen.getByText("↳ Tentativa #1 registrada.")).toBeInTheDocument();
    expect(screen.queryByText(/XP/)).not.toBeInTheDocument();
  });

  it("shows safe feedback and never approves a failed answer", async () => {
    apiMocks.post.mockResolvedValue(attempt(false, "Revise sua resposta."));
    const button = await renderWorkspace();
    fireEvent.click(button);
    expect(await screen.findByText("✗ Revise sua resposta.")).toBeInTheDocument();
    expect(screen.queryByText("✓ DESAFIO APROVADO")).not.toBeInTheDocument();
  });

  it("does not approve when the HTTP request fails", async () => {
    apiMocks.post.mockRejectedValue(new Error("network"));
    const button = await renderWorkspace();
    fireEvent.click(button);
    expect(
      await screen.findByText("✗ Não foi possível enviar a tentativa. Tente novamente."),
    ).toBeInTheDocument();
    expect(screen.queryByText("✓ DESAFIO APROVADO")).not.toBeInTheDocument();
  });

  it("reuses the idempotency key for a technical retry of the same answer", async () => {
    apiMocks.post
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce(attempt(true, "Resposta aprovada."));
    const button = await renderWorkspace();
    fireEvent.click(button);
    await waitFor(() => expect(button).not.toBeDisabled());
    fireEvent.click(button);
    await screen.findByText("✓ DESAFIO APROVADO");

    const firstPayload = apiMocks.post.mock.calls[0][1];
    const retryPayload = apiMocks.post.mock.calls[1][1];
    expect(retryPayload.idempotency_key).toBe(firstPayload.idempotency_key);
    expect(retryPayload.submitted_answer).toBe(firstPayload.submitted_answer);
  });

  it("creates a new idempotency key after the answer changes", async () => {
    apiMocks.post
      .mockResolvedValueOnce(attempt(false, "Ainda não."))
      .mockResolvedValueOnce(attempt(true, "Resposta aprovada."));
    const button = await renderWorkspace();
    fireEvent.click(button);
    await screen.findByText("✗ Ainda não.");
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "SELECT name FROM customers" },
    });
    fireEvent.click(button);
    await screen.findByText("✓ DESAFIO APROVADO");

    expect(apiMocks.post.mock.calls[1][1].idempotency_key).not.toBe(
      apiMocks.post.mock.calls[0][1].idempotency_key,
    );
  });

  it("creates a new idempotency key when switching exercises with the same answer", async () => {
    apiMocks.post
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce(attempt(true, "Resposta aprovada."));
    const button = await renderWorkspace();
    fireEvent.click(button);
    await waitFor(() => expect(button).not.toBeDisabled());

    fireEvent.click(screen.getByRole("button", { name: /Consulta alternativa/ }));
    fireEvent.click(button);
    await screen.findByText("✓ DESAFIO APROVADO");

    expect(apiMocks.post.mock.calls[0][0]).toBe("/api/exercises/4/attempts/");
    expect(apiMocks.post.mock.calls[1][0]).toBe("/api/exercises/6/attempts/");
    expect(apiMocks.post.mock.calls[1][1].submitted_answer).toBe(
      apiMocks.post.mock.calls[0][1].submitted_answer,
    );
    expect(apiMocks.post.mock.calls[1][1].idempotency_key).not.toBe(
      apiMocks.post.mock.calls[0][1].idempotency_key,
    );
  });

  it("preserves the logical submission after a malformed successful response", async () => {
    apiMocks.post
      .mockResolvedValueOnce({ data: { unexpected: true } })
      .mockResolvedValueOnce(attempt(true, "Resposta aprovada."));
    const button = await renderWorkspace();
    fireEvent.click(button);
    await screen.findByText("✗ Não foi possível enviar a tentativa. Tente novamente.");
    await waitFor(() => expect(button).not.toBeDisabled());
    fireEvent.click(button);
    await screen.findByText("✓ DESAFIO APROVADO");

    expect(apiMocks.post.mock.calls[1][1]).toEqual(apiMocks.post.mock.calls[0][1]);
  });
});

describe("ExerciseCard public contract", () => {
  it("renders without private expected keywords", () => {
    render(
      <ExerciseCard
        exercise={{
          title: "Consulta",
          answer_type: "SQL",
          statement: "Selecione os nomes.",
        }}
      />,
    );
    expect(screen.getByText("Consulta")).toBeInTheDocument();
    expect(screen.getByText("Selecione os nomes.")).toBeInTheDocument();
    expect(screen.queryByText(/Critérios:/)).not.toBeInTheDocument();
  });
});

describe("Workspace enrollment contract", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows the course catalog when the user has no active enrollment", async () => {
    apiMocks.get
      .mockResolvedValueOnce(courseResponse)
      .mockResolvedValueOnce({ data: { access_type: "none", courses: [] } });

    render(<Workspace />);

    expect(await screen.findByText("Escolha sua formação")).toBeInTheDocument();
    expect(screen.getByText("SQL")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Matricular-se" })).toBeInTheDocument();
    expect(apiMocks.get).toHaveBeenNthCalledWith(2, "/api/enrollments/access/");
  });

  it("enrolls using only course_id and opens the existing workspace", async () => {
    apiMocks.get
      .mockResolvedValueOnce(courseResponse)
      .mockResolvedValueOnce({ data: { access_type: "none", courses: [] } })
      .mockResolvedValueOnce(defaultProgressResponse);
    apiMocks.post.mockResolvedValue({ data: { id: 9, status: "active" } });

    render(<Workspace />);
    fireEvent.click(await screen.findByRole("button", { name: "Matricular-se" }));

    await waitFor(() => {
      expect(apiMocks.post).toHaveBeenCalledWith("/api/enrollments/", { course_id: 1 });
    });
    expect(await screen.findByRole("button", { name: "⚔ Compilar desafio" })).toBeInTheDocument();
  });

  it("renders an explicit enrollment loading error with retry", async () => {
    apiMocks.get.mockRejectedValue(new Error("unauthorized"));
    render(<Workspace />);
    expect(await screen.findByText("Não foi possível carregar o Workspace.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("opens courses with an administrative access indicator and no enrollment prompt", async () => {
    apiMocks.get
      .mockResolvedValueOnce(courseResponse)
      .mockResolvedValueOnce({
        data: { access_type: "administrative", courses: courseResponse.data.results },
      });

    render(<Workspace />);

    expect(await screen.findByText("Acesso administrativo")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "⚔ Compilar desafio" })).not.toBeInTheDocument();
    expect(screen.getByText("Prévia administrativa: submissões acadêmicas desativadas.")).toBeInTheDocument();
    expect(screen.queryByText("Matricule-se para acessar o conteúdo no Workspace.")).not.toBeInTheDocument();
    expect(apiMocks.post).not.toHaveBeenCalledWith(
      "/api/enrollments/",
      expect.anything(),
    );
    expect(apiMocks.get).not.toHaveBeenCalledWith(expect.stringContaining("/api/course-progress/"));
  });

  it("shows a safe zero state for an enrolled course without activity", async () => {
    apiMocks.get
      .mockResolvedValueOnce(courseResponse)
      .mockResolvedValueOnce(enrolledAccessResponse)
      .mockResolvedValueOnce(defaultProgressResponse);

    render(<Workspace />);

    expect(await screen.findByText("Progresso: 0%")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "⚔ Compilar desafio" })).toBeInTheDocument();
  });

  it("shows persisted progress without accepting a frontend percentage", async () => {
    apiMocks.get
      .mockResolvedValueOnce(courseResponse)
      .mockResolvedValueOnce(enrolledAccessResponse)
      .mockResolvedValueOnce({
        data: { ...defaultProgressResponse.data, percentage: "35.00" },
      });

    render(<Workspace />);

    expect(await screen.findByText("Progresso: 35%")).toBeInTheDocument();
    expect(apiMocks.post).not.toHaveBeenCalledWith(
      expect.stringContaining("course-progress"),
      expect.anything(),
    );
  });

  it("keeps the workspace usable when progress loading fails", async () => {
    apiMocks.get
      .mockResolvedValueOnce(courseResponse)
      .mockResolvedValueOnce(enrolledAccessResponse)
      .mockRejectedValueOnce(new Error("progress unavailable"));

    render(<Workspace />);

    expect(await screen.findByText("Progresso indisponível.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "⚔ Compilar desafio" })).toBeInTheDocument();
  });

  it("shows the course percentage recalculated after a lesson transition", async () => {
    apiMocks.get
      .mockResolvedValueOnce(courseResponse)
      .mockResolvedValueOnce(enrolledAccessResponse)
      .mockResolvedValueOnce(defaultProgressResponse);
    render(<Workspace />);
    await screen.findByText("Progresso: 0%");

    fireEvent.click(screen.getByRole("button", { name: "Simular conclusão" }));

    expect(await screen.findByText("Progresso: 50%")).toBeInTheDocument();
  });
});
