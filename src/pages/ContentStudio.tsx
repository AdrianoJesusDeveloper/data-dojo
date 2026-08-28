import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Archive,
  BookOpen,
  CheckCircle2,
  Database,
  FileQuestion,
  FolderSearch,
  History,
  LoaderCircle,
  Eye,
  MessageSquare,
  Pencil,
  Printer,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast, Toaster } from "sonner";

import { DojoHeader } from "@/components/DojoHeader";
import { EditorialPlanEditor } from "@/components/content-studio/EditorialPlanEditor";
import { EditorialContentRenderer, EditorialPlanRenderer } from "@/components/content-studio/EditorialPlanRenderer";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { API_ORIGIN, api } from "@/lib/api";

type StudioStatus = {
  enabled: boolean;
  local_only: boolean;
  sources: number;
  supported: number;
  unsupported: number;
  missing: number;
  books: number;
  ready_books: number;
  scripts: number;
};

type LibrarySource = {
  id: number;
  relative_path: string;
  filename: string;
  extension: string;
  size_bytes: number;
  sha256: string;
  status: "discovered" | "supported" | "unsupported" | "missing";
  modified_at: string | null;
  duplicate: boolean;
  book_id: number | null;
  book_status: "uploaded" | "processing" | "ready" | "error" | null;
  book_error: string;
};

type PaginatedSources = { count: number; next: string | null; previous: string | null; results: LibrarySource[] };
type Book = { id: number; title: string; author: string; status: string; source: number | null };
type StudioProject = {
  id: number; title: string; theme: string; objective: string; project_type: "youtube" | "premium"; status: string; books: number[];
  modernization_plan?: any; citations: Array<{ id: number; book_title: string; page_number: number | null; excerpt: string }>;
  content_package?: any;
  editorial_comments: Array<{ id: number; text: string; target: string; target_type: string; target_id: string; plan_version: number | null; resolved: boolean; resolved_at: string | null; author_name: string; created_at: string }>;
  is_archived: boolean;
};

function localOrigin(value: string) {
  try {
    return ["localhost", "127.0.0.1", "::1"].includes(new URL(value).hostname);
  } catch {
    return false;
  }
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const statusLabels = {
  discovered: "Descoberto",
  supported: "Pronto para PDF",
  unsupported: "Catalogado",
  missing: "Ausente",
};

export default function ContentStudio() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [sourcePage, setSourcePage] = useState(1);
  const [sourcePageSize, setSourcePageSize] = useState<25 | 50 | 100>(25);
  const [ragStatus, setRagStatus] = useState("");
  const [sourceExtension, setSourceExtension] = useState("");
  const [projectTitle, setProjectTitle] = useState("");
  const [projectTheme, setProjectTheme] = useState("");
  const [projectObjective, setProjectObjective] = useState("");
  const [projectType, setProjectType] = useState<"youtube" | "premium">("premium");
  const [selectedBook, setSelectedBook] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [planView, setPlanView] = useState<"editorial" | "technical">("editorial");
  const [showArchived, setShowArchived] = useState(false);
  const [editingPlan, setEditingPlan] = useState<Record<string, unknown> | null>(null);
  const [studentPreview, setStudentPreview] = useState(false);
  const [commentText, setCommentText] = useState("");
  const [commentTarget, setCommentTarget] = useState("plan:");
  const [contentTarget, setContentTarget] = useState("");
  const isLocal = useMemo(() => localOrigin(API_ORIGIN), []);

  const statusQuery = useQuery({
    queryKey: ["content-studio-status"],
    queryFn: async () => (await api.get<StudioStatus>("/api/library/studio/status/")).data,
    enabled: isLocal,
    retry: false,
  });

  const sourcesQuery = useQuery({
    queryKey: ["content-studio-sources", search, sourcePage, sourcePageSize, ragStatus, sourceExtension],
    queryFn: async () => (
      await api.get<PaginatedSources>("/api/library/sources/", { params: {
        page: sourcePage, page_size: sourcePageSize,
        ...(search ? { search } : {}),
        ...(ragStatus ? { rag_status: ragStatus } : {}),
        ...(sourceExtension ? { extension: sourceExtension } : {}),
      } })
    ).data,
    enabled: isLocal && statusQuery.isSuccess,
    retry: false,
    refetchInterval: (query) => query.state.data?.results.some((source) => source.book_status === "processing") ? 2000 : false,
  });

  const booksQuery = useQuery({
    queryKey: ["content-studio-books"],
    queryFn: async () => (await api.get<{ results: Book[] }>("/api/library/books/")).data.results,
    enabled: isLocal && statusQuery.isSuccess,
    retry: false,
  });

  const projectsQuery = useQuery({
    queryKey: ["content-studio-projects", showArchived],
    queryFn: async () => (await api.get<{ results: StudioProject[] }>("/api/library/studio/projects/", { params: { archived: showArchived } })).data.results,
    enabled: isLocal && statusQuery.isSuccess,
    retry: false,
  });

  const selectedProject = projectsQuery.data?.find((project) => project.id === selectedProjectId) ?? projectsQuery.data?.[0];
  const selectedBookData = booksQuery.data?.find((book) => book.id === Number(selectedBook));

  const versionsQuery = useQuery({
    queryKey: ["content-studio-plan-versions", selectedProject?.id],
    queryFn: async () => (await api.get<Array<{ id: number; version: number; content: unknown; origin: string; state: string; created_by_name: string; created_at: string }>>(`/api/library/studio/projects/${selectedProject!.id}/plan/versions/`)).data,
    enabled: Boolean(selectedProject?.modernization_plan),
    retry: false,
  });

  const refreshProjects = () => { queryClient.invalidateQueries({ queryKey: ["content-studio-projects"] }); queryClient.invalidateQueries({ queryKey: ["content-studio-plan-versions"] }); };

  const createProjectMutation = useMutation({
    mutationFn: async () => (await api.post("/api/library/studio/projects/", {
      title: projectTitle, theme: projectTheme, objective: projectObjective, project_type: projectType,
      books: selectedBookData ? [selectedBookData.id] : [], source: selectedBookData?.source ?? null,
    })).data,
    onSuccess: (project) => {
      toast.success("Projeto editorial criado.");
      setSelectedProjectId(project.id); setProjectTitle(""); setProjectTheme(""); setProjectObjective(""); setProjectType("premium"); setSelectedBook("");
      queryClient.invalidateQueries({ queryKey: ["content-studio-projects"] });
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Não foi possível criar o projeto."),
  });

  const workflowMutation = useMutation({
    mutationFn: async ({ projectId, action, payload }: { projectId: number; action: string; payload?: any }) => (
      await api.post(`/api/library/studio/projects/${projectId}/${action}/`, payload ?? {})
    ).data,
    onSuccess: () => {
      toast.success("Etapa concluída.");
      queryClient.invalidateQueries({ queryKey: ["content-studio-projects"] });
      queryClient.invalidateQueries({ queryKey: ["content-studio-status"] });
    },
    onError: (error: any) => toast.error(error.response?.data?.detail || "A etapa não pôde ser concluída."),
  });

  const savePlanMutation = useMutation({
    mutationFn: async () => (await api.put(`/api/library/studio/projects/${selectedProject!.id}/plan/`, { plan: editingPlan })).data,
    onSuccess: () => { toast.success("Nova versão do plano salva."); setEditingPlan(null); refreshProjects(); },
    onError: (error: any) => toast.error(error.response?.data?.detail || "O plano não passou pela validação editorial."),
  });

  const commentMutation = useMutation({
    mutationFn: async () => {
      const [target_type, target_id] = commentTarget.split(":", 2);
      return (await api.post(`/api/library/studio/projects/${selectedProject!.id}/comments/`, { text: commentText, target_type, target_id })).data;
    },
    onSuccess: () => { setCommentText(""); toast.success("Comentário editorial adicionado."); refreshProjects(); },
    onError: (error: any) => toast.error(error.response?.data?.text?.[0] || "Não foi possível adicionar o comentário."),
  });

  const resolveCommentMutation = useMutation({
    mutationFn: async (commentId: number) => (await api.post(`/api/library/studio/projects/${selectedProject!.id}/comments/${commentId}/resolve/`)).data,
    onSuccess: refreshProjects,
  });

  const archiveMutation = useMutation({
    mutationFn: async (archived: boolean) => (await api.post(`/api/library/studio/projects/${selectedProject!.id}/archive/`, { archived })).data,
    onSuccess: (_, archived) => { toast.success(archived ? "Projeto arquivado." : "Projeto restaurado."); setSelectedProjectId(null); refreshProjects(); },
  });

  const permanentDeleteMutation = useMutation({
    mutationFn: async () => {
      const confirmation = window.prompt('Digite "EXCLUIR DEFINITIVAMENTE" para confirmar.');
      if (confirmation !== "EXCLUIR DEFINITIVAMENTE") throw new Error("cancelled");
      return (await api.delete(`/api/library/studio/projects/${selectedProject!.id}/permanent-delete/`, { data: { confirmation } })).data;
    },
    onSuccess: () => { toast.success("Projeto excluído definitivamente."); setSelectedProjectId(null); refreshProjects(); },
    onError: (error: any) => { if (error.message !== "cancelled") toast.error("Não foi possível excluir o projeto."); },
  });

  const generateItemMutation = useMutation({
    mutationFn: async () => {
      const [target_type, index] = contentTarget.split(":");
      return (await api.post(`/api/library/studio/projects/${selectedProject!.id}/generate-content/`, { target_type, target_index: Number(index) })).data;
    },
    onSuccess: () => { toast.success("Conteúdo editorial gerado como draft."); refreshProjects(); },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Não foi possível gerar o item."),
  });

  const scanMutation = useMutation({
    mutationFn: async () => (await api.post("/api/library/studio/scan/")).data,
    onSuccess: (result) => {
      toast.success(`Catálogo atualizado: ${result.total} arquivos encontrados.`);
      queryClient.invalidateQueries({ queryKey: ["content-studio-status"] });
      queryClient.invalidateQueries({ queryKey: ["content-studio-sources"] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Não foi possível examinar o acervo.");
    },
  });

  const processSourceMutation = useMutation({
    mutationFn: async (sourceId: number) => (
      await api.post(`/api/library/sources/${sourceId}/process/`)
    ).data,
    onSuccess: () => {
      toast.success("Processamento para RAG iniciado.");
      queryClient.invalidateQueries({ queryKey: ["content-studio-sources"] });
      queryClient.invalidateQueries({ queryKey: ["content-studio-books"] });
      queryClient.invalidateQueries({ queryKey: ["content-studio-status"] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Não foi possível processar esta fonte.");
    },
  });

  if (!isLocal) {
    return (
      <div className="min-h-screen bg-background">
        <DojoHeader />
        <main className="mx-auto max-w-3xl px-6 py-16">
          <Alert variant="destructive">
            <ShieldCheck className="h-4 w-4" />
            <AlertTitle>Studio bloqueado</AlertTitle>
            <AlertDescription>
              Esta área somente funciona quando o frontend e a API utilizam endereços locais.
            </AlertDescription>
          </Alert>
        </main>
      </div>
    );
  }

  const status = statusQuery.data;
  const sources = sourcesQuery.data?.results ?? [];
  const sourceCount = sourcesQuery.data?.count ?? 0;
  const sourcePages = Math.max(1, Math.ceil(sourceCount / sourcePageSize));

  return (
    <div className="min-h-screen bg-background">
      <Toaster position="top-right" />
      <DojoHeader compact />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <section className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-kaizen">
              <ShieldCheck className="h-4 w-4" /> Ambiente privado local
            </div>
            <h1 className="font-display text-3xl font-extrabold sm:text-4xl">DDJ Content Studio</h1>
            <p className="mt-3 text-muted-foreground">
              Transforme seu acervo em projetos modernos, estudos, aulas e roteiros mantendo a decisão humana em cada etapa.
            </p>
          </div>
          <Button onClick={() => scanMutation.mutate()} disabled={!status || scanMutation.isPending}>
            {scanMutation.isPending ? <LoaderCircle className="animate-spin" /> : <FolderSearch />}
            Examinar C:\livros
          </Button>
        </section>

        {statusQuery.isError && (
          <Alert variant="destructive" className="mt-8">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Studio indisponível</AlertTitle>
            <AlertDescription>
              Ative `DDJ_CONTENT_STUDIO_ENABLED=true`, execute a API localmente e entre com uma conta administradora.
            </AlertDescription>
          </Alert>
        )}

        {statusQuery.isLoading && (
          <div className="mt-12 flex items-center justify-center gap-3 text-muted-foreground">
            <LoaderCircle className="animate-spin" /> Verificando o ambiente privado...
          </div>
        )}

        {status && (
          <>
            <Alert className="mt-8 border-kaizen/30 bg-kaizen/5">
              <ShieldCheck className="h-4 w-4 text-kaizen" />
              <AlertTitle>Proteção local ativa</AlertTitle>
              <AlertDescription>
                Acervo privado local configurado. Caminhos absolutos e arquivos não são enviados ao frontend nem ao repositório.
              </AlertDescription>
            </Alert>

            <section className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Metric icon={Database} label="Arquivos catalogados" value={status.sources} />
              <Metric icon={BookOpen} label="PDFs suportados" value={status.supported} />
              <Metric icon={CheckCircle2} label="Livros processados" value={status.ready_books} />
              <Metric icon={Sparkles} label="Roteiros gerados" value={status.scripts} />
            </section>

            <section className="mt-8 grid gap-6 lg:grid-cols-[1.6fr_0.8fr]">
              <Card>
                <CardHeader className="gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <CardTitle>Catálogo privado</CardTitle>
                    <CardDescription>{sourceCount} {sourceCount === 1 ? "livro encontrado" : "livros encontrados"} sem expor caminhos absolutos.</CardDescription>
                  </div>
                  <div className="relative w-full sm:w-72">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input value={search} onChange={(event) => { setSearch(event.target.value); setSourcePage(1); }} placeholder="Buscar título em todo o catálogo" className="pl-9" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="mb-4 flex flex-wrap items-center gap-3">
                    <select aria-label="Status RAG" value={ragStatus} onChange={(event) => { setRagStatus(event.target.value); setSourcePage(1); }} className="h-9 rounded-md border border-input bg-background px-3 text-sm">
                      <option value="">Todos os status RAG</option><option value="not_processed">Não processado</option><option value="uploaded">Enviado</option><option value="processing">Processando</option><option value="ready">Pronto</option><option value="error">Erro</option>
                    </select>
                    <select aria-label="Formato" value={sourceExtension} onChange={(event) => { setSourceExtension(event.target.value); setSourcePage(1); }} className="h-9 rounded-md border border-input bg-background px-3 text-sm">
                      <option value="">Todos os formatos</option><option value="pdf">PDF</option><option value="epub">EPUB</option><option value="mobi">MOBI</option>
                    </select>
                    <span className="text-xs text-muted-foreground" title="Área, tecnologia, categoria, tema, nível e idioma ainda não existem de forma consistente em LibrarySource.">Mais filtros editoriais serão habilitados quando houver metadados catalogados.</span>
                  </div>
                  {sourcesQuery.isFetching && <div className="mb-3 flex items-center gap-2 text-sm text-muted-foreground"><RefreshCw className="h-4 w-4 animate-spin" /> Atualizando...</div>}
                  {!sources.length ? (
                    <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground">
                      <FileQuestion className="mx-auto mb-3 h-8 w-8" />
                      Examine o acervo para criar o primeiro catálogo.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                          <tr><th className="py-3 pr-4">Arquivo</th><th className="py-3 pr-4">Tipo</th><th className="py-3 pr-4">Tamanho</th><th className="py-3 pr-4">Estado</th><th className="py-3">Ação</th></tr>
                        </thead>
                        <tbody>
                          {sources.map((source) => (
                            <tr key={source.id} className="border-b border-border/60 last:border-0">
                              <td className="max-w-md py-4 pr-4"><p className="truncate font-medium" title={source.relative_path}>{source.filename}</p><p className="truncate text-xs text-muted-foreground">{source.relative_path}</p></td>
                              <td className="py-4 pr-4 font-mono text-xs uppercase">{source.extension}</td>
                              <td className="py-4 pr-4 text-muted-foreground">{formatSize(source.size_bytes)}</td>
                              <td className="py-4 pr-4"><div className="flex flex-wrap gap-2"><Badge variant={source.status === "supported" ? "default" : source.status === "missing" ? "destructive" : "secondary"}>{statusLabels[source.status]}</Badge>{source.duplicate && <Badge variant="outline">Duplicado</Badge>}</div></td>
                              <td className="py-4">
                                {source.duplicate ? <span className="text-xs text-muted-foreground">Duplicado / não disponível</span>
                                  : source.book_status === "processing" ? <span className="inline-flex items-center gap-2 text-xs text-muted-foreground"><LoaderCircle className="h-4 w-4 animate-spin" /> Processando</span>
                                  : source.book_status === "ready" ? <Badge variant="outline">Pronto para RAG</Badge>
                                  : source.status === "supported" ? <Button size="sm" variant={source.book_status === "error" ? "outline" : "default"} disabled={processSourceMutation.isPending} onClick={() => processSourceMutation.mutate(source.id)}>{source.book_status === "error" ? "Tentar novamente" : "Processar para RAG"}</Button>
                                  : <span className="text-xs text-muted-foreground">Não disponível</span>}
                                {source.book_status === "error" && <p className="mt-1 max-w-48 text-xs text-destructive">{source.book_error || "Erro no processamento."}</p>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
                    <label className="flex items-center gap-2 text-sm text-muted-foreground">Itens por página
                      <select aria-label="Itens por página" value={sourcePageSize} onChange={(event) => { setSourcePageSize(Number(event.target.value) as 25 | 50 | 100); setSourcePage(1); }} className="h-9 rounded-md border border-input bg-background px-2 text-foreground">
                        <option value={25}>25</option><option value={50}>50</option><option value={100}>100</option>
                      </select>
                    </label>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button size="sm" variant="outline" disabled={sourcePage <= 1 || sourcesQuery.isFetching} onClick={() => setSourcePage(1)}>Primeira pÃ¡gina</Button>
                      <Button size="sm" variant="outline" disabled={!sourcesQuery.data?.previous || sourcesQuery.isFetching} onClick={() => setSourcePage((page) => Math.max(1, page - 1))}>← Anterior</Button>
                      <span className="min-w-24 text-center text-sm font-medium">Página {sourcePage} de {sourcePages}</span>
                      <Button size="sm" variant="outline" disabled={!sourcesQuery.data?.next || sourcesQuery.isFetching} onClick={() => setSourcePage((page) => Math.min(sourcePages, page + 1))}>Próxima →</Button>
                      <Button size="sm" variant="outline" disabled={sourcePage >= sourcePages || sourcesQuery.isFetching} onClick={() => setSourcePage(sourcePages)}>Ãšltima pÃ¡gina</Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle>Fluxo de produção</CardTitle><CardDescription>Próximas etapas controladas pelo desenvolvedor.</CardDescription></CardHeader>
                <CardContent className="space-y-3">
                  {["Selecionar livro e projeto", "Revisar fontes do RAG", "Aprovar modernização", "Implementar e testar", "Produzir aula, kata e roteiro"].map((step, index) => (
                    <div key={step} className="flex items-center gap-3 rounded-lg border bg-secondary/30 p-3">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-kaizen/15 font-mono text-xs font-bold text-kaizen">{index + 1}</span>
                      <span className="text-sm font-medium">{step}</span>
                    </div>
                  ))}
                  <p className="pt-2 text-xs text-muted-foreground">A execução dessas etapas será liberada gradualmente conforme cada mecanismo for validado.</p>
                </CardContent>
              </Card>
            </section>

            <section className="mt-8 grid gap-6 lg:grid-cols-[0.8fr_1.4fr]">
              <Card>
                <CardHeader><CardTitle>Novo projeto</CardTitle><CardDescription>Defina o problema antes de pedir qualquer geração à IA.</CardDescription></CardHeader>
                <CardContent className="space-y-4">
                  <Input value={projectTitle} onChange={(event) => setProjectTitle(event.target.value)} placeholder="Nome do projeto modernizado" />
                  <Input value={projectTheme} onChange={(event) => setProjectTheme(event.target.value)} placeholder="Tema ou problema real" />
                  <Textarea value={projectObjective} onChange={(event) => setProjectObjective(event.target.value)} placeholder="Objetivo, público e resultado esperado" rows={5} />
                  <select aria-label="Tipo editorial" value={projectType} onChange={(event) => setProjectType(event.target.value as "youtube" | "premium")} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm">
                    <option value="youtube">Trilha YouTube</option><option value="premium">Formação Premium</option>
                  </select>
                  <select value={selectedBook} onChange={(event) => setSelectedBook(event.target.value)} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm">
                    <option value="">Selecione um livro processado</option>
                    {(booksQuery.data ?? []).map((book) => <option key={book.id} value={book.id} disabled={book.status !== "ready"}>{book.title} — {book.status}</option>)}
                  </select>
                  <Button className="w-full" disabled={!projectTitle || !projectTheme || !projectObjective || !selectedBookData || createProjectMutation.isPending} onClick={() => createProjectMutation.mutate()}>
                    {createProjectMutation.isPending ? <LoaderCircle className="animate-spin" /> : <Sparkles />} Criar projeto editorial
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div><CardTitle>Workflow com aprovação humana</CardTitle><CardDescription>Nenhum pacote é gerado antes de você aprovar o plano.</CardDescription></div>
                    <div className="flex flex-wrap gap-2"><Button size="sm" variant={showArchived ? "default" : "outline"} onClick={() => { setShowArchived((value) => !value); setSelectedProjectId(null); }}><Archive />{showArchived ? "Ver ativos" : "Arquivados"}</Button><select aria-label="Projeto editorial" value={selectedProject?.id ?? ""} onChange={(event) => setSelectedProjectId(Number(event.target.value))} className="h-9 rounded-md border border-input bg-background px-3 text-sm"><option value="">Selecione um projeto</option>{(projectsQuery.data ?? []).map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></div>
                  </div>
                </CardHeader>
                <CardContent>
                  {!selectedProject ? <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">Crie seu primeiro projeto para iniciar o workflow.</div> : (
                    <div className="space-y-5">
                      <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex flex-wrap items-center gap-3"><Badge>{selectedProject.status}</Badge><h3 className="font-display text-xl font-bold">{selectedProject.title}</h3></div><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => archiveMutation.mutate(!selectedProject.is_archived)}><Archive />{selectedProject.is_archived ? "Restaurar" : "Arquivar projeto"}</Button>{selectedProject.is_archived && <Button size="sm" variant="destructive" onClick={() => permanentDeleteMutation.mutate()}><Trash2 />Excluir definitivamente</Button>}</div></div>
                      <p className="text-sm text-muted-foreground">{selectedProject.objective}</p>
                      {!selectedProject.modernization_plan && <Button disabled={!selectedProject.books.length || workflowMutation.isPending} onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "generate-plan" })}><Sparkles /> Gerar plano com fontes</Button>}
                      {selectedProject.modernization_plan && (
                        <div className="space-y-4 rounded-lg border p-4">
                          <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
                            <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-kaizen">{planView === "editorial" ? "Visão editorial" : "Visão técnica / JSON"}</p><p className="mt-1 text-xs text-muted-foreground">O objeto estruturado permanece preservado como formato interno.</p></div>
                            <div className="no-print flex flex-wrap gap-1 rounded-lg border p-1" role="group" aria-label="Visualização do plano">
                              <Button size="sm" variant={planView === "editorial" ? "default" : "ghost"} onClick={() => setPlanView("editorial")}>Visão editorial</Button>
                              <Button size="sm" variant={planView === "technical" ? "default" : "ghost"} onClick={() => setPlanView("technical")}>Visão técnica / JSON</Button>
                              <Button size="sm" variant="ghost" onClick={() => setEditingPlan(structuredClone(selectedProject.modernization_plan.proposed_architecture))}><Pencil />Editar plano</Button>
                              <Button size="sm" variant="ghost" onClick={() => setStudentPreview((value) => !value)}><Eye />Visualizar como aluno</Button>
                              <Button size="sm" variant="ghost" onClick={() => window.print()}><Printer />Imprimir / Exportar PDF</Button>
                            </div>
                          </div>
                          {editingPlan ? <div className="space-y-4"><EditorialPlanEditor value={editingPlan} onChange={setEditingPlan} /><div className="flex gap-3"><Button disabled={savePlanMutation.isPending} onClick={() => savePlanMutation.mutate()}>Salvar nova versão</Button><Button variant="outline" onClick={() => setEditingPlan(null)}>Cancelar</Button></div></div> : studentPreview ? <div className="student-preview rounded-xl bg-background p-6"><p className="mb-5 text-xs font-bold uppercase tracking-widest text-kaizen">Prévia do aluno · não publicada</p><EditorialPlanRenderer plan={selectedProject.modernization_plan} projectType={selectedProject.project_type} citations={selectedProject.citations} /></div> : planView === "editorial" ? <div className="editorial-print-area"><EditorialPlanRenderer plan={selectedProject.modernization_plan} projectType={selectedProject.project_type} citations={selectedProject.citations} /></div> : <JsonSummary title="Plano estruturado" value={selectedProject.modernization_plan} />}
                          {selectedProject.modernization_plan.status !== "approved" && !editingPlan && <div className="no-print flex flex-wrap gap-3"><Button onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "approve", payload: { decision: "approved", notes: "Plano revisado e aprovado no Content Studio." } })}><CheckCircle2 /> Aprovar plano</Button><Button variant="outline" onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "approve", payload: { decision: "revision", notes: "Revisar o plano antes de prosseguir." } })}>Solicitar revisão</Button></div>}
                        </div>
                      )}
                      {!!versionsQuery.data?.length && <details className="no-print rounded-lg border p-4"><summary className="flex cursor-pointer list-none items-center gap-2 font-bold"><History className="h-4 w-4" />Histórico do plano ({versionsQuery.data.length})</summary><div className="mt-3 space-y-2">{versionsQuery.data.map((version) => <details key={version.id} className="rounded-md border p-3"><summary className="cursor-pointer text-sm font-semibold">Plano v{version.version} · {version.origin} · {version.state}</summary><p className="mt-1 text-xs text-muted-foreground">{version.created_by_name} · {new Date(version.created_at).toLocaleString("pt-BR")}</p><JsonSummary title={`Conteúdo da versão ${version.version}`} value={version.content} /></details>)}</div></details>}
                      <section className="no-print rounded-lg border p-4"><h4 className="flex items-center gap-2 font-bold"><MessageSquare className="h-4 w-4" />Comentários editoriais</h4><div className="mt-3 flex flex-wrap gap-2"><select aria-label="Alvo do comentário" value={commentTarget} onChange={(event) => setCommentTarget(event.target.value)} className="h-10 rounded-md border border-input bg-background px-3 text-sm">{commentTargets(selectedProject).map((target) => <option key={target.value} value={target.value}>{target.label}</option>)}</select><Input className="min-w-56 flex-1" placeholder="Adicionar comentário" value={commentText} onChange={(event) => setCommentText(event.target.value)} /><Button disabled={!commentText.trim() || commentMutation.isPending} onClick={() => commentMutation.mutate()}>Adicionar comentário</Button></div><div className="mt-3 space-y-2">{(selectedProject.editorial_comments ?? []).map((comment) => <div key={comment.id} className={`rounded-md border p-3 text-sm ${comment.resolved ? "opacity-60" : ""}`}><div className="flex justify-between gap-3"><p><strong>{comment.author_name}</strong> · {comment.target}</p>{!comment.resolved && <Button size="sm" variant="ghost" onClick={() => resolveCommentMutation.mutate(comment.id)}>Resolver</Button>}</div><p className="mt-1 whitespace-pre-wrap">{comment.text}</p></div>)}</div></section>
                      {selectedProject.modernization_plan?.status === "approved" && <section className="no-print rounded-lg border border-kaizen/30 bg-kaizen/5 p-4"><p className="font-bold text-kaizen">Gerar conteúdo editorial</p><p className="mt-1 text-xs text-muted-foreground">Escolha uma aula, módulo ou vídeo. O resultado fica em draft e não é publicado no Workspace.</p><div className="mt-3 flex flex-wrap gap-3"><select aria-label="Item para geração" value={contentTarget} onChange={(event) => setContentTarget(event.target.value)} className="h-10 min-w-64 rounded-md border border-input bg-background px-3 text-sm"><option value="">Selecione um item</option>{contentTargets(selectedProject).map((target: { value: string; label: string }) => <option key={target.value} value={target.value}>{target.label}</option>)}</select><Button disabled={!contentTarget || generateItemMutation.isPending} onClick={() => generateItemMutation.mutate()}><Sparkles />Gerar conteúdo</Button></div></section>}
                      {!!selectedProject.content_package?.generated_items?.length && <section className="rounded-lg border border-kaizen/30 bg-kaizen/5 p-4"><p className="font-bold text-kaizen">Conteúdos em draft</p><div className="mt-4 space-y-4">{selectedProject.content_package.generated_items.map((item: any) => <article key={item.id ?? `${item.target_type}-${item.target_id}-${item.generation}`} className="rounded-lg border bg-background p-4"><Badge variant="outline">{item.target_type} {item.target_index + 1} · plano v{item.plan_version ?? "legado"} · geração {item.generation ?? "legada"}</Badge><div className="mt-3"><EditorialContentRenderer value={item.content} /></div></article>)}</div></section>}
                    </div>
                  )}
                </CardContent>
              </Card>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

function JsonSummary({ title, value }: { title: string; value: unknown }) {
  return <div className="mt-3"><p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{title}</p><pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-background/70 p-3 text-xs">{JSON.stringify(value, null, 2)}</pre></div>;
}

function contentTargets(project: StudioProject) {
  const plan = project.modernization_plan?.proposed_architecture ?? {};
  if (project.project_type === "youtube") return (plan.videos ?? []).map((video: any, index: number) => ({ value: `video:${index}`, label: `Vídeo ${index + 1} · ${video.title ?? video.theme ?? "Sem título"}` }));
  const modules = (plan.modules ?? []).map((module: any, index: number) => ({ value: `module:${index}`, label: `Módulo ${index + 1} · ${module.title ?? "Sem título"}` }));
  const lessons = (plan.modules ?? []).flatMap((module: any) => module.lessons ?? []).map((lesson: any, index: number) => ({ value: `lesson:${index}`, label: `Aula ${index + 1} · ${lesson.title ?? "Sem título"}` }));
  return [...modules, ...lessons];
}

function commentTargets(project: StudioProject) {
  const plan = project.modernization_plan?.proposed_architecture ?? {};
  const targets = [{ value: "plan:", label: "Plano inteiro" }, { value: "project:", label: "Projeto" }];
  for (const [index, module] of (plan.modules ?? []).entries()) {
    if (module.editorial_id) targets.push({ value: `module:${module.editorial_id}`, label: `Módulo ${index + 1} · ${module.title ?? "Sem título"}` });
    for (const [lessonIndex, lesson] of (module.lessons ?? []).entries()) if (lesson.editorial_id) targets.push({ value: `lesson:${lesson.editorial_id}`, label: `Aula ${lessonIndex + 1} · ${lesson.title ?? "Sem título"}` });
  }
  for (const [index, video] of (plan.videos ?? []).entries()) if (video.editorial_id) targets.push({ value: `video:${video.editorial_id}`, label: `Vídeo ${index + 1} · ${video.title ?? "Sem título"}` });
  return targets;
}

function Metric({ icon: Icon, label, value }: { icon: typeof Database; label: string; value: number }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="rounded-lg bg-primary/10 p-3 text-primary"><Icon className="h-5 w-5" /></div>
        <div><p className="text-2xl font-black">{value}</p><p className="text-xs text-muted-foreground">{label}</p></div>
      </CardContent>
    </Card>
  );
}
