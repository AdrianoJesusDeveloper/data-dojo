import { DojoHeader } from "@/components/DojoHeader";
import { useEffect, useState } from "react";
import { toast, Toaster } from "sonner";

const API = "https://data-dojo.onrender.com";

type User = { id: number; username: string; profile_picture?: string | null; xp_points?: number };
type Comment = { id: number; content: string; created_at: string; user?: User; student_name?: string; parent?: number | null; replies?: Comment[]; is_owner?: boolean };
type Post = { id: number; content: string; created_at: string; user?: User; student_name?: string; student_username?: string; student_belt?: string; likes_count: number; comments_count: number; comments?: Comment[]; is_owner?: boolean };

function avatarUrl(user?: User) {
  const value = user?.profile_picture;
  if (!value) return null;
  if (value.startsWith("http") || value.startsWith("data:")) return value;
  return `${API}${value.startsWith("/") ? value : `/${value}`}`;
}

function Avatar({ user, size = "h-10 w-10" }: { user?: User; size?: string }) {
  const url = avatarUrl(user);
  return <div className={`${size} shrink-0 overflow-hidden rounded-full border border-orange-500/60 bg-zinc-800 flex items-center justify-center font-bold text-orange-400`}>
    {url ? <img src={url} alt={user?.username || "Usuário"} className="h-full w-full object-cover" /> : (user?.username || "S").slice(0, 2).toUpperCase()}
  </div>;
}

export default function Community() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [draft, setDraft] = useState("");
  const [comment, setComment] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;

  async function fetchPosts() {
    if (!token) { setLoading(false); return; }
    try {
      const response = await fetch(`${API}/api/community/posts/`, { headers: { Authorization: `Token ${token}` } });
      if (!response.ok) throw new Error("Falha ao carregar comunidade");
      const data = await response.json();
      setPosts(Array.isArray(data) ? data : data.results || []);
    } catch { toast.error("Não foi possível carregar a comunidade."); }
    finally { setLoading(false); }
  }

  useEffect(() => { fetchPosts(); }, []);

  async function publish() {
    if (!draft.trim() || !token) return;
    const response = await fetch(`${API}/api/community/posts/`, { method: "POST", headers: { Authorization: `Token ${token}` }, body: (() => { const f = new FormData(); f.append("title", "Post da Comunidade"); f.append("content", draft.trim()); return f; })() });
    if (response.ok) { setDraft(""); toast.success("Postagem publicada no dojô 🥋"); fetchPosts(); } else toast.error("Erro ao publicar.");
  }

  async function like(postId: number) {
    const response = await fetch(`${API}/api/community/posts/${postId}/like/`, { method: "POST", headers: { Authorization: `Token ${token}` } });
    if (response.ok) { const data = await response.json(); setPosts((current) => current.map((p) => p.id === postId ? { ...p, likes_count: data.likes_count } : p)); }
  }

  async function sendComment(postId: number) {
    const text = comment[postId]?.trim();
    if (!text) return;
    const response = await fetch(`${API}/api/community/comments/`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Token ${token}` }, body: JSON.stringify({ topic: postId, content: text }) });
    if (response.ok) { setComment((c) => ({ ...c, [postId]: "" })); toast.success("Comentário publicado!"); fetchPosts(); } else toast.error("Erro ao comentar.");
  }

  return <div className="min-h-screen bg-background text-foreground"><Toaster position="top-right" theme="dark" richColors /><DojoHeader />
    <main className="mx-auto max-w-5xl px-4 py-10">
      <div><div className="text-xs uppercase tracking-[0.25em] text-muted-foreground">Comunidade</div><h1 className="font-display font-extrabold text-4xl mt-1">Salão dos Samurais</h1><p className="text-muted-foreground mt-1">Conquistas, dúvidas e insights de quem trilha o caminho dos dados.</p></div>
      <section className="mt-8 rounded-xl border border-border bg-card p-5"><textarea value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Compartilhe sua conquista, dúvida ou insight Kaizen..." className="w-full min-h-28 rounded-lg border border-border bg-background p-3 text-sm text-white outline-none focus:border-kaizen" /><div className="mt-3 flex justify-end"><button onClick={publish} disabled={!draft.trim()} className="rounded-md bg-destructive px-5 py-2 font-bold text-destructive-foreground disabled:opacity-40">Publicar</button></div></section>
      <div className="mt-6 space-y-5">
        {loading ? <p className="text-sm text-muted-foreground">Carregando comunidade...</p> : posts.length === 0 ? <p className="text-sm text-muted-foreground">O salão está silencioso. Seja o primeiro a publicar!</p> : posts.map((post) => {
          const author = post.user;
          return <article key={post.id} className="rounded-xl border border-border bg-card p-5">
            <header className="flex items-center gap-3"><Avatar user={author} size="h-12 w-12" /><div><div className="font-display font-semibold">{author?.username || post.student_name || post.student_username || "Samurai"}</div><div className="text-xs text-muted-foreground">{new Date(post.created_at).toLocaleString("pt-BR")}</div></div></header>
            <p className="mt-5 whitespace-pre-wrap leading-7 text-zinc-200">{post.content}</p>
            <div className="mt-5 flex items-center gap-5 text-sm text-muted-foreground"><button onClick={() => like(post.id)} className="hover:text-orange-400">❤️ {post.likes_count}</button><span>💬 {post.comments_count}</span></div>
            <div className="mt-5 border-t border-border pt-4"><div className="flex gap-2"><input value={comment[post.id] || ""} onChange={(e) => setComment((c) => ({ ...c, [post.id]: e.target.value }))} onKeyDown={(e) => { if (e.key === "Enter") sendComment(post.id); }} placeholder="Escreva uma resposta..." className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-white" /><button onClick={() => sendComment(post.id)} className="rounded-md border border-orange-500 px-4 py-2 text-sm font-bold text-orange-400">Responder</button></div>
              <div className="mt-4 space-y-3">{(post.comments || []).map((item) => <div key={item.id} className="flex gap-3 rounded-lg bg-background/60 p-3"><Avatar user={item.user} size="h-9 w-9" /><div><div className="text-sm font-semibold">{item.user?.username || item.student_name || "Samurai"}</div><div className="mt-1 text-sm text-zinc-300 whitespace-pre-wrap">{item.content}</div></div></div>)}</div>
            </div>
          </article>;
        })}
      </div>
    </main>
  </div>;
}
