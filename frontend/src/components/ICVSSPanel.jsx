import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import axios from 'axios';
import { toast } from 'sonner';
import { Activity, Wifi, WifiOff, Zap, TrendingUp } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || import.meta.env.VITE_REACT_APP_BACKEND_URL;

export default function ICVSSPanel({ boutId, currentRound }) {
  const [cvMode, setCvMode] = useState(false);
  const [roundId, setRoundId] = useState(null);
  const [cvScore, setCvScore] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [wsConnection, setWsConnection] = useState(null);
  const [cvEventCount, setCvEventCount] = useState(0);
  const [simulationRunning, setSimulationRunning] = useState(false);

  // Initialize ICVSS round when CV mode is enabled
  const initializeICVSS = async () => {
    try {
      const response = await axios.post(`${API}/api/icvss/round/open`, null, {
        params: {
          bout_id: boutId,
          round_num: currentRound
        }
      });
      
      const newRoundId = response.data.round_id;
      setRoundId(newRoundId);
      
      // Connect WebSocket for score updates
      connectWebSocket(boutId);
      
      toast.success('CV Mode Enabled - ICVSS Activated');
      console.log('[ICVSS] Round opened:', newRoundId);
    } catch (error) {
      console.error('[ICVSS] Error initializing:', error);
      toast.error('Failed to enable CV Mode');
      setCvMode(false);
    }
  };

  // Connect to ICVSS WebSocket score feed
  const connectWebSocket = (bout) => {
    const wsUrl = `${API}/api/icvss/ws/score-feed/${bout}`.replace('https://', 'wss://').replace('http://', 'ws://');
    
    console.log('[ICVSS] Connecting to WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('[ICVSS] WebSocket connected');
      setWsConnected(true);
      toast.success('CV Feed Connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('[ICVSS] WebSocket message:', data);
      
      if (data.type === 'score_update') {
        setCvScore(data.data);
        console.log('[ICVSS] Score updated:', data.data.score_card);
      }
    };
    
    ws.onerror = (error) => {
      console.error('[ICVSS] WebSocket error:', error);
      setWsConnected(false);
    };
    
    ws.onclose = () => {
      console.log('[ICVSS] WebSocket disconnected');
      setWsConnected(false);
    };
    
    setWsConnection(ws);
  };

  // Toggle CV mode
  const handleCvModeToggle = async (enabled) => {
    setCvMode(enabled);
    
    if (enabled) {
      await initializeICVSS();
    } else {
      // Disconnect WebSocket
      if (wsConnection) {
        wsConnection.close();
        setWsConnection(null);
      }
      setRoundId(null);
      setCvScore(null);
      setCvEventCount(0);
      toast.info('CV Mode Disabled');
    }
  };

  // Simulate CV events for testing
  const simulateCVEvents = async () => {
    if (!roundId) {
      toast.error('CV Mode not enabled');
      return;
    }
    
    setSimulationRunning(true);
    
    const eventTypes = [
      { type: 'strike_jab', severity: 0.6, confidence: 0.92 },
      { type: 'strike_cross', severity: 0.8, confidence: 0.95 },
      { type: 'kick_body', severity: 0.7, confidence: 0.88 },
      { type: 'strike_hook', severity: 0.85, confidence: 0.93 },
      { type: 'KD_hard', severity: 1.0, confidence: 0.99 }
    ];
    
    try {
      // Simulate 10 events over 5 seconds
      for (let i = 0; i < 10; i++) {
        const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
        const fighter = Math.random() > 0.5 ? 'fighter1' : 'fighter2';
        
        const cvEvent = {
          bout_id: boutId,
          round_id: roundId,
          fighter_id: fighter,
          event_type: eventType.type,
          severity: eventType.severity,
          confidence: eventType.confidence,
          position: 'distance',
          timestamp_ms: Date.now() + (i * 500),
          source: 'cv_system',
          vendor_id: 'demo_simulator'
        };
        
        await axios.post(`${API}/api/icvss/round/event`, { event: cvEvent }, {
          params: { round_id: roundId }
        });
        
        setCvEventCount(prev => prev + 1);
        
        // Wait 500ms between events
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
      // Calculate score after all events
      const scoreResponse = await axios.get(`${API}/api/icvss/round/score/${roundId}`);
      setCvScore(scoreResponse.data);
      
      toast.success('Simulation Complete');
    } catch (error) {
      console.error('[ICVSS] Simulation error:', error);
      toast.error('Simulation failed');
    } finally {
      setSimulationRunning(false);
    }
  };

  // Get current score
  const refreshScore = async () => {
    if (!roundId) return;
    
    try {
      const response = await axios.get(`${API}/api/icvss/round/score/${roundId}`);
      setCvScore(response.data);
      toast.success('Score refreshed');
    } catch (error) {
      console.error('[ICVSS] Error refreshing score:', error);
      toast.error('Failed to refresh score');
    }
  };

  // Lock round
  const lockRound = async () => {
    if (!roundId) return;
    
    try {
      const response = await axios.post(`${API}/api/icvss/round/lock/${roundId}`);
      toast.success(`Round locked with hash: ${response.data.event_hash.slice(0, 16)}...`);
      console.log('[ICVSS] Round locked:', response.data);
    } catch (error) {
      console.error('[ICVSS] Error locking round:', error);
      toast.error('Failed to lock round');
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsConnection) {
        wsConnection.close();
      }
    };
  }, [wsConnection]);

  return (
    <Card className="bg-gradient-to-br from-purple-950/30 to-blue-950/30 border-purple-600/30 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Activity className="w-6 h-6 text-purple-400" />
          <h2 className="text-2xl font-bold text-purple-400">ICVSS - CV Enhanced Scoring</h2>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Connection Status */}
          {cvMode && (
            <div className="flex items-center gap-2">
              {wsConnected ? (
                <Wifi className="w-5 h-5 text-green-500 animate-pulse" />
              ) : (
                <WifiOff className="w-5 h-5 text-red-500" />
              )}
              <span className={`text-sm ${wsConnected ? 'text-green-400' : 'text-red-400'}`}>
                {wsConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          )}
          
          {/* CV Mode Toggle */}
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-400">CV Mode</span>
            <Switch
              checked={cvMode}
              onCheckedChange={handleCvModeToggle}
              className="data-[state=checked]:bg-purple-600"
            />
          </div>
        </div>
      </div>

      {!cvMode ? (
        <div className="text-center py-8">
          <Zap className="w-16 h-16 text-purple-400 mx-auto mb-4 opacity-50" />
          <p className="text-gray-400">Enable CV Mode to activate computer vision scoring</p>
          <p className="text-sm text-gray-500 mt-2">
            Hybrid scoring: 70% CV events + 30% manual judge events
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Round Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-black/30 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Round ID</div>
              <div className="text-xs text-purple-400 font-mono">{roundId?.slice(0, 16)}...</div>
            </div>
            <div className="bg-black/30 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">CV Events</div>
              <div className="text-2xl text-white font-bold">{cvEventCount}</div>
            </div>
          </div>

          {/* Score Display */}
          {cvScore && (
            <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 border-2 border-purple-600/30 rounded-lg p-6">
              <div className="text-center mb-4">
                <div className="text-6xl font-black text-white mb-2">{cvScore.score_card}</div>
                <Badge className="bg-purple-600 text-white text-lg px-4 py-1">
                  Winner: {cvScore.winner.toUpperCase()}
                </Badge>
              </div>
              
              <div className="grid grid-cols-2 gap-6 mt-6">
                {/* Fighter 1 */}
                <div>
                  <h3 className="text-red-400 font-bold mb-3">Fighter 1</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">CV Score:</span>
                      <span className="text-white font-semibold">{cvScore.fighter1_breakdown.cv_score.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Striking:</span>
                      <span className="text-white">{cvScore.fighter1_breakdown.striking.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Grappling:</span>
                      <span className="text-white">{cvScore.fighter1_breakdown.grappling.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Control:</span>
                      <span className="text-white">{cvScore.fighter1_breakdown.control.toFixed(1)}</span>
                    </div>
                  </div>
                </div>
                
                {/* Fighter 2 */}
                <div>
                  <h3 className="text-blue-400 font-bold mb-3">Fighter 2</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">CV Score:</span>
                      <span className="text-white font-semibold">{cvScore.fighter2_breakdown.cv_score.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Striking:</span>
                      <span className="text-white">{cvScore.fighter2_breakdown.striking.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Grappling:</span>
                      <span className="text-white">{cvScore.fighter2_breakdown.grappling.toFixed(1)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Control:</span>
                      <span className="text-white">{cvScore.fighter2_breakdown.control.toFixed(1)}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="mt-4 pt-4 border-t border-purple-600/30 grid grid-cols-3 gap-4 text-center text-xs">
                <div>
                  <div className="text-gray-400">Confidence</div>
                  <div className="text-purple-400 font-semibold">{(cvScore.confidence * 100).toFixed(0)}%</div>
                </div>
                <div>
                  <div className="text-gray-400">CV Events</div>
                  <div className="text-purple-400 font-semibold">{cvScore.cv_event_count}</div>
                </div>
                <div>
                  <div className="text-gray-400">Judge Events</div>
                  <div className="text-purple-400 font-semibold">{cvScore.judge_event_count}</div>
                </div>
              </div>
            </div>
          )}

          {/* Controls */}
          <div className="grid grid-cols-3 gap-3">
            <Button
              onClick={simulateCVEvents}
              disabled={simulationRunning}
              className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800"
            >
              <TrendingUp className="mr-2 h-4 w-4" />
              {simulationRunning ? 'Simulating...' : 'Simulate CV Events'}
            </Button>
            
            <Button
              onClick={refreshScore}
              className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800"
            >
              Refresh Score
            </Button>
            
            <Button
              onClick={lockRound}
              className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800"
            >
              Lock Round
            </Button>
          </div>

          <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-lg p-4 text-sm text-yellow-200">
            <strong>💡 CV Mode:</strong> This is a hybrid scoring system combining computer vision (70%) 
            and manual judge events (30%). Use "Simulate CV Events" to test without a real CV system.
          </div>
        </div>
      )}
    </Card>
  );
}
