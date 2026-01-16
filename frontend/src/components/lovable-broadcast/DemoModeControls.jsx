import { memo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Settings, X, Play, Eye, Trophy, RotateCcw, Tv, Radio } from "lucide-react";

export const DemoModeControls = memo(function DemoModeControls({
  onLoadRounds,
  onStartSimulation,
  onShowRoundWinner,
  onShowFinalResult,
  onShowScoresOnly,
  onReset,
  displayMode,
  hasRounds,
  roundCount,
  isDemo,
  onSwitchMode,
}) {
  const [isOpen, setIsOpen] = useState(false);

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 left-4 z-50 w-10 h-10 rounded-full bg-lb-gold/20 border border-lb-gold/30 flex items-center justify-center hover:bg-lb-gold/30 transition-colors"
      >
        <Settings className="w-4 h-4 text-lb-gold" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 left-4 z-50 bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-xl min-w-[220px]">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-lb-gold uppercase tracking-wider">
          Controls
        </span>
        <button
          onClick={() => setIsOpen(false)}
          className="w-5 h-5 rounded flex items-center justify-center hover:bg-gray-700 transition-colors"
        >
          <X className="w-3 h-3 text-gray-400" />
        </button>
      </div>

      <div className="space-y-2">
        {/* Mode Toggle */}
        <div className="flex items-center gap-1 bg-gray-800 rounded-lg p-1">
          <Button
            size="sm"
            variant={isDemo ? "default" : "ghost"}
            onClick={() => onSwitchMode(true)}
            className="h-7 px-3 text-xs gap-1.5 flex-1"
          >
            <Tv className="w-3 h-3" />
            Demo
          </Button>
          <Button
            size="sm"
            variant={!isDemo ? "default" : "ghost"}
            onClick={() => onSwitchMode(false)}
            className="h-7 px-3 text-xs gap-1.5 flex-1"
          >
            <Radio className="w-3 h-3" />
            Live
          </Button>
        </div>

        {/* Load / Simulate - Demo mode only */}
        {isDemo && !hasRounds && (
          <>
            <div className="grid grid-cols-2 gap-1">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onLoadRounds(false)}
                className="h-7 text-xs"
              >
                Load Red Win
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => onLoadRounds(true)}
                className="h-7 text-xs"
              >
                Load Blue Win
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-1">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => onStartSimulation(false)}
                className="h-7 text-xs gap-1"
              >
                <Play className="w-3 h-3" /> Red
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => onStartSimulation(true)}
                className="h-7 text-xs gap-1"
              >
                <Play className="w-3 h-3" /> Blue
              </Button>
            </div>
          </>
        )}

        {/* Display Controls */}
        {hasRounds && (
          <>
            <Button
              size="sm"
              variant={displayMode === "scores" ? "default" : "outline"}
              onClick={onShowScoresOnly}
              className="w-full h-7 text-xs justify-start gap-2"
            >
              <Eye className="w-3 h-3" />
              Show Scores
            </Button>

            <div className="grid grid-cols-3 gap-1">
              {[1, 2, 3].map((round) => (
                <Button
                  key={round}
                  size="sm"
                  variant={displayMode === `rd${round}_winner` ? "default" : "outline"}
                  onClick={() => onShowRoundWinner(round)}
                  className="h-7 text-xs"
                  disabled={roundCount < round}
                >
                  R{round}
                </Button>
              ))}
            </div>

            <Button
              size="sm"
              variant={displayMode === "final" ? "default" : "secondary"}
              onClick={onShowFinalResult}
              className="w-full h-7 text-xs justify-start gap-2"
              disabled={roundCount < 3}
            >
              <Trophy className="w-3 h-3" />
              Final Result
            </Button>
          </>
        )}

        {/* Reset */}
        <Button
          size="sm"
          variant="ghost"
          onClick={onReset}
          className="w-full h-7 text-xs justify-start gap-2 text-gray-400"
        >
          <RotateCcw className="w-3 h-3" />
          Reset
        </Button>
      </div>
    </div>
  );
});
