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
  LessonPlayer: ({ course, setCurrentLesson, setCode }: {
    course: typeof courseResponse.data.results[number] | null;
    setCurrentLesson: (lesson: unknown) => void;
    setCode: (code: string) => void;
  }) => {
    const alternative = course?.modules[0]?.lessons[1];
    return alternative ? (
      <button onClick={() => {
        setCurrentLesson(alternative);
        setCode(alternative.body);
      }}>
        {alternative.title}
      </button>
    ) : <div>Lesson</div>;
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

function attempt(passed: boolean, message: string) {
  return {
    data: {
      id: 10,
      exercise: 4,
      attempt_number: 1,
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
    apiMocks.get.mockResolvedValue(courseResponse);
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

    pending.resolve(attempt(true, "Resposta aprovada."));
    expect(await screen.findByText("✓ DESAFIO APROVADO")).toBeInTheDocument();
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
