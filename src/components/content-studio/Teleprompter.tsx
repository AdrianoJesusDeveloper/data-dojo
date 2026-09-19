import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

type Props = {
  title: string;
  text: string;
  sourceNote?: string;
  status: "REVIEW" | "APPROVED";
  onClose: () => void;
};

export function Teleprompter({ title, text, sourceNote, status, onClose }: Props) {
  const viewport = useRef<HTMLDivElement>(null);
  const panel = useRef<HTMLDivElement>(null);

  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(35);
  const [fontSize, setFontSize] = useState(40);
  const [mirrored, setMirrored] = useState(false);
  const [focusMode, setFocusMode] = useState(true);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  const updateProgress = () => {
    const element = viewport.current;
    if (!element) return;

    const maximum = element.scrollHeight - element.clientHeight;
    if (maximum <= 0) {
      setProgress(100);
      return;
    }

    setProgress(
      Math.min(100, Math.max(0, (element.scrollTop / maximum) * 100)),
    );
  };

  const restart = () => {
    setPlaying(false);

    if (viewport.current) {
      viewport.current.scrollTop = 0;
    }

    setProgress(0);
  };

  const move = (direction: number) => {
    setPlaying(false);

    if (viewport.current) {
      viewport.current.scrollTop +=
        direction * viewport.current.clientHeight * 0.7;

      requestAnimationFrame(updateProgress);
    }
  };

  const fullscreen = async () => {
    try {
      setError("");

      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else if (panel.current?.requestFullscreen) {
        await panel.current.requestFullscreen();
      } else {
        throw new Error("unsupported");
      }
    } catch {
      setError("Tela cheia indisponível neste navegador.");
    }
  };

  useEffect(() => {
    if (!playing) return;

    let frame: number;
    let previous: number | undefined;
    let position = viewport.current?.scrollTop ?? 0;

    const tick = (now: number) => {
      const element = viewport.current;
      if (!element) return;

      if (previous !== undefined) {
        position += (speed * Math.min(now - previous, 100)) / 1000;
        element.scrollTop = position;

        if (
          element.scrollTop >=
          element.scrollHeight - element.clientHeight - 1
        ) {
          setPlaying(false);
          setProgress(100);
          return;
        }
      }

      previous = now;
      frame = requestAnimationFrame(tick);
    };

    frame = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(frame);
  }, [playing, speed]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;

      if (
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT"
      ) {
        return;
      }

      switch (event.key) {
        case " ":
          event.preventDefault();
          setPlaying((value) => !value);
          break;
        case "ArrowUp":
          event.preventDefault();
          move(-1);
          break;
        case "ArrowDown":
          event.preventDefault();
          move(1);
          break;
        case "+":
        case "=":
          setFontSize((value) => Math.min(88, value + 4));
          break;
        case "-":
        case "_":
          setFontSize((value) => Math.max(24, value - 4));
          break;
        case "r":
        case "R":
          restart();
          break;
        case "m":
        case "M":
          setMirrored((value) => !value);
          break;
        case "f":
        case "F":
          void fullscreen();
          break;
        default:
          break;
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent
        ref={panel}
        aria-describedby={undefined}
        className="flex h-[92vh] max-w-6xl flex-col bg-black text-white [&:fullscreen]:left-0 [&:fullscreen]:top-0 [&:fullscreen]:h-screen [&:fullscreen]:max-w-none [&:fullscreen]:translate-x-0 [&:fullscreen]:translate-y-0"
      >
        <div className="pr-8">
          <DialogTitle>{title}</DialogTitle>

          <p className="mt-1 text-sm text-zinc-300">
            {status === "REVIEW"
              ? "Ensaio de roteiro em revisão — ainda não aprovado."
              : "Roteiro aprovado para gravação."}
          </p>

          {sourceNote && (
            <p className="mt-1 text-sm text-zinc-400">{sourceNote}</p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 border-y border-zinc-800 py-3">
          <Button onClick={() => setPlaying((value) => !value)}>
            {playing ? "Pausar" : "Iniciar"}
          </Button>

          <Button variant="secondary" onClick={restart}>
            Reiniciar
          </Button>

          <Button variant="secondary" onClick={() => move(-1)}>
            Voltar
          </Button>

          <Button variant="secondary" onClick={() => move(1)}>
            Avançar
          </Button>

          <label className="flex items-center gap-2 text-sm">
            <span>Velocidade: {speed} px/s</span>
            <input
              aria-label="Velocidade"
              type="range"
              min="10"
              max="160"
              step="5"
              value={speed}
              onChange={(event) => setSpeed(Number(event.target.value))}
            />
          </label>

          <Button
            variant="secondary"
            aria-label="Diminuir fonte"
            onClick={() =>
              setFontSize((value) => Math.max(24, value - 4))
            }
          >
            A−
          </Button>

          <span className="min-w-14 text-center text-sm text-zinc-300">
            {fontSize}px
          </span>

          <Button
            variant="secondary"
            aria-label="Aumentar fonte"
            onClick={() =>
              setFontSize((value) => Math.min(88, value + 4))
            }
          >
            A+
          </Button>

          <Button
            variant={mirrored ? "default" : "secondary"}
            onClick={() => setMirrored((value) => !value)}
          >
            {mirrored ? "Espelho ativo" : "Espelhar"}
          </Button>

          <Button
            variant={focusMode ? "default" : "secondary"}
            onClick={() => setFocusMode((value) => !value)}
          >
            {focusMode ? "Foco ativo" : "Modo foco"}
          </Button>

          <Button variant="secondary" onClick={() => void fullscreen()}>
            Tela cheia
          </Button>

          <span className="ml-auto text-sm font-medium text-zinc-300">
            {Math.round(progress)}%
          </span>
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-400">
            {error}
          </p>
        )}

        <div className="relative min-h-0 flex-1 overflow-hidden">
          {focusMode && (
            <>
              <div
                aria-hidden="true"
                className="pointer-events-none absolute left-0 right-0 top-[42%] z-20 h-[20%] border-y border-zinc-700 bg-white/5"
              />
              <div
                aria-hidden="true"
                className="pointer-events-none absolute left-0 right-0 top-[52%] z-20 border-t border-red-500/40"
              />
            </>
          )}

          <div
            ref={viewport}
            tabIndex={0}
            aria-label="Texto do teleprompter"
            onScroll={updateProgress}
            onWheel={() => setPlaying(false)}
            onTouchStart={() => setPlaying(false)}
            className="h-full overflow-y-auto whitespace-pre-wrap px-6 py-10 leading-relaxed sm:px-12"
            style={{ fontSize }}
          >
            <div
              className="mx-auto max-w-5xl"
              style={{
                transform: mirrored ? "scaleX(-1)" : undefined,
              }}
            >
              {text}
            </div>

            <div aria-hidden="true" className="h-[45vh]" />
          </div>
        </div>

        <div className="flex flex-wrap gap-x-5 gap-y-1 border-t border-zinc-800 pt-2 text-xs text-zinc-500">
          <span>Espaço: iniciar/pausar</span>
          <span>↑ ↓: navegar</span>
          <span>+ −: fonte</span>
          <span>R: reiniciar</span>
          <span>M: espelho</span>
          <span>F: tela cheia</span>
        </div>
      </DialogContent>
    </Dialog>
  );
}
