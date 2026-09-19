import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { bookUrl } from "./library-api";

type StoredNarratorState = {
  position: number;
  charIndex: number;
  rate: number;
  voiceURI: string;
  language: string;
};

type Props = {
  bookId: number;
  position: number;
  total: number;
  onNavigate: (position: number) => void;
  getVisibleText: () => string;
  onHighlight?: (start: number, end: number) => void;
  onClearHighlight?: () => void;
};

const DEFAULT_RATE = 1;
const STORAGE_PREFIX = "dojo-reader-narrator";

function storageKey(bookId: number) {
  return `${STORAGE_PREFIX}:${bookId}`;
}

function readStored(bookId: number): StoredNarratorState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(storageKey(bookId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<StoredNarratorState>;
    if (!Number.isInteger(parsed.position) || (parsed.position ?? 0) < 1) return null;
    return {
      position: parsed.position as number,
      charIndex: Math.max(0, Number(parsed.charIndex) || 0),
      rate: Math.min(2, Math.max(0.5, Number(parsed.rate) || DEFAULT_RATE)),
      voiceURI: typeof parsed.voiceURI === "string" ? parsed.voiceURI : "",
      language: typeof parsed.language === "string" ? parsed.language : "",
    };
  } catch {
    return null;
  }
}

export function NarratorControls({
  bookId,
  position,
  total,
  onNavigate,
  getVisibleText,
  onHighlight,
  onClearHighlight,
}: Props) {
  const initialStored = useMemo(() => readStored(bookId), [bookId]);
  const [supported, setSupported] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [language, setLanguage] = useState(initialStored?.language || "");
  const [voiceURI, setVoiceURI] = useState(initialStored?.voiceURI || "");
  const [rate, setRate] = useState(initialStored?.rate ?? DEFAULT_RATE);
  const [speaking, setSpeaking] = useState(false);
  const [paused, setPaused] = useState(false);
  const [message, setMessage] = useState("");
  const [resumePosition, setResumePosition] = useState(initialStored?.position ?? position);
  const [resumeChar, setResumeChar] = useState(initialStored?.charIndex ?? 0);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const currentTextRef = useRef("");
  const currentPositionRef = useRef(position);
  const charIndexRef = useRef(initialStored?.charIndex ?? 0);
  const cancelledRef = useRef(false);

  const persist = useCallback((next: Partial<StoredNarratorState> = {}) => {
    if (typeof window === "undefined") return;
    const value: StoredNarratorState = {
      position: next.position ?? currentPositionRef.current,
      charIndex: next.charIndex ?? charIndexRef.current,
      rate: next.rate ?? rate,
      voiceURI: next.voiceURI ?? voiceURI,
      language: next.language ?? language,
    };
    window.localStorage.setItem(storageKey(bookId), JSON.stringify(value));
    setResumePosition(value.position);
    setResumeChar(value.charIndex);
  }, [bookId, language, rate, voiceURI]);

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    setSupported(true);
    const loadVoices = () => {
      const available = window.speechSynthesis.getVoices();
      setVoices(available);
      if (!available.length) return;
      const storedVoice = initialStored?.voiceURI && available.find(v => v.voiceURI === initialStored.voiceURI);
      const preferred =
        storedVoice ||
        available.find(v => v.lang.toLowerCase() === "pt-br") ||
        available.find(v => v.lang.toLowerCase().startsWith("pt")) ||
        available[0];
      const nextLanguage = initialStored?.language || preferred.lang;
      setLanguage(nextLanguage);
      setVoiceURI(preferred.voiceURI);
    };
    loadVoices();
    window.speechSynthesis.addEventListener?.("voiceschanged", loadVoices);
    return () => window.speechSynthesis.removeEventListener?.("voiceschanged", loadVoices);
  }, [initialStored]);

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        cancelledRef.current = true;
        window.speechSynthesis.cancel();
      }
      onClearHighlight?.();
    };
  }, [onClearHighlight]);

  const languages = useMemo(
    () => Array.from(new Set(voices.map(v => v.lang).filter(Boolean))).sort((a, b) => a.localeCompare(b)),
    [voices],
  );
  const filteredVoices = useMemo(
    () => voices.filter(v => !language || v.lang === language),
    [voices, language],
  );

  useEffect(() => {
    if (!filteredVoices.length) return;
    if (!filteredVoices.some(v => v.voiceURI === voiceURI)) {
      const nextVoice = filteredVoices[0].voiceURI;
      setVoiceURI(nextVoice);
      persist({ voiceURI: nextVoice, language: filteredVoices[0].lang });
    }
  }, [filteredVoices, persist, voiceURI]);

  async function loadText(targetPosition: number) {
    const visible = targetPosition === position ? getVisibleText().trim() : "";
    if (visible) return visible;
    try {
      const response = await api.get<{ text: string }>(`${bookUrl(bookId)}sections/${targetPosition}/`);
      if (response.data.text?.trim()) return response.data.text.trim();
    } catch {
      // PDFs sem seção/chunk nesta página podem cair no texto visível abaixo.
    }
    return targetPosition === position ? getVisibleText().trim() : "";
  }

  const stop = useCallback((keepPosition = true) => {
    if (!supported) return;
    cancelledRef.current = true;
    window.speechSynthesis.cancel();
    utteranceRef.current = null;
    setSpeaking(false);
    setPaused(false);
    onClearHighlight?.();
    if (keepPosition) persist();
  }, [onClearHighlight, persist, supported]);

  async function speak(targetPosition = position, startAt = 0, rateOverride?: number) {
    if (!supported) {
      setMessage("Leitura em voz alta não é suportada neste navegador.");
      return;
    }
    const text = await loadText(targetPosition);
    if (!text) {
      setMessage("Não há texto disponível para narrar nesta página/seção.");
      return;
    }

    stop(false);
    cancelledRef.current = false;
    currentTextRef.current = text;
    currentPositionRef.current = targetPosition;
    charIndexRef.current = Math.min(Math.max(0, startAt), text.length);
    persist({ position: targetPosition, charIndex: charIndexRef.current });

    const spokenText = text.slice(charIndexRef.current);
    const utterance = new SpeechSynthesisUtterance(spokenText);
    const voice = voices.find(v => v.voiceURI === voiceURI);
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else if (language) {
      utterance.lang = language;
    }
    utterance.rate = rateOverride ?? rate;

    const baseOffset = charIndexRef.current;
    utterance.onstart = () => {
      setSpeaking(true);
      setPaused(false);
      setMessage(`Narrando ${targetPosition}/${total}`);
    };
    utterance.onboundary = event => {
      const absolute = Math.min(text.length, baseOffset + event.charIndex);
      charIndexRef.current = absolute;
      persist({ position: targetPosition, charIndex: absolute });
      const length = Math.max(1, event.charLength || 1);
      onHighlight?.(absolute, Math.min(text.length, absolute + length));
    };
    utterance.onend = () => {
      if (cancelledRef.current) return;
      charIndexRef.current = 0;
      persist({ position: targetPosition, charIndex: 0 });
      setSpeaking(false);
      setPaused(false);
      setMessage("Trecho concluído.");
      onClearHighlight?.();
    };
    utterance.onerror = event => {
      if (cancelledRef.current || event.error === "interrupted" || event.error === "canceled") return;
      setSpeaking(false);
      setPaused(false);
      setMessage("Não foi possível continuar a narração.");
      onClearHighlight?.();
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }

  function togglePause() {
    if (!supported || !speaking) return;
    if (paused) {
      window.speechSynthesis.resume();
      setPaused(false);
      setMessage("Narração retomada.");
    } else {
      window.speechSynthesis.pause();
      setPaused(true);
      persist();
      setMessage("Narração pausada.");
    }
  }

  async function move(direction: -1 | 1) {
    const nextPosition = Math.min(total, Math.max(1, currentPositionRef.current + direction));
    if (nextPosition === currentPositionRef.current) return;
    stop(false);
    currentPositionRef.current = nextPosition;
    charIndexRef.current = 0;
    persist({ position: nextPosition, charIndex: 0 });
    onNavigate(nextPosition);
    await speak(nextPosition, 0);
  }

  function changeRate(value: number) {
    setRate(value);
    persist({ rate: value });
    if (speaking) {
      const restartAt = charIndexRef.current;
      void speak(currentPositionRef.current, restartAt, value);
    }
  }

  function changeLanguage(value: string) {
    setLanguage(value);
    const first = voices.find(v => v.lang === value);
    if (first) setVoiceURI(first.voiceURI);
    persist({ language: value, voiceURI: first?.voiceURI ?? "" });
  }

  function changeVoice(value: string) {
    setVoiceURI(value);
    const voice = voices.find(v => v.voiceURI === value);
    if (voice) setLanguage(voice.lang);
    persist({ voiceURI: value, language: voice?.lang ?? language });
  }

  if (!supported) {
    return <p className="text-xs text-muted-foreground">Narrador indisponível neste navegador.</p>;
  }

  const canResume = resumePosition === position && resumeChar > 0 && !speaking;

  return (
    <section aria-label="Narrador" className="flex flex-wrap items-center gap-2 rounded border bg-background/70 p-2">
      <strong className="text-xs">Narrador</strong>
      {!speaking ? (
        <Button size="sm" onClick={() => void speak(position, canResume ? resumeChar : 0)}>
          {canResume ? "Continuar áudio" : "Ouvir"}
        </Button>
      ) : (
        <Button size="sm" variant="outline" onClick={togglePause}>{paused ? "Continuar" : "Pausar"}</Button>
      )}
      <Button size="sm" variant="outline" disabled={!speaking && resumeChar === 0} onClick={() => stop(true)}>Parar</Button>
      <Button size="sm" variant="outline" disabled={currentPositionRef.current <= 1} onClick={() => void move(-1)}>← Ouvir anterior</Button>
      <Button size="sm" variant="outline" disabled={currentPositionRef.current >= total} onClick={() => void move(1)}>Ouvir próxima →</Button>

      <label className="flex items-center gap-1 text-xs">
        Velocidade
        <select aria-label="Velocidade da narração" className="rounded border bg-background p-1" value={rate} onChange={e => changeRate(Number(e.target.value))}>
          {[0.5, 0.75, 1, 1.25, 1.5, 1.75, 2].map(value => <option key={value} value={value}>{value}×</option>)}
        </select>
      </label>

      <label className="flex items-center gap-1 text-xs">
        Idioma
        <select aria-label="Idioma da narração" className="max-w-32 rounded border bg-background p-1" value={language} onChange={e => changeLanguage(e.target.value)}>
          {languages.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
      </label>

      <label className="flex items-center gap-1 text-xs">
        Voz
        <select aria-label="Voz da narração" className="max-w-48 rounded border bg-background p-1" value={voiceURI} onChange={e => changeVoice(e.target.value)}>
          {filteredVoices.map(voice => <option key={voice.voiceURI} value={voice.voiceURI}>{voice.name}</option>)}
        </select>
      </label>

      {message && <span role="status" className="text-xs text-muted-foreground">{message}</span>}
    </section>
  );
}
