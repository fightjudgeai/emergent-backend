import { useState, useCallback, useRef } from "react";

const mockData = {
  event: "PFC 50",
  fight_id: "demo-001",
  division: "Lightweight",
  red: { name: "Marcus Silva" },
  blue: { name: "Jake Thompson" },
  rounds: [],
  unified_total: { red: 0, blue: 0 },
  winner: null,
  status: "pending",
};

const demoRoundsRedWins = [
  { round: 1, unified_red: 10, unified_blue: 9 },
  { round: 2, unified_red: 9, unified_blue: 10 },
  { round: 3, unified_red: 10, unified_blue: 9 },
];

const demoRoundsBlueWins = [
  { round: 1, unified_red: 9, unified_blue: 10 },
  { round: 2, unified_red: 9, unified_blue: 10 },
  { round: 3, unified_red: 10, unified_blue: 9 },
];

export function useDemoMode() {
  const [data, setData] = useState(mockData);
  const [connectionStatus] = useState("connected");
  const [isLoading, setIsLoading] = useState(false);
  const [displayMode, setDisplayMode] = useState("scores");
  const simulationRef = useRef(null);

  const loadRounds = useCallback((blueWins = false) => {
    const rounds = blueWins ? demoRoundsBlueWins : demoRoundsRedWins;
    const total = {
      red: rounds.reduce((sum, r) => sum + r.unified_red, 0),
      blue: rounds.reduce((sum, r) => sum + r.unified_blue, 0),
    };

    setData({
      ...mockData,
      rounds,
      unified_total: total,
      status: "in_progress",
      winner: null,
    });
    setDisplayMode("scores");
  }, []);

  const startSimulation = useCallback((blueWins = false) => {
    let currentRound = 0;
    const rounds = blueWins ? demoRoundsBlueWins : demoRoundsRedWins;

    setData({ ...mockData, status: "in_progress" });
    setDisplayMode("scores");
    setIsLoading(false);

    const simulateRound = () => {
      if (currentRound < rounds.length) {
        const roundData = rounds[currentRound];
        
        setData((prev) => {
          const newRounds = [...prev.rounds, roundData];
          const newTotal = {
            red: newRounds.reduce((sum, r) => sum + r.unified_red, 0),
            blue: newRounds.reduce((sum, r) => sum + r.unified_blue, 0),
          };

          return {
            ...prev,
            rounds: newRounds,
            unified_total: newTotal,
            status: currentRound === rounds.length - 1 ? "completed" : "in_progress",
            winner: currentRound === rounds.length - 1 
              ? (newTotal.red > newTotal.blue ? "red" : newTotal.blue > newTotal.red ? "blue" : "draw")
              : null,
          };
        });

        currentRound++;
        
        if (currentRound < rounds.length) {
          simulationRef.current = setTimeout(simulateRound, 2500);
        }
      }
    };

    simulationRef.current = setTimeout(simulateRound, 1500);
  }, []);

  const showRoundWinner = useCallback((roundNumber) => {
    setDisplayMode(`rd${roundNumber}_winner`);
  }, []);

  const showFinalResult = useCallback(() => {
    setData((prev) => ({
      ...prev,
      status: "completed",
      winner: prev.unified_total.red > prev.unified_total.blue 
        ? "red" 
        : prev.unified_total.blue > prev.unified_total.red 
        ? "blue" 
        : "draw",
    }));
    setDisplayMode("final");
  }, []);

  const showScoresOnly = useCallback(() => {
    setDisplayMode("scores");
  }, []);

  const resetToStandby = useCallback(() => {
    if (simulationRef.current) {
      clearTimeout(simulationRef.current);
    }
    setData({ ...mockData, status: "pending" });
    setDisplayMode("scores");
  }, []);

  return {
    data,
    connectionStatus,
    isLoading,
    displayMode,
    loadRounds,
    startSimulation,
    showRoundWinner,
    showFinalResult,
    showScoresOnly,
    resetToStandby,
  };
}
