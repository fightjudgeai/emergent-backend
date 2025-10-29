import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { GraduationCap, Eye, EyeOff, Lock, TrendingUp, Trophy, Target } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function ShadowJudgingMode() {
  const navigate = useNavigate();
  const [historicalRounds, setHistoricalRounds] = useState([]);
  const [selectedRound, setSelectedRound] = useState(null);
  const [myScore, setMyScore] = useState(null);
  const [officialRevealed, setOfficialRevealed] = useState(false);
  const [calibrationScore, setCalibrationScore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [judgeStats, setJudgeStats] = useState(null);
  const [showStats, setShowStats] = useState(false);

  useEffect(() => {
    initializeShadowJudging();
  }, []);

  const initializeShadowJudging = async () => {
    // First, seed the training library if empty
    await seedLibraryIfNeeded();
    // Then load rounds
    await loadHistoricalRounds();
    // Load judge stats if available
    await loadJudgeStats();
  };

  const seedLibraryIfNeeded = async () => {
    try {
      // Check if rounds exist
      const response = await fetch(`${BACKEND_URL}/api/training-library/rounds`);
      const rounds = await response.json();
      
      // If no rounds, seed the library
      if (rounds.length === 0) {
        const seedResponse = await fetch(`${BACKEND_URL}/api/training-library/seed`, {
          method: 'POST'
        });
        const seedResult = await seedResponse.json();
        console.log('Training library seeded:', seedResult);
      }
    } catch (error) {
      console.error('Error checking/seeding training library:', error);
    }
  };

  const loadHistoricalRounds = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/training-library/rounds`);
      if (!response.ok) throw new Error('Failed to fetch training rounds');
      
      const rounds = await response.json();
      setHistoricalRounds(rounds);
    } catch (error) {
      console.error('Error loading training rounds:', error);
      toast.error('Failed to load training library');
    } finally {
      setLoading(false);
    }
  };

  const loadJudgeStats = async () => {
    try {
      const judgeProfile = JSON.parse(localStorage.getItem('judgeProfile') || '{}');
      if (!judgeProfile.id && !judgeProfile.judgeId) return;

      const judgeId = judgeProfile.id || judgeProfile.judgeId;
      const response = await fetch(`${BACKEND_URL}/api/training-library/judge-stats/${judgeId}`);
      if (response.ok) {
        const stats = await response.json();
        setJudgeStats(stats);
      } else if (response.status === 404) {
        // No stats yet - set empty stats to show button
        setJudgeStats({
          judgeId: judgeId,
          judgeName: judgeProfile.name || judgeProfile.judgeName || 'Unknown',
          totalAttempts: 0,
          averageAccuracy: 0,
          averageMAE: 0,
          sensitivity108Rate: 0,
          perfectMatches: 0
        });
      }
    } catch (error) {
      console.error('Error loading judge stats:', error);
      // Ignore error if no stats exist yet
    }
  };

  const startJudging = (round) => {
    setSelectedRound(round);
    setMyScore(null);
    setOfficialRevealed(false);
    setCalibrationScore(null);
  };

  const submitMyScore = async (card) => {
    setMyScore(card);
    const calibration = calculateCalibration(card);
    setCalibrationScore(calibration);
    
    // Save to backend
    try {
      const judgeProfile = JSON.parse(localStorage.getItem('judgeProfile') || '{}');
      const judgeId = judgeProfile.id || judgeProfile.judgeId || 'anonymous';
      const judgeName = judgeProfile.name || judgeProfile.judgeName || 'Anonymous Judge';
      
      await fetch(`${BACKEND_URL}/api/training-library/submit-score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          judgeId: judgeId,
          judgeName: judgeName,
          roundId: selectedRound.id,
          myScore: card,
          officialScore: selectedRound.officialCard,
          mae: calibration.mae,
          sensitivity108: calibration.sensitivity108,
          accuracy: calibration.accuracy,
          match: calibration.match
        })
      });
      
      // Reload stats after submission
      await loadJudgeStats();
    } catch (error) {
      console.error('Error saving judge performance:', error);
    }
  };

  const calculateCalibration = (myCard) => {
    if (!selectedRound?.officialCard) return null;

    const officialCard = selectedRound.officialCard;
    
    // Calculate MAE (Mean Absolute Error)
    const myPoints = parseInt(myCard.split('-')[0]);
    const officialPoints = parseInt(officialCard.split('-')[0]);
    const mae = Math.abs(myPoints - officialPoints);

    // Check 10-8 sensitivity
    const my108 = myCard.includes('10-8');
    const official108 = officialCard.includes('10-8');
    const sensitivity108 = my108 === official108;

    // Calculate accuracy score
    let accuracy = 100;
    if (mae === 0) accuracy = 100;
    else if (mae === 1) accuracy = 85;
    else if (mae === 2) accuracy = 60;
    else accuracy = 30;

    return {
      mae,
      sensitivity108,
      accuracy,
      match: myCard === officialCard
    };
  };

  const revealOfficial = () => {
    setOfficialRevealed(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a0b]">
        <p className="text-gray-400">Loading training library...</p>
      </div>
    );
  }

  if (selectedRound && !officialRevealed) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
        <div className="max-w-4xl mx-auto">
          <Card className="bg-[#13151a] border-[#2a2d35] p-8">
            <CardHeader>
              <CardTitle className="text-white text-2xl flex items-center gap-3">
                <GraduationCap className="w-6 h-6 text-amber-500" />
                Shadow Judging - Round {selectedRound.roundNumber}
              </CardTitle>
              <p className="text-gray-400 mt-2">
                {selectedRound.event} - {selectedRound.fighters}
              </p>
            </CardHeader>

            <CardContent className="space-y-6">
              <div className="bg-[#1a1d24] p-6 rounded-lg border border-[#2a2d35]">
                <h3 className="text-white font-semibold mb-4">Round Summary</h3>
                <div className="space-y-2 text-gray-300">
                  {selectedRound.summary?.map((line, idx) => (
                    <p key={idx}>• {line}</p>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="text-white font-semibold">Your Score</h3>
                <div className="grid grid-cols-4 gap-3">
                  {['10-10', '10-9', '10-8', '10-7'].map((card) => (
                    <Button
                      key={card}
                      onClick={() => submitMyScore(card)}
                      disabled={myScore !== null}
                      className={`h-16 text-xl font-bold ${
                        myScore === card
                          ? 'bg-gradient-to-r from-amber-500 to-orange-600 text-white'
                          : 'bg-[#1a1d24] hover:bg-[#22252d] text-gray-300'
                      }`}
                    >
                      {card}
                    </Button>
                  ))}
                </div>
              </div>

              {myScore && (
                <Button
                  onClick={revealOfficial}
                  className="w-full h-14 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white text-lg"
                >
                  <Eye className="mr-2 h-5 w-5" />
                  Reveal Official Card
                </Button>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (selectedRound && officialRevealed) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          <Card className="bg-[#13151a] border-[#2a2d35] p-8">
            <CardHeader>
              <CardTitle className="text-white text-2xl flex items-center gap-3">
                <TrendingUp className="w-6 h-6 text-amber-500" />
                Calibration Results
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-6">
              <div className="grid md:grid-cols-2 gap-6">
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-400 mb-2">Your Score</div>
                    <div className="text-4xl font-bold text-white">{myScore}</div>
                  </div>
                </Card>

                <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-400 mb-2">Official Score</div>
                    <div className="text-4xl font-bold text-amber-500">
                      {selectedRound.officialCard}
                    </div>
                  </div>
                </Card>
              </div>

              <Card className={`p-6 ${
                calibrationScore?.match 
                  ? 'bg-green-900/30 border-green-700/50' 
                  : 'bg-amber-900/30 border-amber-700/50'
              }`}>
                <div className="text-center space-y-4">
                  <div className="text-6xl font-bold text-white">
                    {calibrationScore?.accuracy}%
                  </div>
                  <div className="text-lg text-gray-300">
                    {calibrationScore?.match ? 'Perfect Match!' : 'Close - Keep Training'}
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4 pt-4">
                    <div>
                      <div className="text-xs text-gray-400">MAE</div>
                      <div className="text-2xl font-bold text-white">
                        {calibrationScore?.mae}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-400">10-8 Sensitivity</div>
                      <div className="text-2xl font-bold text-white">
                        {calibrationScore?.sensitivity108 ? '✓' : '✗'}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-400">Match</div>
                      <div className="text-2xl font-bold text-white">
                        {calibrationScore?.match ? '✓' : '✗'}
                      </div>
                    </div>
                  </div>
                </div>
              </Card>

              <div className="flex gap-3">
                <Button
                  onClick={() => setSelectedRound(null)}
                  className="flex-1 h-12 bg-[#1a1d24] hover:bg-[#22252d] text-gray-300"
                >
                  Back to Library
                </Button>
                <Button
                  onClick={() => navigate('/')}
                  className="flex-1 h-12 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white"
                >
                  Back to Events
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        <Card className="bg-[#13151a] border-[#2a2d35] p-8 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">Shadow Judging Library</h1>
              <p className="text-gray-400 text-lg">
                Train with {historicalRounds.length} historical rounds from real events
              </p>
            </div>
            <div className="flex gap-3">
              {judgeStats && (
                <Button
                  onClick={() => setShowStats(!showStats)}
                  className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white"
                >
                  <Trophy className="mr-2 h-4 w-4" />
                  {showStats ? 'Hide Stats' : 'My Stats'}
                </Button>
              )}
              <Button
                onClick={() => navigate('/')}
                className="bg-[#1a1d24] hover:bg-[#22252d] text-gray-300"
              >
                Back to Events
              </Button>
            </div>
          </div>
        </Card>

        {/* Judge Stats Dashboard */}
        {showStats && judgeStats && (
          <Card className="bg-[#13151a] border-[#2a2d35] p-8 mb-8">
            <CardHeader>
              <CardTitle className="text-white text-2xl flex items-center gap-3">
                <Target className="w-6 h-6 text-purple-500" />
                Your Calibration Stats
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-5 gap-6">
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-400 mb-2">Total Rounds</div>
                    <div className="text-4xl font-bold text-white">{judgeStats.totalAttempts}</div>
                  </div>
                </Card>
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-400 mb-2">Avg Accuracy</div>
                    <div className="text-4xl font-bold text-amber-500">{judgeStats.averageAccuracy}%</div>
                  </div>
                </Card>
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-400 mb-2">Avg MAE</div>
                    <div className="text-4xl font-bold text-blue-500">{judgeStats.averageMAE}</div>
                  </div>
                </Card>
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-400 mb-2">10-8 Accuracy</div>
                    <div className="text-4xl font-bold text-green-500">{judgeStats.sensitivity108Rate}%</div>
                  </div>
                </Card>
                <Card className="bg-[#1a1d24] border-[#2a2d35] p-6">
                  <div className="text-center">
                    <div className="text-sm text-gray-400 mb-2">Perfect Matches</div>
                    <div className="text-4xl font-bold text-purple-500">{judgeStats.perfectMatches}</div>
                  </div>
                </Card>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          {historicalRounds.map((round) => (
            <Card key={round.id} className="bg-[#13151a] border-[#2a2d35]">
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-white font-semibold text-lg">{round.event}</h3>
                    <p className="text-gray-400 text-sm">{round.fighters}</p>
                    <p className="text-gray-500 text-xs mt-1">Round {round.roundNumber}</p>
                  </div>
                  <Badge className="bg-amber-900/30 text-amber-400 border-amber-700/30">
                    <Lock className="w-3 h-3 mr-1" />
                    Official Hidden
                  </Badge>
                </div>

                <Button
                  onClick={() => startJudging(round)}
                  className="w-full h-12 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white"
                >
                  Start Judging
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        {historicalRounds.length === 0 && (
          <Card className="bg-[#13151a] border-[#2a2d35] p-12">
            <div className="text-center text-gray-400">
              <GraduationCap className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>No training rounds available yet</p>
              <p className="text-sm mt-2">Check back soon for historical rounds</p>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
