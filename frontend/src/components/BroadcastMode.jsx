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
    setupRealtimeListeners();
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
    // Listen to bout changes
    const unsubscribeBout = db.collection('bouts').doc(boutId)
      .onSnapshot((doc) => {
        if (doc.exists) {
          setBout({ id: doc.id, ...doc.data() });
        }
      });

    // Listen to score changes
    const calculateScoresForRound = async (round) => {
      try {
        const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/calculate-score`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bout_id: boutId, round })
        });
        if (response.ok) {
          const data = await response.json();
          setScores(prev => ({ ...prev, [round]: data }));
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
        
        // Recalculate scores for all rounds
        if (bout) {
          for (let r = 1; r <= (bout.totalRounds || 3); r++) {
            calculateScoresForRound(r);
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
      if (roundScore && roundScore[`${fighter}_score`]) {
        total += roundScore[`${fighter}_score`];
      }
    });
    return total;
  };

  const getCurrentRoundScore = (fighter) => {
    const currentRoundScore = scores[bout?.currentRound];
    return currentRoundScore?.[`${fighter}_score`] || 0;
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
                
                <div className="bg-red-900/30 rounded-xl p-4 border border-red-700/50">
                  <div className="text-red-300 text-lg mb-1">Total Score</div>
                  <div className="text-5xl font-bold text-white">
                    {fighter1Total}
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
                
                <div className="bg-blue-900/30 rounded-xl p-4 border border-blue-700/50">
                  <div className="text-blue-300 text-lg mb-1">Total Score</div>
                  <div className="text-5xl font-bold text-white">
                    {fighter2Total}
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
                  const f1Score = roundScore?.fighter1_score || '-';
                  const f2Score = roundScore?.fighter2_score || '-';
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

        {/* Footer */}
        <div className="text-center mt-8">
          <div className="text-2xl text-gray-500">
            Powered by FightJudge Scoring System
          </div>
        </div>
      </div>
    </div>
  );
}
