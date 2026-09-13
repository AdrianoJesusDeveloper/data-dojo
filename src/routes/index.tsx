import { Link, createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DojoHeader } from "../components/DojoHeader";
import { api } from "../lib/api";
import { useAuthStore } from "../lib/auth-store";
import bgTech from "../assets/plano_de_fundo_tecnologico.png";
import logoOficial from "../assets/logooicial.png";

export const Route = createFileRoute("/")({ component: HomePage });

export function HomePage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const [step, setStep] = useState<LearningStep | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const loadStep = async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    setError(false);
    try {
      const response = await api.get<LearningStep>("/api/learning/continue/");
      setStep(response.data);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadStep(); }, [isAuthenticated]);

  if (isAuthenticated) {
    return <AuthenticatedHome step={step} loading={loading} error={error} retry={loadStep} />;
  }

  return (
    <div style={{ minHeight: "100vh", width: "100vw", backgroundImage: `linear-gradient(rgba(0,0,0,.65), rgba(0,0,0,.65)), url(${bgTech})`, backgroundSize: "cover", backgroundPosition: "center", backgroundRepeat: "no-repeat", color: "#fff", fontFamily: "var(--font-sans)", position: "relative" }}>
      <div style={{ position: "absolute", top: 24, left: 24, zIndex: 10 }}>
        <img src={logoOficial} alt="Data Driven Dojô" style={{ height: 60, borderRadius: 8, boxShadow: "0 4px 12px rgba(0,0,0,.35)" }} />
      </div>
      <main className="min-h-screen text-white flex items-center">
        <section className="mx-auto max-w-7xl px-6 py-40 sm:px-10 lg:py-48">
          <div className="font-mono text-orange-500 font-bold tracking-[0.35em]">DATA DRIVEN DOJÔ</div>
          <h1 className="mt-8 max-w-5xl font-display text-5xl font-extrabold leading-[1.02] sm:text-6xl lg:text-7xl">
            Transforme dados
            <br />
            em conhecimento.
            <br />
            Desenvolva a mente
            <br />
            de um <span className="text-kaizen text-glow-kaizen">NINJA dos dados.</span>
          </h1>
          <p className="mt-8 max-w-3xl text-lg leading-8 text-zinc-300 sm:text-xl">
            Uma plataforma de aprendizado baseada na filosofia <strong className="text-white">3D</strong>:
            <strong className="text-orange-400"> Determinação, Disciplina e Direção.</strong>
            <br />
            Evolua sua carreira em Dados, IA e Tecnologia com propósito e prática.
          </p>
          <div className="mt-12 flex flex-wrap gap-4">
            <Link to="/login" className="rounded-xl bg-orange-500 px-8 py-4 font-display font-bold text-black hover:bg-orange-600 transition-colors">Entrar no Dojô</Link>
            <Link to="/store" className="inline-flex items-center rounded-xl border border-orange-500/70 bg-orange-500/10 px-8 py-4 font-display font-bold text-orange-300 hover:bg-orange-500/20 transition-colors">🛒 Conhecer 3DStore</Link>
            <a href="https://data-dojo-nine.vercel.app/conheca-sensey" className="rounded-xl border border-zinc-700 px-8 py-4 hover:bg-zinc-800 transition-colors">Conhecer Sensey</a>
            <Link to="/ai-sales" className="rounded-xl border border-orange-500/60 bg-orange-500/10 px-8 py-4 font-bold text-orange-400 hover:bg-orange-500/20 transition-colors">💬 Falar com o Sensey</Link>
          </div>
        </section>
      </main>
    </div>
  );
}

type StepType = "administrative" | "no_enrollment" | "start_course" | "continue_lesson" | "next_lesson" | "complete_course" | "course_completed";
interface LearningStep {
  type: StepType;
  course?: { id: number; title: string; description: string };
  course_progress?: { percentage: string; academic_state: string; completed_at: string | null };
  lesson?: { id: number; title: string; module: { title: string } };
}

function AuthenticatedHome({ step, loading, error, retry }: { step: LearningStep | null; loading: boolean; error: boolean; retry: () => Promise<void> }) {
  const [completing, setCompleting] = useState(false);
  const [completionError, setCompletionError] = useState(false);
  let title = "Seu próximo passo";
  let description = "Preparando sua jornada acadêmica...";
  let cta = "Ir ao Workspace";
  let href = "/workspace";

  if (step?.type === "administrative") {
    title = "Acesso administrativo";
    description = "Gerencie o Dojô pelas áreas administrativas disponíveis no menu.";
    cta = "Abrir Workspace em modo de prévia";
  } else if (step?.type === "no_enrollment") {
    title = "Escolha sua primeira formação";
    description = "Matricule-se em um curso para começar sua jornada no Dojô.";
    cta = "Escolher um curso";
  } else if (step?.type === "start_course") {
    title = "Comece sua formação";
    description = `Sua primeira aula é ${step.lesson?.title}.`;
    cta = "Começar curso";
  } else if (step?.type === "continue_lesson") {
    title = "Continue sua aula";
    description = `Retome ${step.lesson?.module.title} — ${step.lesson?.title}.`;
    cta = "Continuar aula";
  } else if (step?.type === "next_lesson") {
    title = "Continue aprendendo";
    description = `Seu próximo passo é ${step.lesson?.module.title} — ${step.lesson?.title}.`;
    cta = "Continuar aprendendo";
  } else if (step?.type === "complete_course") {
    title = "Finalize sua formação";
    description = "Todas as aulas foram concluídas. Solicite agora a conclusão acadêmica do curso.";
    cta = "Finalizar curso";
  } else if (step?.type === "course_completed") {
    title = "Formação concluída";
    description = "Sua conclusão está registrada. Explore o Workspace para escolher seu próximo caminho.";
    cta = "Voltar ao Workspace";
  }

  if (step?.course && step?.lesson) href = `/workspace?course=${step.course.id}&lesson=${step.lesson.id}`;
  else if (step?.course) href = `/workspace?course=${step.course.id}`;

  const finishCourse = async () => {
    if (!step?.course || completing) return;
    setCompleting(true);
    setCompletionError(false);
    try {
      await api.post(`/api/course-progress/by-course/${step.course.id}/complete/`, {});
      await retry();
    } catch {
      setCompletionError(true);
    } finally {
      setCompleting(false);
    }
  };

  return <div className="min-h-screen bg-background text-foreground"><DojoHeader/><main className="mx-auto max-w-5xl px-6 py-14"><p className="font-mono text-sm font-bold tracking-[0.25em] text-kaizen">CONTINUAR SUA JORNADA</p><h1 className="mt-3 font-display text-4xl font-extrabold">Qual é o meu próximo passo no Dojô?</h1>{loading?<div role="status" className="mt-10 rounded-xl border border-border bg-card p-8">Carregando sua jornada...</div>:error?<div role="alert" className="mt-10 rounded-xl border border-destructive/50 bg-card p-8"><h2 className="text-xl font-bold">Não foi possível carregar seu próximo passo</h2><p className="mt-2 text-muted-foreground">Seu Workspace continua disponível enquanto tentamos novamente.</p><div className="mt-5 flex gap-3"><button onClick={()=>void retry()} className="rounded bg-kaizen px-4 py-2 font-bold text-kaizen-foreground">Tentar novamente</button><Link to="/workspace" className="rounded border border-border px-4 py-2">Ir ao Workspace</Link></div></div>:<section className="mt-10 rounded-2xl border border-kaizen/40 bg-card p-8 shadow-lg"><h2 className="font-display text-3xl font-bold">{title}</h2>{step?.course&&<div className="mt-5"><p className="text-sm text-muted-foreground">Curso atual</p><p className="text-xl font-semibold">{step.course.title}</p></div>}{step?.course_progress&&<div className="mt-5"><div className="flex justify-between text-sm"><span>Progresso persistente</span><strong>{Number(step.course_progress.percentage)}%</strong></div><div className="mt-2 h-2 overflow-hidden rounded bg-muted"><div className="h-full bg-kaizen" style={{width:`${Math.min(100,Number(step.course_progress.percentage))}%`}}/></div></div>}<p className="mt-5 text-muted-foreground">{description}</p>{step?.type==="complete_course"?<button type="button" onClick={()=>void finishCourse()} disabled={completing} className="mt-7 rounded bg-kaizen px-5 py-3 font-bold text-kaizen-foreground disabled:opacity-60">{completing?"Finalizando...":cta}</button>:<a href={href} className="mt-7 inline-flex rounded bg-kaizen px-5 py-3 font-bold text-kaizen-foreground">{cta}</a>}{completionError&&<p role="alert" className="mt-3 text-sm text-destructive">Não foi possível concluir o curso agora. Revise os requisitos e tente novamente.</p>}</section>}</main></div>;
}
