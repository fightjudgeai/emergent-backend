/**
 * Fight Judge AI - Final Result Display
 * Shows final fight scores with animated winner announcement
 */

import { memo, useState, useEffect } from "react";

export const FinalResult = memo(function FinalResult({ total, winner, redName, blueName, isVisible }) {
  const [showWinner, setShowWinner] = useState(false);
  const [isFlashing, setIsFlashing] = useState(false);

  useEffect(() => {
    if (isVisible && winner) {
      const timeout = setTimeout(() => { setShowWinner(true); setIsFlashing(true); setTimeout(() => setIsFlashing(false), 1500); }, 800);
      return () => clearTimeout(timeout);
    } else { setShowWinner(false); setIsFlashing(false); }
  }, [isVisible, winner]);

  if (!isVisible) return null;

  const winnerName = winner === "red" ? redName : winner === "blue" ? blueName : "DRAW";
  const winnerCorner = winner === "red" ? "RED CORNER" : winner === "blue" ? "BLUE CORNER" : "";

  return (
    <div className="border-t-2 animate-broadcast-count-reveal flex-shrink-0" style={{ borderColor: "hsl(195 100% 70%)", background: "linear-gradient(to top, hsl(0 0% 12% / 0.6), transparent)" }}>
      <div className="px-4 py-3">
        <div className="flex items-center justify-center gap-4 mb-3">
          <div className="h-px flex-1" style={{ background: "linear-gradient(to right, transparent, hsl(195 100% 70% / 0.5), transparent)" }} />
          <span className="text-xs font-semibold tracking-[0.4em] uppercase" style={{ color: "hsl(195 100% 70%)" }}>Final Score</span>
          <div className="h-px flex-1" style={{ background: "linear-gradient(to right, transparent, hsl(195 100% 70% / 0.5), transparent)" }} />
        </div>
        <div className="grid grid-cols-2 gap-4 mb-3">
          <div className="flex flex-col items-center p-3 rounded border-2" style={{ borderColor: "hsl(348 83% 47%)", background: "hsl(348 83% 47% / 0.15)", boxShadow: "0 0 25px hsl(348 83% 47% / 0.5)" }}>
            <span className="text-xs font-medium tracking-[0.2em] uppercase mb-1" style={{ color: "hsl(348 83% 47%)" }}>Red Total</span>
            <span className="text-4xl font-bold tabular-nums" style={{ color: "hsl(348 83% 47%)", textShadow: "0 0 20px hsl(348 83% 47% / 0.7)" }}>{total.red}</span>
          </div>
          <div className="flex flex-col items-center p-3 rounded border-2" style={{ borderColor: "hsl(195 100% 70%)", background: "hsl(195 100% 70% / 0.15)", boxShadow: "0 0 25px hsl(195 100% 70% / 0.5)" }}>
            <span className="text-xs font-medium tracking-[0.2em] uppercase mb-1" style={{ color: "hsl(195 100% 70%)" }}>Blue Total</span>
            <span className="text-4xl font-bold tabular-nums" style={{ color: "hsl(195 100% 70%)", textShadow: "0 0 20px hsl(195 100% 70% / 0.7)" }}>{total.blue}</span>
          </div>
        </div>
        {showWinner && winner && (
          <div className={`flex flex-col items-center p-3 border-2 rounded ${isFlashing ? "animate-broadcast-winner-flash" : ""}`} style={{ borderColor: winner === "red" ? "hsl(348 83% 47%)" : "hsl(195 100% 70%)", background: winner === "red" ? "linear-gradient(to bottom, hsl(348 83% 47% / 0.25), hsl(348 83% 47% / 0.1))" : "linear-gradient(to bottom, hsl(195 100% 70% / 0.25), hsl(195 100% 70% / 0.1))", animation: isFlashing ? undefined : winner === "red" ? "broadcast-pulse-winner-red 2s ease-in-out infinite" : "broadcast-pulse-winner-blue 2s ease-in-out infinite" }}>
            <span className="text-xs font-medium tracking-[0.4em] uppercase mb-1" style={{ color: "hsl(195 100% 70%)" }}>Winner</span>
            <span className="text-2xl font-bold tracking-wider uppercase text-white mb-0.5">{winnerName}</span>
            {winnerCorner && <span className="text-xs font-semibold tracking-[0.3em] uppercase" style={{ color: winner === "red" ? "hsl(348 83% 47%)" : "hsl(195 100% 70%)" }}>{winnerCorner}</span>}
          </div>
        )}
      </div>
    </div>
  );
});