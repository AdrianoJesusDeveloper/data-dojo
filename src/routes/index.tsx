import { createFileRoute, Link } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <main className="min-h-screen bg-zinc-950 text-white">

      <section className="mx-auto max-w-7xl px-8 py-32">

        <span className="text-orange-500 font-bold tracking-[6px]">
          ADRIANO JESUS
        </span>

        <h1 className="mt-6 text-7xl font-black leading-tight">
          Data Engineer
          <br />
          Data Scientist
          <br />
          Full Stack Developer
        </h1>

        <p className="mt-10 max-w-3xl text-xl text-zinc-400 leading-9">
          Desenvolvedor apaixonado por resolver problemas de negócio
          utilizando Engenharia de Dados, Ciência de Dados,
          Inteligência Artificial e Desenvolvimento Full Stack.
        </p>

        <div className="mt-12 flex gap-5">

          <Link
            to="/portfolio"
            className="rounded-xl bg-orange-500 px-8 py-4 font-bold hover:bg-orange-600 transition"
          >
            Ver Portfólio
          </Link>

          <a
            href="https://github.com/AdrianoJesusDeveloper"
            target="_blank"
            className="rounded-xl border border-zinc-700 px-8 py-4 hover:border-orange-500"
          >
            GitHub
          </a>

        </div>

      </section>

    </main>
  );
}