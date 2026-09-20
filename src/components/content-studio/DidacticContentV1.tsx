import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Eye, LoaderCircle, Printer, Upload, WandSparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";

type Section = {
  id: number;
  section_type: string;
  section_type_label: string;
  title: string;
  content: string;
  order: number;
  metadata: Record<string, unknown> & { claim_grounding?: {
    version: number;
    kind: string;
    validation: string;
    claims: Array<{ text: string; evidence: Array<{ source_id: number; book_id: number; chunk_id: number; pdf_page: number; quote: string }> }>;
  } };
};
type GroundingExcerpt = {
  source_id: number;
  library_source_id: number | null;
  book_id: number;
  book_title: string;
  pdf_page: number | null;
  chunk_id: number;
  chunk_index: number;
  approved_ranges: Array<{ pdf_start: number; pdf_end: number }>;
  content: string;
};
type Lesson = {
  id: number;
  title: string;
  audience: "SENSEI" | "STUDENT";
  status: "DRAFT" | "REVIEW" | "APPROVED" | "PUBLISHED" | "ARCHIVED";
  source_mode: "APPROVED_SOURCES" | "AI_GENERATED_UNSOURCED";
  ai_provider: string;
  ai_model: string;
  generated_at: string | null;
  grounding_snapshot?: {
    version?: number;
    captured_at?: string;
    provider?: string;
    model?: string;
    sources?: Array<{ id: number; title: string; location: string; approved_ranges?: Array<{ pdf_start: number; pdf_end: number }> }>;
    excerpts?: GroundingExcerpt[];
  };
  sections: Section[];
};
type Attempt = {
  id: number;
  attempt_number: number;
  answer: string;
  feedback: string;
  outcome: string;
  identified_gap: string;
  next_step: string;
  ai_provider?: string;
  ai_model?: string;
};
type Activity = { id: number; prompt: string; attempts: Attempt[] };
type ChallengeResponse = { section: Section | null; activity: Activity | null };
type LessonResponse = { lesson: Lesson | null };
type PublicationScope = "LESSON" | "MODULE" | "FORMATION";
type PublicationPreview = {
  preview_token: string;
  scope: PublicationScope;
  status: "PREVIEW";
  summary: { total: number; eligible: number; ineligible: number };
  eligibility_items: Array<{
    unit_id: number;
    unit_title: string;
    module_id: number;
    module_title: string;
    eligibility: string;
    reason: string;
    source_status: Lesson["status"] | null;
    student_is_stale: boolean;
  }>;
  items: Array<{
    source_lesson_id: number;
    title: string;
    audience: "STUDENT";
    sections: Array<{ title: string; content: string }>;
    adaptation: {
      profile: string;
      human_publication_required: boolean;
      does_not_grant_mastery: boolean;
    };
  }>;
};

function unwrapLesson(data: LessonResponse | Lesson): LessonResponse {
  return "lesson" in data ? data : { lesson: data };
}

export function DidacticContentV1({
  formationId,
  unitId,
  enabled,
  hasApprovedSource = false,
}: {
  formationId: number;
  unitId: number;
  enabled: boolean;
  hasApprovedSource?: boolean;
}) {
  const client = useQueryClient();
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [challengeResponse, setChallengeResponse] = useState("");
  const [exporting, setExporting] = useState<"docx" | "html" | null>(null);
  const [publicationScope, setPublicationScope] = useState<PublicationScope>("LESSON");
  const [publicationPreview, setPublicationPreview] = useState<PublicationPreview | null>(null);
  useEffect(() => {
    if (hasApprovedSource && generationError?.includes("Fontes insuficientes")) {
      setGenerationError(null);
    }
  }, [generationError, hasApprovedSource]);
  const queryKey = ["sensei-didactic-content", formationId, unitId];
  const query = useQuery({
    queryKey,
    queryFn: async () =>
      unwrapLesson(
        (await api.get<LessonResponse>(`/api/library/sensei-units/${unitId}/didactic-content/`))
          .data,
      ),
    enabled,
    retry: false,
  });
  const lesson = query.data?.lesson;
  const handleExport = async (format: "docx" | "html") => {
    setExporting(format);
    try {
      const response = await api.get<Blob>(
        `/api/library/sensei-units/${unitId}/didactic-content/export/${format}/`,
        { responseType: "blob" },
      );
      const disposition = String(response.headers?.["content-disposition"] ?? "");
      const filename =
        disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? `aula-didatica.${format}`;
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast.error(`Não foi possível exportar a aula em ${format.toUpperCase()}.`);
    } finally {
      setExporting(null);
    }
  };
  const handlePrint = () => {
    if (!lesson) return;

    const escapeHtml = (value: string) =>
      value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

    const sectionsHtml = [...lesson.sections]
      .sort((a, b) => a.order - b.order)
      .map(
        (section) => `
          <section class="lesson-section">
            <div class="section-type">${escapeHtml(section.section_type_label)}</div>
            <h2>${escapeHtml(section.title)}</h2>
            <div class="section-content">${escapeHtml(section.content).replaceAll("\n", "<br />")}</div>
          </section>
        `,
      )
      .join("");

    const unsourcedWarning =
      lesson.source_mode === "AI_GENERATED_UNSOURCED"
        ? `
          <div class="warning">
            Aula gerada por IA sem fonte aprovada.
            Exige revisão humana antes de qualquer publicação.
          </div>
        `
        : "";

    const printWindow = window.open("", "_blank", "width=900,height=700");

    if (!printWindow) {
      toast.error("O navegador bloqueou a janela de impressão.");
      return;
    }

    printWindow.document.open();
    printWindow.document.write(`
      <!doctype html>
      <html lang="pt-BR">
        <head>
          <meta charset="utf-8" />
          <title>${escapeHtml(lesson.title)}</title>
          <style>
            @page { size: A4; margin: 18mm; }
            * { box-sizing: border-box; }
            html, body { background: #fff !important; color: #111 !important; }
            body { margin: 0; font-family: Arial, Helvetica, sans-serif; font-size: 12pt; line-height: 1.55; }
            .document { max-width: 190mm; margin: 0 auto; }
            .header { border-bottom: 2px solid #111; padding-bottom: 16px; margin-bottom: 24px; }
            h1 { margin: 0 0 12px; font-size: 24px; color: #111; }
            .metadata { font-size: 10pt; line-height: 1.6; }
            .warning { margin: 18px 0; padding: 12px; border: 1px solid #a16207; background: #fef3c7; color: #713f12; font-weight: 600; }
            .lesson-section { margin: 0 0 24px; break-inside: avoid; page-break-inside: avoid; }
            .section-type { display: inline-block; margin-bottom: 6px; padding: 3px 8px; border: 1px solid #777; border-radius: 4px; font-size: 9pt; text-transform: uppercase; }
            h2 { margin: 4px 0 10px; font-size: 17px; color: #111; }
            .section-content { color: #111; }
            .footer { border-top: 1px solid #bbb; margin-top: 32px; padding-top: 10px; font-size: 9pt; color: #555; }
            @media print { html, body { background: #fff !important; color: #111 !important; } }
          </style>
        </head>
        <body>
          <main class="document">
            <header class="header">
              <h1>${escapeHtml(lesson.title)}</h1>
              <div class="metadata">
                <div><strong>Status:</strong> ${escapeHtml(lesson.status)}</div>
                <div><strong>Audiência:</strong> ${escapeHtml(lesson.audience)}</div>
                <div><strong>Modo de fonte:</strong> ${escapeHtml(lesson.source_mode)}</div>
                ${
                  lesson.ai_provider
                    ? `<div><strong>Gerada por:</strong> ${escapeHtml(lesson.ai_provider)}${
                        lesson.ai_model ? ` · ${escapeHtml(lesson.ai_model)}` : ""
                      }</div>`
                    : ""
                }
              </div>
            </header>
            ${unsourcedWarning}
            ${sectionsHtml}
            <footer class="footer">Data Driven Dojô — Conteúdo Didático</footer>
          </main>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();

    setTimeout(() => {
      printWindow.print();
    }, 300);
  };
  const generate = useMutation({
    mutationFn: async () =>
      unwrapLesson(
        (
          await api.post<LessonResponse | Lesson>(
            `/api/library/sensei-units/${unitId}/didactic-content/`,
            {},
          )
        ).data,
      ),
    onMutate: () => setGenerationError(null),
    onSuccess: (data) => {
      client.setQueryData(queryKey, data);
    },
    onError: (error: any) => {
      const detail = error?.response?.data?.detail;
      const message =
        typeof detail === "string" && detail.includes("NEEDS_SOURCE")
          ? "Fontes insuficientes. NEEDS_SOURCE: uma fonte aprovada é necessária antes da geração."
          : typeof detail === "string" && detail.includes("SEMANTIC_MISMATCH")
            ? "A resposta da IA foi rejeitada por incoerência temática com a unidade e suas fontes. Gere novamente."
            : "Não foi possível gerar a aula neste momento.";
      setGenerationError(message);
      toast.error(message);
    },
  });
  const regenerate = useMutation({
    mutationFn: async () => {
      if (lesson?.status !== "ARCHIVED") {
        await api.patch(`/api/library/sensei-units/${unitId}/didactic-content/`, { status: "ARCHIVED" });
      }
      return unwrapLesson(
        (
          await api.post<LessonResponse | Lesson>(
            `/api/library/sensei-units/${unitId}/didactic-content/`,
            {},
          )
        ).data,
      );
    },
    onSuccess: (data) => {
      client.setQueryData(queryKey, data);
      toast.success("Aula regenerada com o grounding aprovado mais recente.");
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail ?? "Não foi possível regenerar a aula.");
    },
  });

  const transitionLesson = useMutation({
    mutationFn: async (status: Lesson["status"]) =>
      (await api.patch<Lesson>(`/api/library/sensei-units/${unitId}/didactic-content/`, { status }))
        .data,
    onSuccess: (updated) => {
      client.setQueryData<LessonResponse>(queryKey, { lesson: updated });
      setPublicationPreview(null);
      toast.success(`Status editorial da aula: ${updated.status}.`);
    },
    onError: (error: any) =>
      toast.error(
        error?.response?.data?.detail ?? "Não foi possível atualizar o status editorial da aula.",
      ),
  });
  const challengeSection = lesson?.sections.find(
    (section) => section.section_type === "AUTHORSHIP_CHALLENGE",
  );
  const challengeKey = [
    "sensei-authorship-challenge",
    formationId,
    unitId,
    lesson?.id ?? "no-lesson",
    challengeSection?.id ?? "no-challenge",
  ];
  const challengeQuery = useQuery({
    queryKey: challengeKey,
    queryFn: async () =>
      (
        await api.get<ChallengeResponse>(
          `/api/library/sensei-units/${unitId}/authorship-challenge/`,
        )
      ).data,
    enabled: Boolean(lesson && challengeSection),
    retry: false,
  });
  const startChallenge = useMutation({
    mutationFn: async () =>
      (
        await api.post<ChallengeResponse>(
          `/api/library/sensei-units/${unitId}/authorship-challenge/`,
          {},
        )
      ).data,
    onSuccess: (data) => client.setQueryData(challengeKey, data),
    onError: () => toast.error("Não foi possível iniciar o Desafio de Autoria neste momento."),
  });
  const submitChallenge = useMutation({
    mutationFn: async () => {
      const activity = challengeQuery.data?.activity;
      if (!activity) throw new Error("missing-authorship-activity");
      return (
        await api.post<Activity>(`/api/library/sensei-learning-activities/${activity.id}/answer/`, {
          response: challengeResponse,
        })
      ).data;
    },
    onSuccess: (activity) => {
      setChallengeResponse("");
      client.setQueryData<ChallengeResponse>(challengeKey, (current) =>
        current ? { ...current, activity } : current,
      );
    },
    onError: () => toast.error("Não foi possível enviar o desafio. Sua produção foi preservada."),
  });
  const previewPublication = useMutation({
    mutationFn: async () =>
      (
        await api.post<PublicationPreview>(
          `/api/library/sensei-units/${unitId}/publication-preview/`,
          { scope: publicationScope },
        )
      ).data,
    onSuccess: setPublicationPreview,
    onError: (error: any) =>
      toast.error(
        error?.response?.data?.detail ?? "Não foi possível gerar a prévia para o Workspace.",
      ),
  });
  const publishToWorkspace = useMutation({
    mutationFn: async () => {
      if (!publicationPreview) throw new Error("missing-preview");
      return (
        await api.post(`/api/library/sensei-units/${unitId}/publication-publish/`, {
          preview_token: publicationPreview.preview_token,
        })
      ).data;
    },
    onSuccess: () => {
      setPublicationPreview(null);
      toast.success("Conteúdo Student publicado no Workspace.");
    },
    onError: (error: any) =>
      toast.error(error?.response?.data?.detail ?? "Não foi possível publicar no Workspace."),
  });
  if (!enabled) return null;
  const needsSource =
    query.isError &&
    String((query.error as any)?.response?.data?.detail ?? "").includes("NEEDS_SOURCE");
  return (
    <section
      aria-labelledby="didactic-content-title"
      className="mt-6 rounded-xl border border-kaizen/30 bg-kaizen/5 p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 id="didactic-content-title" className="flex items-center gap-2 font-bold">
            <WandSparkles className="h-4 w-4" />
            CONTEÚDO DA AULA
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            A aula ensina; o Sensei Learning pratica, questiona e avalia.
          </p>
        </div>
        {lesson && (
          <div className="flex flex-wrap items-center gap-2 print:hidden">
            <Badge variant="outline">{lesson.status}</Badge>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={exporting !== null}
              onClick={() => void handleExport("docx")}
            >
              <Download className="h-4 w-4" />
              {exporting === "docx" ? "Exportando..." : "Exportar DOCX"}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={exporting !== null}
              onClick={() => void handleExport("html")}
            >
              <Download className="h-4 w-4" />
              {exporting === "html" ? "Exportando..." : "Exportar HTML"}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={handlePrint}>
              <Printer className="h-4 w-4" />
              Imprimir / Salvar PDF
            </Button>
          </div>
        )}
      </div>
      {lesson && (
        <div className="hidden print:mt-2 print:block">
          <p className="text-xs">Status: {lesson.status}</p>
          <h2 className="mt-2 text-xl font-bold">{lesson.title}</h2>
        </div>
      )}
      {query.isLoading ? (
        <p className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
          <LoaderCircle className="h-4 w-4 animate-spin" />
          Carregando conteúdo da aula...
        </p>
      ) : query.isError ? (
        needsSource ? (
          <p className="mt-4 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
            Fontes insuficientes. NEEDS_SOURCE: uma fonte aprovada é necessária antes da geração.
          </p>
        ) : (
          <p className="mt-4 rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
            Não foi possível carregar o conteúdo da aula.
          </p>
        )
      ) : !lesson ? (
        <div className="mt-4 rounded-lg border border-dashed p-4">
          <p className="text-sm text-muted-foreground">
            {generationError ?? "Nenhuma aula criada."}
          </p>
          {!generationError?.includes("Fontes insuficientes") && (
            <Button
              className="mt-3"
              disabled={generate.isPending}
              onClick={() => generate.mutate()}
            >
              {generate.isPending && <LoaderCircle className="animate-spin" />}
              <WandSparkles />
              GERAR AULA
            </Button>
          )}
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          {lesson.source_mode === "AI_GENERATED_UNSOURCED" && (
            <p className="rounded border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-700 dark:text-amber-300">
              Aula gerada por IA sem fonte aprovada. Exige revisão humana antes de qualquer
              publicação.
            </p>
          )}
          {lesson.ai_provider && (
            <p className="text-xs text-muted-foreground">
              Gerada por: {lesson.ai_provider}
              {lesson.ai_model ? ` · ${lesson.ai_model}` : ""}
            </p>
          )}
          {lesson.grounding_snapshot?.sources?.length ? (
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">GROUNDING AUDITÁVEL</Badge>
                <span>{lesson.grounding_snapshot.sources.length} fonte(s) preservada(s)</span>
                <span>{lesson.grounding_snapshot.excerpts?.length ?? 0} trecho(s) local(is)</span>
              </div>
              {(lesson.grounding_snapshot.excerpts?.length ?? 0) > 0 && (
                <p className="mt-2 text-muted-foreground">
                  Páginas PDF usadas: {Array.from(new Set((lesson.grounding_snapshot.excerpts ?? []).map((item) => item.pdf_page).filter((value): value is number => typeof value === "number"))).sort((a, b) => a - b).join(", ")}
                </p>
              )}
              <details className="mt-2">
                <summary className="cursor-pointer font-medium">Ver proveniência do grounding</summary>
                <div className="mt-2 space-y-2">
                  {(lesson.grounding_snapshot.sources ?? []).map((source) => (
                    <div key={source.id} className="rounded border bg-background p-2">
                      <b>{source.title}</b>
                      <p className="mt-1 text-muted-foreground">{source.location}</p>
                    </div>
                  ))}
                  {(lesson.grounding_snapshot.excerpts ?? []).map((item) => (
                    <div key={item.chunk_id} className="rounded border bg-background p-2">
                      <b>{item.book_title}</b> · PDF p.{item.pdf_page ?? "?"} · chunk {item.chunk_index}
                      <p className="mt-1 line-clamp-3 text-muted-foreground">{item.content}</p>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          ) : lesson.source_mode === "APPROVED_SOURCES" ? (
            <p className="rounded border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-700 dark:text-amber-300">
              Esta aula foi gerada antes do snapshot de grounding. Regenere o rascunho antes de enviá-lo para revisão.
            </p>
          ) : null}
          <div className="rounded-lg border bg-background p-4 print:hidden">
            <h4 className="font-bold">STATUS EDITORIAL DA AULA</h4>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge>{lesson.status}</Badge>
              {lesson.status === "DRAFT" && (
                <>
                  <Button size="sm" disabled={transitionLesson.isPending || regenerate.isPending} onClick={() => transitionLesson.mutate("REVIEW")}>Enviar para revisão</Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={transitionLesson.isPending || regenerate.isPending}
                    onClick={() => {
                      if (window.confirm("Regenerar substitui o rascunho atual usando as fontes e intervalos aprovados mais recentes. Continuar?")) {
                        regenerate.mutate();
                      }
                    }}
                  >
                    {regenerate.isPending ? "Regenerando..." : "Regenerar com grounding atual"}
                  </Button>
                </>
              )}
              {lesson.status === "ARCHIVED" && (
                <Button size="sm" disabled={regenerate.isPending} onClick={() => regenerate.mutate()}>
                  {regenerate.isPending ? "Regenerando..." : "Gerar nova versão"}
                </Button>
              )}
              {lesson.status === "REVIEW" && (
                <>
                  <Button size="sm" disabled={transitionLesson.isPending} onClick={() => transitionLesson.mutate("APPROVED")}>Aprovar aula</Button>
                  <Button variant="outline" size="sm" disabled={transitionLesson.isPending} onClick={() => transitionLesson.mutate("DRAFT")}>Retornar a rascunho</Button>
                </>
              )}
              {lesson.status === "APPROVED" && (
                <Button variant="outline" size="sm" disabled={transitionLesson.isPending} onClick={() => transitionLesson.mutate("REVIEW")}>Reabrir revisão</Button>
              )}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              Este status pertence à aula didática e não aprova fontes, atividades, evidências ou competências.
            </p>
          </div>
          <div className="rounded-lg border border-kaizen/30 bg-background p-4 print:hidden">
            <h4 className="font-bold">PUBLICAR NO WORKSPACE DO ALUNO</h4>
            <p className="mt-1 text-xs text-muted-foreground">
              A adaptação Student precisa ser visualizada antes da publicação e não concede domínio
              de competência.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <select
                aria-label="Escopo de publicação"
                className="h-9 rounded-md border bg-background px-3 text-sm"
                value={publicationScope}
                onChange={(event) => {
                  setPublicationScope(event.target.value as PublicationScope);
                  setPublicationPreview(null);
                }}
              >
                <option value="LESSON">Aula</option>
                <option value="MODULE">Módulo</option>
                <option value="FORMATION">Formação inteira</option>
              </select>
              <Button
                variant="outline"
                size="sm"
                disabled={previewPublication.isPending}
                onClick={() => previewPublication.mutate()}
              >
                <Eye className="h-4 w-4" />
                {previewPublication.isPending ? "Gerando prévia..." : "Prévia da adaptação"}
              </Button>
            </div>
            {publicationPreview && (
              <div className="mt-4 space-y-3 rounded border p-3">
                <p className="text-sm font-bold">
                  PRÉVIA STUDENT · {publicationPreview.summary.total} unidade(s) encontrada(s)
                </p>
                <p className="text-sm">
                  {publicationPreview.summary.eligible} elegível(is) para publicação ·{" "}
                  {publicationPreview.summary.ineligible} não elegível(is)
                </p>
                <div className="space-y-2">
                  {publicationPreview.eligibility_items.map((item) => (
                    <div key={item.unit_id} className="rounded border p-3 text-sm">
                      {publicationPreview.scope === "FORMATION" && (
                        <p className="text-xs font-medium text-muted-foreground">{item.module_title}</p>
                      )}
                      <p className="font-semibold">
                        {item.eligibility === "ELIGIBLE" ? "✓" : "✗"} {item.unit_title}
                      </p>
                      <p className="text-xs text-muted-foreground">{item.reason}</p>
                      {item.student_is_stale && (
                        <p className="mt-1 text-xs font-medium text-amber-700 dark:text-amber-300">
                          A versão Student está desatualizada e será atualizada sem duplicação.
                        </p>
                      )}
                    </div>
                  ))}
                </div>
                {publicationPreview.items.map((item) => (
                  <article key={item.source_lesson_id} className="rounded border p-3">
                    <h5 className="font-semibold">{item.title}</h5>
                    <p className="text-xs text-muted-foreground">
                      Perfil: {item.adaptation.profile} · publicação humana obrigatória
                    </p>
                    {item.sections.map((section, index) => (
                      <div key={`${section.title}-${index}`} className="mt-2">
                        <b className="text-sm">{section.title}</b>
                        <p className="whitespace-pre-wrap text-xs">{section.content}</p>
                      </div>
                    ))}
                  </article>
                ))}
                {publicationPreview.summary.eligible === 0 && (
                  <p className="text-xs font-medium text-amber-700 dark:text-amber-300">
                    Nenhuma unidade pode ser publicada. Aprove ao menos uma aula didática e gere uma nova prévia.
                  </p>
                )}
                <Button
                  disabled={publishToWorkspace.isPending || publicationPreview.summary.eligible === 0}
                  onClick={() => publishToWorkspace.mutate()}
                >
                  <Upload className="h-4 w-4" />
                  {publishToWorkspace.isPending
                    ? "Publicando..."
                    : `Confirmar publicação de ${publicationPreview.summary.eligible} unidade(s) elegível(is) (de ${publicationPreview.summary.total} encontrada(s)) no Workspace`}
                </Button>
              </div>
            )}
          </div>
          {lesson.sections.map((section) => (
            <article key={section.id} className="rounded-lg border bg-background p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{section.section_type_label}</Badge>
                <h4 className="font-bold">{section.title}</h4>
              </div>
              <div className="mt-3 whitespace-pre-wrap text-sm leading-6">{section.content}</div>
              {lesson.source_mode === "APPROVED_SOURCES" && (
                <div className="mt-3 border-t pt-3 text-xs">
                  {section.metadata.claim_grounding?.kind === "source_derived" ? (
                    <details>
                      <summary className="cursor-pointer font-medium">Ver evidências das afirmações · citações literais verificadas</summary>
                      <p className="mt-2 text-muted-foreground">Correspondência com o snapshot; interpretação e adequação pedagógica exigem revisão humana.</p>
                      {section.metadata.claim_grounding.claims.map((claim, index) => (
                        <div key={index} className="mt-3 space-y-2 rounded border p-3">
                          <blockquote className="whitespace-pre-wrap font-medium">{claim.text}</blockquote>
                          {claim.evidence.map((ref, evidenceIndex) => {
                            const excerpt = lesson.grounding_snapshot?.excerpts?.find(item => item.chunk_id === ref.chunk_id && item.source_id === ref.source_id && item.book_id === ref.book_id && item.pdf_page === ref.pdf_page);
                            return <div key={evidenceIndex} className="rounded bg-secondary/40 p-2">
                              <p>{excerpt?.book_title ?? "Evidência indisponível no snapshot"} · PDF p.{ref.pdf_page} · chunk #{ref.chunk_id} · fonte #{ref.source_id}</p>
                              {excerpt && <p className="mt-2 whitespace-pre-wrap text-muted-foreground">{excerpt.content}</p>}
                            </div>;
                          })}
                        </div>
                      ))}
                    </details>
                  ) : section.metadata.claim_grounding?.kind === "references" ? (
                    <p className="text-muted-foreground">Referências derivadas pelo backend das evidências do snapshot.</p>
                  ) : (
                    <p className="text-muted-foreground">{section.metadata.claim_grounding?.kind === "pedagogical"
                      ? "Orientação pedagógica — não certificada como afirmação da fonte. Revise também as premissas dos exercícios."
                      : section.metadata.claim_grounding?.kind === "human_edited"
                        ? "Conteúdo editado por pessoa — evidências anteriores não certificam esta redação."
                        : "Sem validação por afirmação nesta seção. O snapshot global não comprova cada afirmação."}</p>
                  )}
                </div>
              )}
              {section.section_type === "AUTHORSHIP_CHALLENGE" && (
                <div className="mt-4 border-t pt-4 print:hidden">
                  {challengeQuery.isLoading ? (
                    <p className="text-sm text-muted-foreground">Carregando desafio...</p>
                  ) : challengeQuery.isError ? (
                    <p className="text-sm text-destructive">
                      Não foi possível carregar o Desafio de Autoria.
                    </p>
                  ) : !challengeQuery.data?.activity ? (
                    <Button
                      disabled={startChallenge.isPending}
                      onClick={() => startChallenge.mutate()}
                    >
                      {startChallenge.isPending && <LoaderCircle className="animate-spin" />}Iniciar
                      Desafio de Autoria
                    </Button>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-sm font-semibold">Produção do desafio</p>
                      <p className="whitespace-pre-wrap rounded border bg-background/60 p-3 text-sm">
                        {challengeQuery.data.activity.prompt}
                      </p>
                      {challengeQuery.data.activity.attempts.map((attempt) => (
                        <div key={attempt.id} className="space-y-2 rounded border p-3 text-sm">
                          <b>TENTATIVA {attempt.attempt_number}</b>
                          <p className="mt-1 whitespace-pre-wrap">{attempt.answer}</p>
                          <div className="border-t pt-2">
                            <b>FEEDBACK DO SENSEI</b>
                            <p className="mt-1 whitespace-pre-wrap">{attempt.feedback}</p>
                          </div>
                        </div>
                      ))}
                      <Textarea
                        aria-label="Sua produção no Desafio de Autoria"
                        value={challengeResponse}
                        onChange={(event) => setChallengeResponse(event.target.value)}
                        placeholder="Escreva sua compreensão, aplicação, explicação e reflexão"
                      />
                      <Button
                        disabled={!challengeResponse.trim() || submitChallenge.isPending}
                        onClick={() => submitChallenge.mutate()}
                      >
                        {submitChallenge.isPending && <LoaderCircle className="animate-spin" />}
                        Submeter desafio
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
