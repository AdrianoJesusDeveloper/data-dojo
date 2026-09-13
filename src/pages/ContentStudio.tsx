import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Archive,
  BookOpen,
  CheckCircle2,
  Database,
  FileQuestion,
  FileText,
  FolderSearch,
  GraduationCap,
  History,
  LoaderCircle,
  Eye,
  MessageSquare,
  Pencil,
  Printer,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { flushSync } from "react-dom";
import { toast, Toaster } from "sonner";

import { DojoHeader } from "@/components/DojoHeader";
import { Teleprompter } from "@/components/content-studio/Teleprompter";
import { downloadFilename } from "@/lib/download-filename";
import { EditorialPlanEditor } from "@/components/content-studio/EditorialPlanEditor";
import { EditorialContentRenderer, EditorialPlanRenderer } from "@/components/content-studio/EditorialPlanRenderer";
import { KnowledgeMapV1 } from "@/components/content-studio/KnowledgeMapV1";
import { SenseiStudyPlanDialog } from "@/components/content-studio/SenseiStudyPlanDialog";
import { SenseiJourneyButton } from "@/components/content-studio/SenseiJourneyButton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { API_ORIGIN, api } from "@/lib/api";
import {
  isContentFlow,
  isFormationFlow,
  type EditorialProjectType,
} from "@/lib/editorial-project-type";

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
  book_progress_percent: number | null;
  book_progress_stage: string;
  book_error: string;
};

type PaginatedSources = { count: number; next: string | null; previous: string | null; results: LibrarySource[] };
type Book = { id: number; title: string; author: string; status: string; source: number | null };
type CouncilAgentRun = { id: number; role: string; status: string; provider: string; model: string; output_payload: Record<string, unknown>; error_code: string };
type CouncilRun = { id: number; plan_version: number; status: string; final_synthesis: Record<string, unknown>; agent_runs: CouncilAgentRun[]; created_at: string; human_decision?: string | null; human_decision_by?: string | null; human_decision_at?: string | null };
type ProductionChannel = "youtube" | "instagram" | "facebook" | "linkedin" | "premium";
type ProductionFormat =
  | "long_video"
  | "short_vertical"
  | "reel"
  | "feed_post"
  | "carousel"
  | "stories"
  | "article"
  | "premium_formation"
  | "premium_lesson"
  | "slides"
  | "recording_package";

type StudioProject = {
  id: number; title: string; theme: string; objective: string; original_intent: string; project_type: EditorialProjectType; production_channel: ProductionChannel | ""; production_format: ProductionFormat | ""; research_policy: "ACERVO_ONLY" | "WEB_ONLY" | "HYBRID"; status: string; books: number[];
  modernization_plan?: any; citations: Array<{ id: number; book_title: string; page_number: number | null; excerpt: string }>;
  content_package?: any;
  editorial_comments: Array<{ id: number; text: string; target: string; target_type: string; target_id: string; plan_version: number | null; resolved: boolean; resolved_at: string | null; author_name: string; created_at: string }>;
  is_archived: boolean;
  research_context?: { status: string; policy: string; dossier: Record<string, unknown>; evidence: Array<{ id: number; source_kind: "ACERVO" | "WEB" | "GAP"; title: string; url: string; domain: string; excerpt: string; retrieved_at: string }> };
  artifacts?: Array<{ id: number; artifact_type: string; target_type: string; status: "DRAFT" | "REVIEW" | "APPROVED"; plan_version: number; generation: number; content: Record<string, unknown> }>;
  formation_link?: { formation: number; synced_plan_version: number; synced_at: string };
};
type SenseiProgress = { percentage: string; state: "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED" };
type SenseiFormation = { id: number; title: string; slug: string; description: string; objective: string; status: "DRAFT" | "ACTIVE" | "PAUSED" | "COMPLETED" | "ARCHIVED"; level: string; module_count: number; competency_count: number; progress: SenseiProgress | null };
type SenseiUnit = { id: number; title: string; objective: string; order: number; status: string };
type SenseiModule = { id: number; title: string; description: string; order: number; unit_count: number; study_units: SenseiUnit[] };
type SenseiCompetency = { id: number; module: number | null; title: string; description: string; expected_level: number; expected_level_label: string; mastery_criteria: string[]; evidence_count: number; progress: { current_level: number; current_level_label: string; state: string } | null };

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
  supported: "Pronto para processar",
  unsupported: "Catalogado",
  missing: "Ausente",
};

const productionFormatOptions: Record<ProductionChannel, Array<{ value: ProductionFormat; label: string }>> = {
  youtube: [
    { value: "long_video", label: "Vídeo completo" },
    { value: "short_vertical", label: "YouTube Short" },
    { value: "slides", label: "Slides para vídeo" },
    { value: "recording_package", label: "Pacote de gravação" },
  ],
  instagram: [
    { value: "reel", label: "Instagram Reel" },
    { value: "feed_post", label: "Post de feed" },
    { value: "carousel", label: "Carrossel" },
    { value: "stories", label: "Stories" },
  ],
  facebook: [
    { value: "reel", label: "Facebook Reel" },
    { value: "feed_post", label: "Post" },
    { value: "long_video", label: "Vídeo" },
    { value: "carousel", label: "Carrossel" },
  ],
  linkedin: [
    { value: "feed_post", label: "Post profissional" },
    { value: "article", label: "Artigo" },
    { value: "carousel", label: "Carrossel / documento" },
  ],
  premium: [
    { value: "premium_formation", label: "Formação Premium" },
    { value: "premium_lesson", label: "Aula Premium" },
    { value: "slides", label: "Slides didáticos" },
    { value: "recording_package", label: "Pacote de gravação da aula" },
  ],
};

const defaultProductionFormat: Record<ProductionChannel, ProductionFormat> = {
  youtube: "long_video",
  instagram: "reel",
  facebook: "reel",
  linkedin: "feed_post",
  premium: "premium_formation",
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
  const [projectIntent, setProjectIntent] = useState("");
  const [projectType, setProjectType] = useState<"content" | "formation">("formation");
  const [productionChannel, setProductionChannel] = useState<ProductionChannel>("premium");
  const [productionFormat, setProductionFormat] = useState<ProductionFormat>("premium_formation");
  const [researchPolicy, setResearchPolicy] = useState<"ACERVO_ONLY" | "WEB_ONLY" | "HYBRID">("ACERVO_ONLY");
  const [selectedBook, setSelectedBook] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [planView, setPlanView] = useState<"editorial" | "technical">("editorial");
  const [showArchived, setShowArchived] = useState(false);
  const [editingPlan, setEditingPlan] = useState<Record<string, unknown> | null>(null);
  const [studentPreview, setStudentPreview] = useState(false);
  const [readingMode, setReadingMode] = useState(false);
  const [teleprompterId, setTeleprompterId] = useState<number | null>(null);
  const [exportingPlanFormat, setExportingPlanFormat] = useState<"pdf" | "docx" | "pptx" | null>(null);
  const [exportingCouncilFormat, setExportingCouncilFormat] = useState<"pdf" | "docx" | "pptx" | null>(null);
  const [commentText, setCommentText] = useState("");
  const [commentTarget, setCommentTarget] = useState("plan:");
  const [contentTarget, setContentTarget] = useState("");
  const [selectedFormationId, setSelectedFormationId] = useState<number | null>(null);
  const [selectedStudyUnit, setSelectedStudyUnit] = useState<SenseiUnit | null>(null);
  const isLocal = useMemo(() => localOrigin(API_ORIGIN), []);

  const openFormation = (formationId: number) => {
    setSelectedStudyUnit(null);
    setSelectedFormationId(formationId);
  };

  useEffect(() => {
    setSelectedStudyUnit(null);
  }, [selectedFormationId]);

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

  const formationsQuery = useQuery({
    queryKey: ["sensei-formations"],
    queryFn: async () => {
      const data = (await api.get<SenseiFormation[] | { results: SenseiFormation[] }>("/api/library/sensei-formations/")).data;
      return Array.isArray(data) ? data : data.results;
    },
    enabled: isLocal && statusQuery.isSuccess,
    retry: false,
  });

  const selectedFormation = formationsQuery.data?.find((formation) => formation.id === selectedFormationId) ?? null;
  const formationModulesQuery = useQuery({
    queryKey: ["sensei-formation-modules", selectedFormationId],
    queryFn: async () => (await api.get<SenseiModule[]>(`/api/library/sensei-formations/${selectedFormationId}/modules/`)).data,
    enabled: Boolean(selectedFormationId), retry: false,
  });
  const formationCompetenciesQuery = useQuery({
    queryKey: ["sensei-formation-competencies", selectedFormationId],
    queryFn: async () => (await api.get<SenseiCompetency[]>(`/api/library/sensei-formations/${selectedFormationId}/competencies/`)).data,
    enabled: Boolean(selectedFormationId), retry: false,
  });
  const formationProgressQuery = useQuery({
    queryKey: ["sensei-formation-progress", selectedFormationId],
    queryFn: async () => (await api.get<SenseiProgress>(`/api/library/sensei-formations/${selectedFormationId}/progress/`)).data,
    enabled: Boolean(selectedFormationId), retry: false,
  });

  const selectedProject = projectsQuery.data?.find((project) => project.id === selectedProjectId) ?? projectsQuery.data?.[0];
  const teleprompterArtifact = selectedProject?.artifacts?.find((artifact) => artifact.id === teleprompterId && ["REVIEW", "APPROVED"].includes(artifact.status));
  useEffect(() => {
    setTeleprompterId(null);
    setEditingPlan(null);
    setReadingMode(false);
  }, [selectedProject?.id]);
  const selectedBookData = booksQuery.data?.find((book) => book.id === Number(selectedBook));

  const versionsQuery = useQuery({
    queryKey: ["content-studio-plan-versions", selectedProject?.id],
    queryFn: async () => (await api.get<Array<{ id: number; version: number; content: unknown; origin: string; state: string; created_by_name: string; created_at: string }>>(`/api/library/studio/projects/${selectedProject!.id}/plan/versions/`)).data,
    enabled: Boolean(selectedProject?.modernization_plan),
    retry: false,
  });

  const councilQuery = useQuery({
    queryKey: ["content-studio-council", selectedProject?.id],
    queryFn: async () => (await api.get<CouncilRun[]>(`/api/library/studio/projects/${selectedProject!.id}/council-runs/`)).data,
    enabled: Boolean(selectedProject?.modernization_plan),
    retry: false,
  });

  const refreshProjects = () => { queryClient.invalidateQueries({ queryKey: ["content-studio-projects"] }); queryClient.invalidateQueries({ queryKey: ["content-studio-plan-versions"] }); };

  const createProjectMutation = useMutation({
    mutationFn: async () => (await api.post("/api/library/studio/projects/", {
      title: projectTitle, theme: projectTheme, objective: projectObjective, original_intent: projectIntent,
      project_type: projectType,
      production_channel: productionChannel,
      production_format: productionFormat,
      research_policy: researchPolicy,
      books: selectedBookData ? [selectedBookData.id] : [], source: selectedBookData?.source ?? null,
    })).data,
    onSuccess: (project) => {
      toast.success("Projeto editorial criado.");
      setSelectedProjectId(project.id); setProjectTitle(""); setProjectTheme(""); setProjectObjective(""); setProjectIntent(""); setProjectType("formation"); setProductionChannel("premium"); setProductionFormat("premium_formation"); setResearchPolicy("ACERVO_ONLY"); setSelectedBook("");
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

  const councilMutation = useMutation({
    mutationFn: async ({ action, runId, projectId }: { action: "run" | "approve" | "revision"; runId?: number; projectId: number }) => {
      if (action === "run") return (await api.post(`/api/library/studio/projects/${projectId}/council-runs/`, {})).data;
      if (!runId) throw new Error("missing-run");
      const endpoint = action === "approve" ? "approve" : "request-revision";
      return (await api.post(`/api/library/studio/council-runs/${runId}/${endpoint}/`, {})).data;
    },
    onSuccess: () => { toast.success("Conselho Editorial atualizado."); queryClient.invalidateQueries({ queryKey: ["content-studio-council"] }); },
    onError: (error: any) => toast.error(error.response?.data?.detail || "O Conselho Editorial não pôde concluir a operação."),
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

  const artifactMutation = useMutation({
    mutationFn: async ({ artifactId, status }: { artifactId: number; status: "DRAFT" | "REVIEW" | "APPROVED" }) =>
      (await api.post(`/api/library/studio/artifacts/${artifactId}/transition/`, { status })).data,
    onSuccess: () => { toast.success("Status editorial do artefato atualizado."); refreshProjects(); },
    onError: (error: any) => toast.error(error.response?.data?.detail || "Não foi possível atualizar o artefato."),
  });

  const downloadPlan = async (format: "pdf" | "docx" | "pptx") => {
    if (!selectedProject?.modernization_plan) {
      toast.error("Gere o plano editorial antes de exportar.");
      return;
    }
    try {
      setExportingPlanFormat(format);
      const response = await api.get<Blob>(
        `/api/library/studio/projects/${selectedProject.id}/plan/export/${format}/`,
        { responseType: "blob" },
      );
      const disposition = response.headers?.["content-disposition"] as string | undefined;
      const fallback = `content-studio-${selectedProject.id}.${format}`;
      const filename = downloadFilename(disposition, fallback);
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} exportado com sucesso.`);
    } catch (error: any) {
      const status = error.response?.status;
      toast.error(status === 404 ? "O plano editorial não foi encontrado para exportação." : "Não foi possível exportar o plano.");
    } finally {
      setExportingPlanFormat(null);
    }
  };

  const downloadCouncilReport = async (runId: number, format: "pdf" | "docx" | "pptx") => {
    try {
      setExportingCouncilFormat(format);
      const response = await api.get<Blob>(
        `/api/library/studio/council-runs/${runId}/export/${format}/`,
        { responseType: "blob" },
      );
      const disposition = response.headers?.["content-disposition"] as string | undefined;
      const filename = downloadFilename(disposition, `conselho-editorial-${runId}.${format}`);
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      toast.success(`Relatório do Conselho em ${format.toUpperCase()} exportado com sucesso.`);
    } catch (error: any) {
      toast.error(error.response?.status === 404 ? "Relatório do Conselho não encontrado." : "Não foi possível exportar o relatório do Conselho.");
    } finally {
      setExportingCouncilFormat(null);
    }
  };

  const downloadArtifact = async (artifactId: number, format: "docx" | "html" | "teleprompter") => {
    try {
      const response = await api.get<Blob>(`/api/library/studio/artifacts/${artifactId}/export/${format}/`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = `artefato-${artifactId}.${format === "docx" ? "docx" : "html"}`;
      document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
    } catch { toast.error("Não foi possível exportar o artefato."); }
  };

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
      {teleprompterArtifact && typeof teleprompterArtifact.content.teleprompter_text === "string" && (
        <Teleprompter key={teleprompterArtifact.id} title={String(teleprompterArtifact.content.title || "Roteiro")}
          text={teleprompterArtifact.content.teleprompter_text}
          sourceNote={typeof teleprompterArtifact.content.source_summary === "string" ? teleprompterArtifact.content.source_summary : undefined}
          status={teleprompterArtifact.status as "REVIEW" | "APPROVED"} onClose={() => setTeleprompterId(null)} />
      )}
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
              <Metric icon={BookOpen} label="Arquivos suportados" value={status.supported} />
              <Metric icon={CheckCircle2} label="Livros processados" value={status.ready_books} />
              <Metric icon={Sparkles} label="Roteiros gerados" value={status.scripts} />
            </section>

            <section className="mt-8" aria-labelledby="sensei-formation-title">
              <Card className="border-primary/30">
                <CardHeader><div className="flex items-start gap-3"><div className="rounded-lg bg-primary/10 p-3 text-primary"><GraduationCap className="h-6 w-6" /></div><div><CardTitle id="sensei-formation-title">FORMAÇÃO DO SENSEI</CardTitle><CardDescription>Estudo e conclusão são registrados separadamente de competência demonstrada e aptidão para ensinar.</CardDescription></div></div></CardHeader>
                <CardContent className="space-y-5">
                  {formationsQuery.isLoading ? <p className="flex items-center gap-2 text-sm text-muted-foreground"><LoaderCircle className="h-4 w-4 animate-spin" />Carregando formações...</p> : !(formationsQuery.data?.length) ? <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">Nenhuma formação cadastrada.</p> : <div className="grid gap-3 md:grid-cols-2">{formationsQuery.data.map((formation) => <article key={formation.id} className="rounded-lg border bg-background p-4"><div className="flex flex-wrap items-center gap-2"><Badge>{formation.status}</Badge>{formation.level && <Badge variant="outline">{formation.level}</Badge>}</div><h3 className="mt-3 font-display text-lg font-bold">{formation.title}</h3><p className="mt-2 text-sm text-muted-foreground">{formation.description}</p><div className="mt-3 flex flex-wrap gap-4 text-xs text-muted-foreground"><span>{formation.module_count} módulos</span><span>{formation.competency_count} competências</span><span>{formation.progress?.percentage ?? "0.00"}% demonstrado</span></div><div className="flex flex-wrap gap-2"><Button className="mt-4" size="sm" variant={selectedFormationId === formation.id ? "default" : "outline"} onClick={() => openFormation(formation.id)}>Abrir formação</Button><SenseiJourneyButton formationId={formation.id} onOpen={(unit) => { openFormation(formation.id); setSelectedStudyUnit(unit); }} /></div></article>)}</div>}
                  {selectedFormation && <div className="rounded-xl border bg-secondary/10 p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-widest text-kaizen">Visão geral</p><h3 className="mt-1 font-display text-2xl font-bold">{selectedFormation.title}</h3><p className="mt-2 max-w-4xl text-sm text-muted-foreground">{selectedFormation.objective}</p></div><Badge variant="outline">{formationProgressQuery.data?.state ?? "NOT_STARTED"}</Badge></div><div className="mt-5 grid gap-4 sm:grid-cols-3"><div className="rounded-md border bg-background p-3"><p className="text-2xl font-black text-primary">{formationProgressQuery.data?.percentage ?? "0.00"}%</p><p className="text-xs text-muted-foreground">Competências demonstradas</p></div><div className="rounded-md border bg-background p-3"><p className="text-2xl font-black">{formationModulesQuery.data?.length ?? 0}</p><p className="text-xs text-muted-foreground">Módulos no mapa</p></div><div className="rounded-md border bg-background p-3"><p className="text-2xl font-black">{(formationCompetenciesQuery.data ?? []).reduce((total, competency) => total + competency.evidence_count, 0)}</p><p className="text-xs text-muted-foreground">Evidências registradas: {(formationCompetenciesQuery.data ?? []).reduce((total, competency) => total + competency.evidence_count, 0)}</p></div></div><div className="mt-6 border-t pt-6"><KnowledgeMapV1 key={selectedFormationId} modules={formationModulesQuery.data ?? []} competencies={formationCompetenciesQuery.data ?? []} loading={formationModulesQuery.isLoading} onOpenUnit={(unitId) => setSelectedStudyUnit((formationModulesQuery.data ?? []).flatMap((module) => module.study_units).find((unit) => unit.id === unitId) ?? null)} /></div></div>}
                </CardContent>
              </Card>
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
                    <div className="overflow-hidden rounded-lg border">
                      <div className="max-h-[520px] overflow-auto">
                        <table className="w-full text-left text-sm">
                          <thead className="sticky top-0 z-10 border-b bg-background/95 text-[11px] uppercase tracking-wide text-muted-foreground backdrop-blur">
                            <tr>
                              <th className="px-3 py-2 pr-4">Arquivo</th>
                              <th className="px-3 py-2 pr-4">Tipo</th>
                              <th className="px-3 py-2 pr-4">Tamanho</th>
                              <th className="px-3 py-2 pr-4">Estado</th>
                              <th className="px-3 py-2">Ação</th>
                            </tr>
                          </thead>
                          <tbody>
                            {sources.map((source) => (
                              <tr key={source.id} className="border-b border-border/50 align-middle last:border-0 hover:bg-muted/30">
                                <td className="max-w-[420px] px-3 py-2 pr-4">
                                  <div className="flex min-w-0 items-center gap-2">
                                    <p className="min-w-0 flex-1 truncate text-sm font-medium" title={`${source.filename}\n${source.relative_path}`}>{source.filename}</p>
                                    {source.duplicate && <Badge variant="outline" className="shrink-0 text-[10px]">Duplicado</Badge>}
                                  </div>
                                </td>
                                <td className="px-3 py-2 pr-4 font-mono text-[11px] uppercase text-muted-foreground">{source.extension}</td>
                                <td className="whitespace-nowrap px-3 py-2 pr-4 text-xs text-muted-foreground">{formatSize(source.size_bytes)}</td>
                                <td className="px-3 py-2 pr-4">
                                  <div className="flex flex-wrap items-center gap-1.5">
                                    <Badge variant={source.status === "supported" ? "default" : source.status === "missing" ? "destructive" : "secondary"} className="text-[10px]">{statusLabels[source.status]}</Badge>
                                    {source.book_status === "processing" && <Badge variant="outline" className="text-[10px]">RAG {source.book_progress_percent ?? 0}%</Badge>}
                                    {source.book_status === "ready" && <Badge variant="outline" className="text-[10px]">RAG pronto</Badge>}
                                  </div>
                                </td>
                                <td className="px-3 py-2">
                                  {source.duplicate ? <span className="text-[11px] text-muted-foreground">Indisponível</span>
                                    : source.book_status === "processing" ? (
                                      <div className="min-w-44 space-y-1.5">
                                        <div className="flex items-center justify-between gap-2 text-[11px] text-muted-foreground">
                                          <span className="inline-flex min-w-0 items-center gap-1.5">
                                            <LoaderCircle className="h-3.5 w-3.5 shrink-0 animate-spin" />
                                            <span className="truncate" title={source.book_progress_stage || "Processando"}>
                                              {source.book_progress_stage || "Processando"}
                                            </span>
                                          </span>
                                          <span className="shrink-0 font-mono font-medium">{source.book_progress_percent ?? 0}%</span>
                                        </div>
                                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                                          <div
                                            className="h-full rounded-full bg-primary transition-[width] duration-500"
                                            style={{ width: `${Math.min(100, Math.max(0, source.book_progress_percent ?? 0))}%` }}
                                          />
                                        </div>
                                      </div>
                                    )
                                    : source.status === "supported" ? <Button size="sm" variant={source.book_status === "error" ? "outline" : "default"} className="h-8 px-2.5 text-xs" disabled={processSourceMutation.isPending} onClick={() => processSourceMutation.mutate(source.id)}>{source.book_status === "error" ? "Tentar novamente" : source.book_status === "ready" ? "Reprocessar" : "Processar RAG"}</Button>
                                    : <span className="text-[11px] text-muted-foreground">Não disponível</span>}
                                  {source.book_status === "error" && <p className="mt-1 max-w-48 truncate text-[11px] text-destructive" title={source.book_error || "Erro no processamento."}>{source.book_error || "Erro no processamento."}</p>}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                  <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
                    <label className="flex items-center gap-2 text-sm text-muted-foreground">Itens por página
                      <select aria-label="Itens por página" value={sourcePageSize} onChange={(event) => { setSourcePageSize(Number(event.target.value) as 25 | 50 | 100); setSourcePage(1); }} className="h-9 rounded-md border border-input bg-background px-2 text-foreground">
                        <option value={25}>25</option><option value={50}>50</option><option value={100}>100</option>
                      </select>
                    </label>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button size="sm" variant="outline" disabled={sourcePage <= 1 || sourcesQuery.isFetching} onClick={() => setSourcePage(1)}>Primeira página</Button>
                      <Button size="sm" variant="outline" disabled={!sourcesQuery.data?.previous || sourcesQuery.isFetching} onClick={() => setSourcePage((page) => Math.max(1, page - 1))}>← Anterior</Button>
                      <span className="min-w-24 text-center text-sm font-medium">Página {sourcePage} de {sourcePages}</span>
                      <Button size="sm" variant="outline" disabled={!sourcesQuery.data?.next || sourcesQuery.isFetching} onClick={() => setSourcePage((page) => Math.min(sourcePages, page + 1))}>Próxima →</Button>
                      <Button size="sm" variant="outline" disabled={sourcePage >= sourcePages || sourcesQuery.isFetching} onClick={() => setSourcePage(sourcePages)}>Última página</Button>
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
                  <Textarea value={projectIntent} onChange={(event) => setProjectIntent(event.target.value)} placeholder="Descreva sua intenção em linguagem natural" rows={4} aria-label="Intenção original" />
                  <Input value={projectTheme} onChange={(event) => setProjectTheme(event.target.value)} placeholder="Tema ou problema real" />
                  <Textarea value={projectObjective} onChange={(event) => setProjectObjective(event.target.value)} placeholder="Objetivo, público e resultado esperado" rows={5} />
                  <select
                    aria-label="Canal de produção"
                    value={productionChannel}
                    onChange={(event) => {
                      const channel = event.target.value as ProductionChannel;
                      setProductionChannel(channel);
                      setProductionFormat(defaultProductionFormat[channel]);
                      setProjectType(channel === "premium" ? "formation" : "content");
                    }}
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="youtube">YouTube</option>
                    <option value="instagram">Instagram</option>
                    <option value="facebook">Facebook</option>
                    <option value="linkedin">LinkedIn</option>
                    <option value="premium">Formação Premium</option>
                  </select>
                  <select
                    aria-label="Formato de produção"
                    value={productionFormat}
                    onChange={(event) => setProductionFormat(event.target.value as ProductionFormat)}
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  >
                    {productionFormatOptions[productionChannel].map((format) => (
                      <option key={format.value} value={format.value}>{format.label}</option>
                    ))}
                  </select>
                  <p className="text-xs text-muted-foreground">
                    Fluxo editorial: {isFormationFlow(projectType) ? "Formação Premium" : "Conteúdo multicanal"}.
                    O mesmo projeto poderá gerar artefatos derivados sem criar geradores separados.
                  </p>
                  <select aria-label="Política de pesquisa" value={researchPolicy} onChange={(event) => setResearchPolicy(event.target.value as typeof researchPolicy)} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm">
                    <option value="ACERVO_ONLY">Somente acervo</option><option value="WEB_ONLY">Somente web</option><option value="HYBRID">Acervo + web</option>
                  </select>
                  <select value={selectedBook} onChange={(event) => setSelectedBook(event.target.value)} className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm">
                    <option value="">Selecione um livro processado</option>
                    {(booksQuery.data ?? []).map((book) => <option key={book.id} value={book.id} disabled={book.status !== "ready"}>{book.title} — {book.status}</option>)}
                  </select>
                  <Button className="w-full" disabled={!projectTitle || !projectTheme || !projectObjective || !projectIntent.trim() || (researchPolicy === "ACERVO_ONLY" && !selectedBookData) || createProjectMutation.isPending} onClick={() => createProjectMutation.mutate()}>
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
                      <section className="rounded-lg border p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-bold">PESQUISA FUNDAMENTADA</p><p className="text-xs text-muted-foreground">{selectedProject.research_policy} · intenção preservada: {selectedProject.original_intent}</p></div><Button disabled={workflowMutation.isPending} onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "research" })}><Search />Pesquisar / Construir contexto</Button></div>
                        {selectedProject.research_context && (
                          <div className="mt-4 space-y-3">
                            <div className="grid gap-3 sm:grid-cols-4">
                              <div className="rounded-md border bg-secondary/20 p-3">
                                <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Status</p>
                                <div className="mt-2"><Badge>{selectedProject.research_context.status}</Badge></div>
                              </div>
                              <div className="rounded-md border bg-secondary/20 p-3">
                                <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Evidências</p>
                                <p className="mt-1 text-xl font-black">{selectedProject.research_context.evidence.length}</p>
                              </div>
                              <div className="rounded-md border bg-secondary/20 p-3">
                                <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Acervo</p>
                                <p className="mt-1 text-xl font-black">{selectedProject.research_context.evidence.filter((item) => item.source_kind === "ACERVO").length}</p>
                              </div>
                              <div className="rounded-md border bg-secondary/20 p-3">
                                <p className="text-[11px] font-bold uppercase tracking-wide text-muted-foreground">Web</p>
                                <p className="mt-1 text-xl font-black">{selectedProject.research_context.evidence.filter((item) => item.source_kind === "WEB").length}</p>
                              </div>
                            </div>

                            <details className="group rounded-lg border bg-background">
                              <summary className="cursor-pointer list-none px-4 py-3 text-sm font-bold">
                                Ver dossiê completo da pesquisa
                                <span className="ml-2 text-xs font-normal text-muted-foreground">conteúdo recolhido por padrão</span>
                              </summary>
                              <div className="border-t p-4">
                                <EditorialContentRenderer value={selectedProject.research_context.dossier} />
                              </div>
                            </details>

                            <details className="group rounded-lg border bg-background">
                              <summary className="cursor-pointer list-none px-4 py-3 text-sm font-bold">
                                Ver fontes e evidências ({selectedProject.research_context.evidence.length})
                              </summary>
                              <div className="max-h-[420px] space-y-2 overflow-auto border-t p-3">
                                {selectedProject.research_context.evidence.map((item) => (
                                  <article key={item.id} className="rounded border p-3">
                                    <div className="flex flex-wrap items-center gap-2">
                                      <Badge variant="outline">{item.source_kind}</Badge>
                                      <strong className="min-w-0 flex-1 truncate text-sm" title={item.title || "Lacuna de pesquisa"}>
                                        {item.title || "Lacuna de pesquisa"}
                                      </strong>
                                    </div>
                                    {item.domain && (
                                      <p className="mt-1 text-xs text-muted-foreground">
                                        {item.domain} · consultado em {new Date(item.retrieved_at).toLocaleString("pt-BR")}
                                      </p>
                                    )}
                                    {item.url && (
                                      <a className="text-xs text-primary underline" href={item.url} target="_blank" rel="noreferrer">
                                        Abrir fonte
                                      </a>
                                    )}
                                    <p className="mt-2 line-clamp-3 text-xs">{item.excerpt}</p>
                                  </article>
                                ))}
                              </div>
                            </details>
                          </div>
                        )}
                      </section>
                      {!selectedProject.modernization_plan && (
                        <div className="space-y-2">
                          <Button
                            disabled={
                              (selectedProject.research_policy === "ACERVO_ONLY" && !selectedProject.books.length) ||
                              workflowMutation.isPending
                            }
                            onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "generate-plan" })}
                          >
                            <Sparkles />
                            {selectedProject.research_context?.evidence?.some((item) => item.source_kind === "ACERVO" || item.source_kind === "WEB")
                              ? "Gerar plano fundamentado"
                              : "Gerar rascunho sem fontes"}
                          </Button>
                          {!selectedProject.research_context?.evidence?.some((item) => item.source_kind === "ACERVO" || item.source_kind === "WEB") &&
                            selectedProject.research_policy !== "ACERVO_ONLY" && (
                              <p className="text-xs text-amber-500">
                                Nenhuma evidência suficiente foi localizada. O plano será gerado como rascunho não fundamentado,
                                sem referências inventadas, e deverá passar por revisão humana antes de qualquer aprovação.
                              </p>
                            )}
                        </div>
                      )}
                      {selectedProject.modernization_plan && (
                        <div className="space-y-4 rounded-lg border p-4">
                          <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-4">
                            <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-kaizen">{planView === "editorial" ? "Visão editorial" : "Visão técnica / JSON"}</p><p className="mt-1 text-xs text-muted-foreground">O objeto estruturado permanece preservado como formato interno.</p></div>
                            <div className="no-print flex flex-wrap items-center gap-1 rounded-lg border p-1" role="group" aria-label="Ações do plano editorial">
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={!editingPlan || JSON.stringify(editingPlan) === JSON.stringify(selectedProject.modernization_plan.proposed_architecture) || savePlanMutation.isPending}
                                onClick={() => savePlanMutation.mutate()}
                                title={editingPlan ? "Salvar uma nova versão do plano" : "Entre no modo de edição para salvar alterações"}
                              >
                                {savePlanMutation.isPending ? <LoaderCircle className="animate-spin" /> : <Save />}
                                Salvar
                              </Button>
                              <Button
                                size="sm"
                                variant={readingMode ? "default" : "ghost"}
                                onClick={() => {
                                  setReadingMode((value) => !value);
                                  setPlanView("editorial");
                                  setStudentPreview(false);
                                  setEditingPlan(null);
                                }}
                              >
                                <BookOpen />{readingMode ? "Sair do modo leitura" : "Modo leitura"}
                              </Button>
                              <Button size="sm" variant="ghost" disabled={!!editingPlan} onClick={() => { flushSync(() => { setReadingMode(true); setStudentPreview(false); }); window.print(); }}><Printer />Imprimir</Button>
                              <span className="mx-1 hidden h-6 w-px bg-border sm:block" aria-hidden="true" />
                              {(["pdf", "docx", "pptx"] as const).map((format) => (
                                <Button
                                  key={format}
                                  size="sm"
                                  variant="ghost"
                                  disabled={exportingPlanFormat !== null}
                                  onClick={() => void downloadPlan(format)}
                                >
                                  {exportingPlanFormat === format ? <LoaderCircle className="animate-spin" /> : <FileText />}
                                  {format.toUpperCase()}
                                </Button>
                              ))}
                              <span className="mx-1 hidden h-6 w-px bg-border sm:block" aria-hidden="true" />
                              <Button size="sm" variant={planView === "editorial" && !studentPreview ? "default" : "ghost"} onClick={() => { setPlanView("editorial"); setStudentPreview(false); setReadingMode(false); }}>Visão editorial</Button>
                              <Button size="sm" variant={planView === "technical" ? "default" : "ghost"} onClick={() => { setPlanView("technical"); setStudentPreview(false); setReadingMode(false); }}>Visão técnica / JSON</Button>
                              <Button size="sm" variant="ghost" onClick={() => { setEditingPlan(structuredClone(selectedProject.modernization_plan.proposed_architecture)); setReadingMode(false); setStudentPreview(false); }}><Pencil />Editar plano</Button>
                              <Button size="sm" variant={studentPreview ? "default" : "ghost"} onClick={() => { setStudentPreview((value) => !value); setReadingMode(false); setEditingPlan(null); }}><Eye />Visualizar como aluno</Button>
                            </div>
                          </div>
                          {editingPlan ? <div className="space-y-4"><EditorialPlanEditor value={editingPlan} onChange={setEditingPlan} /><div className="flex gap-3"><Button variant="outline" onClick={() => setEditingPlan(null)}>Cancelar edição</Button></div></div> : readingMode ? <div className="editorial-print-area mx-auto max-w-4xl rounded-xl bg-background p-6 sm:p-10"><div className="mb-6 border-b pb-4"><p className="text-xs font-bold uppercase tracking-[0.2em] text-kaizen">Modo leitura</p><h3 className="mt-2 font-display text-2xl font-bold">{selectedProject.title}</h3><p className="mt-2 text-sm text-muted-foreground">{selectedProject.objective}</p></div><EditorialPlanRenderer plan={selectedProject.modernization_plan} projectType={selectedProject.project_type} citations={selectedProject.citations} /></div> : studentPreview ? <div className="student-preview rounded-xl bg-background p-6"><p className="mb-5 text-xs font-bold uppercase tracking-widest text-kaizen">Prévia do aluno · não publicada</p><EditorialPlanRenderer plan={selectedProject.modernization_plan} projectType={selectedProject.project_type} citations={selectedProject.citations} /></div> : planView === "editorial" ? <div className="editorial-print-area"><EditorialPlanRenderer plan={selectedProject.modernization_plan} projectType={selectedProject.project_type} citations={selectedProject.citations} /></div> : <JsonSummary title="Plano estruturado" value={selectedProject.modernization_plan} />}
                          {selectedProject.modernization_plan.status !== "approved" && !editingPlan && <div className="no-print flex flex-wrap gap-3"><Button onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "approve", payload: { decision: "approved", notes: "Plano revisado e aprovado no Content Studio." } })}><CheckCircle2 /> Aprovar plano</Button><Button variant="outline" onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "approve", payload: { decision: "revision", notes: "Revisar o plano antes de prosseguir." } })}>Solicitar revisão</Button></div>}
                        </div>
                      )}
                      {!!versionsQuery.data?.length && <details className="no-print rounded-lg border p-4"><summary className="flex cursor-pointer list-none items-center gap-2 font-bold"><History className="h-4 w-4" />Histórico do plano ({versionsQuery.data.length})</summary><div className="mt-3 space-y-2">{versionsQuery.data.map((version) => <details key={version.id} className="rounded-md border p-3"><summary className="cursor-pointer text-sm font-semibold">Plano v{version.version} · {version.origin} · {version.state}</summary><p className="mt-1 text-xs text-muted-foreground">{version.created_by_name} · {new Date(version.created_at).toLocaleString("pt-BR")}</p><JsonSummary title={`Conteúdo da versão ${version.version}`} value={version.content} /></details>)}</div></details>}
                      <section className="no-print rounded-lg border p-4"><h4 className="flex items-center gap-2 font-bold"><MessageSquare className="h-4 w-4" />Comentários editoriais</h4><div className="mt-3 flex flex-wrap gap-2"><select aria-label="Alvo do comentário" value={commentTarget} onChange={(event) => setCommentTarget(event.target.value)} className="h-10 rounded-md border border-input bg-background px-3 text-sm">{commentTargets(selectedProject).map((target) => <option key={target.value} value={target.value}>{target.label}</option>)}</select><Input className="min-w-56 flex-1" placeholder="Adicionar comentário" value={commentText} onChange={(event) => setCommentText(event.target.value)} /><Button disabled={!commentText.trim() || commentMutation.isPending} onClick={() => commentMutation.mutate()}>Adicionar comentário</Button></div><div className="mt-3 space-y-2">{(selectedProject.editorial_comments ?? []).map((comment) => <div key={comment.id} className={`rounded-md border p-3 text-sm ${comment.resolved ? "opacity-60" : ""}`}><div className="flex justify-between gap-3"><p><strong>{comment.author_name}</strong> · {comment.target}</p>{!comment.resolved && <Button size="sm" variant="ghost" onClick={() => resolveCommentMutation.mutate(comment.id)}>Resolver</Button>}</div><p className="mt-1 whitespace-pre-wrap">{comment.text}</p></div>)}</div></section>
                      {selectedProject.modernization_plan?.status === "approved" && <CouncilPanel projectId={selectedProject.id} projectTitle={selectedProject.title} projectObjective={selectedProject.objective} runs={councilQuery.data ?? []} loading={councilQuery.isLoading || councilMutation.isPending} exportingFormat={exportingCouncilFormat} onExport={(runId, format) => void downloadCouncilReport(runId, format)} onAction={(args) => councilMutation.mutate(args)} />}
                      {selectedProject.modernization_plan?.status === "approved" && <section className="no-print rounded-lg border border-kaizen/30 bg-kaizen/5 p-4"><p className="font-bold text-kaizen">Gerar conteúdo editorial</p><p className="mt-1 text-xs text-muted-foreground">Escolha uma aula, módulo ou vídeo. O resultado fica em draft e não é publicado no Workspace.</p><div className="mt-3 flex flex-wrap gap-3"><select aria-label="Item para geração" value={contentTarget} onChange={(event) => setContentTarget(event.target.value)} className="h-10 min-w-64 rounded-md border border-input bg-background px-3 text-sm"><option value="">Selecione um item</option>{contentTargets(selectedProject).map((target: { value: string; label: string }) => <option key={target.value} value={target.value}>{target.label}</option>)}</select><Button disabled={!contentTarget || generateItemMutation.isPending} onClick={() => generateItemMutation.mutate()}><Sparkles />Gerar conteúdo</Button></div></section>}
                      {isFormationFlow(selectedProject.project_type) && selectedProject.modernization_plan?.status === "approved" && <section className="rounded-lg border border-primary/30 p-4"><p className="font-bold">FORMAÇÃO EXECUTÁVEL</p><p className="mt-1 text-xs text-muted-foreground">Sincroniza o plano aprovado com SenseiFormation sem publicar aulas automaticamente.</p><Button className="mt-3" disabled={workflowMutation.isPending} onClick={() => workflowMutation.mutate({ projectId: selectedProject.id, action: "materialize-formation" })}><GraduationCap />{selectedProject.formation_link ? `Sincronizar formação #${selectedProject.formation_link.formation}` : "Materializar formação"}</Button></section>}
                      {!!selectedProject.artifacts?.length && <section className="rounded-lg border p-4"><p className="font-bold">ARTEFATOS EDITORIAIS</p><div className="mt-3 space-y-3">{selectedProject.artifacts.map((artifact) => <article key={artifact.id} className="rounded border bg-background p-3"><div className="flex flex-wrap items-center gap-2"><Badge>{artifact.status}</Badge><strong>{artifact.artifact_type}</strong><span className="text-xs text-muted-foreground">plano v{artifact.plan_version} · geração {artifact.generation}</span></div><div className="mt-2"><EditorialContentRenderer value={artifact.content} /></div><div className="mt-3 flex flex-wrap gap-2">{artifact.status === "DRAFT" && <Button size="sm" onClick={() => artifactMutation.mutate({ artifactId: artifact.id, status: "REVIEW" })}>Enviar para revisão</Button>}{artifact.status === "REVIEW" && <><Button size="sm" onClick={() => artifactMutation.mutate({ artifactId: artifact.id, status: "APPROVED" })}>Aprovar artefato</Button><Button size="sm" variant="outline" onClick={() => artifactMutation.mutate({ artifactId: artifact.id, status: "DRAFT" })}>Retornar a draft</Button></>}{artifact.status !== "DRAFT" && <><Button size="sm" variant="outline" onClick={() => void downloadArtifact(artifact.id, "docx")}>DOCX</Button><Button size="sm" variant="outline" onClick={() => void downloadArtifact(artifact.id, "html")}>HTML</Button>{["YOUTUBE_PACKAGE", "PREMIUM_CONTENT"].includes(artifact.artifact_type) && typeof artifact.content.teleprompter_text === "string" && artifact.content.teleprompter_text.trim() && <Button size="sm" variant="outline" onClick={() => setTeleprompterId(artifact.id)}>Teleprompter</Button>}</>}</div></article>)}</div></section>}
                      {!!selectedProject.content_package?.generated_items?.length && <section className="rounded-lg border border-kaizen/30 bg-kaizen/5 p-4"><p className="font-bold text-kaizen">Histórico de gerações</p><p className="mt-1 text-xs text-muted-foreground">Registro original de cada geração. O status atual de revisão e aprovação aparece em Artefatos editoriais.</p><div className="mt-4 space-y-4">{selectedProject.content_package.generated_items.map((item: any) => <article key={item.id ?? `${item.target_type}-${item.target_id}-${item.generation}`} className="rounded-lg border bg-background p-4"><Badge variant="outline">{item.target_type} {item.target_index + 1} · plano v{item.plan_version ?? "legado"} · geração {item.generation ?? "legada"}</Badge><div className="mt-3"><EditorialContentRenderer value={item.content} /></div></article>)}</div></section>}
                    </div>
                  )}
                </CardContent>
              </Card>
            </section>
          </>
        )}
      </main>
      <SenseiStudyPlanDialog formationId={selectedFormationId} unitId={selectedStudyUnit?.id ?? null} unitTitle={selectedStudyUnit?.title ?? "Plano de estudo"} onClose={() => setSelectedStudyUnit(null)} />
    </div>
  );
}

function JsonSummary({ title, value }: { title: string; value: unknown }) {
  return <div className="mt-3"><p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{title}</p><pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-background/70 p-3 text-xs">{JSON.stringify(value, null, 2)}</pre></div>;
}

const councilRoleLabels: Record<string, string> = {
  technical: "Técnico", pedagogy: "Pedagogia", learning_science: "Ciência da aprendizagem",
  technical_content: "Conteúdo técnico", youtube: "YouTube", social_media: "Redes sociais",
  seo: "SEO", fact_checker: "Fact-checking",
};

function CouncilPanel({ projectId, projectTitle, projectObjective, runs, loading, exportingFormat, onExport, onAction }: { projectId: number; projectTitle: string; projectObjective: string; runs: CouncilRun[]; loading: boolean; exportingFormat: "pdf" | "docx" | "pptx" | null; onExport: (runId: number, format: "pdf" | "docx" | "pptx") => void; onAction: (args: { action: "run" | "approve" | "revision"; runId?: number; projectId: number }) => void }) {
  const latest = runs[0];
  const awaitingDecision = latest?.status === "awaiting_human_approval";
  const active = latest && ["queued", "running", "reviewing"].includes(latest.status);
  const [readingReport, setReadingReport] = useState(false);

  const printReport = () => {
    flushSync(() => setReadingReport(true));
    window.print();
  };

  return <section className="rounded-lg border border-primary/30 bg-primary/5 p-4" aria-labelledby="editorial-council-title">
    <div className="no-print flex flex-wrap items-start justify-between gap-3">
      <div><h4 id="editorial-council-title" className="font-bold">CONSELHO EDITORIAL</h4><p className="mt-1 text-xs text-muted-foreground">O Sensei Editorial coordena especialistas. A IA propõe e revisa; somente uma pessoa aprova.</p></div>
      <Button disabled={loading || Boolean(active)} onClick={() => onAction({ action: "run", projectId })}>{loading ? <LoaderCircle className="animate-spin" /> : <Sparkles />}{latest ? "Executar novo Conselho" : "Executar Conselho"}</Button>
    </div>
    {!latest ? <p className="no-print mt-4 rounded-md border border-dashed p-4 text-sm text-muted-foreground">Nenhuma análise executada para este projeto.</p> : <div className="mt-4 space-y-4">
      <div className="no-print flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-background p-2">
        <div className="flex flex-wrap items-center gap-2"><Badge>{latest.status}</Badge><Badge variant="outline">Conselho #{latest.id}</Badge><Badge variant="outline">Plano v{latest.plan_version}</Badge><span className="text-xs text-muted-foreground">{new Date(latest.created_at).toLocaleString("pt-BR")}</span></div>
        <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Ações do relatório do Conselho Editorial">
          <Button size="sm" variant="ghost" onClick={() => toast.success("O relatório do Conselho já está salvo no histórico do projeto.")}><Save />Salvar</Button>
          <Button size="sm" variant={readingReport ? "default" : "ghost"} onClick={() => setReadingReport((v) => !v)}><BookOpen />{readingReport ? "Sair do modo leitura" : "Modo leitura"}</Button>
          <Button size="sm" variant="ghost" onClick={printReport}><Printer />Imprimir</Button>
          <span className="mx-1 hidden h-6 w-px bg-border sm:block" aria-hidden="true" />
          {(["pdf", "docx", "pptx"] as const).map((format) => <Button key={format} size="sm" variant="ghost" disabled={exportingFormat !== null} onClick={() => onExport(latest.id, format)}>{exportingFormat === format ? <LoaderCircle className="animate-spin" /> : <FileText />}{format.toUpperCase()}</Button>)}
        </div>
      </div>
      <div className={readingReport ? "council-print-area mx-auto max-w-4xl rounded-xl bg-background p-6 sm:p-10" : "council-print-area"}>
        {readingReport && <div className="mb-6 border-b pb-4"><p className="text-xs font-bold uppercase tracking-[0.2em] text-kaizen">Relatório do Conselho Editorial</p><h3 className="mt-2 font-display text-2xl font-bold">{projectTitle}</h3><p className="mt-2 text-sm text-muted-foreground">{projectObjective}</p></div>}
        <div className="grid gap-3 sm:grid-cols-2">{latest.agent_runs.map((agent) => <article key={agent.id} className="rounded-md border bg-background p-3"><div className="flex items-center justify-between gap-2"><strong className="text-sm">{councilRoleLabels[agent.role] ?? agent.role}</strong><Badge variant={agent.status === "failed" ? "destructive" : "outline"}>{agent.status}</Badge></div>{agent.error_code ? <p className="mt-2 text-xs text-destructive">Falha segura: {agent.error_code}</p> : Object.keys(agent.output_payload ?? {}).length > 0 ? <div className="mt-2"><EditorialContentRenderer value={agent.output_payload} /></div> : <p className="mt-2 text-xs text-muted-foreground">Parecer ainda não disponível.</p>}</article>)}</div>
        {Object.keys(latest.final_synthesis ?? {}).length > 0 && <div className="mt-4 rounded-md border border-kaizen/30 bg-background p-4"><p className="font-bold text-kaizen">Síntese final do Sensei Editorial</p><div className="mt-3"><EditorialContentRenderer value={latest.final_synthesis} /></div></div>}
        {!awaitingDecision && <div className="mt-4 rounded-md border bg-background p-4"><p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Decisão humana registrada</p><p className="mt-2 font-semibold">{latest.status === "revision_requested" ? "REVISÃO SOLICITADA" : latest.status === "approved" ? "APROVADO" : (latest.human_decision || latest.status).replaceAll("_", " ").toUpperCase()}</p>{latest.human_decision_by && <p className="mt-1 text-xs text-muted-foreground">Responsável: {latest.human_decision_by}</p>}{latest.human_decision_at && <p className="text-xs text-muted-foreground">Data: {new Date(latest.human_decision_at).toLocaleString("pt-BR")}</p>}</div>}
      </div>
      {awaitingDecision && <div className="no-print flex flex-wrap gap-2"><Button disabled={loading} onClick={() => onAction({ action: "approve", runId: latest.id, projectId })}><CheckCircle2 />Aprovar</Button><Button disabled={loading} variant="outline" onClick={() => onAction({ action: "revision", runId: latest.id, projectId })}>Solicitar revisão</Button></div>}
      {runs.length > 1 && <details className="no-print"><summary className="cursor-pointer text-sm font-bold">Histórico das execuções ({runs.length})</summary><div className="mt-2 space-y-2">{runs.map((run) => <details key={run.id} className="rounded-md border bg-background p-3"><summary className="cursor-pointer text-sm">Conselho #{run.id} · plano v{run.plan_version} · {run.status}</summary><JsonSummary title="Síntese" value={run.final_synthesis} /></details>)}</div></details>}
    </div>}
  </section>;
}

function contentTargets(project: StudioProject) {
  const plan = project.modernization_plan?.proposed_architecture ?? {};
  if (isContentFlow(project.project_type)) return (plan.videos ?? []).map((video: any, index: number) => ({ value: `video:${index}`, label: `Vídeo ${index + 1} · ${video.title ?? video.theme ?? "Sem título"}` }));
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
