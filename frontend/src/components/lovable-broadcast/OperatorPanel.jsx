import { memo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Monitor, X, Eye, Trophy, RotateCcw, Zap } from "lucide-react";

export const OperatorPanel = memo(function OperatorPanel({ 
  onShowRoundWinner, 
  onShowFinalResult, 
  onShowScoresOnly, 
  onReset, 
  displayMode, 
  hasRounds, 
  roundCount, 
  isLive, 
  fighterRed = "RED", 
  fighterBlue = "BLUE" 
}) {
  const [isOpen, setIsOpen] = useState(false);

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)} 
        className="fixed top-16 right-4 z-50 px-4 py-2 rounded-lg bg-lb-gold/90 border border-lb-gold flex items-center gap-2 hover:bg-lb-gold transition-colors shadow-lg"
      >
        <Monitor className="w-4 h-4 text-black" />
        <span className="text-sm font-bold text-black uppercase tracking-wide">Operator Panel</span>
      </button>
    );
  }

  const getCurrentDisplayLabel = () => {
    if (displayMode === "scores") return "LIVE SCORES";
    if (displayMode === "final") return "FINAL RESULT";
    if (displayMode.includes("winner")) { 
      const round = displayMode.replace("rd", "").replace("_winner", ""); 
      return `ROUND ${round} WINNER`; 
    }
    return displayMode.toUpperCase();
  };

  return (
    <div className="fixed top-16 right-4 z-50 bg-gray-900/98 backdrop-blur-md border-2 border-lb-gold/50 rounded-xl p-4 shadow-2xl min-w-[320px]">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-lb-gold" />
          <span className="text-sm font-bold text-lb-gold uppercase tracking-wider">PFC 50 Arena Control</span>
        </div>
        <button onClick={() => setIsOpen(false)} className="w-6 h-6 rounded flex items-center justify-center hover:bg-gray-800 transition-colors">
          <X className="w-4 h-4 text-gray-400" />
        </button>
      </div>
      
      {/* Current Display Status */}
      <div className="mb-4 p-2 rounded-lg bg-gray-800 border border-gray-700">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400 uppercase">Current Display:</span>
          <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded ${
            displayMode === "final" ? "bg-yellow-500/20 text-yellow-400" : 
            displayMode.includes("winner") ? "bg-green-500/20 text-green-400" : 
            "bg-lb-gold/20 text-lb-gold"
          }`}>
            {getCurrentDisplayLabel()}
          </span>
        </div>
        {isLive && (
          <div className="mt-2 flex items-center gap-2">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            <span className="text-xs text-red-400 font-medium">BROADCASTING LIVE</span>
          </div>
        )}
      </div>
      
      {/* Fighter Names */}
      <div className="mb-4 p-2 rounded-lg bg-gray-800/50 text-center">
        <div className="flex items-center justify-center gap-3 text-sm">
          <span className="font-bold text-red-400">{fighterRed}</span>
          <span className="text-gray-500">vs</span>
          <span className="font-bold text-blue-400">{fighterBlue}</span>
        </div>
      </div>
      
      {/* Controls */}
      <div className="space-y-3">
        <Button 
          size="lg" 
          variant={displayMode === "scores" ? "default" : "outline"} 
          onClick={onShowScoresOnly} 
          className="w-full h-12 text-sm font-bold justify-start gap-3" 
          disabled={!hasRounds}
        >
          <Eye className="w-5 h-5" />SHOW LIVE SCORES
        </Button>
        
        <div className="space-y-2">
          <span className="text-xs text-gray-400 uppercase tracking-wide">Round Winners</span>
          <div className="grid grid-cols-3 gap-2">
            {[1, 2, 3].map((round) => (
              <Button 
                key={round} 
                size="lg" 
                variant={displayMode === `rd${round}_winner` ? "default" : "secondary"} 
                onClick={() => onShowRoundWinner(round)} 
                className={`h-14 text-base font-bold ${roundCount >= round ? "hover:scale-105 transition-transform" : "opacity-50"}`} 
                disabled={roundCount < round}
              >
                RD {round}
              </Button>
            ))}
          </div>
        </div>
        
        <Button 
          size="lg" 
          variant={displayMode === "final" ? "default" : "outline"} 
          onClick={onShowFinalResult} 
          className={`w-full h-14 text-base font-bold justify-center gap-3 ${
            roundCount >= 3 
              ? "bg-gradient-to-r from-yellow-600/80 to-yellow-500/80 hover:from-yellow-500 hover:to-yellow-400 text-white border-yellow-500/50 hover:scale-105 transition-transform" 
              : "opacity-50"
          }`} 
          disabled={roundCount < 3}
        >
          <Trophy className="w-5 h-5" />SHOW FINAL RESULT
        </Button>
        
        <Button 
          size="sm" 
          variant="ghost" 
          onClick={onReset} 
          className="w-full h-8 text-xs text-gray-400 hover:text-white gap-2"
        >
          <RotateCcw className="w-3 h-3" />Reset Display
        </Button>
      </div>
      
      <div className="mt-4 pt-3 border-t border-gray-700">
        <div className="text-[10px] text-gray-500 text-center space-y-1">
          <div>Press <kbd className="px-1 py-0.5 bg-gray-800 rounded text-[9px]">F</kbd> for fullscreen</div>
        </div>
      </div>
    </div>
  );
});
