import { useState, useEffect, useCallback, useRef } from "react";

// Use environment variable for backend URL
const API_BASE = process.env.REACT_APP_BACKEND_URL || '';
const CACHE_KEY = "fightjudge_offline_cache";

const defaultData = {
  event: "PFC 50",
  fight_id: "",
  division: "",
  red: { name: "Red Corner" },
  blue: { name: "Blue Corner" },
  rounds: [],
  unified_total: { red: 0, blue: 0 },
  winner: null,
  status: "pending",
};

// Offline cache helpers
const saveToCache = (boutId, data) => {
  try {
    const cache = {
      boutId,
      data,
      timestamp: Date.now(),
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
    console.log("[FightJudge] Cached data for offline use");
  } catch (e) {
    console.warn("[FightJudge] Failed to cache data:", e);
  }
};

const loadFromCache = (boutId) => {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;
    
    const cache = JSON.parse(cached);
    
    if (boutId && cache.boutId !== boutId) return null;
    
    const maxAge = 24 * 60 * 60 * 1000;
    if (Date.now() - cache.timestamp > maxAge) {
      localStorage.removeItem(CACHE_KEY);
      return null;
    }
    
    console.log("[FightJudge] Loaded cached data from", new Date(cache.timestamp).toLocaleTimeString());
    return cache.data;
  } catch (e) {
    console.warn("[FightJudge] Failed to load cache:", e);
    return null;
  }
};

export function useFightJudgeAPI(boutId) {
  const [data, setData] = useState(defaultData);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [isLoading, setIsLoading] = useState(true);
  const [displayMode, setDisplayMode] = useState("scores");
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const pollingRef = useRef(null);
  const currentBoutIdRef = useRef(boutId);
  const initialLoadDoneRef = useRef(false);

  useEffect(() => {
    currentBoutIdRef.current = boutId;
  }, [boutId]);

  useEffect(() => {
    if (!initialLoadDoneRef.current && boutId) {
      initialLoadDoneRef.current = true;
      const cached = loadFromCache(boutId);
      if (cached) {
        setData(cached);
        console.log("[FightJudge] Loaded cached data on mount");
      }
    }
  }, [boutId]);

  // Transform API response to BroadcastData format
  const transformResponse = useCallback((response) => {
    // Handle the existing backend format from /api/live/{bout_id}
    const rounds = [];
    
    // If rounds array exists in response
    if (response.rounds && Array.isArray(response.rounds)) {
      response.rounds.forEach((r, idx) => {
        rounds.push({
          round: idx + 1,
          unified_red: r.fighter1_score || r.red_score || r.unified_red || 0,
          unified_blue: r.fighter2_score || r.blue_score || r.unified_blue || 0,
        });
      });
    }
    
    // Calculate totals
    const totalRed = response.fighter1_total || response.total_red || 
      rounds.reduce((sum, r) => sum + r.unified_red, 0);
    const totalBlue = response.fighter2_total || response.total_blue || 
      rounds.reduce((sum, r) => sum + r.unified_blue, 0);

    return {
      event: response.event || "PFC 50",
      fight_id: response.bout_id || boutId,
      division: response.division || "",
      red: { name: response.fighter1_name || response.red_fighter || "Red Corner" },
      blue: { name: response.fighter2_name || response.blue_fighter || "Blue Corner" },
      rounds,
      unified_total: { red: totalRed, blue: totalBlue },
      winner: response.winner || null,
      status: response.status || "in_progress",
    };
  }, [boutId]);

  const updateData = useCallback((newData, boutIdForCache) => {
    setData(newData);
    if (boutIdForCache && newData.rounds.length > 0) {
      saveToCache(boutIdForCache, newData);
    }
  }, []);

  // Fetch live data via REST polling
  const fetchLiveData = useCallback(async (id) => {
    try {
      setIsOfflineMode(false);
      const response = await fetch(`${API_BASE}/api/live/${id}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const result = await response.json();
      const transformedData = transformResponse(result);
      updateData(transformedData, id);
      setConnectionStatus("connected");
      setIsLoading(false);
      console.log("[FightJudge] Live data loaded:", result);
    } catch (error) {
      console.error("[FightJudge] Failed to fetch live data:", error);
      
      const cached = loadFromCache(id);
      if (cached) {
        setData(cached);
        setIsOfflineMode(true);
        setConnectionStatus("disconnected");
        console.log("[FightJudge] Using offline cached data");
      } else {
        setConnectionStatus("error");
      }
      setIsLoading(false);
    }
  }, [transformResponse, updateData]);

  // Fetch final results
  const fetchFinalResult = useCallback(async (id) => {
    try {
      const response = await fetch(`${API_BASE}/api/final/${id}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const result = await response.json();
      const transformedData = transformResponse(result);
      updateData(transformedData, id);
      setDisplayMode("final");
      console.log("[FightJudge] Final result loaded:", result);
    } catch (error) {
      console.error("[FightJudge] Failed to fetch final result:", error);
    }
  }, [transformResponse, updateData]);

  // Start polling for a bout
  const connectToBout = useCallback((id) => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    
    setIsLoading(true);
    fetchLiveData(id);
    
    // Poll every 2 seconds
    pollingRef.current = setInterval(() => {
      fetchLiveData(id);
    }, 2000);
  }, [fetchLiveData]);

  // Manual display controls
  const showRoundWinner = useCallback((roundNumber) => {
    setDisplayMode(`rd${roundNumber}_winner`);
  }, []);

  const showFinalResult = useCallback(() => {
    if (boutId) {
      fetchFinalResult(boutId);
    }
    setDisplayMode("final");
  }, [boutId, fetchFinalResult]);

  const showScoresOnly = useCallback(() => {
    setDisplayMode("scores");
  }, []);

  const resetToStandby = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    setData(defaultData);
    setConnectionStatus("disconnected");
    setDisplayMode("scores");
    setIsLoading(false);
    setIsOfflineMode(false);
  }, []);

  // Auto-connect when boutId changes
  useEffect(() => {
    if (boutId) {
      connectToBout(boutId);
    } else {
      setIsLoading(false);
    }
    
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [boutId, connectToBout]);

  // Emergency refresh hotkey
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === "R") {
        e.preventDefault();
        if (boutId) {
          connectToBout(boutId);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [boutId, connectToBout]);

  return {
    data,
    connectionStatus,
    isLoading,
    displayMode,
    isOfflineMode,
    connectToBout,
    showRoundWinner,
    showFinalResult,
    showScoresOnly,
    resetToStandby,
    refreshData: () => boutId && fetchLiveData(boutId),
  };
}
