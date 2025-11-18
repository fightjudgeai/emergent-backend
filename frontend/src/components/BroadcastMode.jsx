import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { db } from '@/firebase';
import deviceSyncManager from '@/utils/deviceSync';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Maximize2 } from 'lucide-react';

export default function BroadcastMode() {
  const { boutId } = useParams();
  const [bout, setBout] = useState(null);
  const [scores, setScores] = useState({});
  const [events, setEvents] = useState([]);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('connecting'); // connecting, connected, disconnected
  const [lastUpdateTime, setLastUpdateTime] = useState(Date.now());
  const [showControls, setShowControls] = useState(true);

  useEffect(() => {
    loadBout();
    const cleanup = setupRealtimeListeners();
    
    // Initialize device sync for broadcast
    const initBroadcastSync = async () => {
      try {
        await deviceSyncManager.initializeDevice(boutId, 'broadcast', {
          role: 'broadcast_display'
        });
        
        // Listen for real-time score updates
        deviceSyncManager.listenToCollection('events', { boutId }, (updates) => {
          // Automatically refresh scores when new events come in
          if (updates.length > 0 && bout?.currentRound) {
            console.log('[Broadcast] Auto-refreshing scores due to new events');
            for (let r = 1; r <= bout.currentRound; r++) {
              fetchScoreForRound(r);
            }
          }
        });
      } catch (error) {
        console.error('[Broadcast] Failed to initialize sync:', error);
      }
    };
    
    if (boutId) {
      initBroadcastSync();
    }
    
    // Periodic score refresh every 5 seconds to ensure updates
    const refreshInterval = setInterval(() => {
      if (bout?.currentRound) {
        console.log('[Broadcast] Periodic score refresh');
        for (let r = 1; r <= bout.currentRound; r++) {
          fetchScoreForRound(r);
        }
      }
    }, 5000);
    
    return () => {
      cleanup();
      clearInterval(refreshInterval);
      deviceSyncManager.cleanup();
    };
  }, [boutId, bout?.currentRound]);

  const loadBout = async () => {
    try {
      console.log('[Broadcast] Loading bout:', boutId);
      const boutDoc = await db.collection('bouts').doc(boutId).get();
      if (boutDoc.exists) {
        const boutData = { id: boutDoc.id, ...boutDoc.data() };
        console.log('[Broadcast] Bout loaded:', boutData);
        setBout(boutData);
        
        // Fetch initial scores for all rounds up to current round
        if (boutData.currentRound) {
          console.log('[Broadcast] Fetching scores for rounds 1 to', boutData.currentRound);
          for (let r = 1; r <= boutData.currentRound; r++) {
            fetchScoreForRound(r);
          }
        } else {
          console.log('[Broadcast] No current round set yet');
        }
      } else {
        console.error('[Broadcast] Bout not found:', boutId);
      }
    } catch (error) {
      console.error('[Broadcast] Error loading bout:', error);
    }
  };
  
  const fetchScoreForRound = async (round) => {
    try {
      console.log(`[Broadcast] Fetching events for round ${round}, boutId:`, boutId);
      
      // Fetch events for this round from Firebase
      const eventsSnapshot = await db.collection('events')
        .where('boutId', '==', boutId)
        .where('round', '==', round)
        .get();
      
      const roundEvents = eventsSnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      
      console.log(`[Broadcast] Found ${roundEvents.length} events for round ${round}`);
      console.log(`[Broadcast] Sample events:`, roundEvents.slice(0, 3));
      
      const requestBody = { 
        bout_id: boutId, 
        round_num: round,
        events: roundEvents,
        round_duration: 300
      };
      
      console.log('[Broadcast] Calling API with:', requestBody);
      
      // Call backend API with correct parameters
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/calculate-score-v2`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });
      
      console.log(`[Broadcast] API response status for round ${round}:`, response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log(`[Broadcast] Score data for round ${round}:`, data);
        console.log(`[Broadcast] Score card for round ${round}:`, data.card);
        console.log(`[Broadcast] Fighter1 score:`, data.fighter1_score);
        console.log(`[Broadcast] Fighter2 score:`, data.fighter2_score);
        
        setScores(prev => {
          const newScores = { ...prev, [round]: data };
          console.log(`[Broadcast] Updated scores state:`, newScores);
          return newScores;
        });
        console.log(`[Broadcast] ✅ Loaded score for round ${round}:`, data.card);
      } else {
        const errorText = await response.text();
        console.error(`[Broadcast] ❌ Failed to fetch score for round ${round}:`, response.status, errorText);
      }
    } catch (error) {
      console.error(`[Broadcast] ❌ Error fetching score for round ${round}:`, error);
    }
  };

  const setupRealtimeListeners = () => {
    let currentBout = null;
    
    // Listen to bout changes
    const unsubscribeBout = db.collection('bouts').doc(boutId)
      .onSnapshot((doc) => {
        if (doc.exists) {
          const boutData = { id: doc.id, ...doc.data() };
          const previousRound = currentBout?.currentRound;
          setBout(boutData);
          currentBout = boutData;
          
          // Fetch score when round changes
          if (previousRound && boutData.currentRound && boutData.currentRound > previousRound) {
            console.log(`[Broadcast] Round changed from ${previousRound} to ${boutData.currentRound}, fetching new scores`);
            for (let r = 1; r <= boutData.currentRound; r++) {
              fetchScoreForRound(r);
            }
          }
        }
      });

    // Listen to events for score recalculation and stats
    // Note: Removed orderBy to avoid Firebase index requirement
    const unsubscribeEvents = db.collection('events')
      .where('boutId', '==', boutId)
      .onSnapshot((snapshot) => {
        const eventsList = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));
        
        // Sort by timestamp in memory (descending - most recent first)
        eventsList.sort((a, b) => {
          const aTime = a.timestamp || 0;
          const bTime = b.timestamp || 0;
          return bTime - aTime;
        });
        
        setEvents(eventsList);
        console.log('[Broadcast] Events updated, total count:', eventsList.length);
        
        // Recalculate scores for current and past rounds when events change
        if (currentBout && currentBout.currentRound) {
          console.log('[Broadcast] Recalculating scores for rounds 1 to', currentBout.currentRound);
          for (let r = 1; r <= currentBout.currentRound; r++) {
            fetchScoreForRound(r);
          }
        }
      });

    return () => {
      unsubscribeBout();
      unsubscribeEvents();
    };
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const getTotalScore = (fighter) => {
    let total = 0;
    Object.values(scores).forEach(roundScore => {
      if (roundScore && roundScore.card) {
        // Parse card like "10-9" or "9-10"
        const [score1, score2] = roundScore.card.split('-').map(Number);
        total += fighter === 'fighter1' ? score1 : score2;
      }
    });
    return total;
  };

  const getCurrentRoundScore = (fighter) => {
    const currentRoundScore = scores[bout?.currentRound];
    console.log('[Broadcast] getCurrentRoundScore called:', {
      fighter,
      currentRound: bout?.currentRound,
      allScores: scores,
      currentRoundScore,
      card: currentRoundScore?.card
    });
    
    if (currentRoundScore && currentRoundScore.card) {
      // Parse card like "10-9" or "9-10"
      const [score1, score2] = currentRoundScore.card.split('-').map(Number);
      const score = fighter === 'fighter1' ? score1 : score2;
      console.log('[Broadcast] Returning score:', score, 'for', fighter);
      return score;
    }
    // If no score yet for current round, show placeholder
    console.log('[Broadcast] No score available yet');
    return '—';
  };

  const getEventStats = (fighter) => {
    const fighterEvents = events.filter(e => e.fighter === fighter);
    const stats = {
      knockdowns: 0,
      significantStrikes: 0,
      totalStrikes: 0,
      takedowns: 0,
      submissionAttempts: 0,
      controlTime: 0
    };

    fighterEvents.forEach(event => {
      if (event.eventType === 'KD') stats.knockdowns++;
      if (event.eventType === 'Submission Attempt') stats.submissionAttempts++;
      if (event.eventType === 'Takedown Landed') stats.takedowns++;
      
      // Count strikes
      const strikeTypes = ['Hook', 'Cross', 'Jab', 'Uppercut', 'Head Kick', 'Body Kick', 'Low Kick', 'Elbow', 'Knee', 'Front Kick/Teep'];
      if (strikeTypes.includes(event.eventType)) {
        stats.totalStrikes++;
        if (event.metadata?.significant !== false) {
          stats.significantStrikes++;
        }
      }
      
      // Sum control time
      if (event.eventType === 'Ground Back Control' || event.eventType === 'Ground Top Control' || event.eventType === 'Cage Control Time') {
        stats.controlTime += event.metadata?.duration || 0;
      }
    });

    return stats;
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!bout) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white text-4xl">Loading Broadcast...</div>
      </div>
    );
  }

  const fighter1Total = getTotalScore('fighter1');
  const fighter2Total = getTotalScore('fighter2');
  const fighter1Current = getCurrentRoundScore('fighter1');
  const fighter2Current = getCurrentRoundScore('fighter2');

  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-gray-900 to-black text-white overflow-hidden">
      {/* Fullscreen Toggle */}
      <button
        onClick={toggleFullscreen}
        className="fixed top-4 right-4 z-50 bg-white/10 hover:bg-white/20 p-3 rounded-lg backdrop-blur"
      >
        <Maximize2 className="h-6 w-6 text-white" />
      </button>

      <div className="container mx-auto p-8 h-screen flex flex-col justify-between">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-6xl font-black text-amber-500 mb-2 uppercase tracking-wider">
            {bout.eventName || 'Combat Event'}
          </h1>
          <div className="flex items-center justify-center gap-8 mt-6">
            <Badge className="bg-red-600 text-white text-2xl px-6 py-2">
              LIVE
            </Badge>
            <div className="text-4xl font-bold text-gray-300">
              ROUND {bout.currentRound} OF {bout.totalRounds}
            </div>
          </div>
        </div>

        {/* Main Scoreboard */}
        <div className="flex-1 flex items-center justify-center">
          <div className="grid grid-cols-3 gap-12 w-full max-w-7xl">
            {/* RED CORNER */}
            <Card className="bg-gradient-to-br from-red-900/50 to-red-950/50 border-4 border-red-600 p-12 text-center transform hover:scale-105 transition-transform">
              <div className="mb-4">
                <div className="text-red-400 text-2xl font-bold uppercase tracking-wider mb-2">
                  Red Corner
                </div>
                <h2 className="text-7xl font-black text-white mb-8 break-words">
                  {bout.fighter1}
                </h2>
              </div>
              
              <div className="space-y-6">
                {/* Current Round Score */}
                <div className="bg-red-950/50 rounded-xl p-6 border-2 border-red-700">
                  <div className="text-red-300 text-xl mb-2">Round {bout.currentRound}</div>
                  <div className="text-8xl font-black text-white">
                    {fighter1Current}
                  </div>
                </div>
                
                {/* Total Score */}
                {Object.keys(scores).length > 0 && (
                  <div className="bg-red-900/30 rounded-xl p-4 border border-red-700/50">
                    <div className="text-red-300 text-lg mb-1">Total Score</div>
                    <div className="text-5xl font-bold text-white">
                      {fighter1Total}
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* VS / STATUS */}
            <div className="flex flex-col items-center justify-center">
              <div className="text-9xl font-black text-amber-500 mb-8">
                VS
              </div>
              {bout.currentRound > 1 && (
                <div className="text-3xl text-gray-400">
                  Score After {bout.currentRound - 1} Round{bout.currentRound > 2 ? 's' : ''}
                </div>
              )}
            </div>

            {/* BLUE CORNER */}
            <Card className="bg-gradient-to-br from-blue-900/50 to-blue-950/50 border-4 border-blue-600 p-12 text-center transform hover:scale-105 transition-transform">
              <div className="mb-4">
                <div className="text-blue-400 text-2xl font-bold uppercase tracking-wider mb-2">
                  Blue Corner
                </div>
                <h2 className="text-7xl font-black text-white mb-8 break-words">
                  {bout.fighter2}
                </h2>
              </div>
              
              <div className="space-y-6">
                {/* Current Round Score */}
                <div className="bg-blue-950/50 rounded-xl p-6 border-2 border-blue-700">
                  <div className="text-blue-300 text-xl mb-2">Round {bout.currentRound}</div>
                  <div className="text-8xl font-black text-white">
                    {fighter2Current}
                  </div>
                </div>
                
                {/* Total Score */}
                {Object.keys(scores).length > 0 && (
                  <div className="bg-blue-900/30 rounded-xl p-4 border border-blue-700/50">
                    <div className="text-blue-300 text-lg mb-1">Total Score</div>
                    <div className="text-5xl font-bold text-white">
                      {fighter2Total}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          </div>
        </div>

        {/* Round Breakdown */}
        {Object.keys(scores).length > 0 && (
          <div className="mt-8">
            <div className="bg-black/50 backdrop-blur rounded-xl p-6 border border-gray-700">
              <h3 className="text-3xl font-bold text-amber-500 mb-4 text-center">Round Breakdown</h3>
              <div className="flex justify-center gap-4">
                {Array.from({ length: bout.totalRounds }, (_, i) => i + 1).map(roundNum => {
                  const roundScore = scores[roundNum];
                  let f1Score = '-';
                  let f2Score = '-';
                  
                  if (roundScore && roundScore.card) {
                    // Parse card like "10-9" or "9-10"
                    const [score1, score2] = roundScore.card.split('-').map(Number);
                    f1Score = score1;
                    f2Score = score2;
                  }
                  
                  const isCurrent = roundNum === bout.currentRound;
                  
                  return (
                    <div
                      key={roundNum}
                      className={`p-4 rounded-lg border-2 ${
                        isCurrent
                          ? 'bg-amber-600/30 border-amber-500'
                          : 'bg-gray-800/50 border-gray-600'
                      }`}
                    >
                      <div className={`text-sm mb-2 ${isCurrent ? 'text-amber-400' : 'text-gray-400'}`}>
                        Round {roundNum}
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="text-3xl font-bold text-red-400">{f1Score}</div>
                        <div className="text-gray-500">-</div>
                        <div className="text-3xl font-bold text-blue-400">{f2Score}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Fight Statistics */}
        {events.length > 0 && (
          <div className="mt-8 grid grid-cols-2 gap-6">
            {/* Fighter 1 Stats */}
            <Card className="bg-gradient-to-br from-red-950/40 to-black border-2 border-red-700/50 p-6">
              <h3 className="text-2xl font-bold text-red-400 mb-4 text-center uppercase">{bout.fighter1} Stats</h3>
              <div className="grid grid-cols-2 gap-4">
                {(() => {
                  const stats = getEventStats('fighter1');
                  return (
                    <>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{stats.knockdowns}</div>
                        <div className="text-sm text-red-300 uppercase">Knockdowns</div>
                      </div>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{stats.significantStrikes}</div>
                        <div className="text-sm text-red-300 uppercase">Sig. Strikes</div>
                      </div>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{stats.takedowns}</div>
                        <div className="text-sm text-red-300 uppercase">Takedowns</div>
                      </div>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{formatTime(stats.controlTime)}</div>
                        <div className="text-sm text-red-300 uppercase">Control Time</div>
                      </div>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{stats.submissionAttempts}</div>
                        <div className="text-sm text-red-300 uppercase">Sub Attempts</div>
                      </div>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{stats.totalStrikes}</div>
                        <div className="text-sm text-red-300 uppercase">Total Strikes</div>
                      </div>
                    </>
                  );
                })()}
              </div>
            </Card>

            {/* Fighter 2 Stats */}
            <Card className="bg-gradient-to-br from-blue-950/40 to-black border-2 border-blue-700/50 p-6">
              <h3 className="text-2xl font-bold text-blue-400 mb-4 text-center uppercase">{bout.fighter2} Stats</h3>
              <div className="grid grid-cols-2 gap-4">
                {(() => {
                  const stats = getEventStats('fighter2');
                  return (
                    <>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{stats.knockdowns}</div>
                        <div className="text-sm text-blue-300 uppercase">Knockdowns</div>
                      </div>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{stats.significantStrikes}</div>
                        <div className="text-sm text-blue-300 uppercase">Sig. Strikes</div>
                      </div>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{stats.takedowns}</div>
                        <div className="text-sm text-blue-300 uppercase">Takedowns</div>
                      </div>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{formatTime(stats.controlTime)}</div>
                        <div className="text-sm text-blue-300 uppercase">Control Time</div>
                      </div>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{stats.submissionAttempts}</div>
                        <div className="text-sm text-blue-300 uppercase">Sub Attempts</div>
                      </div>
                      <div className="bg-black/40 rounded-lg p-3 text-center">
                        <div className="text-4xl font-black text-white">{stats.totalStrikes}</div>
                        <div className="text-sm text-blue-300 uppercase">Total Strikes</div>
                      </div>
                    </>
                  );
                })()}
              </div>
            </Card>
          </div>
        )}

        {/* Recent Events Ticker */}
        {events.length > 0 && (
          <div className="mt-6">
            <Card className="bg-gradient-to-r from-amber-950/40 via-black to-amber-950/40 border-2 border-amber-700/50 p-4">
              <h3 className="text-xl font-bold text-amber-400 mb-3 text-center uppercase">Recent Events</h3>
              <div className="space-y-2">
                {events.slice(0, 5).map((event, idx) => (
                  <div
                    key={event.id}
                    className={`flex items-center justify-between p-2 rounded ${
                      event.fighter === 'fighter1' 
                        ? 'bg-red-950/30 border-l-4 border-red-600' 
                        : 'bg-blue-950/30 border-l-4 border-blue-600'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Badge className={event.fighter === 'fighter1' ? 'bg-red-600' : 'bg-blue-600'}>
                        {event.fighter === 'fighter1' ? bout.fighter1 : bout.fighter2}
                      </Badge>
                      <span className="text-white font-semibold">{event.eventType}</span>
                      {event.metadata?.tier && (
                        <span className="text-amber-400 text-sm">({event.metadata.tier})</span>
                      )}
                      {event.metadata?.depth && (
                        <span className="text-amber-400 text-sm">({event.metadata.depth})</span>
                      )}
                    </div>
                    <div className="text-gray-400 text-sm">
                      Round {event.round}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 pb-6">
          <div className="text-2xl font-semibold text-gray-400">
            Powered By Fight Judge AI
          </div>
        </div>
      </div>
    </div>
  );
}
