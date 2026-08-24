import { Link, createFileRoute } from "@tanstack/react-router";
import { ArrowRight, BookOpen, Database, ShoppingBag, Sparkles } from "lucide-react";
import logoDojo from "../assets/logo_transparente.png";

export const Route = createFileRoute("/store")({
  component: StorePage,
});

const products = [
  {
    icon: BookOpen,
    category: "E-books & Guias",
    title: "Fundamentos para Dados",
    description: "Materiais práticos para construir uma base sólida em dados, Python e tecnologia.",
    tag: "Conhecimento",
  },
  {
    icon: Database,
    category: "Templates & Dados",
    title: "Kit Data Analyst",
    description: "Templates, datasets e recursos para acelerar seus projetos e portfólio profissional.",
    tag: "Prática",
  },
  {
    icon: Sparkles,
    category: "IA & Automação",
    title: "Kit IA para Produtividade",
    description: "Prompts, modelos e recursos para aplicar IA com mais estratégia no dia a dia.",
    tag: "Inovação",
  },
];

function StorePage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link to="/" className="flex items-center gap-3">
            <img src={logoDojo} alt="Data Driven Dojô" className="h-10 w-10 object-contain" />
            <div className="leading-tight">
              <div className="font-display text-lg font-bold">Data Driven Dojô</div>
              <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">3DStore</div>
            </div>
          </Link>
          <Link to="/" className="rounded-lg border border-border px-4 py-2 text-sm transition hover:bg-secondary">
            Voltar ao Dojô
          </Link>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden border-b border-border bg-grid-dojo">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_75%_20%,rgba(255,165,0,.14),transparent_32%),radial-gradient(circle_at_20%_80%,rgba(0,87,184,.12),transparent_32%)]" />
          <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:py-28">
            <div className="max-w-4xl">
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-kaizen/30 bg-kaizen/10 px-4 py-2 font-mono text-xs font-bold uppercase tracking-[0.18em] text-kaizen">
                <ShoppingBag className="h-4 w-4" />
                3DStore · Data Driven Dojô
              </div>
              <h1 className="font-display text-5xl font-extrabold leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">
                Equipamentos para sua
                <span className="block text-kaizen text-glow-kaizen">jornada de evolução.</span>
              </h1>
              <p className="mt-7 max-w-2xl text-lg leading-8 text-muted-foreground sm:text-xl">
                Conhecimento, ferramentas e produtos para quem escolheu evoluir com
                <strong className="text-foreground"> Determinação, Disciplina e Direção.</strong>
              </p>
              <div className="mt-9 flex flex-wrap gap-3">
                <a href="#catalogo" className="inline-flex items-center gap-2 rounded-xl bg-kaizen px-6 py-3.5 font-display font-bold text-kaizen-foreground transition hover:brightness-110">
                  Explorar catálogo <ArrowRight className="h-4 w-4" />
                </a>
                <Link to="/" className="rounded-xl border border-border px-6 py-3.5 font-display font-bold transition hover:bg-secondary">
                  Conhecer o Dojô
                </Link>
              </div>
            </div>
          </div>
        </section>

        <section id="catalogo" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:py-20">
          <div className="mb-10 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-kaizen">Primeiro arsenal</p>
              <h2 className="mt-2 font-display text-3xl font-bold sm:text-4xl">Recursos para entrar em ação</h2>
            </div>
            <p className="max-w-md text-sm leading-6 text-muted-foreground">O catálogo começa digital e evolui com a comunidade: menos logística, mais velocidade para validar produtos.</p>
          </div>

          <div className="grid gap-5 md:grid-cols-3">
            {products.map((product) => {
              const Icon = product.icon;
              return (
                <article key={product.title} className="group rounded-2xl border border-border bg-card p-6 transition hover:-translate-y-1 hover:border-kaizen/50 hover:shadow-[0_18px_50px_rgba(0,0,0,.25)]">
                  <div className="flex items-center justify-between">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-secondary text-kaizen">
                      <Icon className="h-6 w-6" />
                    </div>
                    <span className="rounded-full bg-secondary px-3 py-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{product.tag}</span>
                  </div>
                  <p className="mt-7 font-mono text-xs uppercase tracking-wider text-muted-foreground">{product.category}</p>
                  <h3 className="mt-2 font-display text-2xl font-bold">{product.title}</h3>
                  <p className="mt-3 min-h-20 text-sm leading-6 text-muted-foreground">{product.description}</p>
                  <button disabled className="mt-6 w-full rounded-xl border border-border px-4 py-3 font-display font-bold text-muted-foreground opacity-70">Em breve</button>
                </article>
              );
            })}
          </div>
        </section>

        <section className="border-y border-border bg-card">
          <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6">
            <div className="grid gap-8 md:grid-cols-3">
              {[
                ["01", "Determinação", "Você decide entrar no caminho."],
                ["02", "Disciplina", "Você transforma intenção em prática."],
                ["03", "Direção", "Você sabe qual é o próximo passo."],
              ].map(([number, title, text]) => (
                <div key={number} className="border-l-2 border-kaizen pl-5">
                  <div className="font-mono text-xs text-kaizen">{number}</div>
                  <h3 className="mt-2 font-display text-xl font-bold">{title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
