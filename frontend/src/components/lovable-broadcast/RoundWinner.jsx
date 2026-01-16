import { memo, useState, useEffect } from "react";

export const RoundWinner = memo(function RoundWinner({ round, roundNumber, redName, blueName, isVisible }) {
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
    <div className="border-t-2 border-lb-gold bg-gradient-to-t from-lb-muted/40 to-transparent lb-count-reveal">
      <div className="px-6 py-4">
        <div className="flex items-center justify-center gap-4 mb-4">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-lb-gold/50 to-transparent" />
          <span className="text-sm font-semibold tracking-[0.4em] uppercase text-lb-gold">Round {roundNumber} Score</span>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-lb-gold/50 to-transparent" />
        </div>

        <div className="grid grid-cols-2 gap-6 mb-4">
          <div className="flex flex-col items-center p-4 rounded border-2 transition-all duration-500 border-lb-corner-red bg-lb-corner-red/15 shadow-[0_0_20px_hsl(348_83%_47%_/_0.4)]">
            <span className="text-xs font-medium tracking-[0.2em] uppercase text-lb-corner-red mb-1">Red</span>
            <span className="text-5xl font-bold tabular-nums lb-score-red">{round.unified_red}</span>
          </div>
          <div className="flex flex-col items-center p-4 rounded border-2 transition-all duration-500 border-lb-gold bg-lb-gold/15 shadow-[0_0_20px_hsl(195_100%_70%_/_0.4)]">
            <span className="text-xs font-medium tracking-[0.2em] uppercase text-lb-gold mb-1">Blue</span>
            <span className="text-5xl font-bold tabular-nums lb-score-blue">{round.unified_blue}</span>
          </div>
        </div>

        {showWinner && (
          <div className={`flex flex-col items-center p-4 border-2 rounded ${
            winner === "red" 
              ? "border-lb-corner-red bg-gradient-to-b from-lb-corner-red/20 to-lb-corner-red/5 lb-pulse-winner-red" 
              : winner === "blue" 
              ? "border-lb-gold bg-gradient-to-b from-lb-gold/20 to-lb-gold/5 lb-pulse-winner-blue" 
              : "border-lb-gold bg-gradient-to-b from-lb-gold/20 to-lb-gold/5"
          } ${isFlashing ? "lb-winner-flash" : ""}`}>
            <span className="text-xs font-medium tracking-[0.4em] uppercase text-gray-400 mb-1">Round Winner</span>
            <span className="text-3xl font-bold tracking-wider uppercase text-white mb-0.5">{winnerName}</span>
            {winnerCorner && <span className={`text-sm font-semibold tracking-[0.3em] uppercase ${winner === "red" ? "text-lb-corner-red" : "text-lb-gold"}`}>{winnerCorner}</span>}
          </div>
        )}
      </div>
    </div>
  );
});
