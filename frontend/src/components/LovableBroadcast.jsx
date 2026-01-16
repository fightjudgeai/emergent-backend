import { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { BroadcastScorecard } from "@/components/lovable-broadcast/BroadcastScorecard";
import { DemoModeControls } from "@/components/lovable-broadcast/DemoModeControls";
import { ConnectionIndicator } from "@/components/lovable-broadcast/ConnectionIndicator";
import { useFightJudgeAPI } from "@/hooks/useFightJudgeAPI";
import { useDemoMode } from "@/hooks/useDemoMode";
import { Maximize, Minimize } from "lucide-react";
import "@/styles/lovable-broadcast.css";

export default function LovableBroadcast() {
  const { boutId: paramBoutId } = useParams();
  const [searchParams] = useSearchParams();
  const urlBoutId = searchParams.get('bout') || paramBoutId;
  
  const [isDemo, setIsDemo] = useState(!urlBoutId);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [boutId, setBoutId] = useState(urlBoutId);
  
  // Live API hook
  const liveApi = useFightJudgeAPI(isDemo ? undefined : boutId);
  
  // Demo mode hook
  const demo = useDemoMode();

  // Use demo or live data based on mode
  const activeData = isDemo ? demo : liveApi;

  // Final display data
  const displayData = activeData.data;

  const handleConnect = (id) => {
    setBoutId(id);
    liveApi.connectToBout(id);
  };

  const handleReset = () => {
    if (isDemo) {
      demo.resetToStandby();
    } else {
      setBoutId(undefined);
      liveApi.resetToStandby();
    }
  };

  const handleSwitchMode = (demoMode) => {
    setIsDemo(demoMode);
    if (demoMode) {
      demo.resetToStandby();
    }
  };

  const toggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  // Auto-connect if boutId in URL
  useEffect(() => {
    if (urlBoutId && !isDemo) {
      handleConnect(urlBoutId);
    }
  }, [urlBoutId]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Fullscreen toggle (F key)
      if ((e.key === "f" || e.key === "F") && !e.ctrlKey && !e.shiftKey) {
        if (document.activeElement?.tagName !== "INPUT") {
          e.preventDefault();
          toggleFullscreen();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [toggleFullscreen]);

  // Hide cursor after 3 seconds of inactivity
  useEffect(() => {
    let timeout;
    const hideCursor = () => {
      document.body.style.cursor = 'none';
    };
    const showCursor = () => {
      document.body.style.cursor = 'auto';
      clearTimeout(timeout);
      timeout = setTimeout(hideCursor, 3000);
    };
    
    document.addEventListener('mousemove', showCursor);
    timeout = setTimeout(hideCursor, 3000);
    
    return () => {
      document.removeEventListener('mousemove', showCursor);
      clearTimeout(timeout);
      document.body.style.cursor = 'auto';
    };
  }, []);

  return (
    <main className="w-screen h-screen bg-black overflow-hidden">
      <BroadcastScorecard
        data={displayData}
        connectionStatus={activeData.connectionStatus}
        isLoading={activeData.isLoading}
        displayMode={activeData.displayMode}
      />

      {/* Connection Status Indicator */}
      <ConnectionIndicator
        connectionStatus={activeData.connectionStatus}
        boutId={boutId}
        isDemo={isDemo}
      />
      
      {/* Controls - hidden in fullscreen */}
      {!isFullscreen && (
        <DemoModeControls
          onLoadRounds={demo.loadRounds}
          onStartSimulation={demo.startSimulation}
          onShowRoundWinner={isDemo ? demo.showRoundWinner : liveApi.showRoundWinner}
          onShowFinalResult={isDemo ? demo.showFinalResult : liveApi.showFinalResult}
          onShowScoresOnly={isDemo ? demo.showScoresOnly : liveApi.showScoresOnly}
          onReset={handleReset}
          displayMode={activeData.displayMode}
          hasRounds={displayData.rounds.length > 0}
          roundCount={displayData.rounds.length}
          isDemo={isDemo}
          onSwitchMode={handleSwitchMode}
        />
      )}

      {/* Fullscreen Toggle */}
      <button
        onClick={toggleFullscreen}
        className={`fixed z-50 w-8 h-8 rounded flex items-center justify-center transition-all ${
          isFullscreen 
            ? "bottom-2 right-2 bg-black/30 hover:bg-black/50 border border-gray-600" 
            : "bottom-4 right-4 bg-gray-900 border border-gray-600 shadow-lg hover:bg-gray-800"
        }`}
        title={isFullscreen ? "Exit Fullscreen (F)" : "Fullscreen (F)"}
      >
        {isFullscreen ? (
          <Minimize className="w-3.5 h-3.5 text-gray-400" />
        ) : (
          <Maximize className="w-3.5 h-3.5 text-gray-300" />
        )}
      </button>
    </main>
  );
}
