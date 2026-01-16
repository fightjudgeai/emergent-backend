import { memo, useEffect, useState } from "react";
import { RoundWinner } from "./RoundWinner";

const AnimatedScore = memo(function AnimatedScore({ value, color, delay = 0, compact = false }) {
  const [displayValue, setDisplayValue] = useState(0);
  const [isAnimating, setIsAnimating] = useState(true);

  useEffect(() => {
    const timeout = setTimeout(() => {
      let current = 0;
      const increment = value / 10;
      const interval = setInterval(() => {
        current += increment;
        if (current >= value) {
          setDisplayValue(value);
          setIsAnimating(false);
          clearInterval(interval);
        } else {
          setDisplayValue(Math.floor(current));
        }
      }, 50);
      return () => clearInterval(interval);
    }, delay);
    return () => clearTimeout(timeout);
  }, [value, delay]);

  const sizeClass = compact ? "text-4xl" : "text-5xl";

  return (
    <span className={`${sizeClass} font-bold tabular-nums transition-all duration-300 ${color === "red" ? "lb-score-red" : "lb-score-blue"} ${isAnimating ? "opacity-80 scale-110" : "opacity-100 scale-100"}`}>
      {displayValue}
    </span>
  );
});

export const ScoreGrid = memo(function ScoreGrid({
  rounds,
  maxRounds = 5,
  redName,
  blueName,
  isCompleted,
  activeRoundWinner,
  isManualMode,
  compact = false,
  hideTotals = false,
}) {
  const isShowingRoundWinner = activeRoundWinner !== null && !isCompleted;
  const containerPad = compact ? "px-6 py-2" : "px-8 py-4";
  const headerMb = compact ? "mb-1" : "mb-4";
  const rowPy = compact ? "py-2" : "py-4";
  const roundLabelSize = compact ? "text-lg" : "text-2xl";
  const scoreSize = compact ? "text-3xl" : "text-5xl";

  if (isShowingRoundWinner) {
    return (
      <div className={`flex-1 flex flex-col justify-center ${containerPad}`}>
        {rounds.map((round, index) => (
          <div key={`winner-${index}`} className="px-4">
            <RoundWinner round={round} roundNumber={index + 1} redName={redName} blueName={blueName} isVisible={activeRoundWinner === index} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`flex-1 flex flex-col justify-center ${containerPad}`}>
      <div className={`grid grid-cols-3 gap-4 px-4 ${headerMb}`}>
        <div className="text-center"><span className="text-sm font-medium tracking-[0.2em] uppercase text-gray-400">Round</span></div>
        <div className="text-center"><span className="text-sm font-medium tracking-[0.2em] uppercase text-lb-corner-red">Red</span></div>
        <div className="text-center"><span className="text-sm font-medium tracking-[0.2em] uppercase text-lb-corner-blue">Blue</span></div>
      </div>

      <div className="flex flex-col gap-2">
        {Array.from({ length: maxRounds }).map((_, index) => {
          const roundData = rounds[index];
          const isActive = !!roundData;
          const roundNumber = index + 1;
          if (!isActive) return null;

          return (
            <div key={roundNumber} className={`grid grid-cols-3 gap-4 ${rowPy} px-4 rounded border transition-all duration-500 ${isActive ? "bg-lb-muted/20 border-lb-gold/30" : "bg-transparent border-transparent opacity-30"}`} style={{ animationDelay: `${index * 100}ms` }}>
              <div className="flex items-center justify-center">
                <span className={`${roundLabelSize} font-bold tracking-wider text-lb-accent-gold`}>RD {roundNumber}</span>
              </div>
              <div className="flex items-center justify-center">
                {isActive ? <AnimatedScore value={roundData.unified_red} color="red" delay={index * 200} compact={compact} /> : <span className={`${scoreSize} font-bold text-gray-600`}>—</span>}
              </div>
              <div className="flex items-center justify-center">
                {isActive ? <AnimatedScore value={roundData.unified_blue} color="blue" delay={index * 200 + 100} compact={compact} /> : <span className={`${scoreSize} font-bold text-gray-600`}>—</span>}
              </div>
            </div>
          );
        })}

        {!hideTotals && rounds.length > 1 && (
          <div className={`grid grid-cols-3 gap-4 ${rowPy} px-4 rounded border border-lb-gold/50 bg-lb-gold/10 mt-2`}>
            <div className="flex items-center justify-center"><span className={`${roundLabelSize} font-bold tracking-wider text-lb-gold`}>TOTAL</span></div>
            <div className="flex items-center justify-center"><span className={`${scoreSize} font-bold tabular-nums lb-score-red`}>{rounds.reduce((sum, r) => sum + r.unified_red, 0)}</span></div>
            <div className="flex items-center justify-center"><span className={`${scoreSize} font-bold tabular-nums lb-score-blue`}>{rounds.reduce((sum, r) => sum + r.unified_blue, 0)}</span></div>
          </div>
        )}
      </div>

      {rounds.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <span className="text-lg font-medium tracking-widest uppercase text-gray-400 animate-pulse">Awaiting Official Scores</span>
        </div>
      )}
    </div>
  );
});
