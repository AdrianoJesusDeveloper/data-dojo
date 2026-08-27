import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Database,
  FileQuestion,
  FolderSearch,
  LoaderCircle,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast, Toaster } from "sonner";

import { DojoHeader } from "@/components/DojoHeader";
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
};

type PaginatedSources = { count: number; results: LibrarySource[] };
type Book = { id: number; title: string; author: string; status: string };
type StudioProject = {
  id: number; title: string; theme: string; objective: string; status: string; books: number[];
  modernization_plan?: any; citations: Array<{ id: number; book_title: string; page_number: number | null; excerpt: string }>;
  content_package?: any;
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
  const [projectTitle, setProjectTitle] = useState("");
  const [projectTheme, setProjectTheme] = useState("");
  const [projectObjective, setProjectObjective] = useState("");
  const [selectedBook, setSelectedBook] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const isLocal = useMemo(() => localOrigin(API_ORIGIN), []);

  const statusQuery = useQuery({
    queryKey: ["content-studio-status"],
    queryFn: async () => (await api.get<StudioStatus>("/api/library/studio/status/")).data,
    enabled: isLocal,
    retry: false,
  });

  const sourcesQuery = useQuery({
    queryKey: ["content-studio-sources", search],
    queryFn: async () => (
      await api.get<PaginatedSources>("/api/library/sources/", { params: search ? { search } : {} })
    ).data,
    enabled: isLocal && statusQuery.isSuccess,
    retry: false,
  });

  const booksQuery = useQuery({
    queryKey: ["content-studio-books"],
    queryFn: async () => (await api.get<{ results: Book[] }>("/api/library/books/")).data.results,
    enabled: isLocal && statusQuery.isSuccess,
    retry: false,
  });

  const projectsQuery = useQuery({
    queryKey: ["content-studio-projects"],
    queryFn: async () => (await api.get<{ results: StudioProject[] }>("/api/library/studio/projects/")).data.results,
    enabled: isLocal && statusQuery.isSuccess,
    retry: false,
  });

  const selectedProject = projectsQuery.data?.find((project) => project.id === selectedProjectId) ?? projectsQuery.data?.[0];

  const createProjectMutation = useMutation({
    mutationFn: async () => (await api.post("/api/library/studio/projects/", {
      title: projectTitle, theme: projectTheme, objective: projectObjective,
      books: selectedBook ? [Number(selectedBook)] : [], source: null,
    })).data,
    onSuccess: (project) => {
      toast.success("Projeto editorial criado.");
      setSelectedProjectId(project.id); setProjectTitle(""); setProjectTheme(""); setProjectObjective(""); setSelectedBook("");
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
                    <CardDescription>Arquivos encontrados sem expor o caminho absoluto do computador.</CardDescription>
                  </div>
                  <div className="relative w-full sm:w-72">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar livro ou pasta" className="pl-9" />
                  </div>
                </CardHeader>
                <CardContent>
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
                          <tr><th className="py-3 pr-4">Arquivo</th><th className="py-3 pr-4">Tipo</th><th className="py-3 pr-4">Tamanho</th><th className="py-3">Estado</th></tr>
                        </thead>
                        <tbody>
                          {sources.map((source) => (
                            <tr key={source.id} className="border-b border-border/60 last:border-0">
                              <td className="max-w-md py-4 pr-4"><p className="truncate font-medium" title={source.relative_path}>{source.filename}</p><p className="truncate text-xs text-muted-foreground">{source.relative_path}</p></td>
                              <td className="py-4 pr-4 font-mono text-xs uppercase">{source.extension}</td>
                              <td className="py-4 pr-4 text-muted-foreground">{formatSize(source.size_bytes)}</td>
                              <td className="py-4"><div className="flex flex-wrap gap-2"><Badge variant={source.status === "supported" ? "default" : source.status === "missing" ? "destructive" : "secondary"}>{statusLabels[source.status]}</Badge>{source.duplicate && <Badge variant="outline">Duplicado</Badge>}</div></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
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
                  <select value={selectedBook} onChange={(event) => setSelectedBook(event.target.value)} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm">
                    <option value="">Selecione um livro processado</option>
                    {(booksQuery.data ?? []).map((book) => <option key={book.id} value={book.id} disabled={book.status !== "ready"}>{book.title} — {book.status}</option>)}
                  </select>
                  <Button className="w-full" disabled={!projectTitle || !projectTheme || !projectObjective || createProjectMutation.isPending} onClick={() => createProjectMutation.mutate()}>
                    {createProjectMutation.isPending ? <LoaderCircle className="animate-spin" /> : <Sparkles />} Criar projeto editorial
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div><CardTitle>Workflow com aprovação humana</CardTitle><CardDescription>Nenhum pacote é gerado antes de você aprovar o plano.</CardDescription></div>
                    <select value={selectedProject?.id ?? ""} onChange={(event) => setSelectedProjectId(Number(event.target.value))} className="h-9 rounded-md border border-input bg-background px-3 text-sm">
                      {(projectsQuery.data ?? []).map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}
                    </select>
                  </div>
                </CardHeader>
                <CardContent>
                  {!selectedProject ? <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">Crie seu primeiro projeto para iniciar o workflow.</div> : (
                    <div className="space-y-5">
                      <div className="flex flex-wrap items-center gap-3"><Badge>{selectedProject.status}</Badge><h3 className="font-display text-xl font-bold">{selectedProject.title}</h3></div>
                      <p className="text-sm text-muted-foreground">{selectedProject.objective}</p>
                      {!selectedProject.modernization_plan && <Button disabled={!selectedProject.books.length || workflowMutation.isPending} onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "generate-plan" })}><Sparkles /> Gerar plano com fontes</Button>}
                      {selectedProject.modernization_plan && (
                        <div className="space-y-4 rounded-lg border p-4">
                          <div><p className="text-xs font-bold uppercase tracking-wide text-kaizen">Resumo das fontes</p><p className="mt-1 text-sm">{selectedProject.modernization_plan.source_summary}</p></div>
                          <JsonSummary title="Arquitetura proposta" value={selectedProject.modernization_plan.proposed_architecture} />
                          <JsonSummary title="Critérios de aceite" value={selectedProject.modernization_plan.acceptance_criteria} />
                          <JsonSummary title="Riscos" value={selectedProject.modernization_plan.risks} />
                          {selectedProject.modernization_plan.status !== "approved" && <div className="flex flex-wrap gap-3"><Button onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "approve", payload: { decision: "approved", notes: "Plano revisado e aprovado no Content Studio." } })}><CheckCircle2 /> Aprovar plano</Button><Button variant="outline" onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "approve", payload: { decision: "revision", notes: "Revisar o plano antes de prosseguir." } })}>Solicitar revisão</Button></div>}
                        </div>
                      )}
                      {!!selectedProject.citations?.length && <details className="rounded-lg border p-4"><summary className="cursor-pointer font-medium">Fontes recuperadas ({selectedProject.citations.length})</summary><div className="mt-4 space-y-3">{selectedProject.citations.map((citation) => <blockquote key={citation.id} className="border-l-2 border-kaizen pl-3 text-xs text-muted-foreground"><strong className="text-foreground">{citation.book_title}, p. {citation.page_number ?? "n/d"}</strong><br />{citation.excerpt}</blockquote>)}</div></details>}
                      {selectedProject.modernization_plan?.status === "approved" && !selectedProject.content_package && <Button disabled={workflowMutation.isPending} onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "generate-content" })}><Sparkles /> Gerar aula, kata e roteiro</Button>}
                      {selectedProject.content_package && <div className="rounded-lg border border-kaizen/30 bg-kaizen/5 p-4"><p className="font-bold text-kaizen">Pacote de conteúdo gerado</p><JsonSummary title="Plano de estudo" value={selectedProject.content_package.study_plan} /><JsonSummary title="Roteiro de vídeo" value={selectedProject.content_package.video_script} /></div>}
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
