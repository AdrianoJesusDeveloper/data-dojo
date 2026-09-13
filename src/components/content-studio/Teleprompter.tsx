import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

type Props = { title: string; text: string; sourceNote?: string; status: "REVIEW" | "APPROVED"; onClose: () => void };

export function Teleprompter({ title, text, sourceNote, status, onClose }: Props) {
  const viewport = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(35);
  const [fontSize, setFontSize] = useState(40);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!playing) return;
    let frame: number;
    let previous: number | undefined;
    let position = viewport.current?.scrollTop ?? 0;
    const tick = (now: number) => {
      const element = viewport.current;
      if (!element) return;
      if (previous !== undefined) {
        position += speed * Math.min(now - previous, 100) / 1000;
        element.scrollTop = position;
        if (element.scrollTop >= element.scrollHeight - element.clientHeight - 1) {
          setPlaying(false);
          return;
        }
      }
      previous = now;
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, speed]);

  const move = (direction: number) => {
    setPlaying(false);
    if (viewport.current) viewport.current.scrollTop += direction * viewport.current.clientHeight * 0.7;
  };

  const fullscreen = async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else if (panel.current?.requestFullscreen) await panel.current.requestFullscreen();
      else throw new Error("unsupported");
    } catch { setError("Tela cheia indisponível neste navegador."); }
  };

  return <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
    <DialogContent ref={panel} aria-describedby={undefined} className="flex h-[92vh] max-w-6xl flex-col bg-black text-white [&:fullscreen]:left-0 [&:fullscreen]:top-0 [&:fullscreen]:h-screen [&:fullscreen]:max-w-none [&:fullscreen]:translate-x-0 [&:fullscreen]:translate-y-0">
      <DialogTitle className="pr-8">{title}</DialogTitle>
      <p className="text-sm text-zinc-300">{status === "REVIEW" ? "Ensaio de roteiro em revisão — ainda não aprovado." : "Roteiro aprovado para gravação."}</p>
      {sourceNote && <p className="text-sm text-zinc-300">{sourceNote}</p>}
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => setPlaying((value) => !value)}>{playing ? "Pausar" : "Iniciar"}</Button>
        <Button onClick={() => { setPlaying(false); if (viewport.current) viewport.current.scrollTop = 0; }}>Reiniciar</Button>
        <Button onClick={() => move(-1)}>Voltar</Button>
        <Button onClick={() => move(1)}>Avançar</Button>
        <label>Velocidade: {speed} px/s <input aria-label="Velocidade" type="range" min="10" max="120" value={speed} onChange={(event) => setSpeed(Number(event.target.value))} /></label>
        <Button aria-label="Diminuir fonte" onClick={() => setFontSize((value) => Math.max(24, value - 4))}>A−</Button>
        <Button aria-label="Aumentar fonte" onClick={() => setFontSize((value) => Math.min(80, value + 4))}>A+</Button>
        <Button onClick={() => void fullscreen()}>Tela cheia</Button>
      </div>
      {error && <p role="alert">{error}</p>}
      <div ref={viewport} tabIndex={0} aria-label="Texto do teleprompter" onWheel={() => setPlaying(false)} onTouchStart={() => setPlaying(false)} className="min-h-0 flex-1 overflow-y-auto whitespace-pre-wrap px-6 py-10 leading-relaxed" style={{ fontSize }}>
        {text}
        <div aria-hidden="true" className="h-[40vh]" />
      </div>
    </DialogContent>
  </Dialog>;
}
