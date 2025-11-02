import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import firebase from 'firebase/compat/app';
import { db } from '@/firebase';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { Shield, Check, TrendingUp, ArrowLeft, SkipForward } from 'lucide-react';
import ExplainabilityCard from '@/components/ExplainabilityCard';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function JudgePanel() {
  const { boutId } = useParams();
  const navigate = useNavigate();
  const [bout, setBout] = useState(null);
  const [scores, setScores] = useState({});
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState([]);

  useEffect(() => {
    loadBout();
    setupEventListener();
  }, [boutId]);

  useEffect(() => {
    if (events.length > 0 && bout) {
      calculateScores();
    }
  }, [events, bout]);

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

  const setupEventListener = () => {
    const unsubscribe = db.collection('events')
      .where('boutId', '==', boutId)
      .onSnapshot((snapshot) => {
        const eventsList = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));
        setEvents(eventsList);
      });

    return unsubscribe;
  };

  const calculateScores = async () => {
    setLoading(true);
    try {
      const roundScores = {};
      
      for (let round = 1; round <= (bout?.totalRounds || 3); round++) {
        const roundEvents = events.filter(e => e.round === round);
        
        if (roundEvents.length === 0) {
          roundScores[round] = null;
          continue;
        }

        const formattedEvents = roundEvents.map(e => ({
          bout_id: boutId,
          round_num: round,
          fighter: e.fighter,
          event_type: e.eventType,
          timestamp: e.timestamp || 0,
          metadata: e.metadata || {}
        }));

        const response = await axios.post(`${API}/calculate-score`, {
          bout_id: boutId,
          round_num: round,
          events: formattedEvents,
          round_duration: 300
        });

        console.log('=== CALCULATE SCORE RESPONSE ===');
        console.log('Round:', round);
        console.log('Fighter1 event_counts:', response.data.fighter1_score?.event_counts);
        console.log('Fighter2 event_counts:', response.data.fighter2_score?.event_counts);
        console.log('Full response:', JSON.stringify(response.data, null, 2));

        roundScores[round] = response.data;
      }

      setScores(roundScores);
    } catch (error) {
      console.error('Error calculating scores:', error);
      toast.error('Failed to calculate scores');
    } finally {
      setLoading(false);
    }
  };

  const confirmRound = async (roundNum) => {
    try {
      await db.collection('confirmedRounds').doc(`${boutId}_${roundNum}`).set({
        boutId,
        round: roundNum,
        confirmedAt: new Date().toISOString(),
        scores: scores[roundNum]
      });
      toast.success(`Round ${roundNum} confirmed and locked`);
    } catch (error) {
      console.error('Error confirming round:', error);
      toast.error('Failed to confirm round');
    }
  };

  const goBackToFightList = async () => {
    if (bout?.eventId) {
      navigate(`/event/${bout.eventId}/fights`);
    } else {
      navigate('/');
    }
  };

  const goToNextFight = async () => {
    if (!bout?.eventId) {
      toast.error('No event associated with this fight');
      return;
    }

    try {
      console.log('Current bout:', bout);
      
      // Mark current fight as completed
      await db.collection('bouts').doc(boutId).update({
        status: 'completed'
      });

      // Get ALL fights for this event (avoid compound query index issue)
      const allFightsSnapshot = await db.collection('bouts')
        .where('eventId', '==', bout.eventId)
        .get();

      const allFights = allFightsSnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));

      console.log('All fights:', allFights);

      // Filter and sort manually
      const nextFights = allFights
        .filter(f => (f.fightOrder || 0) > (bout.fightOrder || 0))
        .sort((a, b) => (a.fightOrder || 0) - (b.fightOrder || 0));

      console.log('Next fights:', nextFights);

      if (nextFights.length > 0) {
        const nextFight = nextFights[0];
        console.log('Moving to next fight:', nextFight);
        
        // Mark next fight as active
        await db.collection('bouts').doc(nextFight.id).update({
          status: 'active'
        });
        
        navigate(`/judge/${nextFight.id}`);
        toast.success(`Moving to Fight #${nextFight.fightOrder}`);
      } else {
        toast.info('No more fights in this event');
        navigate(`/event/${bout.eventId}/fights`);
      }
    } catch (error) {
      console.error('Error navigating to next fight:', error);
      toast.error(`Failed to move to next fight: ${error.message}`);
    }
  };

  if (!bout) return <div className="min-h-screen flex items-center justify-center bg-[#0a0a0b]"><p className="text-gray-400">Loading...</p></div>;

  // Distraction-free mode removed

  const renderSubscores = (subscores, eventCounts, label) => {
    if (!subscores) return null;
    
    // Mapping from subscore keys to display categories
    const categoryMap = {
      "SS": "Significant Strikes",
      "GCQ": "Grappling Control",
      "AGG": "Aggression",
      "DMG": "Damage",
      "TD": "Takedowns"
    };
    
    return (
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">{label}</h4>
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(subscores).map(([key, value]) => {
            const categoryName = categoryMap[key] || key;
            const eventCount = eventCounts?.[categoryName] || 0;
            
            return (
              <div key={key} className="bg-[#1a1d24] rounded-lg p-3 border border-[#2a2d35]">
                <div className="text-xs text-gray-500 mb-1">{categoryName}</div>
                <div className="flex items-baseline gap-1">
                  <div className="text-lg font-bold text-white">{value.toFixed(2)}</div>
                  <div className="text-xs text-gray-500">({eventCount})</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <Card className="bg-gradient-to-r from-[#1a1d24] to-[#13151a] border-[#2a2d35] p-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Button
                data-testid="back-to-fights-btn-judge"
                onClick={goBackToFightList}
                className="h-10 px-4 bg-[#1a1d24] hover:bg-[#22252d] text-gray-300 border border-[#2a2d35]"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center">
                  <Shield className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h1 className="text-4xl font-bold text-white">Judge Panel</h1>
                  <p className="text-gray-400 mt-1 text-lg">{bout.fighter1} vs {bout.fighter2}</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button
                data-testid="next-fight-btn-judge"
                onClick={goToNextFight}
                className="h-10 px-4 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white"
              >
                Next Fight
                <SkipForward className="ml-2 h-4 w-4" />
              </Button>
              <Badge className="bg-amber-500/20 text-amber-500 border-amber-500/30 px-4 py-2 text-base">
                View Only
              </Badge>
            </div>
          </div>
        </Card>
      </div>

      {/* Round Scores */}
      <div className="max-w-7xl mx-auto space-y-8">
        {[1, 2, 3].map((roundNum) => {
          const roundScore = scores[roundNum];
          
          return (
            <Card key={roundNum} className="bg-[#13151a] border-[#2a2d35] p-6 md:p-8" data-testid={`round-${roundNum}-card`}>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-amber-500">Round {roundNum}</h2>
                <div className="flex items-center gap-3">
                  {roundScore && (
                    <ExplainabilityCard 
                      roundScore={roundScore} 
                      events={events.filter(e => e.round === roundNum)} 
                      roundNum={roundNum}
                    />
                  )}
                  {roundScore && (
                    <Button
                      data-testid={`confirm-round-${roundNum}-btn`}
                      onClick={() => confirmRound(roundNum)}
                      className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white"
                    >
                      <Check className="mr-2 h-4 w-4" />
                      Confirm Round
                    </Button>
                  )}
                </div>
              </div>

              {loading && <p className="text-gray-400">Calculating scores...</p>}

              {!loading && !roundScore && (
                <p className="text-gray-500 text-center py-8">No events logged for this round yet</p>
              )}

              {!loading && roundScore && (
                <div className="space-y-6">
                  {/* Split-Screen Scoring: Red vs Blue */}
                  <div className="grid md:grid-cols-2 gap-4">
                    {/* RED CORNER - Left Side */}
                    <Card className="bg-gradient-to-br from-red-900/20 to-red-950/20 border-red-800/30 p-4">
                      <div className="space-y-4">
                        {/* Fighter Header */}
                        <div className="text-center border-b border-red-800/30 pb-3">
                          <div className="text-xs text-red-400 font-semibold uppercase tracking-wide">Red Corner</div>
                          <div className="text-2xl font-bold text-white mt-1">{bout.fighter1}</div>
                        </div>
                        
                        {/* Strength Score */}
                        <div className="text-center bg-red-900/30 rounded-lg p-4 border border-red-800/30">
                          <div className="text-4xl font-bold text-red-400" style={{ fontFamily: 'Space Grotesk' }}>
                            {roundScore.fighter1_score.final_score.toFixed(2)}
                          </div>
                          <div className="text-xs text-gray-400 mt-1">Strength Score</div>
                        </div>
                        
                        {/* Subscores with Event Counts */}
                        <div className="space-y-2">
                          <div className="text-xs text-red-400 font-semibold uppercase tracking-wide mb-2">Category Scores</div>
                          {Object.entries(roundScore.fighter1_score.subscores).map(([key, value]) => {
                            const categoryMap = {
                              "SS": "Significant Strikes",
                              "GCQ": "Grappling Control",
                              "AGG": "Aggression",
                              "DMG": "Damage",
                              "TD": "Takedowns"
                            };
                            const categoryName = categoryMap[key] || key;
                            const eventCount = roundScore.fighter1_score.event_counts?.[categoryName] || 0;
                            
                            return (
                              <div key={key} className="bg-red-950/30 rounded p-2 border border-red-900/30 flex items-center justify-between">
                                <div className="text-xs text-gray-400">{categoryName}</div>
                                <div className="flex items-baseline gap-1">
                                  <div className="text-base font-bold text-white">{value.toFixed(1)}</div>
                                  <div className="text-xs text-gray-500">({eventCount})</div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        
                        {/* Dominance Gates */}
                        {roundScore.winner === 'fighter1' && (
                          <div className="border-t border-red-800/30 pt-3">
                            <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Dominance Gates</div>
                            <div className="flex flex-wrap gap-2">
                              {roundScore.reasons.gates_winner.finish_threat && (
                                <Badge className="bg-red-700 text-white text-xs">Finish Threat</Badge>
                              )}
                              {roundScore.reasons.gates_winner.control_dom && (
                                <Badge className="bg-red-700 text-white text-xs">Control Dom</Badge>
                              )}
                              {roundScore.reasons.gates_winner.multi_cat_dom && (
                                <Badge className="bg-red-700 text-white text-xs">Multi-Cat Dom</Badge>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </Card>
                    
                    {/* BLUE CORNER - Right Side */}
                    <Card className="bg-gradient-to-br from-blue-900/20 to-blue-950/20 border-blue-800/30 p-4">
                      <div className="space-y-4">
                        {/* Fighter Header */}
                        <div className="text-center border-b border-blue-800/30 pb-3">
                          <div className="text-xs text-blue-400 font-semibold uppercase tracking-wide">Blue Corner</div>
                          <div className="text-2xl font-bold text-white mt-1">{bout.fighter2}</div>
                        </div>
                        
                        {/* Strength Score */}
                        <div className="text-center bg-blue-900/30 rounded-lg p-4 border border-blue-800/30">
                          <div className="text-4xl font-bold text-blue-400" style={{ fontFamily: 'Space Grotesk' }}>
                            {roundScore.fighter2_score.final_score.toFixed(2)}
                          </div>
                          <div className="text-xs text-gray-400 mt-1">Strength Score</div>
                        </div>
                        
                        {/* Subscores with Event Counts */}
                        <div className="space-y-2">
                          <div className="text-xs text-blue-400 font-semibold uppercase tracking-wide mb-2">Category Scores</div>
                          {Object.entries(roundScore.fighter2_score.subscores).map(([key, value]) => {
                            const categoryMap = {
                              "SS": "Significant Strikes",
                              "GCQ": "Grappling Control",
                              "AGG": "Aggression",
                              "DMG": "Damage",
                              "TD": "Takedowns"
                            };
                            const categoryName = categoryMap[key] || key;
                            const eventCount = roundScore.fighter2_score.event_counts?.[categoryName] || 0;
                            
                            return (
                              <div key={key} className="bg-blue-950/30 rounded p-2 border border-blue-900/30 flex items-center justify-between">
                                <div className="text-xs text-gray-400">{categoryName}</div>
                                <div className="flex items-baseline gap-1">
                                  <div className="text-base font-bold text-white">{value.toFixed(1)}</div>
                                  <div className="text-xs text-gray-500">({eventCount})</div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        
                        {/* Dominance Gates */}
                        {roundScore.winner === 'fighter2' && (
                          <div className="border-t border-blue-800/30 pt-3">
                            <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Dominance Gates</div>
                            <div className="flex flex-wrap gap-2">
                              {roundScore.reasons.gates_winner.finish_threat && (
                                <Badge className="bg-blue-700 text-white text-xs">Finish Threat</Badge>
                              )}
                              {roundScore.reasons.gates_winner.control_dom && (
                                <Badge className="bg-blue-700 text-white text-xs">Control Dom</Badge>
                              )}
                              {roundScore.reasons.gates_winner.multi_cat_dom && (
                                <Badge className="bg-blue-700 text-white text-xs">Multi-Cat Dom</Badge>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </Card>
                  </div>

                  {/* 10-Point-Must Card - Centered */}
                  <Card className="bg-gradient-to-r from-amber-900/30 to-orange-900/30 border-amber-700/50 p-6">
                    <div className="text-center space-y-3">
                      <div className="text-xs text-amber-400 font-semibold uppercase tracking-wide">Official Score Card</div>
                      <div className="text-5xl font-bold text-white" style={{ fontFamily: 'Space Grotesk' }}>
                        {roundScore.card}
                      </div>
                      <div className="flex items-center justify-center gap-3 flex-wrap">
                        {roundScore.winner === 'DRAW' ? (
                          <Badge className="bg-gray-600 text-white border-gray-500 px-4 py-2">
                            Round Draw
                          </Badge>
                        ) : (
                          <>
                            <Badge className={`${
                              roundScore.winner === 'fighter1' 
                                ? 'bg-red-600 border-red-500' 
                                : 'bg-blue-600 border-blue-500'
                            } text-white px-4 py-2`}>
                              Winner: {roundScore.winner === 'fighter1' ? bout.fighter1 : bout.fighter2}
                            </Badge>
                            {roundScore.reasons.to_107 && (
                              <Badge className="bg-red-900 border-red-700 text-white px-3 py-1">10-7 Dominance</Badge>
                            )}
                            {roundScore.reasons.to_108 && !roundScore.reasons.to_107 && (
                              <Badge className="bg-orange-900 border-orange-700 text-white px-3 py-1">10-8 Dominance</Badge>
                            )}
                          </>
                        )}
                      </div>
                      <div className="flex items-center justify-center gap-2 text-sm text-gray-400">
                        <TrendingUp className="w-4 h-4 text-amber-500" />
                        <span>Score Delta: {roundScore.reasons.delta.toFixed(2)} points</span>
                      </div>
                    </div>
                  </Card>

                  {/* Uncertainty Band */}
                  {roundScore.uncertainty && (
                    <Card className={`p-4 border ${
                      roundScore.uncertainty === 'high_confidence' 
                        ? 'bg-green-900/20 border-green-700/50' 
                        : roundScore.uncertainty === 'medium_confidence'
                        ? 'bg-amber-900/20 border-amber-700/50'
                        : 'bg-red-900/20 border-red-700/50'
                    }`}>
                      <div className="flex items-start gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          roundScore.uncertainty === 'high_confidence'
                            ? 'bg-green-600'
                            : roundScore.uncertainty === 'medium_confidence'
                            ? 'bg-amber-600'
                            : 'bg-red-600'
                        }`}>
                          <TrendingUp className="w-5 h-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-base font-bold ${
                              roundScore.uncertainty === 'high_confidence'
                                ? 'text-green-400'
                                : roundScore.uncertainty === 'medium_confidence'
                                ? 'text-amber-400'
                                : 'text-red-400'
                            }`}>
                              {roundScore.uncertainty === 'high_confidence' && 'High Confidence'}
                              {roundScore.uncertainty === 'medium_confidence' && 'Medium Confidence'}
                              {roundScore.uncertainty === 'low_confidence' && 'Low Confidence'}
                            </span>
                            <Badge className={`text-xs ${
                              roundScore.uncertainty === 'high_confidence'
                                ? 'bg-green-900/30 text-green-400 border-green-700/30'
                                : roundScore.uncertainty === 'medium_confidence'
                                ? 'bg-amber-900/30 text-amber-400 border-amber-700/30'
                                : 'bg-red-900/30 text-red-400 border-red-700/30'
                            }`}>
                              Uncertainty Band
                            </Badge>
                          </div>
                          <div className="text-sm text-gray-300 mb-2">
                            {roundScore.uncertainty === 'high_confidence' && 
                              'This score is highly confident. The decision is clear with significant separation from scoring thresholds.'}
                            {roundScore.uncertainty === 'medium_confidence' && 
                              'This score has moderate confidence. Consider reviewing for potential edge cases.'}
                            {roundScore.uncertainty === 'low_confidence' && 
                              'This score has low confidence. The round was very close or had complicating factors.'}
                          </div>
                          {roundScore.uncertainty_factors && roundScore.uncertainty_factors.length > 0 && (
                            <div className="space-y-1">
                              <div className="text-xs text-gray-400 uppercase tracking-wide">Factors:</div>
                              {roundScore.uncertainty_factors.map((factor, idx) => (
                                <div key={idx} className="text-xs text-gray-400 flex items-start gap-2">
                                  <span className="text-amber-500">•</span>
                                  <span>{factor}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </Card>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}