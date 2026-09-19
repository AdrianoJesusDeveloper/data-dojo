import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PrivateImage } from "@/components/library/PrivateImage";
import { bookUrl, errorMessage, uploadFile, type LibraryBook, type Page } from "@/components/library/library-api";

export default function Library() {
  const client = useQueryClient();
  const [search, setSearch] = useState(""); const [term, setTerm] = useState("");
  const [page, setPage] = useState(1); const [grid, setGrid] = useState(true);
  const [format, setFormat] = useState(""); const [status, setStatus] = useState("");
  const [category, setCategory] = useState(""); const [favorite, setFavorite] = useState(false);
  const [lifecycle, setLifecycle] = useState("active"); const [error, setError] = useState("");
  const [busy, setBusy] = useState(false); const [cover, setCover] = useState<{ book: LibraryBook; file: File; url: string } | null>(null);
  useEffect(() => { const timer = setTimeout(() => { setTerm(search); setPage(1); }, 350); return () => clearTimeout(timer); }, [search]);
  useEffect(() => () => { if (cover) URL.revokeObjectURL(cover.url); }, [cover]);
  const query = useQuery({ queryKey: ["library-books", term, page, format, status, category, favorite, lifecycle], queryFn: async () => (await api.get<Page<LibraryBook>>("/api/library/catalog/books/", { params: { search: term, page, format, status, category, favorite, lifecycle } })).data, refetchInterval: (q) => q.state.data?.results.some(b => b.status === "processing") ? 5000 : false });
  async function act(action: () => Promise<unknown>) {
    setBusy(true); setError("");
    try { await action(); await client.invalidateQueries({ queryKey: ["library-books"] }); }
    catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  function filter(setter: (value: string) => void, value: string) { setter(value); setPage(1); }
  return <main className="min-h-screen bg-background text-foreground"><div className="mx-auto max-w-7xl space-y-6 p-4 md:p-8">
    <header className="flex flex-wrap items-center justify-between gap-4"><div><Link to="/content-studio" className="text-sm text-primary">← Dojô / Acervo</Link><h1 className="mt-3 font-display text-3xl font-bold">Biblioteca do Sensei</h1><p className="text-muted-foreground">Seu acervo, suas leituras e descobertas.</p></div><div className="flex gap-2"><Link to="/library/media" className="rounded-md border p-2">Banco de imagens</Link><label className="cursor-pointer rounded-md bg-primary p-2 text-primary-foreground">Adicionar livro<input aria-label="Adicionar livro" type="file" accept=".pdf,.epub,.docx,.txt" className="sr-only" disabled={busy} onChange={e => { const file = e.target.files?.[0]; if (file) void act(() => uploadFile("/api/library/books/", file, { title: file.name.replace(/\.[^.]+$/, "") })); e.target.value = ""; }} /></label></div></header>
    <div className="flex flex-wrap gap-3 rounded-xl border bg-card p-4">
      <Input aria-label="Buscar título ou autor" placeholder="Buscar título ou autor" value={search} onChange={e => setSearch(e.target.value)} className="max-w-sm" />
      <select aria-label="Formato" value={format} onChange={e => filter(setFormat, e.target.value)} className="rounded border bg-background p-2"><option value="">Todos os formatos</option>{["pdf", "epub", "docx", "txt"].map(v => <option key={v}>{v}</option>)}</select>
      <select aria-label="Status" value={status} onChange={e => filter(setStatus, e.target.value)} className="rounded border bg-background p-2"><option value="">Todos os processamentos</option><option value="ready">Pronto</option><option value="uploaded">Aguardando</option><option value="processing">Processando</option><option value="error">Falhou</option></select>
      <Input aria-label="Categoria" placeholder="Categoria" value={category} onChange={e => filter(setCategory, e.target.value)} className="max-w-40" />
      <select aria-label="Situação" value={lifecycle} onChange={e => filter(setLifecycle, e.target.value)} className="rounded border bg-background p-2"><option value="active">Ativos</option><option value="archived">Arquivados</option><option value="discarded">Descartados</option><option value="all">Todos</option></select>
      <label className="flex items-center gap-2"><input type="checkbox" checked={favorite} onChange={e => { setFavorite(e.target.checked); setPage(1); }} />Favoritos</label><Button variant="outline" onClick={() => setGrid(!grid)}>{grid ? "Ver lista" : "Ver grade"}</Button>
    </div>
    {(error || query.isError) && <p role="alert" className="rounded border border-destructive p-4">{error || errorMessage(query.error)}</p>}
    {query.isLoading && <p role="status">Carregando biblioteca…</p>}
    {query.data?.count === 0 && <p className="p-10 text-center text-muted-foreground">Nenhum livro encontrado. Adicione um livro ou processe uma fonte no acervo.</p>}
    <div className={grid ? "grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" : "space-y-4"}>{query.data?.results.map(book => <article key={book.id} className={`overflow-hidden rounded-xl border bg-card ${grid ? "" : "flex flex-wrap"}`}>
      <PrivateImage url={book.cover_url} title={book.title} className={grid ? "h-60 w-full object-contain" : "h-44 w-32 shrink-0 object-contain"} />
      <div className="min-w-0 flex-1 space-y-3 p-4"><div className="flex items-start justify-between gap-2"><h2 className="font-display text-lg font-bold">{book.title}</h2><Button size="sm" variant="ghost" aria-label={`${book.is_favorite ? "Remover favorito" : "Favoritar"}: ${book.title}`} disabled={busy} onClick={() => void act(() => api.patch(bookUrl(book.id), { is_favorite: !book.is_favorite }))}>{book.is_favorite ? "★" : "☆"}</Button></div><p className="text-sm text-muted-foreground">{book.author || "Autor não informado"} · {book.format.toUpperCase()}</p><p className="text-xs">{book.category || "Sem categoria"} · {({ AVAILABLE: "Disponível", PROCESSING: "Processando", MISSING: "Arquivo ausente", UNSUPPORTED: "Não suportado", FAILED: "Falhou", WAITING: "Aguardando", ARCHIVED: "Arquivado", DISCARDED: "Descartado" } as Record<string, string>)[book.availability]}</p>
      {book.status === "processing" && <div><progress className="w-full" value={book.progress_percent} max={100} /><p className="text-xs">{book.progress_percent}% · {book.progress_stage || "Aguardando fila"}</p></div>}
      {book.message && <p className="text-sm text-muted-foreground">{book.message}</p>}
      <p className="text-sm">{Math.round(book.reading?.progress_percentage ?? 0)}% lido</p><div className="flex flex-wrap gap-2">
      {book.availability === "AVAILABLE" ? <Link to="/library/books/$bookId/read" params={{ bookId: String(book.id) }} className="rounded bg-primary px-3 py-2 text-sm text-primary-foreground">{book.reading ? "Continuar de onde parou" : "Abrir livro"}</Link> : book.lifecycle === "active" && book.status !== "processing" && <Button size="sm" disabled={busy} onClick={() => void act(() => api.post(`${bookUrl(book.id)}process/`))}>Processar</Button>}
      <Button size="sm" variant="outline" disabled={busy} onClick={() => { const title = window.prompt("Título", book.title); if (!title) return; const author = window.prompt("Autor", book.author); if (author === null) return; const category = window.prompt("Categoria", book.category); if (category !== null) void act(() => api.patch(bookUrl(book.id), { title, author, category })); }}>Editar</Button>
      <label className="cursor-pointer rounded border p-2 text-xs">Trocar capa<input aria-label={`Capa de ${book.title}`} type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" onChange={e => { const file = e.target.files?.[0]; if (file) setCover({ book, file, url: URL.createObjectURL(file) }); e.target.value = ""; }} /></label>
      {book.lifecycle === "active" ? <><Button size="sm" variant="outline" disabled={busy} onClick={() => void act(() => api.patch(bookUrl(book.id), { lifecycle: "archived" }))}>Arquivar</Button><Button size="sm" variant="outline" disabled={busy} onClick={() => void act(() => api.patch(bookUrl(book.id), { lifecycle: "discarded" }))}>Descartar</Button></> : <Button size="sm" disabled={busy} onClick={() => void act(() => api.patch(bookUrl(book.id), { lifecycle: "active" }))}>Restaurar</Button>}
      <Button size="sm" variant="ghost" disabled={busy} onClick={() => { const confirmation = window.prompt(`Exclusão definitiva do registro. Para confirmar, digite EXCLUIR ${book.id}. Livros com histórico devem ser arquivados.`); if (confirmation) void act(() => api.delete(bookUrl(book.id), { data: { confirmation } })); }}>Excluir…</Button></div></div>
    </article>)}</div>
    {query.data && <nav aria-label="Paginação" className="flex items-center justify-center gap-4"><Button disabled={!query.data.previous || query.isFetching} onClick={() => setPage(page - 1)}>Anterior</Button><span>{page} / {Math.max(1, Math.ceil(query.data.count / 24))} · {query.data.count} livros</span><Button disabled={!query.data.next || query.isFetching} onClick={() => setPage(page + 1)}>Próxima</Button></nav>}
    {cover && <div role="dialog" aria-modal="true" aria-label="Prévia da capa" className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"><div className="space-y-4 rounded-xl bg-background p-6"><img src={cover.url} alt="Prévia da nova capa" className="max-h-80 max-w-full" /><Button disabled={busy} onClick={() => void act(async () => { await uploadFile(`${bookUrl(cover.book.id)}cover/`, cover.file); setCover(null); })}>Salvar capa</Button><Button variant="outline" onClick={() => setCover(null)}>Cancelar</Button></div></div>}
  </div></main>;
}
