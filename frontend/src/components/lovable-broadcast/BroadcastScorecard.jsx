import { memo } from "react";
import { TopBar } from "./TopBar";
import { FighterHeader } from "./FighterHeader";
import { ScoreGrid } from "./ScoreGrid";
import { FinalResult } from "./FinalResult";
import { SignalLostOverlay } from "./SignalLostOverlay";
import { StandbyScreen } from "./StandbyScreen";

export const BroadcastScorecard = memo(function BroadcastScorecard({
  data,
  connectionStatus,
  isLoading,
  displayMode,
}) {
  const isStandby = isLoading || data.status === "pending";
  const isSignalLost = connectionStatus === "disconnected" || connectionStatus === "error";
  const isCompleted = data.status === "completed";
  const isFinalView = displayMode === "final" && isCompleted;
  
  // Determine which round winner to show based on displayMode
  const activeRoundWinner = displayMode === "rd1_winner" ? 0 
    : displayMode === "rd2_winner" ? 1 
    : displayMode === "rd3_winner" ? 2 
    : null;

  return (
    <div className="relative w-full h-full bg-black overflow-hidden">
      {/* Main Content */}
      <div className="flex flex-col h-full lb-broadcast-frame">
        <TopBar event={data.event} division={data.division} compact={isFinalView} />
        
        <FighterHeader
          redName={data.red.name}
          blueName={data.blue.name}
          winner={data.winner}
          compact={isFinalView}
        />

        <div className={`${isFinalView ? 'flex-shrink-0' : 'flex-1'} min-h-0 overflow-hidden`}>
          <ScoreGrid 
            rounds={data.rounds} 
            maxRounds={5} 
            redName={data.red.name}
            blueName={data.blue.name}
            isCompleted={isCompleted}
            activeRoundWinner={activeRoundWinner}
            isManualMode={displayMode !== "scores" || isCompleted}
            compact={isFinalView}
            hideTotals={isFinalView}
          />
        </div>
        <div className="flex-shrink-0">
          <FinalResult
            total={data.unified_total}
            winner={data.winner}
            redName={data.red.name}
            blueName={data.blue.name}
            isVisible={displayMode === "final" && isCompleted}
          />
        </div>
      </div>

      {/* Overlay States */}
      <SignalLostOverlay isVisible={isSignalLost && !isStandby} />
      <StandbyScreen event={data.event} isVisible={isStandby} />

      {/* Gold Corner Accents (always visible) */}
      <div className="absolute top-0 left-0 w-16 h-16 pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-lb-gold to-transparent" />
        <div className="absolute top-0 left-0 w-0.5 h-full bg-gradient-to-b from-lb-gold to-transparent" />
      </div>
      <div className="absolute top-0 right-0 w-16 h-16 pointer-events-none">
        <div className="absolute top-0 right-0 w-full h-0.5 bg-gradient-to-l from-lb-gold to-transparent" />
        <div className="absolute top-0 right-0 w-0.5 h-full bg-gradient-to-b from-lb-gold to-transparent" />
      </div>
      <div className="absolute bottom-0 left-0 w-16 h-16 pointer-events-none">
        <div className="absolute bottom-0 left-0 w-full h-0.5 bg-gradient-to-r from-lb-gold to-transparent" />
        <div className="absolute bottom-0 left-0 w-0.5 h-full bg-gradient-to-t from-lb-gold to-transparent" />
      </div>
      <div className="absolute bottom-0 right-0 w-16 h-16 pointer-events-none">
        <div className="absolute bottom-0 right-0 w-full h-0.5 bg-gradient-to-l from-lb-gold to-transparent" />
        <div className="absolute bottom-0 right-0 w-0.5 h-full bg-gradient-to-t from-lb-gold to-transparent" />
      </div>
    </div>
  );
});
