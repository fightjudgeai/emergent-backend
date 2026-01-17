import { useState, useEffect, useCallback, useRef } from 'react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * useUnifiedScoring - WebSocket-based real-time unified scoring hook
 * 
 * CRITICAL: This hook implements the SERVER-AUTHORITATIVE scoring model.
 * All 4 operator laptops connect to the same WebSocket and receive identical data.
 * NO local scoring computation - everything comes from the server.
 * 
 * @param {string} boutId - The bout ID to subscribe to
 * @param {number} currentRound - Current round number (optional, for filtering)
 * @returns {object} - Unified scoring state and actions
 */
export default function useUnifiedScoring(boutId, currentRound = 1) {
  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [connectionCount, setConnectionCount] = useState(0);
  const [lastUpdate, setLastUpdate] = useState(null);
  
  // Bout info
  const [boutInfo, setBoutInfo] = useState({
    fighter1: 'Red Corner',
    fighter2: 'Blue Corner',
    totalRounds: 5,
    status: 'in_progress'
  });
  
  // Events for current round (aggregated from ALL devices)
  const [events, setEvents] = useState({
    red: {},      // { eventType: count }
    blue: {},     // { eventType: count }
    redTotal: 0,
    blueTotal: 0,
    allEvents: 0
  });
  
  // Computed round results (from server)
  const [roundResults, setRoundResults] = useState([]);
  const [runningTotals, setRunningTotals] = useState({ red: 0, blue: 0 });
  
  // Loading/error state
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // WebSocket reference
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  
  // Process incoming state sync message
  const processStateSync = useCallback((data) => {
    if (data.error) {
      setError(data.error);
      return;
    }
    
    setBoutInfo({
      fighter1: data.fighter1 || 'Red Corner',
      fighter2: data.fighter2 || 'Blue Corner',
      totalRounds: data.total_rounds || 5,
      status: data.status || 'in_progress'
    });
    
    if (data.events) {
      setEvents({
        red: data.events.red || {},
        blue: data.events.blue || {},
        redTotal: data.events.red_total || 0,
        blueTotal: data.events.blue_total || 0,
        allEvents: data.events.all_events || 0
      });
    }
    
    setRoundResults(data.round_results || []);
    setRunningTotals(data.running_totals || { red: 0, blue: 0 });
    setLastUpdate(data.timestamp || new Date().toISOString());
  }, []);
  
  // Process incoming event_added message
  const processEventAdded = useCallback((event) => {
    // Request a full state sync to ensure consistency
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'request_sync',
        round_number: currentRound
      }));
    }
    setLastUpdate(new Date().toISOString());
  }, [currentRound]);
  
  // Process incoming round_computed message
  const processRoundComputed = useCallback((result) => {
    setRoundResults(prev => {
      const existing = prev.findIndex(r => r.round_number === result.round_number);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = result;
        return updated;
      }
      return [...prev, result].sort((a, b) => a.round_number - b.round_number);
    });
    
    // Update running totals
    setRunningTotals(prev => {
      const newRed = (prev.red || 0) + (result.red_points || 0);
      const newBlue = (prev.blue || 0) + (result.blue_points || 0);
      return { red: newRed, blue: newBlue };
    });
    
    setLastUpdate(new Date().toISOString());
  }, []);
  
  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!boutId) return;
    
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    // Build WebSocket URL
    const wsProtocol = API.startsWith('https') ? 'wss' : 'ws';
    const wsHost = API.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${wsHost}/api/ws/unified/${boutId}`;
    
    console.log('[WS] Connecting to:', wsUrl);
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      
      ws.onopen = () => {
        console.log('[WS] Connected to unified scoring');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };
      
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          switch (message.type) {
            case 'state_sync':
              processStateSync(message.data);
              if (message.connection_count !== undefined) {
                setConnectionCount(message.connection_count);
              }
              break;
              
            case 'event_added':
              processEventAdded(message.event);
              break;
              
            case 'round_computed':
              processRoundComputed(message.result);
              break;
              
            case 'fight_finalized':
              // Handle fight finalization
              setBoutInfo(prev => ({ ...prev, status: 'completed' }));
              break;
              
            case 'connection_count':
              setConnectionCount(message.count);
              break;
              
            case 'pong':
              // Server responded to ping
              break;
              
            case 'ping':
              // Server ping - respond with pong
              ws.send(JSON.stringify({ type: 'pong' }));
              break;
              
            default:
              console.log('[WS] Unknown message type:', message.type);
          }
        } catch (e) {
          console.error('[WS] Error parsing message:', e);
        }
      };
      
      ws.onclose = (event) => {
        console.log('[WS] Disconnected:', event.code, event.reason);
        setIsConnected(false);
        
        // Attempt reconnection
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
          console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setError('Connection lost. Please refresh the page.');
        }
      };
      
      ws.onerror = (event) => {
        console.error('[WS] WebSocket error:', event);
        setError('Connection error');
      };
      
    } catch (e) {
      console.error('[WS] Failed to create WebSocket:', e);
      setError('Failed to connect');
    }
  }, [boutId, processStateSync, processEventAdded, processRoundComputed]);
  
  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);
  
  // Request state sync
  const requestSync = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'request_sync',
        round_number: currentRound
      }));
    }
  }, [currentRound]);
  
  // Set current round (triggers sync)
  const setRound = useCallback((roundNumber) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'set_round',
        round_number: roundNumber
      }));
    }
  }, []);
  
  // Log event (sends to server via REST API, not WebSocket)
  const logEvent = useCallback(async (eventType, corner, aspect = 'STRIKING', metadata = {}) => {
    if (!boutId) return { success: false, error: 'No bout ID' };
    
    const deviceRole = localStorage.getItem('device_role') || 'UNKNOWN';
    
    try {
      const response = await fetch(`${API}/api/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          round_number: currentRound,
          corner: corner.toUpperCase(),
          aspect: aspect.toUpperCase(),
          event_type: eventType,
          device_role: deviceRole,
          metadata: metadata
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        return { success: true, event: result.event, connectedClients: result.connected_clients };
      } else {
        const error = await response.json();
        return { success: false, error: error.detail || 'Failed to log event' };
      }
    } catch (e) {
      console.error('[API] Error logging event:', e);
      return { success: false, error: e.message };
    }
  }, [boutId, currentRound]);
  
  // Compute round (triggers server-side computation)
  const computeRound = useCallback(async (roundNumber = currentRound) => {
    if (!boutId) return { success: false, error: 'No bout ID' };
    
    setIsLoading(true);
    try {
      const response = await fetch(`${API}/api/rounds/compute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          round_number: roundNumber
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        return { success: true, result };
      } else {
        const error = await response.json();
        return { success: false, error: error.detail || 'Failed to compute round' };
      }
    } catch (e) {
      console.error('[API] Error computing round:', e);
      return { success: false, error: e.message };
    } finally {
      setIsLoading(false);
    }
  }, [boutId, currentRound]);
  
  // Finalize fight
  const finalizeFight = useCallback(async () => {
    if (!boutId) return { success: false, error: 'No bout ID' };
    
    setIsLoading(true);
    try {
      const response = await fetch(`${API}/api/fights/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bout_id: boutId })
      });
      
      if (response.ok) {
        const result = await response.json();
        return { success: true, result };
      } else {
        const error = await response.json();
        return { success: false, error: error.detail || 'Failed to finalize fight' };
      }
    } catch (e) {
      console.error('[API] Error finalizing fight:', e);
      return { success: false, error: e.message };
    } finally {
      setIsLoading(false);
    }
  }, [boutId]);
  
  // Connect on mount, disconnect on unmount
  useEffect(() => {
    if (boutId) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [boutId, connect, disconnect]);
  
  // Request sync when round changes
  useEffect(() => {
    if (isConnected && currentRound) {
      setRound(currentRound);
    }
  }, [currentRound, isConnected, setRound]);
  
  // Fallback polling if WebSocket fails
  useEffect(() => {
    if (!isConnected && boutId) {
      const poll = async () => {
        try {
          const response = await fetch(`${API}/api/events?bout_id=${boutId}&round_number=${currentRound}`);
          if (response.ok) {
            const data = await response.json();
            
            // Aggregate events
            const red = {};
            const blue = {};
            (data.events || []).forEach(evt => {
              const corner = evt.corner || (evt.fighter === 'fighter1' ? 'RED' : 'BLUE');
              const type = evt.event_type;
              if (corner === 'RED') {
                red[type] = (red[type] || 0) + 1;
              } else {
                blue[type] = (blue[type] || 0) + 1;
              }
            });
            
            setEvents({
              red,
              blue,
              redTotal: Object.values(red).reduce((a, b) => a + b, 0),
              blueTotal: Object.values(blue).reduce((a, b) => a + b, 0),
              allEvents: data.total_events || 0
            });
            setLastUpdate(new Date().toISOString());
          }
        } catch (e) {
          console.error('[POLL] Error:', e);
        }
      };
      
      // Poll every 500ms as fallback
      const interval = setInterval(poll, 500);
      poll(); // Initial poll
      
      return () => clearInterval(interval);
    }
  }, [isConnected, boutId, currentRound]);
  
  return {
    // Connection state
    isConnected,
    connectionCount,
    lastUpdate,
    error,
    
    // Bout info
    boutInfo,
    
    // Events (from ALL devices)
    events,
    
    // Round results (server-computed)
    roundResults,
    runningTotals,
    
    // Loading state
    isLoading,
    
    // Actions
    logEvent,
    computeRound,
    finalizeFight,
    requestSync,
    setRound,
    connect,
    disconnect
  };
}
