import confetti from "canvas-confetti";

export function celebrateXp() {
  if (typeof window === "undefined") return;
  confetti({
    particleCount: 60,
    spread: 65,
    startVelocity: 35,
    origin: { y: 0.7 },
    colors: ["#FFA500", "#E63946", "#0057B8", "#E5E5E5"],
    scalar: 0.9,
    ticks: 120,
  });
  window.dispatchEvent(new CustomEvent("dojo:xp"));
}

export function celebratePromotion(beltColor: string) {
  if (typeof window === "undefined") return;
  const fire = (ratio: number, opts: confetti.Options) =>
    confetti({
      particleCount: Math.floor(220 * ratio),
      colors: [beltColor, "#FFA500", "#E63946", "#FFFFFF"],
      ...opts,
    });

  fire(0.25, { spread: 26, startVelocity: 55, origin: { y: 0.7 } });
  fire(0.2, { spread: 60, origin: { y: 0.7 } });
  fire(0.35, { spread: 100, decay: 0.91, scalar: 0.9, origin: { y: 0.7 } });
  fire(0.1, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2, origin: { y: 0.7 } });
  fire(0.1, { spread: 120, startVelocity: 45, origin: { y: 0.7 } });

  // School-flag fire from the sides
  setTimeout(() => {
    confetti({ particleCount: 80, angle: 60, spread: 70, origin: { x: 0, y: 0.8 }, colors: [beltColor, "#FFA500"] });
    confetti({ particleCount: 80, angle: 120, spread: 70, origin: { x: 1, y: 0.8 }, colors: [beltColor, "#E63946"] });
  }, 250);

  window.dispatchEvent(new CustomEvent("dojo:promoted", { detail: { color: beltColor } }));
}
