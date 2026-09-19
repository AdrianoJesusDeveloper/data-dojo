import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { bookUrl, errorMessage } from "./library-api";

export function FlowReader({ bookId, position, fontSize, onRendered, onLink }: { bookId: number; position: number; fontSize: number; onRendered: () => void; onLink: (href: string) => void }) {
  const query = useQuery({ queryKey: ["reader-section", bookId, position], queryFn: async () => (await api.get<{ html: string; text: string }>(`${bookUrl(bookId)}sections/${position}/`)).data });
  useEffect(() => { if (query.data) onRendered(); }, [query.data, onRendered]);
  if (query.isLoading) return <p role="status">Carregando seção…</p>;
  if (query.isError) return <p role="alert">{errorMessage(query.error)}</p>;
  // HTML comes exclusively from the backend allowlist converter, never from the book directly.
  return <article className="reader-prose mx-auto max-w-[75ch] p-6 leading-relaxed" style={{ fontSize }} onClick={e => { const anchor = (e.target as Element).closest("[data-reader-href]"); if (anchor) { e.preventDefault(); onLink(anchor.getAttribute("data-reader-href") || ""); } }}>
    {query.data?.html ? <div data-reader-text dangerouslySetInnerHTML={{ __html: query.data.html }} /> : <div data-reader-text className="whitespace-pre-wrap break-words">{query.data?.text}</div>}
  </article>;
}
