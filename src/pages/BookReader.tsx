import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ReaderSidebar } from "@/components/library/ReaderSidebar";
import { NarratorControls } from "@/components/library/NarratorControls";
import { FlowReader } from "@/components/library/FlowReader";
import { clearNarratorHighlight, restoreHighlights, selectedRange, setNarratorHighlight } from "@/components/library/reader-selection";
import { bookUrl, errorMessage, type Page, type Progress, type ReadingMark, type ReaderMetadata } from "@/components/library/library-api";
import "@/components/library/reader.css";

const PdfReader = lazy(() => import("@/components/library/PdfReader"));

export default function BookReader({ bookId }: { bookId: number }) {
  const metadata = useQuery({ queryKey: ["reader-metadata", bookId], queryFn: async () => (await api.get<ReaderMetadata>(`${bookUrl(bookId)}reader/`)).data, staleTime: 0 });
  if (metadata.isLoading) return <main className="p-8" role="status">Abrindo livro…</main>;
  if (metadata.isError || !metadata.data) return <main className="space-y-4 p-8"><Link to="/library">← Biblioteca</Link><p role="alert">{errorMessage(metadata.error)}</p><Button onClick={() => void metadata.refetch()}>Tentar novamente</Button></main>;
  return <ReaderSession key={bookId} metadata={metadata.data} />;
}

function ReaderSession({ metadata }: { metadata: ReaderMetadata }) {
  const { book, total, automatic_toc: automaticToc } = metadata; const pdf = book.format === "pdf";
  const [toc, setToc] = useState(metadata.toc); const [tocMode, setTocMode] = useState(metadata.toc_mode);
  const positions = pdf ? Array.from({ length: total }, (_, i) => i + 1) : automaticToc.map(e => e.position);
  const initial = positions.includes(book.reading?.position ?? 1) ? book.reading?.position ?? 1 : positions[0] ?? 1;
  const [position, setPosition] = useState(initial); const [offset, setOffset] = useState(book.reading?.offset ?? 0);
  const [zoom, setZoom] = useState(1); const [fontSize, setFontSize] = useState(19); const [fitPage, setFitPage] = useState(false);
  const [focus, setFocus] = useState(false); const [sidebar, setSidebar] = useState(false); const [width, setWidth] = useState(900);
  const [error, setError] = useState(""); const [saved, setSaved] = useState(""); const [marksPage, setMarksPage] = useState(1);
  const root = useRef<HTMLDivElement>(null); const viewport = useRef<HTMLDivElement>(null); const content = useRef<HTMLDivElement>(null);
  const restoreOffset = useRef<number | null>(book.reading?.offset ?? 0); const mounted = useRef(true);
  const pending = useRef<Progress | null>(null); const timer = useRef<ReturnType<typeof setTimeout> | null>(null); const queue = useRef(Promise.resolve());
  const client = useQueryClient();
  useEffect(() => {
    setToc(metadata.toc);
    setTocMode(metadata.toc_mode);
  }, [metadata.toc, metadata.toc_mode]);
  const updateToc = useCallback((entries: typeof metadata.toc, mode: typeof metadata.toc_mode) => {
    setToc(entries);
    setTocMode(mode);
    client.setQueryData<ReaderMetadata>(["reader-metadata", book.id], current =>
      current ? { ...current, toc: entries, toc_mode: mode } : current,
    );
  }, [book.id, client]);
  const marks = useQuery({ queryKey: ["reader-marks", book.id, marksPage], queryFn: async () => (await api.get<Page<ReadingMark>>(`${bookUrl(book.id)}marks/`, { params: { page: marksPage, page_size: 100 } })).data });
  const flush = useCallback(() => {
    const value = pending.current; if (!value) return; pending.current = null;
    queue.current = queue.current.then(async () => {
      try { await api.put(`${bookUrl(book.id)}progress/`, value); await client.invalidateQueries({ queryKey: ["library-books"] }); if (mounted.current) setSaved("Posição salva"); }
      catch (e) { if (mounted.current) { setError(errorMessage(e)); setSaved("Posição não salva"); pending.current = value; } }
    });
  }, [book.id, client]);
  const schedule = useCallback((newPosition: number, newOffset: number) => {
    const index = positions.indexOf(newPosition); const entry = automaticToc.find(e => e.position === newPosition);
    pending.current = { position: newPosition, location: entry?.location ?? `page:${newPosition}`, offset: newOffset, progress_percentage: Math.min(100, ((index + (pdf ? 1 : newOffset)) / Math.max(total, 1)) * 100) };
    setSaved("Salvando…"); if (timer.current) clearTimeout(timer.current); timer.current = setTimeout(flush, 700);
  }, [positions, automaticToc, total, pdf, flush]);
  useEffect(() => { mounted.current = true; const hide = () => { if (document.visibilityState === "hidden") flush(); }; document.addEventListener("visibilitychange", hide); return () => { mounted.current = false; document.removeEventListener("visibilitychange", hide); if (timer.current) clearTimeout(timer.current); flush(); }; }, [flush]);
  useEffect(() => { if (!viewport.current) return; const observer = new ResizeObserver(entries => setWidth(entries[0].contentRect.width)); observer.observe(viewport.current); return () => observer.disconnect(); }, []);
  const navigate = useCallback((next: number, newOffset = 0) => { if (!positions.includes(next)) return; restoreOffset.current = newOffset; setPosition(next); setOffset(newOffset); schedule(next, newOffset); }, [positions, schedule]);
  const previous = () => navigate(positions[Math.max(0, positions.indexOf(position) - 1)]);
  const next = () => navigate(positions[Math.min(positions.length - 1, positions.indexOf(position) + 1)]);
  const fullScreen = async () => { setFocus(true); try { if (document.fullscreenElement) await document.exitFullscreen(); else if (root.current?.requestFullscreen) await root.current.requestFullscreen(); } catch { setSaved("Modo foco ativado; tela cheia indisponível neste navegador."); } };
  const resize = (amount: number) => pdf ? setZoom(value => Math.max(.5, Math.min(3, value + amount))) : setFontSize(value => Math.max(12, Math.min(36, value + amount * 10)));
  useEffect(() => { const key = (e: KeyboardEvent) => { if ((e.target as HTMLElement).closest("input,textarea,select,[contenteditable=true]") || e.ctrlKey || e.altKey || e.metaKey) return; if (e.key === "ArrowLeft") { e.preventDefault(); previous(); } if (e.key === "ArrowRight") { e.preventDefault(); next(); } if (e.key === "+" || e.key === "=") resize(.1); if (e.key === "-") resize(-.1); if (e.key.toLowerCase() === "f") void fullScreen(); }; window.addEventListener("keydown", key); return () => window.removeEventListener("keydown", key); });
  const rendered = useCallback(() => { requestAnimationFrame(() => { if (viewport.current && restoreOffset.current !== null) { viewport.current.scrollTop = restoreOffset.current * Math.max(0, viewport.current.scrollHeight - viewport.current.clientHeight); restoreOffset.current = null; } const target = content.current?.querySelector<HTMLElement>(pdf ? ".react-pdf__Page__textContent" : "[data-reader-text]"); restoreHighlights(target ?? null, marks.data?.results.filter(m => m.position === position) ?? []); }); }, [pdf, marks.data, position]);
  useEffect(() => { rendered(); }, [rendered]);
  async function mark(kind: ReadingMark["kind"]) {
    const target = content.current?.querySelector<HTMLElement>(pdf ? ".react-pdf__Page__textContent" : "[data-reader-text]");
    const selection = selectedRange(target ?? null);
    if (kind === "highlight" && !selection) { setError("Selecione um trecho do texto. PDFs escaneados sem camada textual não permitem seleção."); return; }
    const note = kind === "annotation" ? window.prompt("Sua anotação") : kind === "bookmark" ? window.prompt("Nome do marcador (opcional)", "") : "";
    if (note === null) return;
    try { await api.post(`${bookUrl(book.id)}marks/`, { kind, position, offset, location: automaticToc.find(e => e.position === position)?.location ?? `page:${position}`, note, ...selection }); await client.invalidateQueries({ queryKey: ["reader-marks", book.id] }); setError(""); } catch (e) { setError(errorMessage(e)); }
  }
  async function changeMark(mark: ReadingMark, note?: string) { try { if (note === undefined) await api.delete(`${bookUrl(book.id)}marks/${mark.id}/`); else await api.patch(`${bookUrl(book.id)}marks/${mark.id}/`, { note }); await client.invalidateQueries({ queryKey: ["reader-marks", book.id] }); } catch (e) { setError(errorMessage(e)); } }
  function internalLink(href: string) { const current = automaticToc.find(e => e.position === position); const base = new URL(current?.location || "", "https://reader.invalid/"); const resolved = new URL(href, base); const entry = automaticToc.find(e => `/${e.location}` === decodeURIComponent(resolved.pathname)); if (entry) { navigate(entry.position); if (resolved.hash && entry.position === position) content.current?.querySelector(`#${CSS.escape(decodeURIComponent(resolved.hash.slice(1)))}`)?.scrollIntoView(); } }
  const visibleReaderText = useCallback(() => {
    const target = content.current?.querySelector<HTMLElement>(pdf ? ".react-pdf__Page__textContent" : "[data-reader-text]");
    return target?.innerText || target?.textContent || "";
  }, [pdf]);
  const highlightNarration = useCallback((start: number, end: number) => {
    const target = content.current?.querySelector<HTMLElement>(pdf ? ".react-pdf__Page__textContent" : "[data-reader-text]");
    setNarratorHighlight(target ?? null, start, end);
  }, [pdf]);
  const clearNarration = useCallback(() => clearNarratorHighlight(), []);
  return <div ref={root} className="flex h-dvh flex-col bg-background text-foreground">
    <header className="space-y-3 border-b bg-card p-3 md:px-6"><div className="flex flex-wrap items-center justify-between gap-2"><Link to="/library" className="text-primary" onClick={flush}>← Biblioteca</Link><div className="min-w-0 flex-1 px-3"><h1 className={`truncate font-display font-bold ${focus ? "text-sm" : "text-xl"}`}>{book.title}</h1>{!focus && <p className="text-sm text-muted-foreground">{book.author}</p>}</div><Button size="sm" variant="outline" onClick={() => setFocus(!focus)}>{focus ? "Sair do foco" : "Modo leitura"}</Button><Button size="sm" onClick={() => void fullScreen()}>Tela cheia</Button></div>
    <div className="flex flex-wrap items-center gap-2"><Button size="sm" variant="outline" onClick={() => setSidebar(!sidebar)}>Índice / Busca / Notas</Button><Button size="sm" disabled={positions.indexOf(position) <= 0} onClick={previous}>← Anterior</Button><label className="flex items-center gap-1 text-sm">{pdf ? "Página" : book.format === "epub" ? "Capítulo" : "Seção"}<select aria-label="Posição atual" className="max-w-44 rounded border bg-background p-1" value={position} onChange={e => navigate(Number(e.target.value))}>{positions.map((p, index) => <option key={p} value={p}>{index + 1}{!pdf && ` · ${automaticToc.find(e => e.position === p)?.title || ""}`}</option>)}</select> / {total}</label><Button size="sm" disabled={positions.indexOf(position) >= positions.length - 1} onClick={next}>Próxima →</Button><Button size="sm" aria-label="Diminuir zoom ou fonte" variant="outline" onClick={() => resize(-.1)}>−</Button><span className="text-xs">{pdf ? `${Math.round(zoom * 100)}%` : `${fontSize}px`}</span><Button size="sm" aria-label="Aumentar zoom ou fonte" variant="outline" onClick={() => resize(.1)}>+</Button>{pdf && <><Button size="sm" variant="outline" onClick={() => { setFitPage(false); setZoom(1); }}>Largura</Button><Button size="sm" variant="outline" onClick={() => { setFitPage(true); setZoom(1); }}>Página inteira</Button></>}<Button size="sm" variant="outline" onClick={() => void mark("bookmark")}>Marcar</Button><Button size="sm" variant="outline" onMouseDown={e => e.preventDefault()} onClick={() => void mark("annotation")}>Anotar</Button><Button size="sm" variant="outline" onMouseDown={e => e.preventDefault()} onClick={() => void mark("highlight")}>Destacar</Button></div>
    {!focus && <p className="text-xs text-muted-foreground">← → navegar · + − zoom/fonte · F tela cheia · Esc sai da tela cheia. {pdf && "A busca também consulta o OCR. Seleção depende da camada textual do PDF."}</p>}
    {!focus && <NarratorControls bookId={book.id} position={position} total={total} onNavigate={navigate} getVisibleText={visibleReaderText} onHighlight={highlightNarration} onClearHighlight={clearNarration} />}
    {error && <p role="alert" className="text-sm text-destructive">{error}<Button size="sm" variant="ghost" onClick={flush}>Salvar novamente</Button></p>}<p role="status" className="text-xs text-muted-foreground">{saved || (book.reading ? "Continuando de onde você parou" : "")}</p></header>
    <div className="flex min-h-0 flex-1 flex-col md:flex-row">{sidebar && !focus && <div className="max-h-[40vh] overflow-auto md:max-h-none"><ReaderSidebar bookId={book.id} total={total} toc={toc} tocMode={tocMode} marks={marks.data?.results ?? []} onNavigate={navigate} onDelete={mark => void changeMark(mark)} onEdit={(mark, note) => void changeMark(mark, note)} onTocChange={updateToc} />{marks.isError && <p role="alert">Não foi possível carregar marcações.</p>}{(marks.data?.next || marksPage > 1) && <div className="flex gap-2 p-3"><Button disabled={marksPage === 1} onClick={() => setMarksPage(marksPage - 1)}>Anteriores</Button><Button disabled={!marks.data?.next} onClick={() => setMarksPage(marksPage + 1)}>Mais marcações</Button></div>}</div>}
    <div ref={viewport} className="min-w-0 flex-1 overflow-auto bg-secondary/20" onScroll={e => { if (restoreOffset.current !== null) return; const element = e.currentTarget; const value = element.scrollTop / Math.max(1, element.scrollHeight - element.clientHeight); setOffset(value); if (!pdf) schedule(position, value); }}><div ref={content} className={pdf ? "mx-auto w-fit p-4" : "w-full"}>
    {pdf ? <Suspense fallback={<p>Preparando leitor PDF…</p>}><PdfReader url={metadata.file_url} page={position} zoom={zoom} width={width} fitPage={fitPage} onRendered={rendered} /></Suspense> : <FlowReader bookId={book.id} position={position} fontSize={fontSize} onRendered={rendered} onLink={internalLink} />}
    </div></div></div>
  </div>;
}
