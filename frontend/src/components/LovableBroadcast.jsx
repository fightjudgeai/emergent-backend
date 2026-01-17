import { useState, useEffect, useCallback } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { BroadcastScorecard } from "@/components/lovable-broadcast/BroadcastScorecard";
import { BoutSelector } from "@/components/lovable-broadcast/BoutSelector";
import { OperatorPanel } from "@/components/lovable-broadcast/OperatorPanel";
import { DemoModeControls } from "@/components/lovable-broadcast/DemoModeControls";
import { ConnectionIndicator } from "@/components/lovable-broadcast/ConnectionIndicator";
import { ManualScoreOverride } from "@/components/lovable-broadcast/ManualScoreOverride";
import { MultiJudgeScoreboard, JudgeStatusIndicator } from "@/components/lovable-broadcast/MultiJudgeScoreboard";
import { useFightJudgeAPI } from "@/hooks/useFightJudgeAPI";
import { useDemoMode } from "@/hooks/useDemoMode";
import { Maximize, Minimize, Users } from "lucide-react";
import "@/styles/lovable-broadcast.css";

export default function LovableBroadcast() {
  const { boutId: paramBoutId } = useParams();
  const [searchParams] = useSearchParams();
  const urlBoutId = searchParams.get('bout') || paramBoutId;
  
  const [isDemo, setIsDemo] = useState(!urlBoutId);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [boutId, setBoutId] = useState(urlBoutId);
  const [overrideData, setOverrideData] = useState(null);
  const [showOverridePanel, setShowOverridePanel] = useState(false);
  const [showMultiJudge, setShowMultiJudge] = useState(false);
  
  // Live API hook
  const liveApi = useFightJudgeAPI(isDemo ? undefined : boutId);
  
  // Demo mode hook
  const demo = useDemoMode();

  // Use demo or live data based on mode
  const activeData = isDemo ? demo : liveApi;

  // Final display data: override takes precedence
  const displayData = overrideData || activeData.data;

  const handleConnect = (id) => {
    setBoutId(id);
    setIsDemo(false);
    liveApi.connectToBout(id);
  };

  const handleReset = () => {
    if (isDemo) {
      demo.resetToStandby();
    } else {
      setBoutId(undefined);
      liveApi.resetToStandby();
    }
    setOverrideData(null);
  };

  const handleSwitchMode = (demoMode) => {
    setIsDemo(demoMode);
    if (demoMode) {
      demo.resetToStandby();
    }
    setOverrideData(null);
  };

  const handleOverride = useCallback((data) => {
    setOverrideData(data);
    console.log("[ManualOverride] Override applied:", data);
  }, []);

  const handleClearOverride = useCallback(() => {
    setOverrideData(null);
    console.log("[ManualOverride] Override cleared");
  }, []);

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
      // Override panel toggle (Ctrl+Shift+O)
      if (e.ctrlKey && e.shiftKey && (e.key === "o" || e.key === "O")) {
        e.preventDefault();
        setShowOverridePanel((prev) => !prev);
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

  const isFinalView = activeData.displayMode === "final" && displayData.status === "completed";

  return (
    <main className="w-screen h-screen bg-black overflow-hidden">
      <BroadcastScorecard
        data={displayData}
        connectionStatus={overrideData ? "connected" : activeData.connectionStatus}
        isLoading={activeData.isLoading}
        displayMode={activeData.displayMode}
      />

      {/* Connection Status Indicator */}
      <ConnectionIndicator
        connectionStatus={overrideData ? "connected" : activeData.connectionStatus}
        boutId={boutId}
        isDemo={isDemo}
        isOverride={!!overrideData}
      />
      
      {/* Controls - hidden in fullscreen */}
      {!isFullscreen && (
        <>
          {/* Live mode: Bout Selector in top left */}
          {!isDemo && (
            <div className="fixed top-4 left-4 z-50">
              <BoutSelector
                onConnect={handleConnect}
                onRefresh={liveApi.refreshData}
                onReset={handleReset}
                connectionStatus={liveApi.connectionStatus}
                currentBoutId={boutId}
              />
            </div>
          )}

          {/* Demo Mode Controls - bottom left */}
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

          {/* Operator Panel - top right (below connection indicator) */}
          {!isDemo && displayData.rounds.length > 0 && (
            <OperatorPanel
              onShowRoundWinner={liveApi.showRoundWinner}
              onShowFinalResult={liveApi.showFinalResult}
              onShowScoresOnly={liveApi.showScoresOnly}
              onReset={handleReset}
              displayMode={activeData.displayMode}
              hasRounds={displayData.rounds.length > 0}
              roundCount={displayData.rounds.length}
              isLive={liveApi.connectionStatus === "connected"}
              fighterRed={displayData.red.name}
              fighterBlue={displayData.blue.name}
            />
          )}

          {/* Emergency Manual Override - bottom left (above demo controls) */}
          {!isFinalView && (
            <div className="fixed bottom-16 left-4 z-50">
              <ManualScoreOverride
                currentData={activeData.data}
                onOverride={handleOverride}
                onClearOverride={handleClearOverride}
                isOverrideActive={!!overrideData}
              />
            </div>
          )}
        </>
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
