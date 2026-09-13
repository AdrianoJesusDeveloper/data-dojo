import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post, put, toastError } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), toastError: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: { get, post, put } }));
vi.mock("sonner", () => ({ toast: { error: toastError } }));
import { SenseiLearningV1 } from "@/components/content-studio/SenseiLearningV1";

const renderPilot = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><SenseiLearningV1 formationId={501} unitId={10} enabled /></QueryClientProvider>);
const providers = (selected_provider: string | null = "groq") => ({ data: { providers: [{ id: "groq", label: "Groq", available: true }, { id: "gemini", label: "Gemini", available: true }, { id: "openai", label: "OpenAI", available: false }], selected_provider } });

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});

describe("SenseiLearningV1", () => {
  it("keeps prior attempts visible, retries the same activity and generates a new exercise independently", async () => {
    const base = { id: 4, activity_type_label: "Debugging", prompt: "Encontre o erro", difficulty_label: "Conhece", competency_title: "Fundamentos", state: "REVIEWED" };
    const first = { id: 1, attempt_number: 1, answer: "Primeira resposta", feedback: "Revise o caso vazio", outcome: "RETRY", identified_gap: "caso-limite", next_step: "Teste vazio", submitted_at: "2026-09-03T12:00:00Z" };
    const second = { id: 2, attempt_number: 2, answer: "Segunda resposta melhorada", feedback: "Evolução reconhecida", outcome: "DEEPEN", identified_gap: "", next_step: "Justifique", submitted_at: "2026-09-03T12:01:00Z" };
    get.mockImplementation((url: string) => url.includes("learning-providers") ? Promise.resolve(providers()) : Promise.resolve({ data: [{ ...base, attempts: [first, second] }] }));
    post.mockResolvedValue({ data: {} });
    renderPilot();
    expect(await screen.findByText("SENSEI DE APRENDIZAGEM")).toBeInTheDocument();
    expect(screen.getByText(/não é evidência validada nem demonstra competência/)).toBeInTheDocument();
    expect(await screen.findByText("Primeira resposta")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Sua resposta ao exercício" }), { target: { value: "Segunda resposta melhorada" } });
    fireEvent.click(screen.getByRole("button", { name: "TENTAR NOVAMENTE" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/sensei-learning-activities/4/answer/", { response: "Segunda resposta melhorada" }));
    expect(await screen.findByText("Segunda resposta melhorada")).toBeInTheDocument();
    expect(screen.getByText("Primeira resposta")).toBeInTheDocument();
    expect(screen.getByText("TENTATIVA 1")).toBeInTheDocument();
    expect(screen.getByText("TENTATIVA 2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "GERAR NOVO EXERCÍCIO" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/sensei-units/10/learning-activities/", {}));
  });

  it("stays hidden outside the pilot", () => {
    const { container } = render(<QueryClientProvider client={new QueryClient()}><SenseiLearningV1 formationId={501} unitId={11} enabled={false} /></QueryClientProvider>);
    expect(container).toBeEmptyDOMElement();
  });

  it("lists only available providers, shows the resolved provider and persists a change", async () => {
    get.mockImplementation((url: string) => url.includes("learning-providers") ? Promise.resolve(providers()) : Promise.resolve({ data: [] }));
    put.mockResolvedValue({ data: { provider: "gemini" } });
    renderPilot();
    const selector = await screen.findByRole("combobox", { name: "Provider de IA" });
    expect(selector).toHaveValue("groq");
    expect(screen.getByRole("option", { name: "Groq" })).toBeEnabled();
    expect(screen.getByRole("option", { name: "Gemini" })).toBeEnabled();
    expect(screen.queryByRole("option", { name: "OpenAI" })).not.toBeInTheDocument();
    fireEvent.change(selector, { target: { value: "gemini" } });
    expect(selector).toHaveValue("groq");
    await waitFor(() => expect(put).toHaveBeenCalledWith("/api/library/sensei-formations/501/learning-providers/", { provider: "gemini" }));
    await waitFor(() => expect(selector).toHaveValue("gemini"));
    expect(post).not.toHaveBeenCalled();
  });

  it("keeps the previous provider after a failed change", async () => {
    get.mockImplementation((url: string) => url.includes("learning-providers") ? Promise.resolve(providers()) : Promise.resolve({ data: [] }));
    put.mockRejectedValue(new Error("provider failure"));
    renderPilot();
    const selector = await screen.findByRole("combobox", { name: "Provider de IA" });
    fireEvent.change(selector, { target: { value: "gemini" } });
    await waitFor(() => expect(toastError).toHaveBeenCalledWith("Não foi possível alterar o provider. A preferência anterior foi mantida."));
    expect(selector).toHaveValue("groq");
  });

  it("handles provider loading, request error and empty availability", async () => {
    let resolveProviders!: (value: unknown) => void;
    get.mockImplementation((url: string) => url.includes("learning-providers") ? new Promise((resolve) => { resolveProviders = resolve; }) : Promise.resolve({ data: [] }));
    renderPilot();
    expect(screen.getByText("Carregando providers...")).toBeInTheDocument();
    resolveProviders({ data: { providers: [], selected_provider: null } });
    expect(await screen.findByText("Nenhum provider de IA está disponível no momento.")).toBeInTheDocument();

    get.mockImplementation((url: string) => url.includes("learning-providers") ? Promise.reject(new Error("request failure")) : Promise.resolve({ data: [] }));
    const { unmount } = renderPilot();
    expect(await screen.findByText("Não foi possível carregar os providers de IA.")).toBeInTheDocument();
    unmount();
  });

  it("isolates provider preferences and activity caches between formations", async () => {
    get.mockImplementation((url: string) => {
      if (url.includes("learning-providers")) return Promise.resolve(url.includes("/502/") ? providers("gemini") : providers("groq"));
      return Promise.resolve({ data: [] });
    });
    const client = new QueryClient();
    const view = render(<QueryClientProvider client={client}><SenseiLearningV1 formationId={501} unitId={10} enabled /></QueryClientProvider>);
    expect(await screen.findByRole("combobox", { name: "Provider de IA" })).toHaveValue("groq");
    view.rerender(<QueryClientProvider client={client}><SenseiLearningV1 formationId={502} unitId={20} enabled /></QueryClientProvider>);
    expect(await screen.findByRole("combobox", { name: "Provider de IA" })).toHaveValue("gemini");
    view.rerender(<QueryClientProvider client={client}><SenseiLearningV1 formationId={501} unitId={10} enabled /></QueryClientProvider>);
    expect(await screen.findByRole("combobox", { name: "Provider de IA" })).toHaveValue("groq");
  });

  it("shows provenance only when activity and attempt metadata exist", async () => {
    const activity = { id: 4, activity_type_label: "Debugging", prompt: "Encontre o erro", difficulty_label: "Conhece", competency_title: "Fundamentos", state: "REVIEWED", ai_provider: "groq", ai_model: "groq-model", attempts: [{ id: 1, attempt_number: 1, answer: "Resposta", feedback: "Feedback", outcome: "RETRY", identified_gap: "", next_step: "", ai_provider: "gemini", ai_model: "gemini-model", submitted_at: "2026-09-03T12:00:00Z" }] };
    get.mockImplementation((url: string) => url.includes("learning-providers") ? Promise.resolve(providers()) : Promise.resolve({ data: [{ ...activity, ai_provider: "", ai_model: "", attempts: [{ ...activity.attempts[0], ai_provider: "", ai_model: "" }] }] }));
    renderPilot();
    await screen.findByText("Encontre o erro");
    expect(screen.queryByText("Gerado por:")).not.toBeInTheDocument();
    expect(screen.queryByText("Avaliado por:")).not.toBeInTheDocument();
  });

  it("renders activity and attempt provenance when supplied by the API", async () => {
    const activity = { id: 4, activity_type_label: "Debugging", prompt: "Encontre o erro", difficulty_label: "Conhece", competency_title: "Fundamentos", state: "REVIEWED", ai_provider: "groq", ai_model: "groq-model", attempts: [{ id: 1, attempt_number: 1, answer: "Resposta", feedback: "Feedback", outcome: "RETRY", identified_gap: "", next_step: "", ai_provider: "gemini", ai_model: "gemini-model", submitted_at: "2026-09-03T12:00:00Z" }] };
    get.mockImplementation((url: string) => url.includes("learning-providers") ? Promise.resolve(providers()) : Promise.resolve({ data: [activity] }));
    renderPilot();
    expect(await screen.findByText("Gerado por: groq")).toBeInTheDocument();
    expect(screen.getByText("Modelo: groq-model")).toBeInTheDocument();
    expect(screen.getByText("Avaliado por: gemini")).toBeInTheDocument();
    expect(screen.getByText("Modelo: gemini-model")).toBeInTheDocument();
  });
});
