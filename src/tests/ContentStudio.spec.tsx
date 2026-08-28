import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";

const { get, post, put } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));

vi.mock("@/lib/api", () => ({
  API_ORIGIN: "http://127.0.0.1:8000",
  api: { get, post, put },
}));

vi.mock("@/components/DojoHeader", () => ({ DojoHeader: () => <div>Header</div> }));

import ContentStudio from "@/pages/ContentStudio";

const source = (id: number, overrides = {}) => ({
  id,
  relative_path: `livro-${id}.pdf`,
  filename: `livro-${id}.pdf`,
  extension: "pdf",
  size_bytes: 100,
  sha256: `hash-${id}`,
  status: "supported",
  modified_at: null,
  duplicate: false,
  book_id: null,
  book_status: null,
  book_error: "",
  ...overrides,
});

describe("ContentStudio catalog actions", () => {
  it("edits with save/cancel, comments, prints, previews and generates a selected draft", async () => {
    const plan = { contract_version: "editorial-plan-v1", title: "Plano editável", general_objective: "Formar", professional_objective: "Atuar", specific_objectives: ["Criar"], target_audience: "Analistas", level: "Básico", prerequisites: ["Lógica"], total_workload: "10h", competencies: ["Dados"], technology_stack: ["Python"], module_count: 1, lesson_count: 1, methodology: "Dojô", modules: [{ title: "Módulo teste", objective: "Base", competencies: ["Análise"], workload: "10h", lessons: [{ title: "Aula teste", objective: "Aprender", concepts: ["Conceito"], practice: "Prática", tools: ["Python"], ai_integration: "Apoiar", human_reasoning: "Pensar", validation: "Testar", reflection: "Explicar", authorship_challenge: { independent_explanation: "Explicar", practical_challenge: "Criar", portfolio_artifact: "Notebook", reflection_question: "Por quê?", comprehension_criteria: "Defender", responsible_ai_use: "Registrar", must_not_delegate_to_ai: "Pensar", expected_result: "Entrega", private_submission_option: "Privado" }, sources: ["Livro"], expected_result: "Entrega" }], exercises: ["Exercício"], kata: "Kata", practical_project: "Projeto", assessment: "Rubrica" }], practical_projects: ["Projeto"], final_project: "Final", assessment_criteria: ["Qualidade"], materials: ["Livro"], completion_requirements: "Concluir", certification_requirements: "Aprovar", sources: ["Livro"] };
    const project = { id: 77, title: "Projeto Marco 3", theme: "Dados", objective: "Ensinar", project_type: "premium", status: "approved", books: [1], citations: [], modernization_plan: { status: "approved", proposed_architecture: plan }, editorial_comments: [], is_archived: false, content_package: { generated_items: [{ id: "stable-generated-id", target_type: "lesson", target_id: "stable-lesson-id", target_index: 0, plan_version: 2, generation: 3, content: { text: "Conteúdo persistido" } }] } };
    get.mockImplementation((url: string) => {
      if (url.endsWith("studio/status/")) return Promise.resolve({ data: { enabled: true, local_only: true, sources: 0, supported: 0, unsupported: 0, missing: 0, books: 0, ready_books: 0, scripts: 0 } });
      if (url.endsWith("studio/projects/")) return Promise.resolve({ data: { results: [project] } });
      if (url.endsWith("sources/")) return Promise.resolve({ data: { count: 0, previous: null, next: null, results: [] } });
      return Promise.resolve({ data: { results: [] } });
    });
    put.mockResolvedValue({ data: project });
    post.mockResolvedValue({ data: project });
    const print = vi.spyOn(window, "print").mockImplementation(() => undefined);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><ContentStudio /></QueryClientProvider>);

    await screen.findByText("Plano editável");
    expect(screen.getByText(/plano v2 .* geração 3/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Editar plano" }));
    fireEvent.change(screen.getByDisplayValue("Plano editável"), { target: { value: "Alteração cancelada" } });
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(put).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Editar plano" }));
    fireEvent.change(screen.getByDisplayValue("Plano editável"), { target: { value: "Plano v2" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar nova versão" }));
    await waitFor(() => expect(put).toHaveBeenCalledWith("/api/library/studio/projects/77/plan/", { plan: expect.objectContaining({ title: "Plano v2" }) }));

    fireEvent.change(screen.getByPlaceholderText("Adicionar comentário"), { target: { value: "Revisar a aula" } });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar comentário" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/studio/projects/77/comments/", { text: "Revisar a aula", target_type: "plan", target_id: "" }));
    fireEvent.click(screen.getByRole("button", { name: "Imprimir / Exportar PDF" }));
    expect(print).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Visualizar como aluno" }));
    expect(screen.getByText("Prévia do aluno · não publicada")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "Item para geração" }), { target: { value: "lesson:0" } });
    fireEvent.click(screen.getByRole("button", { name: "Gerar conteúdo" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/studio/projects/77/generate-content/", { target_type: "lesson", target_index: 0 }));
    fireEvent.click(screen.getByRole("button", { name: "Arquivar projeto" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/studio/projects/77/archive/", { archived: true }));
  });

  it("shows the total and reaches an item on the last page without a silent slice", async () => {
    const catalog = Array.from({ length: 27 }, (_, index) => source(index + 1));
    get.mockImplementation((url: string, config?: { params?: { page?: number; page_size?: number; search?: string } }) => {
      if (url.endsWith("studio/status/")) return Promise.resolve({ data: { enabled: true, local_only: true, sources: 27, supported: 27, unsupported: 0, missing: 0, books: 0, ready_books: 0, scripts: 0 } });
      if (url.endsWith("sources/")) {
        const page = config?.params?.page ?? 1;
        const pageSize = config?.params?.page_size ?? 25;
        const filtered = config?.params?.search ? catalog.filter((item) => item.filename.includes(config.params!.search!)) : catalog;
        const results = filtered.slice((page - 1) * pageSize, page * pageSize);
        return Promise.resolve({ data: { count: filtered.length, previous: page > 1 ? "previous" : null, next: page * pageSize < filtered.length ? "next" : null, results } });
      }
      return Promise.resolve({ data: { results: [] } });
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><ContentStudio /></QueryClientProvider>);

    expect(await screen.findByText("27 livros encontrados sem expor caminhos absolutos.")).toBeInTheDocument();
    expect(screen.queryByText("livro-27.pdf")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Próxima →" }));
    expect(await screen.findByText("Página 2 de 2")).toBeInTheDocument();
    expect((await screen.findAllByText("livro-27.pdf")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "← Anterior" }));
    expect(await screen.findByText("Página 1 de 2")).toBeInTheDocument();
  });

  it("sends search to the API and finds a title beyond the current page", async () => {
    get.mockImplementation((url: string, config?: { params?: { search?: string } }) => {
      if (url.endsWith("studio/status/")) return Promise.resolve({ data: { enabled: true, local_only: true, sources: 187, supported: 187, unsupported: 0, missing: 0, books: 0, ready_books: 0, scripts: 0 } });
      if (url.endsWith("sources/")) {
        const results = config?.params?.search === "Livro distante" ? [source(187, { filename: "Livro distante.pdf", relative_path: "fim/Livro distante.pdf" })] : [];
        return Promise.resolve({ data: { count: results.length, previous: null, next: null, results } });
      }
      return Promise.resolve({ data: { results: [] } });
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><ContentStudio /></QueryClientProvider>);
    fireEvent.change(await screen.findByPlaceholderText("Buscar título em todo o catálogo"), { target: { value: "Livro distante" } });
    expect((await screen.findAllByText("Livro distante.pdf")).length).toBeGreaterThan(0);
    expect(get).toHaveBeenCalledWith("/api/library/sources/", { params: expect.objectContaining({ search: "Livro distante", page: 1, page_size: 25 }) });
  });

  it("uses the editorial view by default, keeps JSON accessible and preserves approval", async () => {
    const project = {
      id: 31, title: "Formação editorial", theme: "Dados", objective: "Ensinar", project_type: "premium", status: "planned", books: [11], citations: [],
      modernization_plan: { source_summary: "Resumo", proposed_architecture: { contract_version: "editorial-plan-v1", title: "Plano legível", general_objective: "Formar", modules: [{ title: "Módulo editorial", lessons: [{ title: "Aula editorial", human_reasoning: "Raciocinar", ai_integration: "Apoiar", validation: "Validar", authorship_challenge: { practical_challenge: "Criar" } }] }] } },
    };
    get.mockImplementation((url: string) => {
      if (url.endsWith("studio/status/")) return Promise.resolve({ data: { enabled: true, local_only: true, sources: 0, supported: 0, unsupported: 0, missing: 0, books: 0, ready_books: 0, scripts: 0 } });
      if (url.endsWith("studio/projects/")) return Promise.resolve({ data: { results: [project] } });
      if (url.endsWith("sources/")) return Promise.resolve({ data: { count: 0, results: [] } });
      return Promise.resolve({ data: { results: [] } });
    });
    post.mockResolvedValue({ data: project });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><ContentStudio /></QueryClientProvider>);

    expect(await screen.findByText("Plano legível")).toBeInTheDocument();
    expect(screen.queryByText('"general_objective": "Formar"')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Visão técnica / JSON" }));
    expect(screen.getByText(/"general_objective": "Formar"/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aprovar plano" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/studio/projects/31/approve/", { decision: "approved", notes: "Plano revisado e aprovado no Content Studio." }));
  });

  it("shows the RAG action only for eligible sources", async () => {
    const sources = [
      source(1),
      source(2, { duplicate: true }),
      source(3, { status: "missing" }),
      source(4, { status: "unsupported", extension: "epub" }),
      source(5, { book_id: 5, book_status: "ready" }),
    ];
    get.mockImplementation((url: string) => {
      if (url.endsWith("studio/status/")) return Promise.resolve({ data: { enabled: true, local_only: true, sources: 5, supported: 3, unsupported: 1, missing: 1, books: 1, ready_books: 1, scripts: 0 } });
      if (url.endsWith("sources/")) return Promise.resolve({ data: { count: 5, results: sources } });
      return Promise.resolve({ data: { results: [] } });
    });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(<QueryClientProvider client={queryClient}><ContentStudio /></QueryClientProvider>);

    const eligibleRow = (await screen.findAllByText("livro-1.pdf"))[0].closest("tr")!;
    expect(within(eligibleRow).getByRole("button", { name: "Processar para RAG" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Processar para RAG" })).toHaveLength(1);
    expect(screen.getByText("Duplicado / não disponível")).toBeInTheDocument();
    expect(screen.getByText("Pronto para RAG")).toBeInTheDocument();
    expect(screen.getAllByText("Não disponível")).toHaveLength(2);
  });

  it("creates a project with the selected Book id and its LibrarySource id", async () => {
    get.mockImplementation((url: string) => {
      if (url.endsWith("studio/status/")) return Promise.resolve({ data: { enabled: true, local_only: true, sources: 1, supported: 1, unsupported: 0, missing: 0, books: 1, ready_books: 1, scripts: 0 } });
      if (url.endsWith("books/")) return Promise.resolve({ data: { results: [{ id: 11, title: "Séries temporais", author: "", status: "ready", source: 7 }] } });
      if (url.endsWith("sources/")) return Promise.resolve({ data: { count: 0, results: [] } });
      return Promise.resolve({ data: { results: [] } });
    });
    post.mockResolvedValueOnce({ data: { id: 20 } });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><ContentStudio /></QueryClientProvider>);

    fireEvent.change(await screen.findByPlaceholderText("Nome do projeto modernizado"), { target: { value: "Projeto temporal" } });
    fireEvent.change(screen.getByPlaceholderText("Tema ou problema real"), { target: { value: "Séries temporais" } });
    fireEvent.change(screen.getByPlaceholderText("Objetivo, público e resultado esperado"), { target: { value: "Ensinar fundamentos" } });
    fireEvent.change(await screen.findByDisplayValue("Selecione um livro processado"), { target: { value: "11" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar projeto editorial" }));

    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/studio/projects/", {
      title: "Projeto temporal",
      theme: "Séries temporais",
      objective: "Ensinar fundamentos",
      project_type: "premium",
      books: [11],
      source: 7,
    }));
  });

  it("renders the coordinated council and keeps approval explicitly human", async () => {
    const project = {
      id: 88, title: "Projeto Conselho", theme: "Dados", objective: "Revisar", project_type: "premium", status: "approved", books: [1], citations: [], editorial_comments: [], is_archived: false,
      modernization_plan: { status: "approved", version: 4, proposed_architecture: { title: "Plano do Conselho", modules: [] } },
    };
    const run = {
      id: 9, plan_version: 4, status: "awaiting_human_approval", created_at: "2026-08-28T12:00:00Z",
      final_synthesis: { summary: "Síntese coordenada", findings: [], recommendations: [], risks: [] },
      agent_runs: [{ id: 1, role: "technical", status: "completed", provider: "test", model: "", output_payload: { summary: "Parecer técnico" }, error_code: "" }],
    };
    get.mockImplementation((url: string) => {
      if (url.endsWith("studio/status/")) return Promise.resolve({ data: { enabled: true, local_only: true, sources: 0, supported: 0, unsupported: 0, missing: 0, books: 0, ready_books: 0, scripts: 0 } });
      if (url.endsWith("studio/projects/")) return Promise.resolve({ data: { results: [project] } });
      if (url.endsWith("council-runs/")) return Promise.resolve({ data: [run] });
      if (url.endsWith("sources/")) return Promise.resolve({ data: { count: 0, results: [] } });
      return Promise.resolve({ data: { results: [] } });
    });
    post.mockResolvedValue({ data: { ...run, status: "approved" } });
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><ContentStudio /></QueryClientProvider>);

    expect(await screen.findByText("CONSELHO EDITORIAL")).toBeInTheDocument();
    expect(await screen.findByText("Parecer técnico")).toBeInTheDocument();
    expect(screen.getByText("Síntese coordenada")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aprovar" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/studio/council-runs/9/approve/", {}));
  });

  it("keeps the clicked run id for revision across reorder and project switch", async () => {
    const projects = [88, 89].map((id) => ({
      id, title: `Projeto ${id}`, theme: "Dados", objective: "Revisar", project_type: "premium", status: "approved", books: [1], citations: [], editorial_comments: [], is_archived: false,
      modernization_plan: { status: "approved", version: 4, proposed_architecture: { title: `Plano ${id}`, modules: [] } },
    }));
    const run9 = { id: 9, plan_version: 4, status: "awaiting_human_approval", created_at: "2026-08-28T12:00:00Z", final_synthesis: {}, agent_runs: [] };
    const run8 = { ...run9, id: 8, created_at: "2026-08-27T12:00:00Z" };
    let councilRuns = [run9, run8];
    get.mockImplementation((url: string) => {
      if (url.endsWith("studio/status/")) return Promise.resolve({ data: { enabled: true, local_only: true, sources: 0, supported: 0, unsupported: 0, missing: 0, books: 0, ready_books: 0, scripts: 0 } });
      if (url.endsWith("studio/projects/")) return Promise.resolve({ data: { results: projects } });
      if (url.includes("/projects/88/council-runs/")) return Promise.resolve({ data: councilRuns });
      if (url.includes("/projects/89/council-runs/")) return Promise.resolve({ data: [] });
      if (url.endsWith("sources/")) return Promise.resolve({ data: { count: 0, results: [] } });
      return Promise.resolve({ data: { results: [] } });
    });
    let finishRequest!: () => void;
    post.mockImplementation(() => new Promise((resolve) => { finishRequest = () => resolve({ data: { ...run9, status: "revision_requested" } }); }));
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={queryClient}><ContentStudio /></QueryClientProvider>);

    await screen.findByText("Plano 88");
    fireEvent.click(await screen.findByRole("button", { name: "Solicitar revisão" }));
    councilRuns = [run8, run9];
    await queryClient.invalidateQueries({ queryKey: ["content-studio-council", 88] });
    fireEvent.change(screen.getByRole("combobox", { name: "Projeto editorial" }), { target: { value: "89" } });
    expect(post).toHaveBeenCalledWith("/api/library/studio/council-runs/9/request-revision/", {});
    finishRequest();
  });
});
