import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { db } from '@/firebase';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Maximize2 } from 'lucide-react';

export default function BroadcastMode() {
  const { boutId } = useParams();
  const [bout, setBout] = useState(null);
  const [scores, setScores] = useState({});
  const [events, setEvents] = useState([]);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    loadBout();
    const cleanup = setupRealtimeListeners();
    return cleanup;
  }, [boutId]);

  const loadBout = async () => {
    try {
      const boutDoc = await db.collection('bouts').doc(boutId).get();
      if (boutDoc.exists) {
        setBout({ id: boutDoc.id, ...boutDoc.data() });
      }
    } catch (error) {
      console.error('Error loading bout:', error);
    }
  };

  const setupRealtimeListeners = () => {
    let currentBout = null;
    
    // Listen to bout changes
    const unsubscribeBout = db.collection('bouts').doc(boutId)
      .onSnapshot((doc) => {
        if (doc.exists) {
          const boutData = { id: doc.id, ...doc.data() };
          setBout(boutData);
          currentBout = boutData;
        }
      });

    // Listen to score changes
    const calculateScoresForRound = async (round, boutData) => {
      try {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/calculate-score-v2`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bout_id: boutId, round })
        });
        if (response.ok) {
          const data = await response.json();
          setScores(prev => ({ ...prev, [round]: data }));
          console.log(`Updated score for round ${round}:`, data.card);
        }
      } catch (error) {
        console.error('Error calculating scores:', error);
      }
    };

    // Listen to events for score recalculation and stats
    const unsubscribeEvents = db.collection('events')
      .where('boutId', '==', boutId)
      .orderBy('timestamp', 'desc')
      .limit(10)
      .onSnapshot((snapshot) => {
        const eventsList = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));
        setEvents(eventsList);
        
        // Recalculate scores for current and past rounds
        if (currentBout && currentBout.currentRound) {
          for (let r = 1; r <= currentBout.currentRound; r++) {
            calculateScoresForRound(r, currentBout);
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
    if (currentRoundScore && currentRoundScore.card) {
      // Parse card like "10-9" or "9-10"
      const [score1, score2] = currentRoundScore.card.split('-').map(Number);
      return fighter === 'fighter1' ? score1 : score2;
    }
    // If no score yet for current round, show placeholder
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
                <div className="bg-red-950/50 rounded-xl p-6 border-2 border-red-700">
                  <div className="text-red-300 text-xl mb-2">Round {bout.currentRound}</div>
                  <div className="text-8xl font-black text-white">
                    {fighter1Current}
                  </div>
                </div>
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
                <div className="bg-blue-950/50 rounded-xl p-6 border-2 border-blue-700">
                  <div className="text-blue-300 text-xl mb-2">Round {bout.currentRound}</div>
                  <div className="text-8xl font-black text-white">
                    {fighter2Current}
                  </div>
                </div>
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
