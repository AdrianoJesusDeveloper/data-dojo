import { createFileRoute } from "@tanstack/react-router";
import { DojoHeader } from "@/components/DojoHeader";
import { useDojo, useHydrated } from "@/lib/dojo-store";
import { celebratePromotion, celebrateXp } from "@/lib/celebrate";
import { useState, useEffect } from "react";
import { toast, Toaster } from "sonner";

export const Route = createFileRoute("/workspace")({
  head: () => ({
    meta: [
      { title: "Workspace de Treinamento · Data Driven Dojô" },
      {
        name: "description",
        content: "Player de aula + IDE integrada. Compile e submeta seu desafio para ganhar XP.",
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

function Workspace() {
  const { state, submitChallenge } = useDojo();
  const hydrated = useHydrated();

  const [course, setCourse] = useState<Course | null>(null);
  const [currentLesson, setCurrentLesson] = useState<Lesson | null>(null);
  const [loading, setLoading] = useState(true);

  const [code, setCode] = useState("");
  const [lines, setLines] = useState<string[]>(["$ dojo-cli pronto. Aguardando submissão..."]);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/courses/")
      .then((res) => res.json())
      .then((data: Course[]) => {
        if (data.length > 0) {
          const activeCourse = data[0];
          setCourse(activeCourse);

          const firstVideoLesson = activeCourse.modules
            ?.flatMap((mod) => mod.lessons)
            .find((les) => les.content_type === "VIDEO");

          const firstLesson =
            firstVideoLesson || activeCourse.modules?.[0]?.lessons?.[0] || null;

          if (firstLesson) {
            setCurrentLesson(firstLesson);
            if (firstLesson.body) setCode(firstLesson.body);
          }
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Erro ao buscar dados do Django:", err);
        toast.error("Não foi possível conectar ao servidor backend.");
        setLoading(false);
      });
  }, []);

  const append = (line: string) => setLines((prev) => [...prev, line]);
  const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

  const compileAndSubmit = async () => {
    if (!currentLesson) return;
    setRunning(true);
    setLines([]);

    const exercise = currentLesson.exercise;
    const expectedKeywords = exercise?.expected_keywords ?? [];
    const expectedAnswer = exercise?.expected_answer ?? "";
    const evaluationMode = exercise?.evaluation_mode ?? "keywords";
    const points = exercise?.points ?? 120;

    const normalizedAnswer = code.replace(/\s+/g, " ").trim().toLowerCase();
    const normalizedExpected = expectedAnswer.replace(/\s+/g, " ").trim().toLowerCase();

    const valid = (() => {
      if (evaluationMode === "exact") {
        return normalizedAnswer === normalizedExpected;
      }
      if (evaluationMode === "contains") {
        return normalizedExpected.length > 0 && normalizedAnswer.includes(normalizedExpected);
      }
      if (expectedKeywords.length > 0) {
        return expectedKeywords.every((keyword) =>
          normalizedAnswer.includes(keyword.toLowerCase()),
        );
      }
      return normalizedAnswer.includes("select") && normalizedAnswer.includes("from");
    })();

    const steps: Array<[string, number]> = [
      ["$ dojo-cli submit ./desafio-dinamico.sql", 120],
      ["» preparando sandbox dojo-db ............... ok", 320],
      ["» rodando testes da lição .................. ok", 300],
    ];

    for (const [msg, delay] of steps) {
      append(msg);
      await wait(delay);
    }

    if (!valid) {
      append("\n✗ FALHA: a resposta não atingiu os critérios de avaliação do exercício.");
      toast.error("Desafio reprovado.");
      setRunning(false);
      return;
    }

    const result = submitChallenge(currentLesson.title, points, 1.5);
    append(`\n✓ DESAFIO APROVADO · +${points} XP`);

    if (result.promoted) {
      celebratePromotion(result.newBelt.color);
      toast.success(`🥋 PROMOVIDO! Você agora é ${result.newBelt.name}`, { duration: 5000 });
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
        <section className="rounded-xl border border-border bg-card overflow-hidden flex flex-col">
          <div className="aspect-video relative bg-black flex items-center justify-center">
            {currentLesson?.file_upload ? (
              <video
                src={currentLesson.file_upload}
                controls
                className="w-full h-full object-contain"
              />
            ) : currentLesson?.video_url ? (
              <iframe
                src={currentLesson.video_url}
                className="w-full h-full border-0"
                allowFullScreen
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
                <div className="mt-2 text-sm font-semibold text-foreground">
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
              <div className="font-display font-semibold text-sm mb-3">🗂 Estrutura do Curso</div>
              {course?.modules?.map((mod) => (
                <div key={mod.id} className="mb-4">
                  <div className="text-xs font-bold text-kaizen uppercase mb-1">{mod.title}</div>
                  <div className="space-y-1">
                    {mod.lessons?.map((les) => (
                      <button
                        key={les.id}
                        onClick={() => {
                          setCurrentLesson(les);
                          if (les.body) setCode(les.body);
                        }}
                        className={`w-full text-left text-sm px-3 py-2 rounded transition ${
                          currentLesson?.id === les.id
                            ? "bg-destructive text-destructive-foreground font-semibold"
                            : "bg-background hover:bg-muted text-muted-foreground"
                        }`}
                      >
                        {les.content_type === "VIDEO" ? "▶ " : "📄 "} {les.title}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

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
              <span className="ml-auto text-xs font-mono text-kaizen">{state.xp} XP</span>
            )}
          </div>
          <div className="flex-1 grid grid-rows-[1fr_auto_240px] min-h-130">
            <div className="relative flex overflow-hidden">
              <div
                aria-hidden
                className="select-none font-mono text-xs leading-relaxed text-muted-foreground/50 py-4 pl-3 pr-2 text-right border-r border-border/40 bg-black/40"
              >
                {code.split("\n").map((_, i) => (
                  <div key={i}>{i + 1}</div>
                ))}
              </div>
              <textarea
                spellCheck={false}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="flex-1 bg-belt-black text-belt-white font-mono text-sm p-4 resize-none outline-none leading-relaxed"
              />
            </div>
            <div className="border-t border-border p-3 bg-black">
              <button
                onClick={compileAndSubmit}
                disabled={running}
                className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-destructive px-6 py-3.5 font-display font-bold text-destructive-foreground uppercase tracking-[0.15em] text-sm transition"
              >
                {running ? "⏳ Analisando..." : "⚔ Compilar e submeter desafio"}
              </button>
            </div>
            <div className="bg-black border-t border-border overflow-hidden flex flex-col">
              <pre className="flex-1 p-4 font-mono text-xs text-[#9EE493] overflow-auto whitespace-pre-wrap leading-relaxed">
                {lines.map((l, i) => (
                  <div
                    key={i}
                    className={l.startsWith("✗") ? "text-destructive" : "text-[#9EE493]"}
                  >
                    {l || "\u00A0"}
                  </div>
                ))}
              </pre>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}