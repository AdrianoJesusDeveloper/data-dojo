import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
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

type Plan = {
  unit: number; learning_objectives: string[]; prerequisites: Array<{ id: number; title: string }>;
  related_competencies: Array<{ id: number; title: string; expected_level_label: string }>;
  practices: string[]; expected_evidence: string[]; completion_criteria: string[]; guidance: string;
  curated_sources: Array<{ id: number; category_label: string; source_type_label: string; title: string; reference: string; location: string; objective: string; priority: number; notes: string; is_required: boolean; url: string; justification: string }>;
  source_proposals: Array<{ id: number; title: string; editorial_status: "PROPOSED" | "APPROVED" | "REJECTED"; category_label: string; source_type_label: string; location: string; justification: string; confidence: string | null; author_or_organization: string; rejection_reason: string }>;
  source_gap: { status: "OPEN" | "RESOLVED"; reason: string; requirements: string[] } | null;
  notes: Array<{ id: number; note_type_label: string; content: string }>;
  study_progress: { status: "NOT_STARTED" | "STUDYING" | "STUDIED" };
};

const List = ({ title, items }: { title: string; items: string[] }) => <section><h3 className="font-bold">{title}</h3>{items.length ? <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">{items.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-2 text-sm text-muted-foreground">Não definido.</p>}</section>;

export function SenseiStudyPlanDialog({ formationId, unitId, unitTitle, onClose }: { formationId: number | null; unitId: number | null; unitTitle: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const queryKey = ["sensei-study-plan", formationId ?? "no-formation", unitId ?? "no-unit"] as const;
  const query = useQuery({ queryKey, queryFn: async () => (await api.get<Plan>(`/api/library/sensei-units/${unitId}/study-plan/`)).data, enabled: Boolean(formationId) && unitId != null, retry: false });
  const formationQuery = useQuery({
    queryKey: ["sensei-formation-source-policy", formationId ?? "no-formation"],
    queryFn: async () => (await api.get<FormationSummary>(`/api/library/sensei-formations/${formationId}/`)).data,
    enabled: Boolean(formationId),
    retry: false,
  });
  const progress = useMutation({ mutationFn: async (status: string) => status === "STUDYING" ? (await api.post(`/api/library/sensei-units/${unitId}/start-study/`, {})).data : (await api.patch(`/api/library/sensei-units/${unitId}/study-progress/`, { status })).data, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["sensei-study-plan", formationId ?? "no-formation", unitId ?? "no-unit"] }); queryClient.invalidateQueries({ queryKey: ["sensei-study-journey"] }); toast.success("Status de estudo atualizado sem alterar competências."); } });
  const addNote = useMutation({ mutationFn: async () => (await api.post(`/api/library/sensei-units/${unitId}/notes/`, { note_type: "OWN_SUMMARY", content: note })).data, onSuccess: () => { setNote(""); queryClient.invalidateQueries({ queryKey: ["sensei-study-plan", formationId ?? "no-formation", unitId ?? "no-unit"] }); toast.success("Anotação privada registrada."); } });
  const reviewSource = useMutation({ mutationFn: async ({ id, editorial_status, rejection_reason = "" }: { id: number; editorial_status: "APPROVED" | "REJECTED"; rejection_reason?: string }) => (await api.patch(`/api/library/sensei-unit-sources/${id}/review/`, { editorial_status, rejection_reason })).data, onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["sensei-study-plan", formationId ?? "no-formation", unitId ?? "no-unit"] }); toast.success("Revisão editorial registrada."); } });
  const plan = query.data;
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
      <section className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4"><h3 className="font-bold">Curadoria de fontes</h3>{plan.source_gap?.status === "OPEN" && <p className="mt-2 text-sm text-amber-700 dark:text-amber-300"><b>NEEDS_SOURCE:</b> {plan.source_gap.reason}</p>}<div className="mt-3 space-y-2">{plan.source_proposals?.map((source) => <article key={source.id} className="rounded border bg-background p-3"><div className="flex flex-wrap items-center justify-between gap-2"><div><Badge variant="outline">{source.editorial_status}</Badge><h4 className="mt-1 font-medium">{source.title}</h4><p className="text-xs text-muted-foreground">{source.author_or_organization || "Autoria a confirmar"} · {source.location || "Referência específica pendente"}</p></div>{source.editorial_status === "PROPOSED" && <div className="flex gap-2"><Button size="sm" onClick={() => reviewSource.mutate({ id: source.id, editorial_status: "APPROVED" })}>Aprovar</Button><Button size="sm" variant="destructive" onClick={() => { const reason = window.prompt("Motivo da rejeição"); if (reason?.trim()) reviewSource.mutate({ id: source.id, editorial_status: "REJECTED", rejection_reason: reason }); }}>Rejeitar</Button></div>}</div><p className="mt-2 text-xs">Justificativa: {source.justification || "Pendente"}</p></article>)}</div></section>
      <List title="Práticas e exercícios" items={plan.practices} /><List title="Evidências esperadas" items={plan.expected_evidence} /><List title="Critérios para considerar estudada" items={plan.completion_criteria} />
      <DidacticContentV1 formationId={formationId!} unitId={plan.unit} enabled={plan.related_competencies.length > 0} />
      <SenseiLearningV1 formationId={formationId} unitId={plan.unit} enabled={plan.related_competencies.length > 0} />
      <section><h3 className="font-bold">Anotações do Sensei</h3><div className="mt-2 flex gap-2"><Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Escreva seu resumo próprio" /><Button disabled={!note.trim() || addNote.isPending} onClick={() => addNote.mutate()}>Salvar nota</Button></div>{plan.notes.map((item) => <div key={item.id} className="mt-2 rounded border p-3 text-sm"><b>{item.note_type_label}:</b> {item.content}</div>)}</section>
    </div>}
  </DialogContent></Dialog>;
}
