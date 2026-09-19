import { api } from "@/lib/api";

export type Progress = { position: number; location: string; offset: number; progress_percentage: number };
export type LibraryBook = { id: number; title: string; author: string; category: string; format: string; status: string; availability: string; message: string; lifecycle: string; is_favorite: boolean; cover_url: string | null; progress_percent: number; progress_stage: string; reading: Progress | null };
export type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };
export type TocEntry = { id?: number; position: number; location: string; title: string; order?: number };
export type TocMode = "automatic" | "manual";
export type ReaderMetadata = { book: LibraryBook; total: number; toc: TocEntry[]; toc_mode: TocMode; file_url: string };
export type ReadingMark = Progress & { id: number; kind: "bookmark" | "annotation" | "highlight"; note: string; selected_text: string; start_offset: number | null; end_offset: number | null };
export const bookUrl = (id: number) => `/api/library/books/${id}/`;
export function errorMessage(error: unknown): string {
  const value = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof value === "string" ? value : Array.isArray(value) ? value.join(" ") : "Não foi possível concluir a operação. Tente novamente.";
}
export async function uploadFile(url: string, file: File, values: Record<string, string> = {}) {
  const form = new FormData();
  form.append("file", file);
  for (const [name, value] of Object.entries(values)) form.append(name, value);
  return api.post(url, form, { headers: { "Content-Type": "multipart/form-data" } });
}
