import { createFileRoute } from "@tanstack/react-router";
import { DojoHeader } from "@/components/DojoHeader";
import { BELTS, useDojo, getCurrentBelt, useHydrated } from "@/lib/dojo-store";
import { useEffect, useState } from "react";
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

interface Comment {
  id: number;
  student_name?: string;
  user?: { id: number; username: string } | string;
  content: string;
  created_at: string;
  parent?: number | null;
  replies?: Comment[];
  is_owner?: boolean;
}

interface Post {
  id: number;
  user?: {
    id: number;
    username: string;
  };
  student_name: string;
  student_username: string;
  student_belt: string;
  content: string;
  created_at: string;
  likes_count: number;
  comments_count: number;
  is_owner?: boolean;
  comments?: Comment[];
}

function beltStyle(beltName: string) {
  const normalized = (beltName || "Faixa Branca").toLowerCase().replace("faixa ", "");
  let mappedId: "white" | "yellow" | "green" | "black" = "white";
  
  if (normalized.includes("amarela")) mappedId = "yellow";
  else if (normalized.includes("verde")) mappedId = "green";
  else if (normalized.includes("preta")) mappedId = "black";

  const b = BELTS.find((x) => x.id === mappedId)!;
  return { color: b.color, name: b.name, kanji: b.kanji, id: b.id };
}

function Community() {
  
  const { state } = useDojo();
  const hydrated = useHydrated();
  const myBelt = getCurrentBelt(state.xp);
  
  const [posts, setPosts] = useState<Post[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);

  console.log("POSTS STATE:", posts);
  

  // Estados para controle de modais, respostas e edições
  const [activeCommentPostId, setActiveCommentPostId] = useState<number | null>(null);
  const [commentText, setCommentText] = useState("");
  const [replyingToCommentId, setReplyingToCommentId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState("");

  const [editingPostId, setEditingPostId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");

  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editCommentText, setEditCommentText] = useState("");

const fetchPosts = async () => {
  const token = localStorage.getItem("token");

  try {

    const response = await fetch(
      "https://data-dojo.onrender.com/api/community/posts/",
      {
        method:"GET",
        headers:{
          "Content-Type":"application/json",
          ...(token && {
            Authorization:`Token ${token}`
          })
        }
      }
    );


    if(!response.ok){

      console.error(
        "Erro API:",
        response.status
      );

      setPosts([]);
      return;
    }


    const data = await response.json();


    console.log(
      "API POSTS:",
      data
    );


    let postsArray:Post[]=[];


    if(Array.isArray(data)){
        postsArray=data;
    }

    else if(
      data &&
      Array.isArray(data.results)
    ){
        postsArray=data.results;
    }


    const normalizedPosts = postsArray.map(
      (post:any)=>({

        ...post,

        comments:
          Array.isArray(post.comments)
          ? post.comments
          : [],


        likes_count:
          post.likes_count ?? 0,


        comments_count:
          post.comments_count ?? 0,


        student_name:
          post.student_name ??
          post.user?.username ??
          "Samurai"

      })
    );


    console.log(
      "NORMALIZED POSTS:",
      normalizedPosts
    );


    setPosts(normalizedPosts);


  } catch(error){

    console.error(
      "Falha carregando posts:",
      error
    );

    setPosts([]);

  }

  finally{

    setLoading(false);

  }

};

  useEffect(()=>{

 if(typeof window === "undefined"){
   return;
 }

 const token =
 localStorage.getItem("token");


 if(token){
    fetchPosts();
 }

 else{
    setLoading(false);
 }

},[]);

  const publish = async () => {
    const text = draft.trim();
    if (!text) return;

    try {
      const formData = new FormData();
      formData.append("content", text);
      formData.append("title", "Post da Comunidade");

      const response = await fetch("https://data-dojo.onrender.com/api/community/posts/", {
        method: "POST",
        headers: {
          Authorization: `Token ${localStorage.getItem("token")}`,
        },
        body: formData,
      });

      if (response.ok) {
        setDraft("");
        toast.success("Postagem enviada ao dojô 🥋");
        fetchPosts();
      } else {
        toast.error("Erro ao publicar sua mensagem no painel.");
      }
    } catch (err) {
      console.error("Erro ao publicar post:", err);
    }
  };

  const handleLike = async (postId: number) => {
    try {
      const response = await fetch(`https://data-dojo.onrender.com/api/community/posts/${postId}/like/`, {
        method: "POST",
        headers: {
          Authorization: `Token ${localStorage.getItem("token")}`,
        },
      });

      if (response.ok) {
        const resData = await response.json();
        setPosts(posts.map(p => p.id === postId ? { ...p, likes_count: resData.likes_count } : p));
      }
    } catch (err) {
      console.error("Erro ao curtir postagem:", err);
    }
  };

  // Enviar comentário principal
  const handleSendComment = async (postId: number) => {
    const text = commentText.trim();
    if (!text) return;

    try {
      const response = await fetch("https://data-dojo.onrender.com/api/community/comments/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Token ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          topic: postId,
          content: text,
        }),
      });

      if (response.ok) {
        setCommentText("");
        toast.success("Resposta publicada!");
        fetchPosts();
      } else {
        toast.error("Erro ao publicar comentário.");
      }
    } catch (err) {
      console.error("Erro ao comentar:", err);
    }
  };

  // Enviar resposta a um comentário específico (sub-comentário)
  const handleSendReply = async (postId: number, parentCommentId: number) => {
    const text = replyText.trim();
    if (!text) return;

    try {
      const response = await fetch("https://data-dojo.onrender.com/api/community/comments/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Token ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          topic: postId,
          parent: parentCommentId,
          content: text,
        }),
      });

      if (response.ok) {
        setReplyText("");
        setReplyingToCommentId(null);
        toast.success("Tréplica enviada!");
        fetchPosts();
      } else {
        toast.error("Erro ao responder comentário.");
      }
    } catch (err) {
      console.error("Erro ao responder:", err);
    }
  };

  // Salvar edição de post
  const handleSaveEdit = async (postId: number) => {
    if (!editText.trim()) return;

    try {
      const response = await fetch(`https://data-dojo.onrender.com/api/community/posts/${postId}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Token ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ content: editText }),
      });

      if (response.ok) {
        toast.success("Postagem atualizada!");
        setEditingPostId(null);
        fetchPosts();
      }
    } catch (err) {
      console.error("Erro ao editar postagem:", err);
    }
  };

  // Salvar edição de comentário
  const handleSaveCommentEdit = async (commentId: number) => {
    if (!editCommentText.trim()) return;

    try {
      const response = await fetch(`https://data-dojo.onrender.com/api/community/comments/${commentId}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Token ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ content: editCommentText }),
      });

      if (response.ok) {
        toast.success("Comentário atualizado!");
        setEditingCommentId(null);
        fetchPosts();
      } else {
        toast.error("Erro ao editar comentário.");
      }
    } catch (err) {
      console.error("Erro ao editar comentário:", err);
    }
  };

  const handleDeletePost = async (postId: number) => {
    if (!confirm("Deseja apagar definitivamente esta postagem?")) return;

    try {
      const response = await fetch(`https://data-dojo.onrender.com/api/community/posts/${postId}/`, {
        method: "DELETE",
        headers: {
          Authorization: `Token ${localStorage.getItem("token")}`,
        },
      });

      if (response.ok || response.status === 204) {
        toast.success("Postagem removida do mural.");
        setPosts(posts.filter(p => p.id !== postId));
      }
    } catch (err) {
      console.error("Erro ao deletar postagem:", err);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Toaster position="top-right" theme="dark" richColors />
      <DojoHeader />
      <main className="mx-auto max-w-5xl px-4 py-10">
        <div>
          <div className="text-xs uppercase tracking-[0.25em] text-muted-foreground">Comunidade</div>
          <h1 className="font-display font-extrabold text-4xl mt-1">Salão dos Samurais</h1>
          <p className="text-muted-foreground mt-1">Conquistas, dúvidas e insights de quem trilha o caminho dos dados.</p>
        </div>

        <div className="mt-8 rounded-xl border border-border bg-card p-5">
          <div className="flex items-start gap-3">
            <div
              className="h-10 w-10 rounded-md flex items-center justify-center font-display font-bold text-sm border-2 border-black/40 shrink-0"
              style={{ background: myBelt.color, color: myBelt.id === "black" ? "#FFA500" : "#1C1C1C" }}
            >
              {myBelt.kanji}
            </div>
            <div className="flex-1">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Compartilhe sua conquista, dúvida ou insight Kaizen..."
                className="w-full bg-background border border-border rounded-lg p-3 text-sm resize-none outline-none focus:border-kaizen/60 transition min-h-80px text-white"
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

        <div className="mt-6 space-y-4">
          {loading ? (
            <p className="text-sm text-muted-foreground font-mono">Buscando rolos de pergaminho do servidor...</p>
          ) : posts.length === 0 ? (
            <p className="text-sm text-muted-foreground font-mono">O salão está silencioso. Seja o primeiro a quebrar o silêncio!</p>
          ) : (
            posts.map((p) => {
              const b = beltStyle(p.student_belt || "Faixa Branca");
              const authorName = p.student_name || p.user?.username || "Samurai";
              
              return (
                <article key={p.id} className="rounded-xl border border-border bg-card p-5 relative group transition hover:border-kaizen/20">
                  
                  {p.is_owner && (
                    <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity font-mono text-xs">
                      <button onClick={() => { setEditingPostId(p.id); setEditText(p.content); }} className="text-muted-foreground hover:text-kaizen transition">[editar]</button>
                      <button onClick={() => handleDeletePost(p.id)} className="text-muted-foreground hover:text-destructive transition">[apagar]</button>
                    </div>
                  )}

                  <header className="flex items-center gap-3">
                    <div
                      className="h-11 w-11 rounded-md flex items-center justify-center font-display font-bold border-2 border-black/40 shrink-0"
                      style={{ background: b.color, color: b.id === "black" ? "#FFA500" : "#1C1C1C" }}
                    >
                      {b.kanji}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-display font-semibold text-white">{authorName}</span>
                        {p.student_username && <span className="text-xs font-mono text-muted-foreground">@{p.student_username}</span>}
                        <span
                          className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border"
                          style={{ color: b.color, borderColor: `${b.color}66`, background: `${b.color}10` }}
                        >
                          {b.name}
                        </span>
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-0.5">
                        {new Date(p.created_at).toLocaleDateString("pt-BR", {
                          day: "2-digit",
                          month: "short",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </div>
                  </header>

                  {editingPostId === p.id ? (
                    <div className="mt-3 space-y-2">
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        className="w-full bg-background border border-border rounded-md p-2 text-sm text-white focus:border-kaizen outline-none"
                      />
                      <div className="flex gap-2 justify-end">
                        <button onClick={() => setEditingPostId(null)} className="text-xs px-3 py-1 bg-background border border-border rounded text-white">Cancelar</button>
                        <button onClick={() => handleSaveEdit(p.id)} className="text-xs px-3 py-1 bg-kaizen text-black font-bold rounded">Salvar</button>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-3 text-sm leading-relaxed text-gray-200 whitespace-pre-wrap">{p.content}</p>
                  )}

                  <footer className="mt-4 flex items-center gap-5 text-xs text-muted-foreground border-t border-border/20 pt-3">
                    <button onClick={() => handleLike(p.id)} className="flex items-center gap-1.5 hover:text-destructive text-muted-foreground transition">
                      <span className="text-base leading-none">❤️</span>
                      <span className="font-mono">{p.likes_count}</span>
                    </button>
                    <button 
                      onClick={() => setActiveCommentPostId(activeCommentPostId === p.id ? null : p.id)} 
                      className="flex items-center gap-1.5 hover:text-white text-muted-foreground transition"
                    >
                      <span className="text-base leading-none">💬</span>
                      <span className="font-mono">{p.comments_count}</span>
                    </button>
                  </footer>

                  {/* Seção de Comentários */}
                  {activeCommentPostId === p.id && (
                    <div className="mt-4 border-t border-border/40 pt-4 space-y-3">
                      <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                        {Array.isArray(p.comments) && p.comments.length > 0 ? (
                          p.comments.map((c) => {
                            const commentAuthor = c.student_name || (typeof c.user === 'object' ? c.user?.username : c.user) || "Samurai";
                            
                            return (
                              <div key={c.id} className="text-xs bg-background/40 rounded-lg p-3 border border-border/40 space-y-2">
                                <div className="flex justify-between items-start">
                                  <div>
                                    <span className="font-bold text-kaizen block">{commentAuthor}</span>
                                    <span className="text-[10px] text-muted-foreground">
                                      {new Date(c.created_at).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                                    </span>
                                  </div>
                                  
                                  {c.is_owner && (
                                    <button 
                                      onClick={() => { setEditingCommentId(c.id); setEditCommentText(c.content); }} 
                                      className="text-[10px] text-muted-foreground hover:text-kaizen font-mono"
                                    >
                                      [editar]
                                    </button>
                                  )}
                                </div>

                                {/* Edição de Comentário */}
                                {editingCommentId === c.id ? (
                                  <div className="space-y-2 pt-1">
                                    <input
                                      type="text"
                                      value={editCommentText}
                                      onChange={(e) => setEditCommentText(e.target.value)}
                                      className="w-full bg-background border border-border rounded px-2 py-1 text-xs text-white outline-none focus:border-kaizen"
                                    />
                                    <div className="flex gap-2 justify-end">
                                      <button onClick={() => setEditingCommentId(null)} className="text-[10px] px-2 py-0.5 border border-border rounded text-white">Cancelar</button>
                                      <button onClick={() => handleSaveCommentEdit(c.id)} className="text-[10px] px-2 py-0.5 bg-kaizen text-black font-bold rounded">Salvar</button>
                                    </div>
                                  </div>
                                ) : (
                                  <p className="text-gray-300">{c.content}</p>
                                )}

                                {/* Botão para responder a este comentário específico */}
                                <div className="pt-1">
                                  <button 
                                    onClick={() => setReplyingToCommentId(replyingToCommentId === c.id ? null : c.id)}
                                    className="text-[10px] text-muted-foreground hover:text-white font-mono flex items-center gap-1"
                                  >
                                    ↳ Responder
                                  </button>
                                </div>

                                {/* Caixa de input para sub-resposta */}
                                {replyingToCommentId === c.id && (
                                  <div className="flex gap-2 pt-2 pl-4 border-l-2 border-kaizen/30 mt-2">
                                    <input
                                      type="text"
                                      placeholder="Escreva sua resposta..."
                                      value={replyText}
                                      onChange={(e) => setReplyText(e.target.value)}
                                      onKeyDown={(e) => e.key === 'Enter' && handleSendReply(p.id, c.id)}
                                      className="flex-1 bg-background border border-border rounded px-2 py-1 text-xs text-white outline-none focus:border-kaizen"
                                    />
                                    <button 
                                      onClick={() => handleSendReply(p.id, c.id)}
                                      disabled={!replyText.trim()}
                                      className="bg-kaizen text-black px-3 py-1 rounded text-[10px] font-bold uppercase disabled:opacity-40"
                                    >
                                      Enviar
                                    </button>
                                  </div>
                                )}
                              </div>
                            );
                          })
                        ) : (
                          <p className="text-[11px] text-muted-foreground font-mono">Nenhuma resposta ainda. Seja o primeiro!</p>
                        )}
                      </div>
                      
                      {/* Input para Comentário Principal */}
                      <div className="flex gap-2 pt-2">
                        <input
                          type="text"
                          placeholder="Digite seu comentário e pressione Enter..."
                          value={commentText}
                          onChange={(e) => setCommentText(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleSendComment(p.id)}
                          className="flex-1 bg-background border border-border rounded px-3 py-1.5 text-xs text-white outline-none focus:border-kaizen/60"
                        />
                        <button 
                          onClick={() => handleSendComment(p.id)} 
                          disabled={!commentText.trim()} 
                          className="bg-destructive text-white px-4 py-1 rounded text-xs font-bold font-display uppercase tracking-wider disabled:opacity-40"
                        >
                          Comentar
                        </button>
                      </div>
                    </div>
                  )}

                </article>
              );
            })
          )}
        </div>
      </main>
    </div>
  );
}