import { memo, useState, useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users, RefreshCw, Wifi, Check, Clock } from "lucide-react";

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

/**
 * Multi-Judge Scoreboard - Shows all judges' scores and unified totals
 */
export const MultiJudgeScoreboard = memo(function MultiJudgeScoreboard({ boutId, refreshInterval = 2000 }) {
  const [syncStatus, setSyncStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchSyncStatus = useCallback(async () => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${API_BASE}/api/sync/status/${boutId}`);
      if (response.ok) {
        const data = await response.json();
        setSyncStatus(data);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error('[MultiJudge] Fetch error:', error);
    }
  }, [boutId]);

  // Auto-refresh
  useEffect(() => {
    if (!boutId) return;
    
    fetchSyncStatus();
    const interval = setInterval(fetchSyncStatus, refreshInterval);
    
    return () => clearInterval(interval);
  }, [boutId, refreshInterval, fetchSyncStatus]);

  const handleRefresh = async () => {
    setIsLoading(true);
    await fetchSyncStatus();
    setIsLoading(false);
  };

  if (!syncStatus) {
    return (
      <div className="p-4 text-center text-gray-400">
        <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>Waiting for sync data...</p>
      </div>
    );
  }

  const { judges, unified_scores, unified_total_red, unified_total_blue, fighter1, fighter2, active_judges } = syncStatus;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-lb-gold" />
          <span className="text-lg font-semibold text-white">
            Multi-Judge Scoreboard
          </span>
          <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
            {active_judges} Active
          </span>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleRefresh}
          disabled={isLoading}
          className="h-8"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Unified Totals */}
      <Card className="bg-gray-900/80 border-lb-gold/30 p-4">
        <div className="text-center mb-2">
          <span className="text-xs text-gray-400 uppercase tracking-wider">Unified Score</span>
        </div>
        <div className="grid grid-cols-3 gap-4 items-center">
          <div className="text-center">
            <div className="text-sm text-red-400 mb-1">{fighter1}</div>
            <div className="text-4xl font-bold text-red-500">{unified_total_red || 0}</div>
          </div>
          <div className="text-center">
            <div className="text-2xl text-gray-500">VS</div>
          </div>
          <div className="text-center">
            <div className="text-sm text-blue-400 mb-1">{fighter2}</div>
            <div className="text-4xl font-bold text-blue-500">{unified_total_blue || 0}</div>
          </div>
        </div>
      </Card>

      {/* Round-by-Round Unified */}
      {unified_scores && unified_scores.length > 0 && (
        <Card className="bg-gray-900/60 border-gray-700 p-4">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-3">Round Scores (Unified)</div>
          <div className="space-y-2">
            {unified_scores.map((round) => (
              <div key={round.round} className="flex items-center justify-between bg-gray-800/50 rounded px-3 py-2">
                <span className="text-gray-400">RD {round.round}</span>
                <div className="flex items-center gap-4">
                  <span className="text-red-400 font-mono text-lg">{round.unified_red || round.red_score}</span>
                  <span className="text-gray-500">-</span>
                  <span className="text-blue-400 font-mono text-lg">{round.unified_blue || round.blue_score}</span>
                </div>
                {round.num_judges && (
                  <span className="text-xs text-gray-500">({round.num_judges} judges)</span>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Individual Judge Scores */}
      {judges && judges.length > 0 && (
        <Card className="bg-gray-900/60 border-gray-700 p-4">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-3">Individual Judges</div>
          <div className="space-y-3">
            {judges.map((judge) => (
              <div key={judge.judge_id} className="bg-gray-800/50 rounded p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Wifi className="w-3 h-3 text-green-400" />
                    <span className="text-white font-medium">{judge.judge_name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-red-400 font-mono">{judge.total_red}</span>
                    <span className="text-gray-500">-</span>
                    <span className="text-blue-400 font-mono">{judge.total_blue}</span>
                  </div>
                </div>
                {/* Round breakdown */}
                <div className="flex gap-2 flex-wrap">
                  {Object.entries(judge.rounds || {}).map(([roundNum, score]) => (
                    <div key={roundNum} className="px-2 py-1 bg-gray-700/50 rounded text-xs">
                      <span className="text-gray-400">R{roundNum}:</span>
                      <span className="text-red-400 ml-1">{score.red}</span>
                      <span className="text-gray-500">-</span>
                      <span className="text-blue-400">{score.blue}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Last Update */}
      {lastUpdate && (
        <div className="text-center text-xs text-gray-500 flex items-center justify-center gap-1">
          <Clock className="w-3 h-3" />
          Last sync: {lastUpdate.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
});

/**
 * Compact Judge Status Indicator
 */
export const JudgeStatusIndicator = memo(function JudgeStatusIndicator({ boutId, refreshInterval = 5000 }) {
  const [activeJudges, setActiveJudges] = useState([]);

  useEffect(() => {
    if (!boutId) return;

    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/sync/status/${boutId}`);
        if (response.ok) {
          const data = await response.json();
          setActiveJudges(data.judges || []);
        }
      } catch (error) {
        console.error('[JudgeStatus] Error:', error);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [boutId, refreshInterval]);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900/80 border border-gray-700 rounded-lg">
      <Users className="w-4 h-4 text-lb-gold" />
      <span className="text-xs text-gray-400">Judges:</span>
      <div className="flex gap-1">
        {activeJudges.length === 0 ? (
          <span className="text-xs text-gray-500">None connected</span>
        ) : (
          activeJudges.map((judge, idx) => (
            <div
              key={judge.judge_id}
              className="flex items-center gap-1 px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs"
              title={judge.judge_name}
            >
              <Check className="w-3 h-3" />
              {judge.judge_name.split(' ')[0]}
            </div>
          ))
        )}
      </div>
    </div>
  );
});

export default MultiJudgeScoreboard;
