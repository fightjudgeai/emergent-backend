import { memo, useState, useEffect } from "react";

// ============= ROUND WINNER COMPONENT =============
export const RoundWinner = memo(function RoundWinner({
  round, roundNumber, redName, blueName, isVisible
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
    <div className="border-t-2 border-fjai-gold bg-gradient-to-t from-fjai-muted/40 to-transparent animate-fjai-count-reveal">
      <div className="px-6 py-4">
        <div className="flex items-center justify-center gap-4 mb-4">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-fjai-gold/50 to-transparent" />
          <span className="text-sm font-semibold tracking-[0.4em] uppercase text-fjai-gold">Round {roundNumber} Score</span>
          <div className="h-px flex-1 bg-gradient-to-r from-transparent via-fjai-gold/50 to-transparent" />
        </div>
        <div className="grid grid-cols-2 gap-6 mb-4">
          <div className="flex flex-col items-center p-4 rounded border-2 border-fjai-red bg-fjai-red/15 shadow-[0_0_20px_hsl(348_83%_47%_/_0.4)]">
            <span className="text-xs font-medium tracking-[0.2em] uppercase text-fjai-red mb-1">Red</span>
            <span className="text-5xl font-bold tabular-nums text-fjai-red" style={{textShadow: "0 0 15px hsl(348 83% 47% / 0.6)"}}>{round.unified_red}</span>
          </div>
          <div className="flex flex-col items-center p-4 rounded border-2 border-fjai-gold bg-fjai-gold/15 shadow-[0_0_20px_hsl(195_100%_70%_/_0.4)]">
            <span className="text-xs font-medium tracking-[0.2em] uppercase text-fjai-gold mb-1">Blue</span>
            <span className="text-5xl font-bold tabular-nums text-fjai-gold" style={{textShadow: "0 0 15px hsl(195 100% 70% / 0.6)"}}>{round.unified_blue}</span>
          </div>
        </div>
        {showWinner && (
          <div className={`flex flex-col items-center p-4 border-2 rounded ${
            winner === "red" ? "border-fjai-red bg-gradient-to-b from-fjai-red/20 to-fjai-red/5 animate-fjai-pulse-red" 
            : "border-fjai-gold bg-gradient-to-b from-fjai-gold/20 to-fjai-gold/5 animate-fjai-pulse-blue"
          } ${isFlashing ? "animate-fjai-flash" : ""}`}>
            <span className="text-xs font-medium tracking-[0.4em] uppercase text-gray-400 mb-1">Round Winner</span>
            <span className="text-3xl font-bold tracking-wider uppercase text-white mb-0.5">{winnerName}</span>
            {winnerCorner && <span className={`text-sm font-semibold tracking-[0.3em] uppercase ${winner === "red" ? "text-fjai-red" : "text-fjai-gold"}`}>{winnerCorner}</span>}
          </div>
        )}
      </div>
    </div>
  );
});

// ============= FINAL RESULT COMPONENT =============
export const FinalResult = memo(function FinalResult({
  total, winner, redName, blueName, isVisible, finishMethod = "DEC", totalRounds = 3, stoppageRound
}) {
  const [showWinner, setShowWinner] = useState(false);
  const [isFlashing, setIsFlashing] = useState(false);

  useEffect(() => {
    if (isVisible && winner) {
      const timeout = setTimeout(() => {
        setShowWinner(true);
        setIsFlashing(true);
        setTimeout(() => setIsFlashing(false), 1500);
      }, 1000);
      return () => clearTimeout(timeout);
    }
  }, [isVisible, winner]);

  if (!isVisible) return null;

  const isDraw = winner === "draw" || winner === null;
  const winnerName = winner === "red" ? redName : winner === "blue" ? blueName : "DRAW";
  const winnerCorner = winner === "red" ? "RED CORNER" : winner === "blue" ? "BLUE CORNER" : "";
  const showScores = finishMethod === "DEC";
  const victoryText = isDraw ? "DRAW" : finishMethod ? `VICTORY BY ${finishMethod}` : "VICTORY";
  const showStoppageRound = finishMethod && finishMethod !== "DEC" && stoppageRound;

  return (
    <div className="border-t-4 border-fjai-gold bg-gradient-to-t from-fjai-muted/60 to-transparent animate-fjai-count-reveal shadow-[0_-8px_30px_hsl(195_100%_70%_/_0.3)]">
      <div className="px-4 py-4">
        <div className="flex items-center justify-center gap-4 mb-4">
          <div className="h-0.5 flex-1 bg-gradient-to-r from-transparent via-fjai-gold/70 to-transparent" />
          <span className="text-base font-bold tracking-[0.4em] uppercase text-fjai-gold drop-shadow-[0_0_10px_hsl(195_100%_70%_/_0.5)]">FJAI Result</span>
          <div className="h-0.5 flex-1 bg-gradient-to-r from-transparent via-fjai-gold/70 to-transparent" />
        </div>
        {showScores && (
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="flex flex-col items-center p-3 rounded-lg border-[3px] border-fjai-red bg-fjai-red/20 shadow-[0_0_30px_hsl(348_83%_47%_/_0.5)]">
              <span className="text-sm font-semibold tracking-[0.25em] uppercase text-fjai-red mb-1">Red</span>
              <span className="text-5xl font-bold tabular-nums text-fjai-red" style={{textShadow: "0 0 15px hsl(348 83% 47% / 0.6)"}}>{total.red}</span>
            </div>
            <div className="flex flex-col items-center p-3 rounded-lg border-[3px] border-fjai-gold bg-fjai-gold/20 shadow-[0_0_30px_hsl(195_100%_70%_/_0.5)]">
              <span className="text-sm font-semibold tracking-[0.25em] uppercase text-fjai-gold mb-1">Blue</span>
              <span className="text-5xl font-bold tabular-nums text-fjai-gold" style={{textShadow: "0 0 15px hsl(195 100% 70% / 0.6)"}}>{total.blue}</span>
            </div>
          </div>
        )}
        {showWinner && (
          <div className={`flex flex-col items-center p-4 border-[3px] rounded-lg ${
            winner === "red" ? "border-fjai-red bg-gradient-to-b from-fjai-red/25 to-fjai-red/10 animate-fjai-pulse-red shadow-[0_0_40px_hsl(348_83%_47%_/_0.5)]" 
            : "border-fjai-gold bg-gradient-to-b from-fjai-gold/25 to-fjai-gold/10 animate-fjai-pulse-blue shadow-[0_0_40px_hsl(195_100%_70%_/_0.5)]"
          } ${isFlashing ? "animate-fjai-flash" : ""}`}>
            <span className="text-sm font-semibold tracking-[0.4em] uppercase text-gray-400 mb-1">{isDraw ? "Result" : "Winner"}</span>
            <span className="text-3xl font-bold tracking-wider uppercase text-white drop-shadow-[0_0_8px_rgba(255,255,255,0.3)]">{winnerName}</span>
            {!isDraw && winnerCorner && (
              <span className={`text-base font-bold tracking-[0.25em] uppercase mt-1 ${winner === "red" ? "text-fjai-red drop-shadow-[0_0_8px_hsl(348_83%_47%_/_0.6)]" : "text-fjai-gold drop-shadow-[0_0_8px_hsl(195_100%_70%_/_0.6)]"}`}>{winnerCorner}</span>
            )}
            <span className="text-lg font-bold tracking-[0.25em] uppercase text-fjai-gold mt-2 drop-shadow-[0_0_10px_hsl(195_100%_70%_/_0.5)]">{victoryText}</span>
            {showStoppageRound && <span className="text-sm font-semibold tracking-[0.2em] uppercase text-gray-400 mt-1">Round {stoppageRound}</span>}
          </div>
        )}
      </div>
    </div>
  );
});

// ============= API TRANSFORM UTILITIES =============
export function transformRoundComplete(message) {
  const data = message.data || message;
  return {
    round: {
      round: data.round_number || data.round || 1,
      unified_red: data.unified_red ?? data.score_red ?? data.red ?? data.red_points ?? 10,
      unified_blue: data.unified_blue ?? data.score_blue ?? data.blue ?? data.blue_points ?? 9,
    },
    roundNumber: data.round_number || data.round || 1,
    redName: data.red_fighter || data.fighters?.red?.name || data.fighter1 || "Red",
    blueName: data.blue_fighter || data.fighters?.blue?.name || data.fighter2 || "Blue",
  };
}

export function transformFinalResult(message) {
  const data = message.data || message;
  return {
    total: {
      red: data.total_red ?? data.totals?.red ?? data.final_red ?? 0,
      blue: data.total_blue ?? data.totals?.blue ?? data.final_blue ?? 0,
    },
    winner: (data.winner?.toLowerCase() || null),
    redName: data.red_fighter || data.fighters?.red?.name || data.fighter1 || "Red",
    blueName: data.blue_fighter || data.fighters?.blue?.name || data.fighter2 || "Blue",
    finishMethod: (data.finish_method || data.finishMethod || "DEC"),
    stoppageRound: data.stoppage_round || data.stoppageRound,
  };
}
