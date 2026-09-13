import { BookOpen, CheckCircle2, Circle, LockKeyhole, Network } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export type KnowledgeMapModule = {
  id: number;
  title: string;
  description: string;
  order: number;
  unit_count: number;
  study_units: Array<{ id: number; title: string; objective: string; order: number; status: string }>;
};

export type KnowledgeMapCompetency = {
  id: number;
  module: number | null;
  title: string;
  description: string;
  expected_level: number;
  expected_level_label: string;
  mastery_criteria: string[];
  evidence_count: number;
  progress: { current_level: number; current_level_label: string; state: string } | null;
};

const masteryLevels = ["Conhece", "Explica", "Implementa", "Debuga", "Justifica", "Ensina"];

function stateLabel(state?: string) {
  if (state === "TEACHING_READY") return "Pronto para ensinar";
  if (state === "DEMONSTRATED") return "Demonstrada";
  if (state === "STUDYING") return "Em estudo";
  return "Não iniciada";
}

function CompetencyNode({ competency }: { competency: KnowledgeMapCompetency }) {
  const level = competency.progress?.current_level ?? 0;
  const complete = ["DEMONSTRATED", "TEACHING_READY"].includes(competency.progress?.state ?? "");
  return (
    <article className={`relative rounded-xl border p-4 ${complete ? "border-kaizen/50 bg-kaizen/5" : "border-border bg-card"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          {complete ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-kaizen" aria-hidden="true" /> : level ? <Circle className="mt-0.5 h-5 w-5 shrink-0 fill-primary/20 text-primary" aria-hidden="true" /> : <LockKeyhole className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden="true" />}
          <div><h5 className="font-bold leading-tight">{competency.title}</h5>{competency.description && <p className="mt-1 text-xs text-muted-foreground">{competency.description}</p>}</div>
        </div>
        <Badge variant={complete ? "default" : "outline"}>{stateLabel(competency.progress?.state)}</Badge>
      </div>
      <div className="mt-4 grid grid-cols-6 gap-1" aria-label={`Domínio atual: ${level} de 6; meta: ${competency.expected_level} de 6`}>
        {masteryLevels.map((label, index) => {
          const value = index + 1;
          return <span key={label} title={`${value}. ${label}`} className={`h-2 rounded-full ${value <= level ? "bg-kaizen" : value <= competency.expected_level ? "bg-primary/30" : "bg-muted"}`} />;
        })}
      </div>
      <div className="mt-2 flex flex-wrap justify-between gap-2 text-[11px] text-muted-foreground">
        <span>Meta: {competency.expected_level_label} · Atual: {competency.progress?.current_level_label ?? "Não demonstrado"}</span>
        <span>{competency.evidence_count} {competency.evidence_count === 1 ? "evidência" : "evidências"}</span>
      </div>
    </article>
  );
}

export function KnowledgeMapV1({ modules, competencies, loading = false, onOpenUnit }: { modules: KnowledgeMapModule[]; competencies: KnowledgeMapCompetency[]; loading?: boolean; onOpenUnit?: (unitId: number) => void }) {
  if (loading) return <p className="text-sm text-muted-foreground">Carregando mapa de conhecimento...</p>;
  const unassigned = competencies.filter((competency) => competency.module == null);
  const lanes = [...modules.map((module) => ({ ...module, competencies: competencies.filter((competency) => competency.module === module.id) })), ...(unassigned.length ? [{ id: -1, title: "Competências transversais", description: "Competências que atravessam toda a formação.", order: Number.MAX_SAFE_INTEGER, unit_count: 0, study_units: [], competencies: unassigned }] : [])];
  if (!lanes.length) return <p className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">O mapa será exibido quando houver módulos ou competências cadastrados.</p>;

  return (
    <section aria-labelledby="knowledge-map-v1-title">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div><div className="flex items-center gap-2"><Network className="h-5 w-5 text-kaizen" aria-hidden="true" /><h4 id="knowledge-map-v1-title" className="font-display text-lg font-bold">Mapa de Conhecimento V1</h4></div><p className="mt-1 text-xs text-muted-foreground">Baseado em competências demonstradas, não em aulas abertas.</p></div>
        <div className="flex gap-3 text-[11px] text-muted-foreground"><span><i className="mr-1 inline-block h-2 w-4 rounded bg-kaizen" />demonstrado</span><span><i className="mr-1 inline-block h-2 w-4 rounded bg-primary/30" />a desenvolver</span></div>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        {lanes.sort((a, b) => a.order - b.order).map((lane, index) => <section key={lane.id} className="rounded-xl border border-border/80 bg-background/60 p-4" aria-label={lane.title}>
          <header className="mb-3 flex items-start gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-black text-primary-foreground">{lane.id === -1 ? "∞" : index + 1}</span><div><h5 className="font-bold">{lane.title}</h5><p className="text-xs text-muted-foreground">{lane.description || `${lane.unit_count} unidades de estudo`}</p></div></header>
          {lane.id !== -1 && <div className="mb-4 space-y-2 border-l-2 border-primary/20 pl-3">{lane.study_units?.map((unit) => <div key={unit.id} className="flex items-center justify-between gap-3 rounded-lg border bg-card p-3"><div><p className="text-sm font-medium">{unit.order + 1}. {unit.title}</p><p className="text-[11px] text-muted-foreground">Unidade de estudo</p></div><Button size="sm" variant="outline" onClick={() => onOpenUnit?.(unit.id)} aria-label={`Abrir plano de estudo: ${unit.title}`}><BookOpen />Plano</Button></div>)}</div>}
          <div className="space-y-3">{lane.competencies.length ? lane.competencies.map((competency) => <CompetencyNode key={competency.id} competency={competency} />) : <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">Nenhuma competência vinculada a este módulo.</p>}</div>
        </section>)}
      </div>
    </section>
  );
}
