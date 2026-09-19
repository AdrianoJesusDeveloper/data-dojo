import { useMemo } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { API_ORIGIN, getAuthToken } from "@/lib/api";
import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();
export default function PdfReader({ url, page, zoom, width, fitPage, onRendered }: { url: string; page: number; zoom: number; width: number; fitPage: boolean; onRendered: () => void }) {
  const file = useMemo(() => ({ url: `${API_ORIGIN}${url}`, httpHeaders: { Authorization: `Token ${getAuthToken()}` }, withCredentials: false }), [url]);
  return <Document file={file} loading={<p role="status">Carregando PDF…</p>} error={<p role="alert">Não foi possível renderizar este PDF.</p>}>
    <Page pageNumber={page} width={fitPage ? undefined : Math.max(200, width - 48)} height={fitPage ? Math.max(300, window.innerHeight - 200) : undefined} scale={zoom} renderAnnotationLayer={false} onRenderTextLayerSuccess={onRendered} loading={<p>Carregando página…</p>} error={<p role="alert">Página indisponível.</p>} />
  </Document>;
}
