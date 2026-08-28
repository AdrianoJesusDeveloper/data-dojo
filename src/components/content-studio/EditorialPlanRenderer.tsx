import { Check, ChevronDown, Clipboard, Code2, FileWarning, Lightbulb, Palette, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type JsonObject = Record<string, unknown>;
export type EditorialCitation = { id: number; book_title: string; page_number: number | null; excerpt: string };

type Props = {
  plan: JsonObject;
  projectType: "youtube" | "premium";
  citations?: EditorialCitation[];
};

const isObject = (value: unknown): value is JsonObject => Boolean(value) && typeof value === "object" && !Array.isArray(value);
const list = (value: unknown): unknown[] => Array.isArray(value) ? value : value == null ? [] : [value];
const text = (value: unknown): string => {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (value == null) return "";
  return JSON.stringify(value);
};
const pick = (object: JsonObject, ...keys: string[]) => keys.map((key) => object[key]).find((value) => value !== undefined && value !== null);
const slug = (prefix: string, index?: number) => `${prefix}${index === undefined ? "" : `-${index + 1}`}`;

export function SafeCodeBlock({ code, language = "text" }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard?.writeText(code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="my-3 overflow-hidden rounded-lg border bg-slate-950 text-slate-100">
      <div className="flex items-center justify-between border-b border-white/10 px-3 py-2 text-xs">
        <span className="inline-flex items-center gap-2 font-mono"><Code2 className="h-3.5 w-3.5" />{language}</span>
        <Button type="button" size="sm" variant="ghost" className="h-7 text-slate-100 hover:bg-white/10 hover:text-white" onClick={copy}>
          {copied ? <Check className="h-3.5 w-3.5" /> : <Clipboard className="h-3.5 w-3.5" />}{copied ? "Copiado" : "Copiar"}
        </Button>
      </div>
      <pre className="overflow-x-auto p-4 text-xs"><code>{code}</code></pre>
    </div>
  );
}

function ContentBlock({ value }: { value: unknown }) {
  if (value == null) return null;
  if (typeof value !== "object") return <p className="whitespace-pre-wrap text-sm leading-6">{text(value)}</p>;
  if (Array.isArray(value)) return <div className="space-y-2">{value.map((item, index) => <ContentBlock key={index} value={item} />)}</div>;
  if (!isObject(value)) return null;
  const kind = text(pick(value, "type", "kind")).toLowerCase();
  const content = pick(value, "content", "text", "description", "value");
  if (kind === "code") return <SafeCodeBlock code={text(pick(value, "code", "content"))} language={text(pick(value, "language", "lang")) || "text"} />;
  if (kind === "table") {
    const headers = list(value.headers);
    const rows = list(value.rows);
    return <div className="my-3 overflow-x-auto rounded-lg border"><table className="w-full text-left text-sm"><thead className="bg-secondary/60"><tr>{headers.map((header, index) => <th className="p-3" key={index}>{text(header)}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr className="border-t" key={index}>{list(row).map((cell, cellIndex) => <td className="p-3 align-top" key={cellIndex}>{text(cell)}</td>)}</tr>)}</tbody></table></div>;
  }
  if (kind === "illustration") return <Callout icon={Palette} label="Ilustração planejada" tone="violet"><ContentBlock value={content} /></Callout>;
  if (kind === "warning") return <Callout icon={FileWarning} label="Atenção" tone="amber"><ContentBlock value={content} /></Callout>;
  if (kind === "insight") return <Callout icon={Lightbulb} label="Insight" tone="blue"><ContentBlock value={content} /></Callout>;
  if (["example", "exercise", "diagram"].includes(kind)) return <Callout icon={Sparkles} label={{ example: "Exemplo", exercise: "Exercício", diagram: "Diagrama" }[kind]!} tone="blue"><ContentBlock value={content} /></Callout>;
  if (content !== undefined) return <ContentBlock value={content} />;
  return <dl className="grid gap-2 sm:grid-cols-2">{Object.entries(value).map(([key, item]) => <div key={key} className="rounded-md bg-secondary/35 p-3"><dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{label(key)}</dt><dd className="mt-1"><ContentBlock value={item} /></dd></div>)}</dl>;
}

export function EditorialContentRenderer({ value }: { value: unknown }) {
  return <ContentBlock value={value} />;
}

function Callout({ icon: Icon, label: title, tone, children }: { icon: typeof Sparkles; label: string; tone: "amber" | "blue" | "violet"; children: React.ReactNode }) {
  const colors = { amber: "border-amber-400/40 bg-amber-400/10", blue: "border-sky-400/40 bg-sky-400/10", violet: "border-violet-400/40 bg-violet-400/10" };
  return <div className={`my-3 rounded-lg border p-4 ${colors[tone]}`}><p className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wider"><Icon className="h-4 w-4" />{title}</p>{children}</div>;
}

function Field({ title, value }: { title: string; value: unknown }) {
  if (value == null || value === "" || (Array.isArray(value) && !value.length)) return null;
  return <div><dt className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{title}</dt><dd className="mt-1"><ContentBlock value={value} /></dd></div>;
}

function Policy({ lesson }: { lesson: JsonObject }) {
  return <div><p className="mb-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">Política global · Compreender → Raciocinar → Estruturar → Consultar IA → Criticar → Validar → Implementar → Explicar</p><div className="grid gap-3 md:grid-cols-3">
    <PolicyItem title="O ALUNO FAZ" value={pick(lesson, "human_reasoning", "student_does", "practice")} />
    <PolicyItem title="A IA PODE AUXILIAR" value={pick(lesson, "ai_integration", "ai_assistance")} />
    <PolicyItem title="O ALUNO DEVE VALIDAR" value={pick(lesson, "validation", "student_validates")} />
  </div><div className="mt-3"><Callout icon={ShieldCheck} label="Desafio sem IA" tone="amber"><ContentBlock value={lesson.without_ai_challenge ?? "Conteúdo ainda não definido"} /></Callout></div></div>;
}

function PolicyItem({ title, value }: { title: string; value: unknown }) {
  return <div className="rounded-lg border border-kaizen/25 bg-kaizen/5 p-3"><p className="text-[11px] font-extrabold tracking-wide text-kaizen">{title}</p><div className="mt-2 text-sm"><ContentBlock value={value ?? "Conteúdo ainda não definido"} /></div></div>;
}

function AuthorshipChallenge({ value }: { value: unknown }) {
  if (value == null) return null;
  return <section className="rounded-xl border-2 border-kaizen/35 bg-kaizen/5 p-4"><h5 className="flex items-center gap-2 font-display font-bold"><Sparkles className="h-4 w-4 text-kaizen" />Desafio de Autoria</h5><div className="mt-3"><ContentBlock value={value} /></div></section>;
}

function Lesson({ lesson, index, youtube = false }: { lesson: JsonObject; index: number; youtube?: boolean }) {
  return <article id={slug(youtube ? "video" : "aula", index)} className="scroll-mt-24 rounded-xl border bg-card p-5 shadow-sm">
    <div className="flex gap-3"><Badge variant="secondary">{youtube ? `Vídeo ${index + 1}` : `Aula ${index + 1}`}</Badge><h4 className="font-display text-lg font-bold">{text(pick(lesson, "title", "theme")) || "Aula"}</h4></div>
    <div className="mt-4 grid gap-4 sm:grid-cols-2"><Field title="Objetivo" value={lesson.objective} /><Field title="Conceitos" value={lesson.concepts} /><Field title="Ferramentas" value={lesson.tools} /><Field title="Resultado esperado" value={lesson.expected_result} /><Field title="Prática" value={pick(lesson, "practice", "practical_demo")} /><Field title="Exercício" value={lesson.exercise} /></div>
    <div className="mt-5"><Policy lesson={lesson} /></div>
    <div className="mt-4"><AuthorshipChallenge value={lesson.authorship_challenge} /></div>
    <div className="mt-4"><Field title="Reflexão" value={lesson.reflection} /></div>
  </article>;
}

function Sources({ sources, citations }: { sources: unknown; citations: EditorialCitation[] }) {
  const embedded = list(sources).map((source, index) => isObject(source) ? { id: `source-${index}`, book_title: text(pick(source, "book_title", "book", "title")) || "Fonte", page_number: pick(source, "page_number", "page") as number | null, excerpt: text(pick(source, "excerpt", "quote", "context")) } : { id: `source-${index}`, book_title: text(source), page_number: null, excerpt: "" });
  const all = citations.length ? citations : embedded;
  return <section id="fontes" className="scroll-mt-24"><h3 className="font-display text-2xl font-bold">Fontes</h3><div className="mt-3 grid gap-2 sm:grid-cols-2">{all.length ? all.map((source) => <details key={source.id} className="group self-start rounded-lg border bg-card p-3"><summary className="flex cursor-pointer list-none items-center justify-between gap-3"><span className="truncate text-xs font-semibold">{source.book_title}{source.page_number != null ? ` · p. ${source.page_number}` : ""}</span><ChevronDown className="h-4 w-4 shrink-0 transition group-open:rotate-180" /></summary>{source.excerpt && <p className="mt-3 whitespace-pre-wrap border-l-2 border-kaizen pl-3 text-xs text-muted-foreground">{source.excerpt.length > 360 ? `${source.excerpt.slice(0, 360)}…` : source.excerpt}</p>}</details>) : <p className="text-sm text-muted-foreground">Nenhuma fonte vinculada ao plano.</p>}</div></section>;
}

export function EditorialPlanRenderer({ plan, projectType, citations = [] }: Props) {
  const nested = pick(plan, "editorial_plan", "proposed_architecture");
  const persistedPlan = "proposed_architecture" in plan || "source_summary" in plan;
  const isV1 = isObject(nested) && nested.contract_version === "editorial-plan-v1";
  if (persistedPlan && !isV1) return <LegacyPlanFallback plan={plan} citations={citations} />;
  const editorial = isV1 ? nested : plan;
  const premium = projectType === "premium";
  const modules = list(editorial.modules).filter(isObject);
  const videos = list(pick(editorial, "videos", "lessons")).filter(isObject);
  const nav = premium ? [["visao-geral", "Visão geral"], ["modulos", "Módulos"], ["aulas", "Aulas"], ["projeto-final", "Projeto final"], ["fontes", "Fontes"]] : [["visao-geral", "Visão geral"], ["videos", "Vídeos"], ["fontes", "Fontes"]];
  return <div className="space-y-8">
    <nav aria-label="Índice do plano" className="sticky top-2 z-10 flex flex-wrap gap-2 rounded-xl border bg-background/95 p-3 shadow-sm backdrop-blur">{nav.map(([id, title]) => <a key={id} href={`#${id}`} className="rounded-full px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-secondary hover:text-foreground">{title}</a>)}</nav>
    <section id="visao-geral" className="scroll-mt-24 rounded-xl border bg-gradient-to-br from-kaizen/10 to-background p-6"><Badge>{premium ? "Formação Premium" : "Trilha YouTube"}</Badge><h2 className="mt-3 font-display text-3xl font-extrabold">{text(editorial.title) || "Plano editorial"}</h2><dl className="mt-6 grid gap-5 md:grid-cols-2"><Field title={premium ? "Objetivo geral" : "Objetivo"} value={pick(editorial, "general_objective", "objective")} />{premium && <Field title="Objetivo profissional" value={editorial.professional_objective} />}<Field title="Objetivos específicos" value={editorial.specific_objectives} /><Field title="Público" value={editorial.target_audience} /><Field title="Nível" value={editorial.level} /><Field title="Pré-requisitos" value={editorial.prerequisites} /><Field title={premium ? "Carga horária" : "Duração estimada"} value={pick(editorial, "total_workload", "estimated_total_duration")} /><Field title="Competências" value={editorial.competencies} /><Field title="Stack / ferramentas" value={pick(editorial, "technology_stack", "tools")} />{!premium && <Field title="Quantidade de vídeos" value={editorial.video_count ?? videos.length} />}</dl></section>
    {premium ? <PremiumBody editorial={editorial} modules={modules} /> : <section id="videos" className="scroll-mt-24 space-y-4"><div><h3 className="font-display text-2xl font-bold">Aulas / vídeos</h3><p className="text-sm text-muted-foreground">1 tema = 1 aula = 1 vídeo</p></div>{videos.map((video, index) => <Lesson key={index} lesson={video} index={index} youtube />)}</section>}
    <Sources sources={editorial.sources} citations={citations} />
  </div>;
}

function LegacyPlanFallback({ plan, citations }: { plan: JsonObject; citations: EditorialCitation[] }) {
  return <div className="space-y-6">
    <div className="rounded-xl border border-amber-400/40 bg-amber-400/10 p-5">
      <Badge variant="outline">Plano legado</Badge>
      <h2 className="mt-3 font-display text-2xl font-bold">Plano de modernização anterior ao contrato editorial v1</h2>
      <p className="mt-2 text-sm text-muted-foreground">Este plano permanece acessível, mas não contém módulos e aulas garantidos pelo contrato editorial atual. Gere uma nova versão para obter a visão editorial completa.</p>
    </div>
    <div className="grid gap-4 md:grid-cols-2"><Field title="Resumo das fontes" value={plan.source_summary} /><Field title="Valor de negócio" value={plan.business_value} /><Field title="Arquitetura proposta" value={plan.proposed_architecture} /><Field title="Critérios de aceite" value={plan.acceptance_criteria} /><Field title="Riscos" value={plan.risks} /><Field title="Estratégia de testes" value={plan.test_strategy} /></div>
    <Sources sources={[]} citations={citations} />
  </div>;
}

function PremiumBody({ editorial, modules }: { editorial: JsonObject; modules: JsonObject[] }) {
  let lessonIndex = 0;
  return <><section id="modulos" className="scroll-mt-24 space-y-5"><h3 className="font-display text-2xl font-bold">Módulos</h3>{modules.map((module, moduleIndex) => <article key={moduleIndex} className="rounded-xl border bg-secondary/15 p-5"><h4 className="font-display text-xl font-bold">Módulo {moduleIndex + 1} · {text(module.title)}</h4><div className="mt-3 grid gap-3 sm:grid-cols-2"><Field title="Objetivo" value={module.objective} /><Field title="Competências" value={module.competencies} /><Field title="Carga horária" value={module.workload} /></div><div id={moduleIndex === 0 ? "aulas" : undefined} className="mt-5 space-y-4">{list(module.lessons).filter(isObject).map((lesson) => <Lesson key={lessonIndex} lesson={lesson} index={lessonIndex++} />)}</div><div className="mt-5 grid gap-4 md:grid-cols-2"><Field title="Exercícios" value={module.exercises} /><Field title="Kata" value={module.kata} /><Field title="Projeto prático" value={module.practical_project} /><Field title="Avaliação" value={module.assessment} /></div></article>)}</section><section id="projeto-final" className="scroll-mt-24 rounded-xl border p-5"><h3 className="font-display text-2xl font-bold">Projeto final e certificação</h3><div className="mt-4 grid gap-5 md:grid-cols-2"><Field title="Projetos" value={editorial.practical_projects} /><Field title="Projeto final" value={editorial.final_project} /><Field title="Avaliações" value={editorial.assessment_criteria} /><Field title="Requisitos de conclusão" value={editorial.completion_requirements} /><Field title="Certificação" value={editorial.certification_requirements} /></div></section></>;
}

function label(value: string) { return value.replaceAll("_", " "); }
