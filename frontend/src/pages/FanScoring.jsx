import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Trophy, 
  Users, 
  Clock, 
  CheckCircle, 
  Share2, 
  User,
  Award,
  ChevronRight,
  Loader2
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const LOGO_URL = "https://customer-assets.emergentagent.com/job_fight-scoring-pro/artifacts/3c45xdoi_FJ.AI%20LOGO%20PRIMARY%20%281%29.PNG";

export default function FanScoring() {
  const [searchParams] = useSearchParams();
  const eventId = searchParams.get('event');
  
  // Auth state
  const [fanId, setFanId] = useState(localStorage.getItem('fan_id'));
  const [sessionId, setSessionId] = useState(localStorage.getItem('fan_session_id'));
  const [username, setUsername] = useState(localStorage.getItem('fan_username') || '');
  const [showRegister, setShowRegister] = useState(false);
  const [registerUsername, setRegisterUsername] = useState('');
  
  // Event state
  const [activeEvent, setActiveEvent] = useState(null);
  const [currentBout, setCurrentBout] = useState(null);
  const [scoringOpen, setScoringOpen] = useState(false);
  const [deadline, setDeadline] = useState(null);
  const [timeRemaining, setTimeRemaining] = useState(0);
  
  // Scoring state
  const [scoreMode, setScoreMode] = useState('simple'); // 'simple' or 'detailed'
  const [selectedWinner, setSelectedWinner] = useState(null);
  const [redScore, setRedScore] = useState(10);
  const [blueScore, setBlueScore] = useState(9);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  
  // Leaderboard state
  const [leaderboard, setLeaderboard] = useState([]);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [fanProfile, setFanProfile] = useState(null);
  
  // Scorecard state
  const [showScorecard, setShowScorecard] = useState(false);
  const [scorecardData, setScorecardData] = useState(null);
  
  const [isLoading, setIsLoading] = useState(false);

  // Initialize guest session if needed
  useEffect(() => {
    const initSession = async () => {
      if (!fanId && !sessionId) {
        try {
          const response = await fetch(`${API}/api/fan/guest-session`, {
            method: 'POST'
          });
          if (response.ok) {
            const data = await response.json();
            setSessionId(data.session_id);
            localStorage.setItem('fan_session_id', data.session_id);
          }
        } catch (error) {
          console.error('Error creating session:', error);
        }
      }
    };
    initSession();
  }, [fanId, sessionId]);

  // Fetch active event
  const fetchActiveEvent = useCallback(async () => {
    try {
      const response = await fetch(`${API}/api/fan/active-event`);
      if (response.ok) {
        const data = await response.json();
        setActiveEvent(data);
        setCurrentBout(data.current_bout);
        setScoringOpen(data.scoring_open);
        setDeadline(data.scoring_deadline);
      }
    } catch (error) {
      console.error('Error fetching event:', error);
    }
  }, []);

  useEffect(() => {
    fetchActiveEvent();
    const interval = setInterval(fetchActiveEvent, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, [fetchActiveEvent]);

  // Countdown timer
  useEffect(() => {
    if (deadline && scoringOpen) {
      const updateTimer = () => {
        const remaining = Math.max(0, deadline - Date.now() / 1000);
        setTimeRemaining(Math.ceil(remaining));
        if (remaining <= 0) {
          setScoringOpen(false);
        }
      };
      updateTimer();
      const interval = setInterval(updateTimer, 100);
      return () => clearInterval(interval);
    }
  }, [deadline, scoringOpen]);

  // Fetch leaderboard
  const fetchLeaderboard = async () => {
    try {
      const response = await fetch(`${API}/api/fan/leaderboard?limit=20`);
      if (response.ok) {
        const data = await response.json();
        setLeaderboard(data.leaderboard);
      }
    } catch (error) {
      console.error('Error fetching leaderboard:', error);
    }
  };

  // Fetch fan profile
  const fetchProfile = async () => {
    if (!fanId) return;
    try {
      const response = await fetch(`${API}/api/fan/profile/${fanId}`);
      if (response.ok) {
        const data = await response.json();
        setFanProfile(data);
      }
    } catch (error) {
      console.error('Error fetching profile:', error);
    }
  };

  useEffect(() => {
    if (fanId) {
      fetchProfile();
    }
  }, [fanId]);

  // Register fan
  const handleRegister = async () => {
    if (!registerUsername.trim()) {
      toast.error('Please enter a username');
      return;
    }
    
    setIsLoading(true);
    try {
      const response = await fetch(`${API}/api/fan/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: registerUsername })
      });
      
      if (response.ok) {
        const data = await response.json();
        setFanId(data.fan_id);
        setUsername(data.username);
        localStorage.setItem('fan_id', data.fan_id);
        localStorage.setItem('fan_username', data.username);
        setShowRegister(false);
        toast.success('Account created! Your scores will now appear on the leaderboard.');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to register');
      }
    } catch (error) {
      toast.error('Error registering');
    } finally {
      setIsLoading(false);
    }
  };

  // Submit score
  const handleSubmitScore = async () => {
    if (!currentBout || !activeEvent) {
      toast.error('No active fight');
      return;
    }
    
    setIsLoading(true);
    try {
      const endpoint = scoreMode === 'simple' ? '/api/fan/score/simple' : '/api/fan/score/detailed';
      const body = scoreMode === 'simple' 
        ? {
            bout_id: currentBout.bout_id,
            round_number: activeEvent.current_round,
            winner: selectedWinner,
            fan_id: fanId,
            session_id: sessionId
          }
        : {
            bout_id: currentBout.bout_id,
            round_number: activeEvent.current_round,
            red_score: redScore,
            blue_score: blueScore,
            fan_id: fanId,
            session_id: sessionId
          };
      
      const response = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      
      if (response.ok) {
        setHasSubmitted(true);
        toast.success('Score submitted!');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to submit score');
      }
    } catch (error) {
      toast.error('Error submitting score');
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch scorecard
  const fetchScorecard = async () => {
    if (!currentBout) return;
    try {
      const params = fanId ? `fan_id=${fanId}` : `session_id=${sessionId}`;
      const response = await fetch(`${API}/api/fan/scorecard/${currentBout.bout_id}?${params}`);
      if (response.ok) {
        const data = await response.json();
        setScorecardData(data);
        setShowScorecard(true);
      }
    } catch (error) {
      console.error('Error fetching scorecard:', error);
    }
  };

  // Share scorecard
  const shareScorecard = () => {
    if (navigator.share && scorecardData) {
      navigator.share({
        title: 'My Fight Judge AI Scorecard',
        text: `I scored ${scorecardData.bout.fighter1} vs ${scorecardData.bout.fighter2}: ${scorecardData.fan_total.red}-${scorecardData.fan_total.blue}. My accuracy: ${scorecardData.accuracy_percentage}%!`,
        url: window.location.href
      });
    } else {
      toast.success('Scorecard link copied!');
    }
  };

  // Reset for new round
  useEffect(() => {
    if (scoringOpen) {
      setHasSubmitted(false);
      setSelectedWinner(null);
      setRedScore(10);
      setBlueScore(9);
    }
  }, [activeEvent?.current_round, scoringOpen]);

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 p-4">
        <div className="max-w-lg mx-auto flex items-center justify-between">
          <img src={LOGO_URL} alt="Fight Judge AI" className="h-10 object-contain" />
          <div className="flex items-center gap-2">
            {fanId ? (
              <Badge className="bg-green-600 text-white">
                <User className="w-3 h-3 mr-1" />
                {username}
              </Badge>
            ) : (
              <Button 
                size="sm" 
                onClick={() => setShowRegister(true)}
                className="bg-amber-500 hover:bg-amber-600 text-black"
              >
                Sign Up
              </Button>
            )}
            <Button 
              size="sm" 
              variant="ghost"
              onClick={() => { fetchLeaderboard(); setShowLeaderboard(true); }}
              className="text-amber-400"
            >
              <Trophy className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-lg mx-auto p-4 space-y-4">
        
        {/* No Active Event */}
        {!activeEvent?.has_active_event && (
          <Card className="bg-gray-900 border-gray-700 p-8 text-center">
            <Clock className="w-16 h-16 mx-auto text-gray-600 mb-4" />
            <h2 className="text-xl font-bold text-gray-400 mb-2">No Active Event</h2>
            <p className="text-gray-500">Check back during the next live event to score fights!</p>
          </Card>
        )}

        {/* Active Event */}
        {activeEvent?.has_active_event && (
          <>
            {/* Event Header */}
            <Card className="bg-gradient-to-r from-red-900/30 via-gray-900 to-blue-900/30 border-gray-700 p-4">
              <div className="text-center">
                <Badge className="bg-green-600 mb-2">LIVE</Badge>
                <h1 className="text-2xl font-bold">{activeEvent.event_name}</h1>
              </div>
            </Card>

            {/* Current Fight */}
            {currentBout && (
              <Card className="bg-gray-900 border-gray-700 p-4">
                <div className="text-center text-gray-400 text-sm mb-2">
                  Round {activeEvent.current_round} of {currentBout.totalRounds}
                </div>
                <div className="flex items-center justify-between">
                  <div className="text-center flex-1">
                    <div className="text-3xl font-bold text-red-400">{currentBout.fighter1?.split(' ')[0]}</div>
                    <div className="text-sm text-gray-500">{currentBout.fighter1?.split(' ').slice(1).join(' ')}</div>
                    <Badge className="bg-red-600 mt-2">RED</Badge>
                  </div>
                  <div className="text-4xl font-black text-gray-600 px-4">VS</div>
                  <div className="text-center flex-1">
                    <div className="text-3xl font-bold text-blue-400">{currentBout.fighter2?.split(' ')[0]}</div>
                    <div className="text-sm text-gray-500">{currentBout.fighter2?.split(' ').slice(1).join(' ')}</div>
                    <Badge className="bg-blue-600 mt-2">BLUE</Badge>
                  </div>
                </div>
              </Card>
            )}

            {/* Scoring Section */}
            {scoringOpen && !hasSubmitted && (
              <Card className="bg-gray-900 border-amber-500 border-2 p-4">
                {/* Timer */}
                <div className="text-center mb-4">
                  <div className="text-amber-400 text-sm font-bold mb-1">SCORING OPEN</div>
                  <div className="text-4xl font-black text-amber-400">
                    {timeRemaining}s
                  </div>
                  <div className="w-full bg-gray-700 h-2 rounded-full mt-2">
                    <div 
                      className="bg-amber-500 h-2 rounded-full transition-all duration-100"
                      style={{ width: `${(timeRemaining / 30) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Mode Toggle */}
                <div className="flex gap-2 mb-4">
                  <Button 
                    className={`flex-1 ${scoreMode === 'simple' ? 'bg-amber-500 text-black' : 'bg-gray-700'}`}
                    onClick={() => setScoreMode('simple')}
                  >
                    Simple
                  </Button>
                  <Button 
                    className={`flex-1 ${scoreMode === 'detailed' ? 'bg-amber-500 text-black' : 'bg-gray-700'}`}
                    onClick={() => setScoreMode('detailed')}
                  >
                    Detailed
                  </Button>
                </div>

                {/* Simple Mode */}
                {scoreMode === 'simple' && (
                  <div className="space-y-3">
                    <div className="text-center text-gray-400 text-sm mb-2">Who won Round {activeEvent.current_round}?</div>
                    <Button 
                      className={`w-full h-16 text-xl font-bold ${selectedWinner === 'RED' ? 'bg-red-600' : 'bg-red-900/50 border border-red-600'}`}
                      onClick={() => setSelectedWinner('RED')}
                    >
                      {currentBout?.fighter1}
                    </Button>
                    <Button 
                      className={`w-full h-16 text-xl font-bold ${selectedWinner === 'DRAW' ? 'bg-gray-600' : 'bg-gray-800 border border-gray-600'}`}
                      onClick={() => setSelectedWinner('DRAW')}
                    >
                      DRAW (10-10)
                    </Button>
                    <Button 
                      className={`w-full h-16 text-xl font-bold ${selectedWinner === 'BLUE' ? 'bg-blue-600' : 'bg-blue-900/50 border border-blue-600'}`}
                      onClick={() => setSelectedWinner('BLUE')}
                    >
                      {currentBout?.fighter2}
                    </Button>
                  </div>
                )}

                {/* Detailed Mode */}
                {scoreMode === 'detailed' && (
                  <div className="space-y-4">
                    <div className="text-center text-gray-400 text-sm">Score Round {activeEvent.current_round}</div>
                    
                    {/* Score Display */}
                    <div className="text-center text-5xl font-black">
                      <span className="text-red-400">{redScore}</span>
                      <span className="text-gray-600 mx-3">-</span>
                      <span className="text-blue-400">{blueScore}</span>
                    </div>
                    
                    {/* Red Score */}
                    <div className="flex items-center gap-2">
                      <Badge className="bg-red-600 w-20">{currentBout?.fighter1?.split(' ')[0]}</Badge>
                      <div className="flex-1 flex gap-1">
                        {[10, 9, 8, 7].map(score => (
                          <Button 
                            key={score}
                            className={`flex-1 ${redScore === score ? 'bg-red-600' : 'bg-gray-700'}`}
                            onClick={() => setRedScore(score)}
                          >
                            {score}
                          </Button>
                        ))}
                      </div>
                    </div>
                    
                    {/* Blue Score */}
                    <div className="flex items-center gap-2">
                      <Badge className="bg-blue-600 w-20">{currentBout?.fighter2?.split(' ')[0]}</Badge>
                      <div className="flex-1 flex gap-1">
                        {[10, 9, 8, 7].map(score => (
                          <Button 
                            key={score}
                            className={`flex-1 ${blueScore === score ? 'bg-blue-600' : 'bg-gray-700'}`}
                            onClick={() => setBlueScore(score)}
                          >
                            {score}
                          </Button>
                        ))}
                      </div>
                    </div>

                    {/* Quick Presets */}
                    <div className="grid grid-cols-3 gap-2">
                      <Button 
                        size="sm"
                        className="bg-red-800 text-xs"
                        onClick={() => { setRedScore(10); setBlueScore(9); }}
                      >
                        10-9 RED
                      </Button>
                      <Button 
                        size="sm"
                        className="bg-gray-700 text-xs"
                        onClick={() => { setRedScore(10); setBlueScore(10); }}
                      >
                        10-10
                      </Button>
                      <Button 
                        size="sm"
                        className="bg-blue-800 text-xs"
                        onClick={() => { setRedScore(9); setBlueScore(10); }}
                      >
                        10-9 BLUE
                      </Button>
                    </div>
                  </div>
                )}

                {/* Submit Button */}
                <Button 
                  className="w-full h-14 mt-4 bg-green-600 hover:bg-green-700 text-xl font-bold"
                  onClick={handleSubmitScore}
                  disabled={isLoading || (scoreMode === 'simple' && !selectedWinner)}
                >
                  {isLoading ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : <CheckCircle className="w-5 h-5 mr-2" />}
                  SUBMIT SCORE
                </Button>
              </Card>
            )}

            {/* Score Submitted */}
            {hasSubmitted && (
              <Card className="bg-green-900/30 border-green-600 p-6 text-center">
                <CheckCircle className="w-16 h-16 mx-auto text-green-400 mb-4" />
                <h2 className="text-2xl font-bold text-green-400 mb-2">Score Submitted!</h2>
                <p className="text-gray-400 mb-4">
                  {scoreMode === 'simple' 
                    ? `You picked: ${selectedWinner}` 
                    : `Your score: ${redScore}-${blueScore}`
                  }
                </p>
                <p className="text-gray-500 text-sm">Waiting for next round...</p>
              </Card>
            )}

            {/* Waiting for Scoring */}
            {!scoringOpen && !hasSubmitted && currentBout && (
              <Card className="bg-gray-900 border-gray-700 p-6 text-center">
                <Clock className="w-12 h-12 mx-auto text-gray-600 mb-4 animate-pulse" />
                <h2 className="text-xl font-bold text-gray-400 mb-2">Round In Progress</h2>
                <p className="text-gray-500">Scoring will open at the end of the round</p>
              </Card>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <Button 
                className="flex-1 bg-gray-800 hover:bg-gray-700"
                onClick={fetchScorecard}
              >
                <Award className="w-4 h-4 mr-2" />
                My Scorecard
              </Button>
              <Button 
                className="flex-1 bg-gray-800 hover:bg-gray-700"
                onClick={() => { fetchLeaderboard(); setShowLeaderboard(true); }}
              >
                <Trophy className="w-4 h-4 mr-2" />
                Leaderboard
              </Button>
            </div>
          </>
        )}

        {/* Sign Up Prompt for Guests */}
        {!fanId && sessionId && (
          <Card className="bg-amber-900/20 border-amber-600 p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-amber-400 font-bold">Track Your Scores!</div>
                <div className="text-gray-400 text-sm">Sign up to appear on the leaderboard</div>
              </div>
              <Button 
                size="sm"
                onClick={() => setShowRegister(true)}
                className="bg-amber-500 hover:bg-amber-600 text-black"
              >
                Sign Up <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </Card>
        )}
      </main>

      {/* Register Dialog */}
      <Dialog open={showRegister} onOpenChange={setShowRegister}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-center">
              <img src={LOGO_URL} alt="Fight Judge AI" className="h-12 mx-auto mb-4" />
              Create Account
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <Input 
              placeholder="Choose a username"
              value={registerUsername}
              onChange={(e) => setRegisterUsername(e.target.value)}
              className="bg-gray-800 border-gray-600 text-white"
            />
            <Button 
              className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold"
              onClick={handleRegister}
              disabled={isLoading}
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Create Account
            </Button>
            <p className="text-gray-500 text-xs text-center">
              Your scores will be tracked and you'll appear on the leaderboard!
            </p>
          </div>
        </DialogContent>
      </Dialog>

      {/* Leaderboard Dialog */}
      <Dialog open={showLeaderboard} onOpenChange={setShowLeaderboard}>
        <DialogContent className="bg-gray-900 border-amber-500 text-white max-w-md max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="text-center flex items-center justify-center gap-2">
              <Trophy className="w-6 h-6 text-amber-400" />
              Leaderboard
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-2 py-4">
            {leaderboard.map((fan, idx) => (
              <div 
                key={fan.fan_id}
                className={`flex items-center justify-between p-3 rounded-lg ${
                  idx === 0 ? 'bg-amber-900/30 border border-amber-600' :
                  idx === 1 ? 'bg-gray-700/50' :
                  idx === 2 ? 'bg-orange-900/30' :
                  'bg-gray-800'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                    idx === 0 ? 'bg-amber-500 text-black' :
                    idx === 1 ? 'bg-gray-400 text-black' :
                    idx === 2 ? 'bg-orange-600 text-white' :
                    'bg-gray-700 text-white'
                  }`}>
                    {fan.rank}
                  </div>
                  <div>
                    <div className="font-bold">{fan.display_name}</div>
                    <div className="text-xs text-gray-500">{fan.rounds_scored} rounds</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-green-400">{fan.accuracy}%</div>
                  <div className="text-xs text-gray-500">{fan.correct_predictions} correct</div>
                </div>
              </div>
            ))}
            {leaderboard.length === 0 && (
              <div className="text-center text-gray-500 py-8">
                No scores yet. Be the first!
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Scorecard Dialog */}
      <Dialog open={showScorecard} onOpenChange={setShowScorecard}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center">
              <img src={LOGO_URL} alt="Fight Judge AI" className="h-10 mx-auto mb-2" />
              My Scorecard
            </DialogTitle>
          </DialogHeader>
          {scorecardData && (
            <div className="space-y-4 py-4">
              {/* Fight Info */}
              <div className="text-center">
                <div className="text-lg font-bold">
                  <span className="text-red-400">{scorecardData.bout?.fighter1}</span>
                  <span className="text-gray-500 mx-2">vs</span>
                  <span className="text-blue-400">{scorecardData.bout?.fighter2}</span>
                </div>
              </div>

              {/* Totals Comparison */}
              <div className="grid grid-cols-2 gap-4">
                <Card className="bg-gray-800 p-4 text-center">
                  <div className="text-gray-400 text-xs mb-1">YOUR SCORE</div>
                  <div className="text-2xl font-bold">
                    <span className="text-red-400">{scorecardData.fan_total?.red}</span>
                    <span className="text-gray-500">-</span>
                    <span className="text-blue-400">{scorecardData.fan_total?.blue}</span>
                  </div>
                </Card>
                <Card className="bg-gray-800 p-4 text-center">
                  <div className="text-gray-400 text-xs mb-1">AI SCORE</div>
                  <div className="text-2xl font-bold">
                    <span className="text-red-400">{scorecardData.ai_total?.red}</span>
                    <span className="text-gray-500">-</span>
                    <span className="text-blue-400">{scorecardData.ai_total?.blue}</span>
                  </div>
                </Card>
              </div>

              {/* Accuracy */}
              <Card className="bg-green-900/30 border-green-600 p-4 text-center">
                <div className="text-gray-400 text-xs mb-1">YOUR ACCURACY</div>
                <div className="text-4xl font-bold text-green-400">{scorecardData.accuracy_percentage}%</div>
                <div className="text-gray-500 text-sm">{scorecardData.rounds_matched}/{scorecardData.total_rounds} rounds matched AI</div>
              </Card>

              {/* Round by Round */}
              <div className="space-y-2">
                <div className="text-gray-400 text-xs">ROUND BY ROUND</div>
                {scorecardData.fan_scores?.map((fs, idx) => {
                  const ai = scorecardData.ai_scores?.find(a => a.round_number === fs.round_number);
                  const matched = ai && fs.winner === ai.winner;
                  return (
                    <div key={idx} className={`flex items-center justify-between p-2 rounded ${matched ? 'bg-green-900/30' : 'bg-red-900/30'}`}>
                      <span className="text-gray-400">R{fs.round_number}</span>
                      <span className="font-bold">
                        <span className="text-red-400">{fs.red_score}</span>
                        <span className="text-gray-500">-</span>
                        <span className="text-blue-400">{fs.blue_score}</span>
                      </span>
                      <span className="text-xs text-gray-500">
                        AI: {ai?.red_points}-{ai?.blue_points}
                      </span>
                      {matched ? (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      ) : (
                        <span className="text-red-400 text-xs">MISS</span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Share Button */}
              <Button 
                className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold"
                onClick={shareScorecard}
              >
                <Share2 className="w-4 h-4 mr-2" />
                Share Scorecard
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
