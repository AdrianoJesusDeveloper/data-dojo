import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { SenseiLearningV1 } from "./SenseiLearningV1";
import { DidacticContentV1 } from "./DidacticContentV1";

type SourcePolicy = "REQUIRE_APPROVED_SOURCE" | "ALLOW_AI_WITHOUT_SOURCE";

type FormationSummary = {
  id: number;
  title: string;
  source_policy: SourcePolicy;
};

type CatalogSource = {
  id: number;
  relative_path: string;
  filename: string;
  extension: string;
  status: string;
  book_id: number | null;
  book_status: string | null;
};

type CatalogPage = {
  count: number;
  results: CatalogSource[];
};

type SourceDraft = {
  sourceId: number | null;
  title: string;
  reference: string;
  location: string;
  objective: string;
  justification: string;
  priority: number;
};

type Plan = {
  unit: number; learning_objectives: string[]; prerequisites: Array<{ id: number; title: string }>;
  related_competencies: Array<{ id: number; title: string; expected_level_label: string }>;
  practices: string[]; expected_evidence: string[]; completion_criteria: string[]; guidance: string;
  curated_sources: Array<{ id: number; category_label: string; source_type_label: string; title: string; reference: string; location: string; approved_ranges: Array<{ pdf_start: number; pdf_end: number }>; objective: string; priority: number; notes: string; is_required: boolean; url: string; justification: string }>;
  source_proposals: Array<{ id: number; title: string; editorial_status: "PROPOSED" | "APPROVED" | "REJECTED"; category_label: string; source_type_label: string; location: string; approved_ranges: Array<{ pdf_start: number; pdf_end: number }>; justification: string; confidence: string | null; author_or_organization: string; rejection_reason: string }>;
  source_gap: { status: "OPEN" | "RESOLVED"; reason: string; requirements: string[] } | null;
  notes: Array<{ id: number; note_type_label: string; content: string }>;
  study_progress: { status: "NOT_STARTED" | "STUDYING" | "STUDIED" };
};

const List = ({ title, items }: { title: string; items: string[] }) => <section><h3 className="font-bold">{title}</h3>{items.length ? <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-2 text-sm text-muted-foreground">Não definido.</p>}</section>;

export function SenseiStudyPlanDialog({ formationId, unitId, unitTitle, onClose }: { formationId: number | null; unitId: number | null; unitTitle: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [sourceSearch, setSourceSearch] = useState("");
  const [sourceDraft, setSourceDraft] = useState<SourceDraft>({
    sourceId: null,
    title: "",
    reference: "",
    location: "",
    objective: "",
    justification: "",
    priority: 1,
  });
  const queryKey = ["sensei-study-plan", formationId ?? "no-formation", unitId ?? "no-unit"] as const;
  const query = useQuery({ queryKey, queryFn: async () => (await api.get<Plan>(`/api/library/sensei-units/${unitId}/study-plan/`)).data, enabled: Boolean(formationId) && unitId != null, retry: false });
  const formationQuery = useQuery({
    queryKey: ["sensei-formation-source-policy", formationId ?? "no-formation"],
    queryFn: async () => (await api.get<FormationSummary>(`/api/library/sensei-formations/${formationId}/`)).data,
    enabled: Boolean(formationId),
    retry: false,
  });
  const catalogQuery = useQuery({
    queryKey: ["sensei-source-catalog", sourceSearch.trim()],
    queryFn: async () => (
      await api.get<CatalogPage>("/api/library/sources/", {
        params: { search: sourceSearch.trim(), rag_status: "ready", page_size: 8 },
      })
    ).data,
    enabled: sourceSearch.trim().length >= 2,
    retry: false,
  });
  const progress = useMutation({ mutationFn: async (status: string) => status === "STUDYING" ? (await api.post(`/api/library/sensei-units/${unitId}/start-study/`, {})).data : (await api.patch(`/api/library/sensei-units/${unitId}/study-progress/`, { status })).data, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["sensei-study-plan", formationId ?? "no-formation", unitId ?? "no-unit"] }); queryClient.invalidateQueries({ queryKey: ["sensei-study-journey"] }); toast.success("Status de estudo atualizado sem alterar competências."); } });
  const addNote = useMutation({ mutationFn: async () => (await api.post(`/api/library/sensei-units/${unitId}/notes/`, { note_type: "OWN_SUMMARY", content: note })).data, onSuccess: () => { setNote(""); queryClient.invalidateQueries({ queryKey: ["sensei-study-plan", formationId ?? "no-formation", unitId ?? "no-unit"] }); toast.success("Anotação privada registrada."); } });
  const createSource = useMutation({
    mutationFn: async () => (
      await api.post(`/api/library/sensei-units/${unitId}/sources/`, {
        source: sourceDraft.sourceId,
        category: "FOUNDATIONAL",
        source_type: "TECHNICAL_BOOK",
        title: sourceDraft.title.trim(),
        reference: sourceDraft.reference.trim(),
        location: sourceDraft.location.trim(),
        objective: sourceDraft.objective.trim(),
        priority: sourceDraft.priority,
        is_required: true,
        justification: sourceDraft.justification.trim(),
        reliability_notes: "Fonte local processada na Biblioteca do Sensei; aprovação humana obrigatória.",
      })
    ).data,
    onSuccess: () => {
      setSourceDraft({ sourceId: null, title: "", reference: "", location: "", objective: "", justification: "", priority: 1 });
      queryClient.invalidateQueries({ queryKey });
      toast.success("Proposta criada ou reenviada para revisão. Revise e aprove antes de gerar a aula.");
    },
    onError: (error: any) => {
      const detail = error?.response?.data;
      toast.error(typeof detail?.detail === "string" ? detail.detail : "Não foi possível criar a proposta de fonte.");
    },
  });
  const reviewSource = useMutation({
    mutationFn: async ({ id, editorial_status, rejection_reason = "" }: { id: number; editorial_status: "APPROVED" | "REJECTED"; rejection_reason?: string }) =>
      (await api.patch(`/api/library/sensei-unit-sources/${id}/review/`, { editorial_status, rejection_reason })).data,
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey });
      queryClient.invalidateQueries({ queryKey: ["sensei-didactic-content", formationId, unitId] });
      toast.success(variables.editorial_status === "APPROVED" ? "Fonte aprovada. A geração didática está liberada." : "Fonte rejeitada.");
    },
  });
  const plan = query.data;
  const chooseCatalogSource = (source: CatalogSource) => {
    setSourceDraft({
      sourceId: source.id,
      title: source.filename.replace(/\.[^.]+$/, ""),
      reference: source.relative_path,
      location: "",
      objective: `Fundamentar a unidade: ${unitTitle}`,
      justification: "",
      priority: 1,
    });
  };
  const sourceDraftValid = Boolean(
    sourceDraft.sourceId &&
    sourceDraft.title.trim() &&
    sourceDraft.reference.trim() &&
    sourceDraft.location.trim() &&
    sourceDraft.objective.trim() &&
    sourceDraft.justification.trim()
  );
  const isMissingPlanError = query.isError && Number((query.error as { response?: { status?: number } } | undefined)?.response?.status) === 404;
  return <Dialog key={`${formationId ?? "no-formation"}:${unitId ?? "no-unit"}`} open={unitId != null && Boolean(formationId)} onOpenChange={(open) => !open && onClose()}><DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto"><DialogHeader><DialogTitle>{unitTitle}</DialogTitle><DialogDescription>Plano de estudo do Sensei — concluir a unidade não demonstra competência.</DialogDescription></DialogHeader>
    {query.isLoading ? <p className="flex items-center gap-2"><LoaderCircle className="animate-spin" />Carregando plano da formação...</p> : query.isError ? <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">{isMissingPlanError ? "Esta unidade ainda não possui plano ou fonte curada. O cadastro poderá ser feito posteriormente." : "Não foi possível carregar o plano desta unidade neste momento. Tente novamente."}</p> : plan && <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2"><Badge variant="outline">{plan.study_progress.status}</Badge><Button size="sm" variant="outline" onClick={() => progress.mutate("STUDYING")}>INICIAR ESTUDO</Button><Button size="sm" disabled={progress.isPending} onClick={() => progress.mutate("STUDIED")}>Marcar como estudada</Button></div>
      {formationQuery.data && (
        <section className="rounded-lg border bg-muted/30 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold">Política de fontes</h3>
            <Badge variant="outline">{formationQuery.data.source_policy}</Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {formationQuery.data.source_policy === "ALLOW_AI_WITHOUT_SOURCE"
              ? "Esta formação aceita geração com ou sem fonte aprovada. Quando não houver fonte aprovada, o conteúdo gerado por IA permanece identificado como sem fonte, em DRAFT e sujeito à revisão humana."
              : "Esta formação exige fonte aprovada antes da geração do conteúdo didático."}
          </p>
        </section>
      )}
      <List title="Objetivos de aprendizagem" items={plan.learning_objectives} />
      <List title="Pré-requisitos" items={plan.prerequisites.map((item) => item.title)} />
      <List title="Competências relacionadas" items={plan.related_competencies.map((item) => `${item.title} — meta: ${item.expected_level_label}`)} />
      <section><h3 className="font-bold">Fontes recomendadas</h3>{plan.curated_sources.length ? <div className="mt-2 space-y-3">{plan.curated_sources.map((source) => <article key={source.id} className="rounded-lg border p-4"><div className="flex flex-wrap gap-2"><Badge>{source.is_required ? "Obrigatória" : "Complementar"}</Badge><Badge variant="outline">{source.category_label}</Badge><Badge variant="outline">Prioridade {source.priority}</Badge></div><h4 className="mt-2 font-bold">{source.title}</h4><p className="mt-1 text-sm">Estudar: {source.location}</p><p className="mt-1 text-sm text-muted-foreground">Motivo: {source.justification || source.objective}</p></article>)}</div> : <p className="mt-2 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">Fontes em curadoria.</p>}</section>
      <section className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="font-bold">Curadoria de fontes</h3>
            <p className="mt-1 text-xs text-muted-foreground">Conecte esta unidade a uma fonte processada da Biblioteca do Sensei. A IA pode usar a fonte somente depois da sua aprovação.</p>
          </div>
          <Badge variant="outline">{plan.curated_sources.length ? "FONTE APROVADA" : "REVISÃO HUMANA"}</Badge>
        </div>
        {plan.source_gap?.status === "OPEN" && <p className="mt-2 text-sm text-amber-700 dark:text-amber-300"><b>NEEDS_SOURCE:</b> {plan.source_gap.reason}</p>}

        <div className="mt-4 rounded-lg border bg-background/70 p-3">
          <h4 className="text-sm font-bold">1. Buscar no acervo local</h4>
          <div className="mt-2 flex flex-wrap gap-2">
            <Input
              aria-label="Buscar fonte na Biblioteca do Sensei"
              className="min-w-64 flex-1"
              value={sourceSearch}
              onChange={(event) => setSourceSearch(event.target.value)}
              placeholder="Ex.: Python, estruturas de dados, pandas..."
            />
            <Button type="button" variant="outline" onClick={() => setSourceSearch((value) => value.trim() || unitTitle)}>
              Sugerir pelo tema da unidade
            </Button>
          </div>
          {catalogQuery.isFetching && <p className="mt-2 text-xs text-muted-foreground">Buscando livros processados...</p>}
          {catalogQuery.isError && <p className="mt-2 text-xs text-destructive">Não foi possível consultar o acervo agora.</p>}
          {catalogQuery.data && (
            <div className="mt-3 space-y-2">
              {catalogQuery.data.results.length === 0 ? <p className="text-xs text-muted-foreground">Nenhuma fonte processada encontrada para esta busca.</p> : catalogQuery.data.results.map((source) => (
                <article key={source.id} className="flex flex-wrap items-center justify-between gap-3 rounded border p-3">
                  <div>
                    <p className="text-sm font-medium">{source.filename}</p>
                    <p className="text-xs text-muted-foreground">{source.extension.toUpperCase()} · RAG {source.book_status ?? "não processado"}</p>
                  </div>
                  <Button type="button" size="sm" variant={sourceDraft.sourceId === source.id ? "default" : "outline"} onClick={() => chooseCatalogSource(source)}>
                    {sourceDraft.sourceId === source.id ? "Selecionada" : "Selecionar"}
                  </Button>
                </article>
              ))}
            </div>
          )}
        </div>

        {sourceDraft.sourceId && (
          <div className="mt-3 space-y-3 rounded-lg border bg-background/70 p-3">
            <h4 className="text-sm font-bold">2. Confirmar localização e justificativa</h4>
            <Input aria-label="Título da fonte" value={sourceDraft.title} onChange={(event) => setSourceDraft((draft) => ({ ...draft, title: event.target.value }))} placeholder="Título da fonte" />
            <Input aria-label="Referência da fonte" value={sourceDraft.reference} onChange={(event) => setSourceDraft((draft) => ({ ...draft, reference: event.target.value }))} placeholder="Arquivo, edição ou referência" />
            <Input aria-label="Capítulo seção ou páginas" value={sourceDraft.location} onChange={(event) => setSourceDraft((draft) => ({ ...draft, location: event.target.value }))} placeholder="Ex.: Cap. 3 · seção 3.2 · páginas 74–91" />
            <p className="text-xs text-muted-foreground">Para fontes locais, informe sempre as páginas físicas do arquivo no formato <b>PDF p.122 a 135</b>. Você pode registrar vários intervalos na mesma localização; o backend os transforma em ranges estruturados para limitar o RAG.</p>
            <Textarea aria-label="Objetivo da fonte" value={sourceDraft.objective} onChange={(event) => setSourceDraft((draft) => ({ ...draft, objective: event.target.value }))} placeholder="O que esta fonte deve sustentar nesta unidade?" />
            <Textarea aria-label="Justificativa da fonte" value={sourceDraft.justification} onChange={(event) => setSourceDraft((draft) => ({ ...draft, justification: event.target.value }))} placeholder="Por que esta é uma fonte adequada e confiável?" />
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-xs">Prioridade
                <select className="h-9 rounded-md border bg-background px-2" value={sourceDraft.priority} onChange={(event) => setSourceDraft((draft) => ({ ...draft, priority: Number(event.target.value) }))}>
                  {[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}
                </select>
              </label>
              <Button type="button" disabled={!sourceDraftValid || createSource.isPending} onClick={() => createSource.mutate()}>
                {createSource.isPending ? "Criando proposta..." : "Criar proposta para revisão"}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setSourceDraft({ sourceId: null, title: "", reference: "", location: "", objective: "", justification: "", priority: 1 })}>Cancelar</Button>
            </div>
          </div>
        )}

        <div className="mt-4 space-y-2">
          <h4 className="text-sm font-bold">3. Revisão editorial</h4>
          {!plan.source_proposals?.length && <p className="rounded border border-dashed p-3 text-xs text-muted-foreground">Nenhuma proposta criada. Busque uma fonte no acervo para iniciar a curadoria.</p>}
          {plan.source_proposals?.map((source) => (
            <article key={source.id} className="rounded border bg-background p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <Badge variant="outline">{source.editorial_status}</Badge>
                  <h4 className="mt-1 font-medium">{source.title}</h4>
                  <p className="text-xs text-muted-foreground">
                    {source.author_or_organization || "Fonte local"} · {source.location || "Referência específica pendente"}
                  </p>
                </div>
                {source.editorial_status === "PROPOSED" && (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      disabled={reviewSource.isPending}
                      onClick={() => reviewSource.mutate({ id: source.id, editorial_status: "APPROVED" })}
                    >
                      Aprovar fonte
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={reviewSource.isPending}
                      onClick={() => {
                        const reason = window.prompt("Motivo da rejeição");
                        if (reason?.trim()) {
                          reviewSource.mutate({
                            id: source.id,
                            editorial_status: "REJECTED",
                            rejection_reason: reason,
                          });
                        }
                      }}
                    >
                      Rejeitar
                    </Button>
                  </div>
                )}
              </div>
              <p className="mt-2 text-xs">Justificativa: {source.justification || "Pendente"}</p>
              {source.approved_ranges?.length > 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Ranges PDF estruturados:{" "}
                  {source.approved_ranges
                    .map((range) =>
                      range.pdf_start === range.pdf_end
                        ? `p.${range.pdf_start}`
                        : `p.${range.pdf_start}–${range.pdf_end}`,
                    )
                    .join(", ")}
                </p>
              )}
              {source.editorial_status === "REJECTED" && source.rejection_reason && (
                <p className="mt-1 text-xs text-destructive">Rejeitada: {source.rejection_reason}</p>
              )}
            </article>
          ))}
        </div>
      </section>
      <List title="Práticas e exercícios" items={plan.practices} /><List title="Evidências esperadas" items={plan.expected_evidence} /><List title="Critérios para considerar estudada" items={plan.completion_criteria} />
      <DidacticContentV1 formationId={formationId!} unitId={plan.unit} enabled={plan.related_competencies.length > 0} hasApprovedSource={plan.curated_sources.length > 0} />
      <SenseiLearningV1 formationId={formationId} unitId={plan.unit} enabled={plan.related_competencies.length > 0} />
      <section><h3 className="font-bold">Anotações do Sensei</h3><div className="mt-2 flex gap-2"><Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Escreva seu resumo próprio" /><Button disabled={!note.trim() || addNote.isPending} onClick={() => addNote.mutate()}>Salvar nota</Button></div>{plan.notes.map((item) => <div key={item.id} className="mt-2 rounded border p-3 text-sm"><b>{item.note_type_label}:</b> {item.content}</div>)}</section>
    </div>}
  </DialogContent></Dialog>;
}
