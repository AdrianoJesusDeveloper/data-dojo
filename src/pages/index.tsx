import { Link, createFileRoute } from "@tanstack/react-router";
import bgTech from "../assets/plano_de_fundo_tecnologico.png";
import logoOficial from "../assets/logooicial.png";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        width: "100vw",
        backgroundImage: `linear-gradient(rgba(0,0,0,.65), rgba(0,0,0,.65)), url(${bgTech})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat",
        color: "#fff",
        fontFamily: "sans-serif",
        position: "relative",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 24,
          left: 24,
          zIndex: 10,
        }}
      >
        <img
          src={logoOficial}
          alt="Data Driven Dojo"
          style={{
            height: 60,
            borderRadius: 8,
            boxShadow: "0 4px 12px rgba(0,0,0,.35)",
          }}
        />
      </div>

      <main className="min-h-screen text-white flex items-center">
        <section className="mx-auto max-w-7xl px-10 py-48">
          <div className="text-orange-500 font-bold tracking-[10px]">
            DATA DRIVEN DOJÔ
          </div>

          <h1 className="mt-8 text-6xl font-black leading-tight">
            Transforme dados
            <br />
            em conhecimento.
            <br />
            Desenvolva a mente
            <br />
            de um NINJA dos dados.
          </h1>

          <p className="mt-8 max-w-3xl text-xl text-zinc-400">
            Uma plataforma de aprendizado baseada na filosofia 3DS:
            Determinação, Disciplina e Direção.
            Evolua sua carreira em Dados, IA e Tecnologia.
          </p>

          <div className="mt-12 flex flex-wrap gap-5">
            <Link
              to="/login"
              className="rounded-xl bg-orange-500 px-8 py-4 font-bold hover:bg-orange-600 transition-colors"
            >
              Entrar no Dojô
            </Link>

            <a
              href="https://data-dojo-nine.vercel.app/conheca-sensey"
              className="rounded-xl border border-zinc-700 px-8 py-4 hover:bg-zinc-800 transition-colors"
            >
              Conhecer Sensei
            </a>

            <Link
              to="/ai-sales"
              className="rounded-xl border border-orange-500/60 bg-orange-500/10 px-8 py-4 font-bold text-orange-400 hover:bg-orange-500/20 transition-colors"
            >
              💼 Falar com AI Sales
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
