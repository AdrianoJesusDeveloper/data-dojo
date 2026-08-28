import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type JsonObject = Record<string, unknown>;

export function EditorialPlanEditor({ value, onChange }: { value: JsonObject; onChange: (value: JsonObject) => void }) {
  return <div className="space-y-5 rounded-xl border bg-card p-5"><p className="text-sm text-muted-foreground">Edite os campos editoriais. A estrutura será validada integralmente antes de salvar uma nova versão.</p><ObjectEditor value={value} onChange={onChange} root /></div>;
}

function ObjectEditor({ value, onChange, root = false }: { value: JsonObject; onChange: (value: JsonObject) => void; root?: boolean }) {
  return <div className={root ? "space-y-5" : "space-y-4 rounded-lg border bg-secondary/10 p-4"}>{Object.entries(value).filter(([key]) => key !== "contract_version").map(([key, item]) => <EditorField key={key} fieldKey={key} value={item} onChange={(next) => onChange({ ...value, [key]: next })} />)}</div>;
}

function EditorField({ fieldKey, value, onChange }: { fieldKey: string; value: unknown; onChange: (value: unknown) => void }) {
  const title = label(fieldKey);
  if (Array.isArray(value)) return <ArrayEditor fieldKey={fieldKey} title={title} value={value} onChange={onChange} />;
  if (value && typeof value === "object") return <fieldset><legend className="mb-2 text-sm font-bold">{title}</legend><ObjectEditor value={value as JsonObject} onChange={onChange} /></fieldset>;
  if (typeof value === "boolean") return <label className="grid gap-1 text-sm font-semibold">{title}<select value={String(value)} onChange={(event) => onChange(event.target.value === "true")} className="h-10 rounded-md border border-input bg-background px-3 font-normal"><option value="true">Sim</option><option value="false">Não</option></select></label>;
  if (typeof value === "number") return <label className="grid gap-1 text-sm font-semibold">{title}<Input type="number" value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
  const stringValue = value == null ? "" : String(value);
  const compact = ["title", "level", "workload", "language", "order", "theme"].includes(fieldKey);
  return <label className="grid gap-1 text-sm font-semibold">{title}{compact ? <Input value={stringValue} onChange={(event) => onChange(event.target.value)} /> : <Textarea rows={3} value={stringValue} onChange={(event) => onChange(event.target.value)} />}</label>;
}

function ArrayEditor({ fieldKey, title, value, onChange }: { fieldKey: string; title: string; value: unknown[]; onChange: (value: unknown[]) => void }) {
  const update = (index: number, next: unknown) => onChange(value.map((item, itemIndex) => itemIndex === index ? next : item));
  return <fieldset className="space-y-3"><div className="flex items-center justify-between gap-3"><legend className="text-sm font-bold">{title}</legend><Button type="button" size="sm" variant="outline" onClick={() => onChange([...value, template(fieldKey)])}><Plus />Adicionar</Button></div>{value.map((item, index) => <div key={index} className="relative rounded-lg border bg-background p-4 pr-12"><Button type="button" size="icon" variant="ghost" aria-label={`Remover ${title} ${index + 1}`} className="absolute right-2 top-2 text-destructive" onClick={() => onChange(value.filter((_, itemIndex) => itemIndex !== index))}><Trash2 /></Button>{item && typeof item === "object" && !Array.isArray(item) ? <ObjectEditor value={item as JsonObject} onChange={(next) => update(index, next)} /> : <EditorField fieldKey={`${fieldKey}_${index + 1}`} value={item} onChange={(next) => update(index, next)} />}</div>)}</fieldset>;
}

function template(key: string): unknown {
  if (key === "modules") return { title: "Novo módulo", objective: "", competencies: [], workload: "", lessons: [], exercises: [], kata: "", practical_project: "", assessment: "" };
  if (key === "lessons") return { title: "Nova aula", objective: "", concepts: [], practice: "", tools: [], ai_integration: "", human_reasoning: "", validation: "", reflection: "", without_ai_challenge: "", authorship_challenge: authorship(), sources: [], expected_result: "" };
  if (key === "videos") return { order: 1, theme: "", title: "Novo vídeo", objective: "", concepts: [], tools: [], practical_demo: "", practice: "", code: [], exercise: "", ai_integration: "", human_reasoning: "", validation: "", reflection: "", without_ai_challenge: "", authorship_challenge: authorship(), rag_sources: [] };
  return "";
}

function authorship() {
  return { independent_explanation: "", practical_challenge: "", portfolio_artifact: "", reflection_question: "", comprehension_criteria: "", responsible_ai_use: "", must_not_delegate_to_ai: "", expected_result: "", private_submission_option: "" };
}

function label(value: string) {
  const labels: Record<string, string> = { ai_integration: "A IA pode auxiliar", human_reasoning: "O aluno faz", validation: "O aluno deve validar", authorship_challenge: "Desafio de Autoria", without_ai_challenge: "Desafio sem IA", rag_sources: "Fontes RAG" };
  return labels[value] ?? value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}
