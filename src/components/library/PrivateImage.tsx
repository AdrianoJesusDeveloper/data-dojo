import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function PrivateImage({ url, title, className = "" }: { url: string | null; title: string; className?: string }) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    setSrc("");
    if (!url) return;
    const controller = new AbortController();
    let objectUrl = "";
    api.get(url, { responseType: "blob", signal: controller.signal }).then(({ data }) => {
      objectUrl = URL.createObjectURL(data);
      setSrc(objectUrl);
    }).catch(() => {});
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [url]);
  return src ? <img src={src} alt={`Capa: ${title}`} loading="lazy" className={className} /> : <div className={`flex items-center justify-center bg-gradient-to-br from-primary/20 to-secondary p-4 text-center font-display font-bold ${className}`} aria-label="Sem capa">{title.slice(0, 80)}</div>;
}
