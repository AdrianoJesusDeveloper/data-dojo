import { api } from "@/lib/api";
import { createFileRoute } from "@tanstack/react-router";
import { DojoHeader } from "@/components/DojoHeader";
import { useDojo, useHydrated } from "@/lib/dojo-store";
import { celebratePromotion, celebrateXp } from "@/lib/celebrate";
import { useEffect, useState } from "react";
import { toast, Toaster } from "sonner";

export const Route = createFileRoute("/workspace")({
  head: () => ({
    meta: [
      {
        title: "Workspace de Treinamento · Data Driven Dojô",
      },
      {
        name: "description",
        content: "Player de aula + IDE integrada.",
      },
    ],
  }),
  component: Workspace,
});

interface Exercise {
  id: number;
  lesson: number;
  title: string;
  statement: string;
  answer_type: string;
  expected_answer: string;
  expected_keywords: string[];
  evaluation_mode: string;
  points: number;
}

interface Lesson {
  id: number;
  title: string;
  content_type: string;
  file_upload: string | null;
  video_url: string | null;
  body: string;
  order: number;
  exercise: Exercise | null;
}

interface Module {
  id: number;
  title: string;
  order: number;
  lessons: Lesson[];
}

interface Course {
  id: number;
  title: string;
  description: string;
  modules: Module[];
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

function Workspace() {
  const { state, submitChallenge } = useDojo();
  const hydrated = useHydrated();

  const [course, setCourse] = useState<Course | null>(null);
  const [currentLesson, setCurrentLesson] = useState<Lesson | null>(null);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState("");
  const [lines, setLines] = useState<string[]>([
    "$ dojo-cli pronto. Aguardando submissão...",
  ]);
  const [running, setRunning] = useState(false);

  /* Busca cursos no Django API Render considerando paginação DRF */
  useEffect(() => {
    api
      .get<PaginatedResponse<Course> | Course[]>("/courses/")
      .then((response) => {
        const responseData = response.data;
        const data = Array.isArray(responseData)
          ? responseData
          : responseData.results;

        if (data && data.length > 0) {
          const activeCourse = data[0];
          setCourse(activeCourse);

          const firstVideoLesson = activeCourse.modules
            ?.flatMap((module) => module.lessons)
            .find((lesson) => lesson.content_type === "VIDEO");

          const firstLesson =
            firstVideoLesson ??
            activeCourse.modules?.[0]?.lessons?.[0] ??
            null;

          if (firstLesson) {
            setCurrentLesson(firstLesson);
            if (firstLesson.body) {
              setCode(firstLesson.body);
            }
          }
        }

        setLoading(false);
      })
      .catch((error) => {
        console.error("Erro API Django:", error);
        toast.error("Falha ao conectar ao backend.");
        setLoading(false);
      });
  }, []);

  const append = (line: string) => {
    setLines((previous) => [...previous, line]);
  };

  const wait = (ms: number) =>
    new Promise((resolve) => setTimeout(resolve, ms));

  const compileAndSubmit = async () => {
    if (!currentLesson) {
      return;
    }

    setRunning(true);
    setLines([]);

    const exercise = currentLesson.exercise;
    const expectedKeywords = exercise?.expected_keywords ?? [];
    const expectedAnswer = exercise?.expected_answer ?? "";
    const evaluationMode = exercise?.evaluation_mode ?? "keywords";
    const points = exercise?.points ?? 120;

    const normalizedAnswer = code
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();

    const normalizedExpected = expectedAnswer
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();

    const valid = (() => {
      if (evaluationMode === "exact") {
        return normalizedAnswer === normalizedExpected;
      }

      if (evaluationMode === "contains") {
        return (
          normalizedExpected.length > 0 &&
          normalizedAnswer.includes(normalizedExpected)
        );
      }

      if (expectedKeywords.length > 0) {
        return expectedKeywords.every((keyword) =>
          normalizedAnswer.includes(keyword.toLowerCase())
        );
      }

      return (
        normalizedAnswer.includes("select") &&
        normalizedAnswer.includes("from")
      );
    })();

    const steps = [
      ["$ dojo-cli submit ./desafio-dinamico.sql", 120],
      ["» preparando sandbox dojo-db ............... ok", 320],
      ["» rodando testes da lição .................. ok", 300],
    ] as const;

    for (const [message, delay] of steps) {
      append(message);
      await wait(delay);
    }

    if (!valid) {
      append("✗ FALHA: a resposta não atingiu os critérios de avaliação.");
      toast.error("Desafio reprovado.");
      setRunning(false);
      return;
    }

    const result = submitChallenge(currentLesson.title, points, 1.5);

    append(`✓ DESAFIO APROVADO · +${points} XP`);

    if (result.promoted) {
      celebratePromotion(result.newBelt.color);
      toast.success(
        `🥋 PROMOVIDO! Você agora é ${result.newBelt.name}`,
        {
          duration: 5000,
        }
      );
    } else {
      celebrateXp();
      toast.success(`Desafio aprovado! +${points} XP`);
    }

    setRunning(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center text-kaizen font-mono">
        ⏳ Carregando ecossistema do Dojô...
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Toaster position="top-right" theme="dark" richColors />
      <DojoHeader />

      <main className="flex-1 mx-auto max-w-[1600px] w-full px-4 py-6 grid lg:grid-cols-2 gap-4">
        {/* Seção Esquerda: Vídeo, Detalhes e Estrutura */}
        <section className="rounded-xl border border-border bg-card overflow-hidden flex flex-col">
          <div className="aspect-video relative bg-black flex items-center justify-center">
            {currentLesson?.file_upload || currentLesson?.video_url ? (
              <video
                src={currentLesson.file_upload || currentLesson.video_url || ""}
                controls
                preload="metadata"
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-muted-foreground text-sm font-mono">
                Nenhum vídeo anexado a esta lição.
              </div>
            )}
          </div>

          <div className="p-6 overflow-y-auto">
            <div className="text-xs uppercase tracking-widest text-muted-foreground">
              Curso: {course?.title || "Sem curso selecionado"}
            </div>

            <h1 className="font-display font-bold text-2xl mt-1">
              {currentLesson ? currentLesson.title : "Nenhuma lição encontrada"}
            </h1>

            <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
              {course?.description}
            </p>

            {currentLesson?.exercise && (
              <div className="mt-4 rounded-lg border border-border bg-background/70 p-4">
                <div className="text-xs font-bold uppercase tracking-[0.2em] text-kaizen">
                  Exercício · {currentLesson.exercise.answer_type}
                </div>

                <div className="mt-2 text-sm font-semibold">
                  {currentLesson.exercise.title}
                </div>

                <div className="mt-2 text-sm text-muted-foreground whitespace-pre-wrap">
                  {currentLesson.exercise.statement}
                </div>

                {currentLesson.exercise.expected_keywords.length > 0 && (
                  <div className="mt-3 text-xs text-muted-foreground">
                    Critérios: {currentLesson.exercise.expected_keywords.join(", ")}
                  </div>
                )}
              </div>
            )}

            <div className="mt-6 border-t border-border pt-4">
              <div className="font-display font-semibold text-sm mb-3">
                🗂 Estrutura do Curso
              </div>

              {course?.modules?.map((module) => (
                <div key={module.id} className="mb-4">
                  <div className="text-xs font-bold text-kaizen uppercase mb-1">
                    {module.title}
                  </div>

                  <div className="space-y-1">
                    {module.lessons?.map((lesson) => (
                      <button
                        key={lesson.id}
                        onClick={() => {
                          setCurrentLesson(lesson);
                          if (lesson.body) {
                            setCode(lesson.body);
                          }
                        }}
                        className={`w-full text-left text-sm px-3 py-2 rounded transition ${
                          currentLesson?.id === lesson.id
                            ? "bg-destructive text-destructive-foreground font-semibold"
                            : "bg-background hover:bg-muted text-muted-foreground"
                        }`}
                      >
                        {lesson.content_type === "VIDEO" ? "▶ " : "📄 "}
                        {lesson.title}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Seção Direita: IDE, Botão de Execução e Terminal */}
        <section className="rounded-xl border border-border bg-belt-black flex flex-col overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border bg-black">
            <div className="flex gap-1.5">
              <span className="h-3 w-3 rounded-full bg-destructive" />
              <span className="h-3 w-3 rounded-full bg-kaizen" />
              <span className="h-3 w-3 rounded-full bg-belt-green" />
            </div>

            <span className="ml-3 text-xs font-mono text-muted-foreground">
              ~/dojo/desafios/workspace.sql
            </span>

            {hydrated && (
              <span className="ml-auto text-xs font-mono text-kaizen">
                {state.xp} XP
              </span>
            )}
          </div>

          <div className="flex-1 grid grid-rows-[1fr_auto_240px]">
            <div className="relative flex overflow-hidden">
              <div className="select-none font-mono text-xs leading-relaxed text-muted-foreground/50 py-4 pl-3 pr-2 text-right border-r border-border/40 bg-black/40">
                {code.split("\n").map((_, index) => (
                  <div key={index}>{index + 1}</div>
                ))}
              </div>

              <textarea
                spellCheck={false}
                value={code}
                onChange={(event) => setCode(event.target.value)}
                className="flex-1 bg-belt-black text-belt-white font-mono text-sm p-4 resize-none outline-none leading-relaxed"
              />
            </div>

            <div className="border-t border-border p-3 bg-black">
              <button
                onClick={compileAndSubmit}
                disabled={running}
                className="w-full rounded-md bg-destructive px-6 py-3.5 font-display font-bold text-destructive-foreground uppercase tracking-[0.15em] text-sm"
              >
                {running ? "⏳ Analisando..." : "⚔ Compilar e submeter desafio"}
              </button>
            </div>

            <div className="bg-black border-t border-border overflow-hidden">
              <pre className="h-full p-4 font-mono text-xs text-[#9EE493] overflow-auto whitespace-pre-wrap">
                {lines.map((line, index) => (
                  <div key={index}>{line || "\u00A0"}</div>
                ))}
              </pre>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}