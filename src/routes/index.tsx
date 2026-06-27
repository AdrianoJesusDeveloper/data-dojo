import { createFileRoute, Link } from "@tanstack/react-router";
import { DojoHeader } from "@/components/DojoHeader";
import { BELTS } from "@/lib/dojo-store";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Data Driven Dojô — Inicie seu treinamento" },
      { name: "description", content: "Disciplina samurai e filosofia Kaizen aplicadas ao aprendizado de dados. Conquiste faixas, evolua sem parar." },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="min-h-screen">
      <DojoHeader />

      {/* HERO */}
      <section className="relative overflow-hidden">
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(80% 60% at 20% 10%, rgba(0,87,184,0.55), transparent 60%), radial-gradient(60% 50% at 90% 30%, rgba(230,57,70,0.25), transparent 70%), #0A1428",
          }}
        />
        <div className="absolute inset-0 bg-grid-dojo opacity-50" />
        <div className="relative mx-auto max-w-7xl px-4 pt-20 pb-28 grid lg:grid-cols-[1.2fr_1fr] gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-kaizen/40 bg-kaizen/10 px-3 py-1 text-xs uppercase tracking-[0.25em] text-kaizen">
              <span className="h-1.5 w-1.5 rounded-full bg-kaizen animate-pulse" />
              Filosofia Kaizen · 改善
            </div>
            <h1 className="mt-6 font-display font-extrabold text-5xl md:text-7xl leading-[1.02] tracking-tight">
              Domine os <span className="text-kaizen text-glow-kaizen">dados</span>.<br />
              Forje sua <span className="text-destructive text-glow-samurai">disciplina</span>.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-muted-foreground">
              O <strong className="text-foreground">Data Driven Dojô</strong> é uma jornada gamificada de treinamento
              para profissionais de dados. Conquiste <strong className="text-kaizen">Pontos Kaizen</strong>, evolua
              entre faixas marciais e trilhe o caminho da maestria — um desafio por vez.
            </p>

            <div className="mt-10 flex flex-wrap items-center gap-4">
              <Link
                to="/workspace"
                className="group relative inline-flex items-center justify-center gap-2 rounded-md bg-destructive px-7 py-4 font-display font-bold text-destructive-foreground uppercase tracking-wider text-sm shadow-[0_10px_40px_-10px_rgba(230,57,70,0.8)] transition-transform hover:-translate-y-0.5 hover:shadow-[0_14px_40px_-8px_rgba(230,57,70,0.9)]"
              >
                ⚔ Iniciar Treinamento
              </Link>
              <Link
                to="/dashboard"
                className="inline-flex items-center justify-center rounded-md border border-border bg-secondary/60 px-6 py-4 text-sm font-semibold text-foreground hover:bg-secondary"
              >
                Ver Dashboard →
              </Link>
            </div>

            <dl className="mt-12 grid grid-cols-3 gap-6 max-w-lg">
              {[
                { k: "+120", v: "Desafios" },
                { k: "4", v: "Faixas" },
                { k: "∞", v: "Kaizen" },
              ].map((s) => (
                <div key={s.v}>
                  <dt className="font-display font-extrabold text-3xl text-kaizen">{s.k}</dt>
                  <dd className="text-xs uppercase tracking-widest text-muted-foreground">{s.v}</dd>
                </div>
              ))}
            </dl>
          </div>

          {/* Belt tower */}
          <div className="relative">
            <div className="absolute -inset-4 bg-primary/20 blur-3xl rounded-full" />
            <div className="relative rounded-2xl border border-border bg-card/80 p-6 backdrop-blur">
              <div className="text-xs uppercase tracking-[0.25em] text-muted-foreground">A Trilha do Guerreiro</div>
              <div className="mt-1 font-display font-bold text-2xl">Sistema de Graduação</div>
              <ul className="mt-6 space-y-3">
                {BELTS.map((b, i) => (
                  <li
                    key={b.id}
                    className="flex items-center gap-4 rounded-lg border border-border bg-background/60 p-3"
                  >
                    <div
                      className="h-12 w-12 rounded-md flex items-center justify-center font-display font-bold text-lg border-2 border-black/40"
                      style={{ background: b.color, color: b.id === "black" ? "#FFA500" : "#1C1C1C" }}
                    >
                      {b.kanji}
                    </div>
                    <div className="flex-1">
                      <div className="font-display font-semibold">{b.name}</div>
                      <div className="text-xs text-muted-foreground">{b.motto}</div>
                    </div>
                    <div className="font-mono text-xs text-kaizen">{b.minXp} XP</div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* PILARES */}
      <section className="mx-auto max-w-7xl px-4 py-20">
        <h2 className="font-display font-bold text-3xl md:text-4xl">Três pilares. Um caminho.</h2>
        <div className="mt-10 grid md:grid-cols-3 gap-5">
          {[
            {
              t: "Treine com propósito",
              d: "Trilhas curadas em SQL, Python, Estatística, Engenharia e Analytics. Cada lição é um movimento.",
              c: "bg-primary",
            },
            {
              t: "Compile e submeta",
              d: "IDE integrada para submeter desafios reais. Ganhe XP imediatamente ao validar sua solução.",
              c: "bg-destructive",
            },
            {
              t: "Evolua de faixa",
              d: "Marcos automáticos: o sistema te promove visualmente quando você prova maestria.",
              c: "bg-kaizen",
            },
          ].map((p) => (
            <div key={p.t} className="rounded-xl border border-border bg-card p-6 hover:border-kaizen/50 transition-colors">
              <div className={`h-1 w-12 rounded-full ${p.c}`} />
              <h3 className="mt-4 font-display font-bold text-xl">{p.t}</h3>
              <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{p.d}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-border py-8 text-center text-xs text-muted-foreground">
        <span className="font-mono">$ echo "kaizen --forever"</span> · Data Driven Dojô © 2026
      </footer>
    </div>
  );
}
