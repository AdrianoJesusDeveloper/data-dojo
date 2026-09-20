import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post, patchApi, toastError, toastSuccess } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patchApi: vi.fn(), toastError: vi.fn(), toastSuccess: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: { get, post, patch: patchApi } }));
vi.mock("sonner", () => ({ toast: { error: toastError, success: toastSuccess } }));

import { DidacticContentV1 } from "@/components/content-studio/DidacticContentV1";

const lesson = (provider = "groq", source_mode = "APPROVED_SOURCES", status = "DRAFT") => ({ lesson: { id: 1, title: "Unidade", audience: "SENSEI", status, source_mode, ai_provider: provider, ai_model: "model-1", generated_at: "2026-09-04T12:00:00Z", sections: [{ id: 1, section_type: "CONCEPT", section_type_label: "Conceito", title: "Conceito principal", content: "Primeiro conteúdo", order: 0, metadata: {} }, { id: 2, section_type: "AUTHORSHIP_CHALLENGE", section_type_label: "Desafio de autoria", title: "Desafio", content: "Crie seu artefato", order: 1, metadata: {} }] } });
const renderContent = (formationId = 501, unitId = 10) => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><DidacticContentV1 formationId={formationId} unitId={unitId} enabled /></QueryClientProvider>);

beforeEach(() => { get.mockReset(); post.mockReset(); patchApi.mockReset(); toastError.mockReset(); toastSuccess.mockReset(); });

describe("DidacticContentV1", () => {
  it("shows section claim evidence from the snapshot and distinguishes pedagogical prose", async () => {
    const base = lesson().lesson;
    const evidence = { source_id: 7, book_id: 8, chunk_id: 9, pdf_page: 124, quote: "Listas são mutáveis." };
    const payload = { lesson: { ...base, grounding_snapshot: { version: 2, sources: [{ id: 7, title: "Fonte Python", location: "PDF p.124" }], excerpts: [{ ...evidence, book_title: "Livro Python", chunk_index: 3, library_source_id: 4, approved_ranges: [{ pdf_start: 122, pdf_end: 135 }], content: "Listas são mutáveis. Contexto integral do trecho." }] }, sections: [
      { ...base.sections[0], metadata: { claim_grounding: { version: 1, kind: "source_derived", validation: "extractive_snapshot_match", claims: [{ text: evidence.quote, evidence: [evidence] }] } } },
      { ...base.sections[1], metadata: { claim_grounding: { version: 1, kind: "pedagogical", validation: "not_source_assertion", claims: [] } } },
    ] } };
    get.mockImplementation((url: string) => Promise.resolve({ data: url.includes("authorship-challenge") ? { section: null, activity: null } : payload }));
    renderContent();
    expect(await screen.findByText(/Ver evidências das afirmações/)).toBeInTheDocument();
    expect(screen.getByText(/Livro Python · PDF p.124 · chunk #9 · fonte #7/)).toBeInTheDocument();
    expect(screen.getByText(/Orientação pedagógica — não certificada/)).toBeInTheDocument();
    expect(screen.getAllByText(/Contexto integral do trecho/).length).toBeGreaterThan(0);
  });

  it("does not claim that a legacy snapshot certifies every assertion", async () => {
    get.mockResolvedValue({ data: lesson() });
    renderContent();
    expect((await screen.findAllByText(/Sem validação por afirmação nesta seção/)).length).toBe(2);
    expect(screen.queryByText(/Ver evidências das afirmações/)).not.toBeInTheDocument();
  });

  it("moves the lesson from DRAFT to REVIEW to APPROVED and updates the cache immediately", async () => {
    get.mockImplementation((url: string) => url.includes("authorship-challenge")
      ? Promise.resolve({ data: { section: lesson().lesson.sections[1], activity: null } })
      : Promise.resolve({ data: lesson() }));
    patchApi
      .mockResolvedValueOnce({ data: { ...lesson().lesson, status: "REVIEW" } })
      .mockResolvedValueOnce({ data: { ...lesson().lesson, status: "APPROVED" } });
    renderContent();
    expect(await screen.findByText("STATUS EDITORIAL DA AULA")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Enviar para revisão" }));
    await waitFor(() => expect(patchApi).toHaveBeenCalledWith("/api/library/sensei-units/10/didactic-content/", { status: "REVIEW" }));
    expect(await screen.findByRole("button", { name: "Aprovar aula" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retornar a rascunho" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aprovar aula" }));
    await waitFor(() => expect(patchApi).toHaveBeenCalledWith("/api/library/sensei-units/10/didactic-content/", { status: "APPROVED" }));
    expect(await screen.findByRole("button", { name: "Reabrir revisão" })).toBeInTheDocument();
    expect(get).toHaveBeenCalledTimes(2);
  });

  it("requires a visible Student preview before publishing the selected scope", async () => {
    get.mockImplementation((url: string) => url.includes("authorship-challenge")
      ? Promise.resolve({ data: { section: lesson().lesson.sections[1], activity: null } })
      : Promise.resolve({ data: lesson("groq", "APPROVED_SOURCES", "APPROVED") }));
    post.mockImplementation((url: string) => url.includes("publication-preview")
      ? Promise.resolve({ data: { preview_token: "preview-1", scope: "MODULE", status: "PREVIEW", summary: { total: 2, eligible: 1, ineligible: 1 }, eligibility_items: [{ unit_id: 10, unit_title: "Unidade", module_id: 2, module_title: "Módulo A", eligibility: "ELIGIBLE", reason: "APPROVED — será publicada", source_status: "APPROVED", student_is_stale: false }, { unit_id: 11, unit_title: "Unidade sem aula", module_id: 2, module_title: "Módulo A", eligibility: "INELIGIBLE_NO_DIDACTIC_LESSON", reason: "Sem aula didática — não será publicada", source_status: null, student_is_stale: false }], items: [{ source_lesson_id: 1, title: "Unidade", audience: "STUDENT", sections: [{ title: "Conceito", content: "Leia e explique com suas próprias palavras." }], adaptation: { profile: "guided-student-v1", human_publication_required: true, does_not_grant_mastery: true } }] } })
      : Promise.resolve({ data: { status: "PUBLISHED", items: [] } }));
    renderContent();
    const scope = await screen.findByRole("combobox", { name: "Escopo de publicação" });
    fireEvent.change(scope, { target: { value: "MODULE" } });
    expect(screen.queryByRole("button", { name: "Confirmar publicação no Workspace" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Prévia da adaptação" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/sensei-units/10/publication-preview/", { scope: "MODULE" }));
    expect(await screen.findByText("PRÉVIA STUDENT · 2 unidade(s) encontrada(s)")).toBeInTheDocument();
    expect(screen.getByText("1 elegível(is) para publicação · 1 não elegível(is)")).toBeInTheDocument();
    expect(screen.getByText("✗ Unidade sem aula")).toBeInTheDocument();
    expect(screen.getByText(/próprias palavras/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Confirmar publicação de 1 unidade/ }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/sensei-units/10/publication-publish/", { preview_token: "preview-1" }));
  });

  it("blocks confirmation when the selected scope has zero eligible units", async () => {
    get.mockResolvedValue({ data: lesson("groq", "APPROVED_SOURCES", "DRAFT") });
    post.mockResolvedValue({ data: { preview_token: "preview-zero", scope: "MODULE", status: "PREVIEW", summary: { total: 1, eligible: 0, ineligible: 1 }, eligibility_items: [{ unit_id: 10, unit_title: "Unidade", module_id: 2, module_title: "Módulo A", eligibility: "INELIGIBLE_DRAFT", reason: "Rascunho (DRAFT) — não será publicada", source_status: "DRAFT", student_is_stale: false }], items: [] } });
    renderContent();
    fireEvent.click(await screen.findByRole("button", { name: "Prévia da adaptação" }));
    expect(await screen.findByText(/Nenhuma unidade pode ser publicada/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Confirmar publicação de 0 unidade/ })).toBeDisabled();
  });

  it("prints an independent lesson document and keeps interactive controls out", async () => {
    get.mockImplementation((url: string) => url.includes("authorship-challenge")
      ? Promise.resolve({ data: { section: lesson().lesson.sections[1], activity: null } })
      : Promise.resolve({ data: lesson() }));
    const write = vi.fn();
    const print = vi.fn();
    const printWindow = {
      document: { open: vi.fn(), write, close: vi.fn() },
      focus: vi.fn(),
      print,
    };
    const open = vi.spyOn(window, "open").mockReturnValue(printWindow as unknown as Window);
    const pagePrint = vi.spyOn(window, "print").mockImplementation(() => undefined);

    renderContent();
    expect(await screen.findByRole("button", { name: "Exportar DOCX" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exportar HTML" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Imprimir / Salvar PDF" }));

    expect(open).toHaveBeenCalledWith("", "_blank", "width=900,height=700");
    expect(write).toHaveBeenCalledOnce();
    const exportedHtml = String(write.mock.calls[0][0]);
    expect(exportedHtml).toContain("Conceito principal");
    expect(exportedHtml).toContain("Crie seu artefato");
    expect(exportedHtml).not.toContain("Iniciar Desafio de Autoria");
    expect(exportedHtml).not.toContain("Submeter desafio");
    expect(pagePrint).not.toHaveBeenCalled();
    await waitFor(() => expect(print).toHaveBeenCalledOnce(), { timeout: 1000 });

    open.mockRestore();
    pagePrint.mockRestore();
  });

  it("downloads backend-generated DOCX without exporting interactive controls", async () => {
    const createObjectURL = vi.fn(() => "blob:lesson");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
    get.mockImplementation((url: string) => url.includes("/export/docx/")
      ? Promise.resolve({ data: new Blob(["docx"]), headers: { "content-disposition": 'attachment; filename="aula-1.docx"' } })
      : Promise.resolve({ data: lesson() }));
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    renderContent();
    fireEvent.click(await screen.findByRole("button", { name: "Exportar DOCX" }));
    await waitFor(() => expect(get).toHaveBeenCalledWith("/api/library/sensei-units/10/didactic-content/export/docx/", { responseType: "blob" }));
    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:lesson");
    click.mockRestore();
  });

  it("shows empty state and generates a draft without changing other Sensei actions", async () => {
    get.mockResolvedValue({ data: { lesson: null } });
    post.mockResolvedValue({ data: lesson() });
    renderContent();
    expect(await screen.findByText("Nenhuma aula criada.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "GERAR AULA" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/sensei-units/10/didactic-content/", {}));
    expect(await screen.findByText("Conceito principal")).toBeInTheDocument();
  });

  it("renders loading, ordered sections and provenance", async () => {
    let resolve!: (value: unknown) => void;
    get.mockReturnValue(new Promise((result) => { resolve = result; }));
    renderContent();
    expect(screen.getByText("Carregando conteúdo da aula...")).toBeInTheDocument();
    resolve({ data: lesson() });
    expect(await screen.findByText("Conceito principal")).toBeInTheDocument();
    expect(screen.getByText("Desafio de autoria")).toBeInTheDocument();
    expect(screen.getByText("Gerada por: groq · model-1")).toBeInTheDocument();
  });

  it("shows safe source and generic errors", async () => {
    get.mockResolvedValue({ data: { lesson: null } });
    post.mockRejectedValue({ response: { status: 409, data: { detail: "NEEDS_SOURCE: fonte aprovada" } } });
    renderContent();
    fireEvent.click(await screen.findByRole("button", { name: "GERAR AULA" }));
    expect(await screen.findByText(/Fontes insuficientes.*NEEDS_SOURCE/)).toBeInTheDocument();
    expect(toastError).toHaveBeenCalled();

    get.mockRejectedValue(new Error("private server error"));
    renderContent(502, 20);
    expect(await screen.findByText("Não foi possível carregar o conteúdo da aula.")).toBeInTheDocument();
  });

  it("does not invent provenance for human content", async () => {
    get.mockResolvedValue({ data: { lesson: { ...lesson().lesson, ai_provider: "", ai_model: "" } } });
    renderContent();
    await screen.findByText("Conceito principal");
    expect(screen.queryByText(/Gerada por:/)).not.toBeInTheDocument();
  });

  it("shows an explicit warning for an unsourced AI draft", async () => {
    get.mockResolvedValue({ data: lesson("groq", "AI_GENERATED_UNSOURCED") });
    renderContent();
    expect(await screen.findByText(/gerada por IA sem fonte aprovada/i)).toBeInTheDocument();
    expect(screen.getAllByText("DRAFT").length).toBeGreaterThanOrEqual(1);
  });

  it("keeps sourced content as a DRAFT without an unsourced warning", async () => {
    get.mockResolvedValue({ data: lesson("groq", "APPROVED_SOURCES") });
    renderContent();
    expect((await screen.findAllByText("DRAFT")).length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText(/sem fonte aprovada/i)).not.toBeInTheDocument();
  });

  it("keeps formation and unit caches isolated", async () => {
    get.mockImplementation((url: string) => Promise.resolve({ data: url.includes("10/") ? lesson("groq") : lesson("gemini") }));
    const client = new QueryClient();
    const view = render(<QueryClientProvider client={client}><DidacticContentV1 formationId={501} unitId={10} enabled /></QueryClientProvider>);
    expect(await screen.findByText("Gerada por: groq · model-1")).toBeInTheDocument();
    view.rerender(<QueryClientProvider client={client}><DidacticContentV1 formationId={502} unitId={20} enabled /></QueryClientProvider>);
    expect(await screen.findByText("Gerada por: gemini · model-1")).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/api/library/sensei-units/20/didactic-content/");
  });

  it("opens, submits and preserves the interactive authorship challenge history", async () => {
    const activity = { id: 7, prompt: "Defenda sua decisão e entregue um artefato.", attempts: [] };
    const reviewed = { ...activity, attempts: [{ id: 8, attempt_number: 1, answer: "Minha produção", feedback: "Explique o trade-off.", outcome: "RETRY", identified_gap: "trade-off", next_step: "Compare alternativas." }] };
    get.mockImplementation((url: string) => url.includes("didactic-content") ? Promise.resolve({ data: lesson() }) : Promise.resolve({ data: { section: { id: 2, section_type: "AUTHORSHIP_CHALLENGE", section_type_label: "Desafio de autoria", title: "Desafio", content: "Crie seu artefato", order: 1, metadata: {} }, activity: null } }));
    post.mockImplementation((url: string) => url.includes("authorship-challenge") ? Promise.resolve({ data: { section: { id: 2, section_type: "AUTHORSHIP_CHALLENGE", section_type_label: "Desafio de autoria", title: "Desafio", content: "Crie seu artefato", order: 1, metadata: {} }, activity } }) : Promise.resolve({ data: reviewed }));
    renderContent();
    expect(await screen.findByRole("button", { name: "Iniciar Desafio de Autoria" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Iniciar Desafio de Autoria" }));
    expect(await screen.findByText("Produção do desafio")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Sua produção no Desafio de Autoria" }), { target: { value: "Minha produção" } });
    fireEvent.click(screen.getByRole("button", { name: "Submeter desafio" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/api/library/sensei-learning-activities/7/answer/", { response: "Minha produção" }));
    expect(await screen.findByText("Explique o trade-off.")).toBeInTheDocument();
    expect(screen.getByText("Minha produção")).toBeInTheDocument();
  });

  it("does not show the authorship action without an authorship section", async () => {
    get.mockResolvedValue({ data: { lesson: { ...lesson().lesson, sections: [{ ...lesson().lesson.sections[0], section_type: "CONCEPT" }] } } });
    renderContent();
    await screen.findByText("Conceito principal");
    expect(screen.queryByRole("button", { name: "Iniciar Desafio de Autoria" })).not.toBeInTheDocument();
  });
});
