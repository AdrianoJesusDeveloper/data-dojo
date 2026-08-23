import { Link, createFileRoute } from "@tanstack/react-router";
import bgTech from "../assets/plano_de_fundo_tecnologico.png";
import logoOficial from "../assets/logooicial.png";

export const Route = createFileRoute("/")({ component: HomePage });

function HomePage() {
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
