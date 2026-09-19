import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { bookUrl, errorMessage, type ReadingMark, type TocEntry, type TocMode } from "./library-api";

type DraftEntry = { title: string; position: number };

export function ReaderSidebar({
  bookId,
  total,
  toc,
  tocMode,
  marks,
  onNavigate,
  onDelete,
  onEdit,
  onTocChange,
}: {
  bookId: number;
  total: number;
  toc: TocEntry[];
  tocMode: TocMode;
  marks: ReadingMark[];
  onNavigate: (position: number, offset?: number) => void;
  onDelete: (mark: ReadingMark) => void;
  onEdit: (mark: ReadingMark, note: string) => void;
  onTocChange: (entries: TocEntry[], mode: TocMode) => void;
}) {
  const [tab, setTab] = useState("toc");
  const [term, setTerm] = useState("");
  const [search, setSearch] = useState("");
  const [editingToc, setEditingToc] = useState(false);
  const [draft, setDraft] = useState<DraftEntry[]>([]);
  const [tocError, setTocError] = useState("");
  const [savingToc, setSavingToc] = useState(false);

  useEffect(() => {
    if (editingToc && tocMode === "manual") {
      setDraft(toc.map(entry => ({ title: entry.title, position: entry.position })));
    }
  }, [toc, tocMode, editingToc]);

  const query = useQuery({
    queryKey: ["reader-search", bookId, search],
    enabled: search.length >= 2,
    queryFn: async () => (
      await api.get<{
        count: number;
        results: { position: number; location: string; title: string; snippet: string; offset: number }[];
      }>(`${bookUrl(bookId)}search/`, { params: { q: search } })
    ).data,
  });

  function beginTocEdit() {
    setTocError("");
    setDraft(
      tocMode === "manual" && toc.length
        ? toc.map(entry => ({ title: entry.title, position: entry.position }))
        : [{ title: "Novo item", position: 1 }],
    );
    setEditingToc(true);
  }

  function updateDraft(index: number, values: Partial<DraftEntry>) {
    setDraft(current => current.map((entry, i) => i === index ? { ...entry, ...values } : entry));
  }

  function moveDraft(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= draft.length) return;
    setDraft(current => {
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  async function saveToc() {
    setTocError("");
    setSavingToc(true);
    try {
      const response = await api.put<{ mode: TocMode; entries: TocEntry[] }>(
        `${bookUrl(bookId)}toc/`,
        { entries: draft.map(entry => ({ title: entry.title.trim(), position: entry.position })) },
      );
      onTocChange(response.data.entries, response.data.mode);
      setEditingToc(false);
    } catch (error) {
      setTocError(errorMessage(error));
    } finally {
      setSavingToc(false);
    }
  }

  async function restoreAutomaticToc() {
    if (!window.confirm("Remover o índice manual e voltar ao índice automático?")) return;
    setTocError("");
    setSavingToc(true);
    try {
      const response = await api.delete<{ mode: TocMode; entries: TocEntry[] }>(`${bookUrl(bookId)}toc/`);
      onTocChange(response.data.entries, response.data.mode);
      setEditingToc(false);
      setDraft([]);
    } catch (error) {
      setTocError(errorMessage(error));
    } finally {
      setSavingToc(false);
    }
  }

  return (
    <aside aria-label="Painel de leitura" className="w-full shrink-0 space-y-4 overflow-auto border-r bg-card p-4 md:w-80">
      <nav className="flex flex-wrap gap-2">
        {[["toc", "Índice"], ["search", "Busca"], ["marks", "Marcações"]].map(([value, label]) => (
          <Button size="sm" key={value} variant={tab === value ? "default" : "outline"} onClick={() => setTab(value)}>
            {label}
          </Button>
        ))}
      </nav>

      {tab === "toc" && (
        <div className="space-y-3">
          {!editingToc && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" variant="outline" onClick={beginTocEdit}>
                  {tocMode === "manual" ? "Editar índice" : "Criar índice manual"}
                </Button>
                {tocMode === "manual" && (
                  <Button size="sm" variant="ghost" disabled={savingToc} onClick={() => void restoreAutomaticToc()}>
                    Voltar ao automático
                  </Button>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {tocMode === "manual" ? "Índice manual salvo." : "Índice automático gerado pelo conteúdo processado."}
              </p>
              <ol className="space-y-2">
                {toc.map(entry => (
                  <li key={entry.id ?? `${entry.position}-${entry.title}`}>
                    <button className="text-left text-sm text-primary hover:underline" onClick={() => onNavigate(entry.position)}>
                      {entry.title}
                    </button>
                  </li>
                ))}
              </ol>
            </>
          )}

          {editingToc && (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground">
                O índice manual não altera o arquivo original, o OCR ou os chunks. Cada item aponta para uma página/seção real do documento.
              </p>

              {draft.map((entry, index) => (
                <div key={index} className="space-y-2 rounded border p-2">
                  <Input
                    aria-label={`Título do item ${index + 1}`}
                    value={entry.title}
                    maxLength={500}
                    onChange={event => updateDraft(index, { title: event.target.value })}
                    placeholder="Título do capítulo ou seção"
                  />
                  <div className="flex items-center gap-2">
                    <Input
                      aria-label={`Página ou seção do item ${index + 1}`}
                      type="number"
                      min={1}
                      max={total}
                      value={entry.position}
                      onChange={event => updateDraft(index, { position: Number(event.target.value) })}
                    />
                    <Button size="sm" variant="outline" disabled={index === 0} onClick={() => moveDraft(index, -1)}>↑</Button>
                    <Button size="sm" variant="outline" disabled={index === draft.length - 1} onClick={() => moveDraft(index, 1)}>↓</Button>
                    <Button size="sm" variant="ghost" disabled={draft.length === 1} onClick={() => setDraft(current => current.filter((_, i) => i !== index))}>Excluir</Button>
                  </div>
                </div>
              ))}

              <Button
                size="sm"
                variant="outline"
                onClick={() => setDraft(current => [...current, { title: "Novo item", position: Math.min(total, (current.at(-1)?.position ?? 0) + 1) || 1 }])}
              >
                + Adicionar item
              </Button>

              {tocError && <p role="alert" className="text-sm text-destructive">{tocError}</p>}

              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  disabled={savingToc || draft.some(entry => !entry.title.trim() || entry.position < 1 || entry.position > total)}
                  onClick={() => void saveToc()}
                >
                  {savingToc ? "Salvando…" : "Salvar índice"}
                </Button>
                <Button size="sm" variant="ghost" disabled={savingToc} onClick={() => { setEditingToc(false); setTocError(""); }}>
                  Cancelar
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {tab === "search" && (
        <>
          <form className="flex gap-2" onSubmit={event => { event.preventDefault(); setSearch(term.trim()); }}>
            <Input aria-label="Buscar no livro" value={term} onChange={event => setTerm(event.target.value)} />
            <Button type="submit">Buscar</Button>
          </form>
          {query.isFetching && <p>Buscando…</p>}
          {query.isError && <p role="alert">Não foi possível buscar.</p>}
          {query.data && <p>{query.data.count} seções/páginas encontradas{query.data.count > 100 && " · mostrando as primeiras 100"}</p>}
          <ul className="space-y-3">
            {query.data?.results.map(result => (
              <li key={result.position}>
                <button className="rounded border p-3 text-left text-sm" onClick={() => onNavigate(result.position, result.offset)}>
                  <strong>{result.title}</strong>
                  <p>{result.snippet}</p>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {tab === "marks" && (
        <>
          <p className="text-xs text-muted-foreground">Selecione texto e use “Destacar” ou “Anotar”.</p>
          {marks.length === 0 && <p>Você ainda não tem marcações.</p>}
          {marks.map(mark => (
            <article key={mark.id} className="space-y-2 rounded border p-3 text-sm">
              <button className="text-primary" onClick={() => onNavigate(mark.position, mark.offset)}>
                {mark.kind === "bookmark" ? "Marcador" : mark.kind === "annotation" ? "Anotação" : "Destaque"} · {mark.position}
              </button>
              {mark.selected_text && <blockquote className="border-l-2 pl-2">{mark.selected_text}</blockquote>}
              <p>{mark.note}</p>
              <div className="flex gap-2">
                {mark.kind !== "highlight" && (
                  <Button size="sm" variant="outline" onClick={() => {
                    const value = window.prompt("Texto da marcação", mark.note);
                    if (value !== null) onEdit(mark, value);
                  }}>
                    Editar
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={() => onDelete(mark)}>Excluir</Button>
              </div>
            </article>
          ))}
        </>
      )}
    </aside>
  );
}
