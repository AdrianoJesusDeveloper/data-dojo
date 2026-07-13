import { createFileRoute } from "@tanstack/react-router";
import { DojoHeader } from "@/components/DojoHeader";
import { BELTS, useDojo, getCurrentBelt, useHydrated } from "@/lib/dojo-store";
import { useMemo, useState } from "react";
import { toast, Toaster } from "sonner";

export const Route = createFileRoute("/community")({
  head: () => ({
    meta: [
      { title: "Comunidade · Data Driven Dojô" },
      {
        name: "description",
        content: "Feed dos samurais de dados. Conquistas, dúvidas e insights da comunidade Kaizen.",
      },
    ],
  }),
  component: Community,
});

interface Post {
  id: string;
  author: string;
  handle: string;
  beltId: "white" | "yellow" | "green" | "black";
  timeAgo: string;
  content: string;
  tags?: string[];
  likes: number;
  comments: number;
  pinned?: boolean;
}

const SEED_POSTS: Post[] = [
  {
    id: "p1",
    author: "Sensei Hiroshi",
    handle: "@hiroshi.sql",
    beltId: "black",
    timeAgo: "12 min",
    content:
      "Lembrete Kaizen do dia: uma CTE bem nomeada vale mais que 200 linhas de subquery. Refatorem, releiam, respirem. 改善",
    tags: ["#sql", "#kaizen"],
    likes: 142,
    comments: 23,
    pinned: true,
  },
  {
    id: "p2",
    author: "Mariana Tanaka",
    handle: "@mari.dados",
    beltId: "green",
    timeAgo: "1 h",
    content:
      "Acabei de passar no desafio 'Top 3 categorias por receita' em 18 min ⚔️ A dica foi tratar o desconto ANTES de agregar. +120 XP no bolso!",
    tags: ["#desafio", "#aprovado"],
    likes: 87,
    comments: 14,
  },
  {
    id: "p3",
    author: "Lucas Kenji",
    handle: "@kenji.py",
    beltId: "yellow",
    timeAgo: "3 h",
    content:
      "Alguém mais sentiu que o módulo de Janelas (window functions) é onde o pulo do gato acontece? Comecei a usar ROW_NUMBER em produção e dobrou a clareza dos meus pipelines.",
    likes: 54,
    comments: 9,
  },
  {
    id: "p4",
    author: "Camila Sato",
    handle: "@cami.bi",
    beltId: "green",
    timeAgo: "5 h",
    content:
      "Promovida hoje para Faixa Verde! 🥋 1.500 XP em 6 semanas estudando 1h por dia. A constância vence o talento. Obrigada Dojô! 🙏",
    tags: ["#promocao", "#kaizen"],
    likes: 231,
    comments: 41,
  },
  {
    id: "p5",
    author: "Pedro Ueda",
    handle: "@ueda.dbt",
    beltId: "black",
    timeAgo: "8 h",
    content:
      "Dúvida pra quem trabalha com dbt: vocês versionam os snapshots junto com os models ou em pastas separadas? Estou tentando reorganizar nosso repo.",
    tags: ["#dbt", "#duvida"],
    likes: 33,
    comments: 27,
  },
  {
    id: "p6",
    author: "Aprendiz Iniciante",
    handle: "@novo.aluno",
    beltId: "white",
    timeAgo: "1 d",
    content:
      "Começando hoje o caminho 🥋 Qual a melhor ordem pra seguir as trilhas? SQL → Python → Modelagem ou tudo em paralelo?",
    likes: 19,
    comments: 12,
  },
  {
    id: "p7",
    author: "Renata Yoshida",
    handle: "@re.analytics",
    beltId: "green",
    timeAgo: "1 d",
    content:
      "Compartilhando: usei o template de modelagem dimensional do Dojô em um projeto real e o time gostou tanto que virou padrão. O caminho é estudar e aplicar no mesmo dia.",
    tags: ["#modelagem", "#aplicado"],
    likes: 76,
    comments: 11,
  },
];

function beltStyle(id: Post["beltId"]) {
  const b = BELTS.find((x) => x.id === id)!;
  return { color: b.color, name: b.name, kanji: b.kanji };
}

function Community() {
  const { state } = useDojo();
  const hydrated = useHydrated();
  const myBelt = getCurrentBelt(state.xp);
  const [posts, setPosts] = useState<Post[]>(SEED_POSTS);
  const [draft, setDraft] = useState("");
  const [liked, setLiked] = useState<Set<string>>(new Set());

  const sorted = useMemo(
    () => [...posts].sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0)),
    [posts],
  );

  const publish = () => {
    const text = draft.trim();
    if (!text) return;
    let id = "";
    try {
      // Use crypto.randomUUID when available, fallback otherwise
      // (some environments/browsers may not implement it)
      // keep ids deterministic-enough for local UI usage

        const g = globalThis as unknown as { crypto?: { randomUUID?: () => string } };
        id = g.crypto?.randomUUID?.() ?? `p_${Math.random().toString(36).slice(2, 9)}`;
    } catch (e) {
      id = `p_${Math.random().toString(36).slice(2, 9)}`;
    }

    const newPost: Post = {
      id,
      author: state.studentName,
      handle: "@voce",
      beltId: myBelt.id,
      timeAgo: "agora",
      content: text,
      likes: 0,
      comments: 0,
    };

    try {
      setPosts((p) => [newPost, ...p]);
      setDraft("");
      toast.success("Postagem enviada ao dojô 🥋");
    } catch (err) {
      console.error("Erro ao publicar post:", err);
      toast.error("Não foi possível publicar o post localmente.");
    }
  };

  const toggleLike = (id: string) => {
    setLiked((s) => {
      const n = new Set(s);
      const isLiked = n.has(id);
      if (isLiked) {
        n.delete(id);
      } else {
        n.add(id);
      }
      setPosts((ps) =>
        ps.map((p) => (p.id === id ? { ...p, likes: p.likes + (isLiked ? -1 : 1) } : p)),
      );
      return n;
    });
  };

  return (
    <div className="min-h-screen">
      <Toaster position="top-right" theme="dark" richColors />
      <DojoHeader />
      <main className="mx-auto max-w-5xl px-4 py-10">
        <div>
          <div className="text-xs uppercase tracking-[0.25em] text-muted-foreground">
            Comunidade
          </div>
          <h1 className="font-display font-extrabold text-4xl mt-1">Salão dos Samurais</h1>
          <p className="text-muted-foreground mt-1">
            Conquistas, dúvidas e insights de quem trilha o caminho dos dados.
          </p>
        </div>

        {/* Composer */}
        <div className="mt-8 rounded-xl border border-border bg-card p-5">
          <div className="flex items-start gap-3">
            <div
              className="h-10 w-10 rounded-md flex items-center justify-center font-display font-bold text-sm border-2 border-black/40 shrink-0"
              style={{
                background: myBelt.color,
                color: myBelt.id === "black" ? "#FFA500" : "#1C1C1C",
              }}
            >
              {myBelt.kanji}
            </div>
            <div className="flex-1">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Compartilhe sua conquista, dúvida ou insight Kaizen..."
                className="w-full bg-background border border-border rounded-lg p-3 text-sm resize-none outline-none focus:border-kaizen/60 transition min-h-20"
              />
              <div className="flex items-center justify-between mt-2">
                <div className="text-[11px] font-mono text-muted-foreground">
                  {hydrated ? `${state.studentName} · ${myBelt.name}` : "—"}
                </div>
                <button
                  onClick={publish}
                  disabled={!draft.trim()}
                  className="rounded-md bg-destructive px-4 py-2 text-sm font-display font-bold text-destructive-foreground uppercase tracking-wider disabled:opacity-40 hover:opacity-90"
                >
                  Publicar
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Feed */}
        <div className="mt-6 space-y-4">
          {sorted.map((p) => {
            const b = beltStyle(p.beltId);
            const isLiked = liked.has(p.id);
            return (
              <article
                key={p.id}
                className={`rounded-xl border bg-card p-5 transition hover:border-kaizen/40 ${
                  p.pinned ? "border-kaizen/50" : "border-border"
                }`}
              >
                {p.pinned && (
                  <div className="text-[10px] uppercase tracking-[0.25em] text-kaizen mb-3 font-semibold">
                    ⛩ Fixado pelo Sensei
                  </div>
                )}
                <header className="flex items-center gap-3">
                  <div
                    className="h-11 w-11 rounded-md flex items-center justify-center font-display font-bold border-2 border-black/40 shrink-0"
                    style={{
                      background: b.color,
                      color: p.beltId === "black" ? "#FFA500" : "#1C1C1C",
                    }}
                  >
                    {b.kanji}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-display font-semibold">{p.author}</span>
                      <span className="text-xs font-mono text-muted-foreground">{p.handle}</span>
                      <span
                        className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border"
                        style={{
                          color: b.color,
                          borderColor: `${b.color}66`,
                          background: `${b.color}10`,
                        }}
                      >
                        {b.name}
                      </span>
                    </div>
                    <div className="text-[11px] text-muted-foreground mt-0.5">há {p.timeAgo}</div>
                  </div>
                </header>
                <p className="mt-3 text-sm leading-relaxed">{p.content}</p>
                {p.tags && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {p.tags.map((t) => (
                      <span
                        key={t}
                        className="text-[11px] font-mono text-[#4A9EFF] px-2 py-0.5 rounded bg-[#0057B8]/10 border border-[#0057B8]/40"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}

                <footer className="mt-4 flex items-center gap-5 text-xs">
                  <button
                    onClick={() => toggleLike(p.id)}
                    className={`flex items-center gap-1.5 transition ${
                      isLiked ? "text-destructive" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <span className="text-base leading-none">{isLiked ? "♥" : "♡"}</span>
                    <span className="font-mono">{p.likes}</span>
                  </button>
                  <button className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground">
                    <span className="text-base leading-none">💬</span>
                    <span className="font-mono">{p.comments}</span>
                  </button>
                  <button className="ml-auto text-muted-foreground hover:text-kaizen">
                    Compartilhar
                  </button>
                </footer>
              </article>
            );
          })}
        </div>
      </main>
    </div>
  );
}
