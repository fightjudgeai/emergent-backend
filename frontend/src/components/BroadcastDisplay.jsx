/**
 * Broadcast Display - Arena Big Screen Mode (PFC 50 Ready)
 * Full-screen display for showing fight scores to the audience
 * Features: Fighter photos, offline capability, responsive design
 */

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { RoundWinner } from './broadcast/RoundWinner.jsx';
import { FinalResult } from './broadcast/FinalResult.jsx';
import '../styles/broadcast.css';

// Default placeholder for fighter photos
const DEFAULT_FIGHTER_PHOTO = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIiB2aWV3Qm94PSIwIDAgMjAwIDIwMCI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiMyMjI1MmQiLz48Y2lyY2xlIGN4PSIxMDAiIGN5PSI4MCIgcj0iNDAiIGZpbGw9IiM0NDQ4NTIiLz48ZWxsaXBzZSBjeD0iMTAwIiBjeT0iMTcwIiByeD0iNjAiIHJ5PSI1MCIgZmlsbD0iIzQ0NDg1MiIvPjwvc3ZnPg==';

export default function BroadcastDisplay() {
  const { boutId } = useParams();
  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  const [boutData, setBoutData] = useState(null);
  const [liveData, setLiveData] = useState(null);
  const [currentRound, setCurrentRound] = useState(null);
  const [showFinal, setShowFinal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Cache key for offline storage
  const CACHE_KEY = `broadcast_${boutId}`;
  
  // Fullscreen toggle handler
  const toggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
        setIsFullscreen(true);
      } else {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch (error) {
      console.error('Fullscreen error:', error);
    }
  };
  
  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);
  
  // Auto-enter fullscreen on load for arena display
  useEffect(() => {
    // Add click listener to enter fullscreen on first interaction
    const handleFirstClick = async () => {
      if (!document.fullscreenElement) {
        try {
          await document.documentElement.requestFullscreen();
          setIsFullscreen(true);
        } catch (e) {
          // Silently fail - user may not have interacted yet
        }
      }
      document.removeEventListener('click', handleFirstClick);
    };
    
    document.addEventListener('click', handleFirstClick);
    return () => document.removeEventListener('click', handleFirstClick);
  }, []);

  // Save to local storage for offline access
  const saveToCache = useCallback((data) => {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({
        data,
        timestamp: Date.now()
      }));
    } catch (e) {
      console.warn('Failed to cache data:', e);
    }
  }, [CACHE_KEY]);

  // Load from local storage
  const loadFromCache = useCallback(() => {
    try {
      const cached = localStorage.getItem(CACHE_KEY);
      if (cached) {
        const { data, timestamp } = JSON.parse(cached);
        return { data, timestamp };
      }
    } catch (e) {
      console.warn('Failed to load cache:', e);
    }
    return null;
  }, [CACHE_KEY]);

  // Monitor online/offline status
  useEffect(() => {
    const handleOnline = () => {
      setIsOffline(false);
      setConnectionAttempts(0);
    };
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Fetch live scoring data
  useEffect(() => {
    const fetchLiveData = async () => {
      // If offline, use cached data
      if (isOffline) {
        const cached = loadFromCache();
        if (cached) {
          setLiveData(cached.data);
          setBoutData({
            fighter1: cached.data.fighter1_name || 'Fighter 1',
            fighter2: cached.data.fighter2_name || 'Fighter 2',
            fighter1Photo: cached.data.fighter1_photo,
            fighter2Photo: cached.data.fighter2_photo,
            status: cached.data.status || 'in_progress',
            currentRound: cached.data.current_round || 1
          });
          setLoading(false);
          setLastUpdate(new Date(cached.timestamp));
        }
        return;
      }

      try {
        const url = `${backendUrl}/api/live/${boutId}`;
        const response = await fetch(url, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        });
        
        if (!response.ok) {
          let errorMessage = '';
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || errorData.message || response.statusText;
          } catch {
            errorMessage = response.statusText;
          }
          
          // Try to use cached data on error
          const cached = loadFromCache();
          if (cached) {
            setLiveData(cached.data);
            setBoutData({
              fighter1: cached.data.fighter1_name || 'Fighter 1',
              fighter2: cached.data.fighter2_name || 'Fighter 2',
              fighter1Photo: cached.data.fighter1_photo,
              fighter2Photo: cached.data.fighter2_photo,
              status: cached.data.status || 'in_progress',
              currentRound: cached.data.current_round || 1
            });
            setLoading(false);
            setLastUpdate(new Date(cached.timestamp));
            setConnectionAttempts(prev => prev + 1);
            return;
          }
          
          if (response.status === 404) {
            setError(`Bout "${boutId}" not found.`);
          } else {
            setError(`API Error: ${response.status} - ${errorMessage}`);
          }
          setLoading(false);
          return;
        }
        
        const data = await response.json();
        setLiveData(data);
        saveToCache(data);
        setLastUpdate(new Date());
        setConnectionAttempts(0);
        
        if (data) {
          setBoutData({
            fighter1: data.fighter1_name || 'Fighter 1',
            fighter2: data.fighter2_name || 'Fighter 2',
            fighter1Photo: data.fighter1_photo,
            fighter2Photo: data.fighter2_photo,
            status: data.status || 'in_progress',
            currentRound: data.current_round || 1
          });
        }
        
        setLoading(false);
        setError(null);
      } catch (err) {
        console.error('Error fetching live data:', err);
        
        // Try to use cached data on network error
        const cached = loadFromCache();
        if (cached) {
          setLiveData(cached.data);
          setBoutData({
            fighter1: cached.data.fighter1_name || 'Fighter 1',
            fighter2: cached.data.fighter2_name || 'Fighter 2',
            fighter1Photo: cached.data.fighter1_photo,
            fighter2Photo: cached.data.fighter2_photo,
            status: cached.data.status || 'in_progress',
            currentRound: cached.data.current_round || 1
          });
          setLoading(false);
          setLastUpdate(new Date(cached.timestamp));
          setConnectionAttempts(prev => prev + 1);
          return;
        }
        
        setError(`Connection error: ${err.message}`);
        setLoading(false);
      }
    };

    if (boutId) {
      fetchLiveData();
      // Poll every 2 seconds for faster updates during live events
      const interval = setInterval(fetchLiveData, 2000);
      return () => clearInterval(interval);
    }
  }, [boutId, backendUrl, isOffline, loadFromCache, saveToCache]);

  // Listen for round complete events
  useEffect(() => {
    if (liveData && liveData.rounds && liveData.rounds.length > 0) {
      const latestRound = liveData.rounds[liveData.rounds.length - 1];
      
      if (latestRound && (latestRound.fighter1_score || latestRound.fighter2_score)) {
        setCurrentRound({
          round: liveData.rounds.length,
          unified_red: latestRound.fighter1_score || latestRound.fighter1_total || 0,
          unified_blue: latestRound.fighter2_score || latestRound.fighter2_total || 0
        });
        
        // Auto-hide after 15 seconds
        const timeout = setTimeout(() => {
          setCurrentRound(null);
        }, 15000);
        
        return () => clearTimeout(timeout);
      }
    }
  }, [liveData]);

  // Check if fight is complete
  useEffect(() => {
    if (liveData && liveData.status === 'completed') {
      setShowFinal(true);
    }
  }, [liveData]);

  // Fighter Photo Component
  const FighterPhoto = ({ src, corner, name }) => (
    <div className="relative">
      <div 
        className="w-32 h-32 md:w-40 md:h-40 lg:w-48 lg:h-48 rounded-full overflow-hidden border-4 mx-auto"
        style={{ 
          borderColor: corner === 'red' ? 'hsl(348 83% 47%)' : 'hsl(195 100% 70%)',
          boxShadow: `0 0 30px ${corner === 'red' ? 'hsl(348 83% 47% / 0.5)' : 'hsl(195 100% 70% / 0.5)'}`
        }}
      >
        <img 
          src={src || DEFAULT_FIGHTER_PHOTO} 
          alt={name}
          className="w-full h-full object-cover"
          onError={(e) => { e.target.src = DEFAULT_FIGHTER_PHOTO; }}
        />
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl font-bold mb-4" style={{ color: 'hsl(195 100% 70%)' }}>
            FIGHT JUDGE AI
          </div>
          <div className="text-2xl" style={{ color: 'hsl(0 0% 70%)' }}>
            Loading Broadcast...
          </div>
        </div>
      </div>
    );
  }

  if (error && !boutData) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-8">
        <div className="text-center max-w-2xl">
          <div className="text-4xl font-bold mb-4 text-red-500">Connection Error</div>
          <div className="text-xl text-gray-400 mb-6">{error}</div>
          
          <div className="p-6 rounded-lg border border-gray-700 bg-gray-900/50 text-left mb-6">
            <div className="text-sm text-gray-300 mb-3">
              <strong>Bout ID:</strong> <code className="text-amber-400 bg-gray-800 px-2 py-1 rounded">{boutId}</code>
            </div>
          </div>

          <div className="flex gap-4 justify-center">
            <button 
              onClick={() => window.location.reload()} 
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
            >
              Retry Connection
            </button>
            <a 
              href={`/arena-demo/${boutId}`}
              className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold transition-colors inline-block"
            >
              Try Demo Mode
            </a>
          </div>
        </div>
      </div>
    );
  }

  if (!boutData) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl font-bold text-gray-400">Bout Not Found</div>
          <div className="text-sm text-gray-500 mt-4">Bout ID: {boutId}</div>
        </div>
      </div>
    );
  }

  // Calculate totals from live data
  const rounds = liveData?.rounds || [];
  const redTotal = liveData?.fighter1_total || rounds.reduce((sum, r) => sum + (r.fighter1_score || r.fighter1_total || 0), 0);
  const blueTotal = liveData?.fighter2_total || rounds.reduce((sum, r) => sum + (r.fighter2_score || r.fighter2_total || 0), 0);
  const winner = redTotal > blueTotal ? 'red' : blueTotal > redTotal ? 'blue' : 'draw';

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center p-4 md:p-8">
      {/* Connection Status Banner */}
      {(isOffline || connectionAttempts > 0) && (
        <div className={`fixed top-0 left-0 right-0 py-2 px-4 text-center text-sm font-semibold ${isOffline ? 'bg-red-600' : 'bg-yellow-600'}`}>
          {isOffline ? (
            <>OFFLINE MODE - Using cached data {lastUpdate && `(Last update: ${lastUpdate.toLocaleTimeString()})`}</>
          ) : (
            <>Reconnecting... Using cached data</>
          )}
        </div>
      )}

      {/* Main Fight Card */}
      <div className="w-full max-w-7xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-3xl md:text-4xl font-bold mb-2" style={{ color: 'hsl(195 100% 70%)' }}>
            FIGHT JUDGE AI
          </div>
          <div className="text-lg md:text-xl" style={{ color: 'hsl(0 0% 70%)' }}>
            LIVE SCORING
          </div>
        </div>

        {/* Fighter Cards with Photos */}
        <div className="grid grid-cols-2 gap-4 md:gap-8 mb-8">
          {/* Red Corner */}
          <div className="text-center p-4 md:p-6 rounded-xl border-2" style={{ 
            borderColor: 'hsl(348 83% 47%)', 
            background: 'linear-gradient(to bottom, hsl(348 83% 47% / 0.15), hsl(348 83% 47% / 0.05))',
            boxShadow: '0 0 40px hsl(348 83% 47% / 0.3)'
          }}>
            <div className="text-sm md:text-base font-semibold tracking-[0.3em] uppercase mb-3" style={{ color: 'hsl(348 83% 47%)' }}>
              RED CORNER
            </div>
            <FighterPhoto 
              src={boutData.fighter1Photo} 
              corner="red" 
              name={boutData.fighter1} 
            />
            <div className="text-2xl md:text-4xl font-bold text-white mt-4 mb-2 truncate px-2">
              {boutData.fighter1 || 'Fighter 1'}
            </div>
            <div className="text-5xl md:text-7xl lg:text-8xl font-bold tabular-nums" style={{ 
              color: 'hsl(348 83% 47%)',
              textShadow: '0 0 30px hsl(348 83% 47% / 0.7)'
            }}>
              {redTotal}
            </div>
          </div>

          {/* Blue Corner */}
          <div className="text-center p-4 md:p-6 rounded-xl border-2" style={{ 
            borderColor: 'hsl(195 100% 70%)', 
            background: 'linear-gradient(to bottom, hsl(195 100% 70% / 0.15), hsl(195 100% 70% / 0.05))',
            boxShadow: '0 0 40px hsl(195 100% 70% / 0.3)'
          }}>
            <div className="text-sm md:text-base font-semibold tracking-[0.3em] uppercase mb-3" style={{ color: 'hsl(195 100% 70%)' }}>
              BLUE CORNER
            </div>
            <FighterPhoto 
              src={boutData.fighter2Photo} 
              corner="blue" 
              name={boutData.fighter2} 
            />
            <div className="text-2xl md:text-4xl font-bold text-white mt-4 mb-2 truncate px-2">
              {boutData.fighter2 || 'Fighter 2'}
            </div>
            <div className="text-5xl md:text-7xl lg:text-8xl font-bold tabular-nums" style={{ 
              color: 'hsl(195 100% 70%)',
              textShadow: '0 0 30px hsl(195 100% 70% / 0.7)'
            }}>
              {blueTotal}
            </div>
          </div>
        </div>

        {/* Current Round Score */}
        {currentRound && (
          <div className="mb-8">
            <RoundWinner
              round={currentRound}
              roundNumber={currentRound.round}
              redName={boutData.fighter1}
              blueName={boutData.fighter2}
              isVisible={true}
            />
          </div>
        )}

        {/* Final Result */}
        {showFinal && (
          <div className="mb-8">
            <FinalResult
              total={{ red: redTotal, blue: blueTotal }}
              winner={winner}
              redName={boutData.fighter1}
              blueName={boutData.fighter2}
              isVisible={true}
            />
          </div>
        )}

        {/* Round History */}
        {rounds.length > 0 && !currentRound && !showFinal && (
          <div className="mt-8 p-4 md:p-6 rounded-xl border" style={{ 
            borderColor: 'hsl(195 100% 70% / 0.3)',
            background: 'hsl(0 0% 12% / 0.4)'
          }}>
            <div className="text-center text-sm md:text-base font-semibold tracking-[0.3em] uppercase mb-4" style={{ color: 'hsl(195 100% 70%)' }}>
              Round Scores
            </div>
            <div className="space-y-2">
              {rounds.map((round, idx) => (
                <div key={idx} className="flex items-center justify-center text-lg md:text-2xl gap-4 md:gap-8">
                  <span className="text-gray-400 w-24 text-right">Round {idx + 1}</span>
                  <span style={{ color: 'hsl(348 83% 47%)' }} className="font-bold w-12 text-center">
                    {round.fighter1_score || round.fighter1_total || 0}
                  </span>
                  <span className="text-gray-500">-</span>
                  <span style={{ color: 'hsl(195 100% 70%)' }} className="font-bold w-12 text-center">
                    {round.fighter2_score || round.fighter2_total || 0}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Status Indicator */}
        <div className="mt-8 text-center">
          <div className="inline-flex items-center gap-3 px-6 py-3 rounded-full" style={{ 
            background: 'hsl(0 0% 15%)',
            border: '1px solid hsl(195 100% 70% / 0.3)'
          }}>
            <div className="w-4 h-4 rounded-full" style={{ 
              background: boutData.status === 'in_progress' ? 'hsl(120 100% 50%)' : 'hsl(0 0% 50%)',
              boxShadow: boutData.status === 'in_progress' ? '0 0 15px hsl(120 100% 50%)' : 'none',
              animation: boutData.status === 'in_progress' ? 'pulse 2s ease-in-out infinite' : 'none'
            }} />
            <span className="text-base md:text-lg uppercase tracking-wider font-semibold" style={{ color: 'hsl(195 100% 70%)' }}>
              {boutData.status === 'in_progress' ? 'LIVE' : boutData.status === 'completed' ? 'FIGHT OVER' : 'PENDING'}
            </span>
            {liveData?.current_round && boutData.status === 'in_progress' && (
              <span className="text-gray-400 text-sm md:text-base">
                | Round {liveData.current_round}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
