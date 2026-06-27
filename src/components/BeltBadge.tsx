import { BELTS, type Belt, getCurrentBelt, getNextBelt, beltProgress } from "@/lib/dojo-store";

export function BeltBadge({ belt, size = "md" }: { belt: Belt; size?: "sm" | "md" | "lg" }) {
  const dims = size === "lg" ? "h-16 w-16 text-2xl" : size === "sm" ? "h-8 w-8 text-sm" : "h-12 w-12 text-lg";
  return (
    <div className="inline-flex items-center gap-3">
      <div
        className={`${dims} rounded-md flex items-center justify-center font-display font-bold border-2 border-black/40 shadow-[inset_0_-6px_0_rgba(0,0,0,0.35)]`}
        style={{ background: belt.color, color: belt.id === "black" ? "#FFA500" : "#1C1C1C" }}
        aria-label={belt.name}
      >
        {belt.kanji}
      </div>
      {size !== "sm" && (
        <div className="leading-tight">
          <div className="text-xs uppercase tracking-widest text-muted-foreground">Faixa atual</div>
          <div className="font-display font-semibold">{belt.name}</div>
        </div>
      )}
    </div>
  );
}

export function BeltProgress({ xp }: { xp: number }) {
  const cur = getCurrentBelt(xp);
  const next = getNextBelt(xp);
  const pct = beltProgress(xp);
  return (
    <div className="w-full">
      <div className="flex items-baseline justify-between text-xs mb-1.5">
        <span className="font-mono text-kaizen">{xp} XP</span>
        <span className="text-muted-foreground">
          {next ? `${next.minXp - xp} XP até ${next.name}` : "Maestria alcançada"}
        </span>
      </div>
      <div className="h-2.5 rounded-full bg-secondary overflow-hidden border border-border">
        <div
          className="h-full transition-all duration-700"
          style={{
            width: `${pct}%`,
            background: "linear-gradient(90deg, #FFA500, #E63946)",
            boxShadow: "0 0 16px rgba(255,165,0,0.6)",
          }}
        />
      </div>
      <div className="mt-2 flex justify-between">
        {BELTS.map((b) => (
          <div key={b.id} className="flex flex-col items-center gap-1">
            <div
              className="h-3 w-3 rounded-sm border border-black/40"
              style={{ background: b.color, opacity: xp >= b.minXp ? 1 : 0.35 }}
            />
            <span
              className={`text-[10px] uppercase tracking-wider ${
                cur.id === b.id ? "text-kaizen font-semibold" : "text-muted-foreground"
              }`}
            >
              {b.name.replace("Faixa ", "")}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
