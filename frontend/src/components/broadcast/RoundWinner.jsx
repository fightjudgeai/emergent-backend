/**
 * Fight Judge AI - Round Winner Display
 * Shows end-of-round scores with animated winner announcement
 */

import { memo, useState, useEffect } from "react";

export const RoundWinner = memo(function RoundWinner({
  round,
  roundNumber,
  redName,
  blueName,
  isVisible,
}) {
  const [showWinner, setShowWinner] = useState(false);
  const [isFlashing, setIsFlashing] = useState(false);

  useEffect(() => {
    if (isVisible) {
      const timeout = setTimeout(() => {
        setShowWinner(true);
        setIsFlashing(true);
        setTimeout(() => setIsFlashing(false), 1500);
      }, 500);
      return () => clearTimeout(timeout);
    } else {
      setShowWinner(false);
      setIsFlashing(false);
    }
  }, [isVisible]);

  if (!isVisible) return null;

  const winner = round.unified_red > round.unified_blue ? "red" : round.unified_blue > round.unified_red ? "blue" : "draw";
  const winnerName = winner === "red" ? redName : winner === "blue" ? blueName : "DRAW";
  const winnerCorner = winner === "red" ? "RED CORNER" : winner === "blue" ? "BLUE CORNER" : "";

  return (
    <div className="border-t-2 animate-broadcast-count-reveal" style={{ borderColor: "hsl(195 100% 70%)", background: "linear-gradient(to top, hsl(0 0% 12% / 0.4), transparent)" }}>
      <div className="px-6 py-4">
        <div className="flex items-center justify-center gap-4 mb-4">
          <div className="h-px flex-1" style={{ background: "linear-gradient(to right, transparent, hsl(195 100% 70% / 0.5), transparent)" }} />
          <span className="text-sm font-semibold tracking-[0.4em] uppercase" style={{ color: "hsl(195 100% 70%)" }}>Round {roundNumber} Score</span>
          <div className="h-px flex-1" style={{ background: "linear-gradient(to right, transparent, hsl(195 100% 70% / 0.5), transparent)" }} />
        </div>
        <div className="grid grid-cols-2 gap-6 mb-4">
          <div className="flex flex-col items-center p-4 rounded border-2 transition-all duration-500" style={{ borderColor: "hsl(348 83% 47%)", background: "hsl(348 83% 47% / 0.15)", boxShadow: "0 0 20px hsl(348 83% 47% / 0.4)" }}>
            <span className="text-xs font-medium tracking-[0.2em] uppercase mb-1" style={{ color: "hsl(348 83% 47%)" }}>Red</span>
            <span className="text-5xl font-bold tabular-nums" style={{ color: "hsl(348 83% 47%)", textShadow: "0 0 15px hsl(348 83% 47% / 0.6)" }}>{round.unified_red}</span>
          </div>
          <div className="flex flex-col items-center p-4 rounded border-2 transition-all duration-500" style={{ borderColor: "hsl(195 100% 70%)", background: "hsl(195 100% 70% / 0.15)", boxShadow: "0 0 20px hsl(195 100% 70% / 0.4)" }}>
            <span className="text-xs font-medium tracking-[0.2em] uppercase mb-1" style={{ color: "hsl(195 100% 70%)" }}>Blue</span>
            <span className="text-5xl font-bold tabular-nums" style={{ color: "hsl(195 100% 70%)", textShadow: "0 0 15px hsl(195 100% 70% / 0.6)" }}>{round.unified_blue}</span>
          </div>
        </div>
        {showWinner && (
          <div className={`flex flex-col items-center p-4 border-2 rounded ${isFlashing ? "animate-broadcast-winner-flash" : ""}`} style={{ borderColor: winner === "red" ? "hsl(348 83% 47%)" : "hsl(195 100% 70%)", background: winner === "red" ? "linear-gradient(to bottom, hsl(348 83% 47% / 0.2), hsl(348 83% 47% / 0.05))" : "linear-gradient(to bottom, hsl(195 100% 70% / 0.2), hsl(195 100% 70% / 0.05))", animation: isFlashing ? undefined : winner === "red" ? "broadcast-pulse-winner-red 2s ease-in-out infinite" : "broadcast-pulse-winner-blue 2s ease-in-out infinite" }}>
            <span className="text-xs font-medium tracking-[0.4em] uppercase mb-1" style={{ color: "hsl(0 0% 70%)" }}>Round Winner</span>
            <span className="text-3xl font-bold tracking-wider uppercase text-white mb-0.5">{winnerName}</span>
            {winnerCorner && <span className="text-sm font-semibold tracking-[0.3em] uppercase" style={{ color: winner === "red" ? "hsl(348 83% 47%)" : "hsl(195 100% 70%)" }}>{winnerCorner}</span>}
          </div>
        )}
      </div>
    </div>
  );
});