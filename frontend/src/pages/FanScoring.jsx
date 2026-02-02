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
  Clock, 
  CheckCircle, 
  Share2, 
  User,
  Award,
  ChevronRight,
  Loader2,
  Play,
  RotateCcw
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;
const LOGO_URL = "https://customer-assets.emergentagent.com/job_fight-scoring-pro/artifacts/3c45xdoi_FJ.AI%20LOGO%20PRIMARY%20%281%29.PNG";

// Demo fighters for demo mode
const DEMO_FIGHTERS = [
  { fighter1: "Conor McGregor", fighter2: "Dustin Poirier", event: "UFC 300" },
  { fighter1: "Jon Jones", fighter2: "Stipe Miocic", event: "UFC 309" },
  { fighter1: "Israel Adesanya", fighter2: "Alex Pereira", event: "UFC 287" },
  { fighter1: "Khabib Nurmagomedov", fighter2: "Justin Gaethje", event: "UFC 254" },
  { fighter1: "Amanda Nunes", fighter2: "Valentina Shevchenko", event: "UFC 289" },
];

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
  
  // Demo mode state
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [demoRound, setDemoRound] = useState(1);
  const [demoFighterIndex, setDemoFighterIndex] = useState(0);
  const [demoScores, setDemoScores] = useState([]);
  const [demoScoringOpen, setDemoScoringOpen] = useState(false);
  const [demoTimeRemaining, setDemoTimeRemaining] = useState(0);
  
  // Scoring state
  const [scoreMode, setScoreMode] = useState('simple');
  const [selectedWinner, setSelectedWinner] = useState(null);
  const [redScore, setRedScore] = useState(10);
  const [blueScore, setBlueScore] = useState(9);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  
  // Scorecard state
  const [showScorecard, setShowScorecard] = useState(false);
  
  const [isLoading, setIsLoading] = useState(false);

  const demoFighters = DEMO_FIGHTERS[demoFighterIndex];

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
    if (isDemoMode) return;
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
  }, [isDemoMode]);

  useEffect(() => {
    fetchActiveEvent();
    const interval = setInterval(fetchActiveEvent, 3000);
    return () => clearInterval(interval);
  }, [fetchActiveEvent]);

  // Countdown timer for live mode
  useEffect(() => {
    if (deadline && scoringOpen && !isDemoMode) {
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
  }, [deadline, scoringOpen, isDemoMode]);

  // Demo mode countdown
  useEffect(() => {
    if (demoScoringOpen && isDemoMode) {
      const interval = setInterval(() => {
        setDemoTimeRemaining(prev => {
          if (prev <= 0) {
            setDemoScoringOpen(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [demoScoringOpen, isDemoMode]);

  // Start demo mode
  const startDemo = () => {
    setIsDemoMode(true);
    setDemoRound(1);
    setDemoScores([]);
    setHasSubmitted(false);
    setSelectedWinner(null);
    setRedScore(10);
    setBlueScore(9);
    // Start scoring window
    setDemoScoringOpen(true);
    setDemoTimeRemaining(30);
  };

  // Reset demo
  const resetDemo = () => {
    setIsDemoMode(false);
    setDemoRound(1);
    setDemoScores([]);
    setHasSubmitted(false);
    setDemoScoringOpen(false);
  };

  // Next round in demo
  const nextDemoRound = () => {
    if (demoRound < 3) {
      setDemoRound(demoRound + 1);
      setHasSubmitted(false);
      setSelectedWinner(null);
      setRedScore(10);
      setBlueScore(9);
      setDemoScoringOpen(true);
      setDemoTimeRemaining(30);
    } else {
      // Fight over - show results
      setShowScorecard(true);
    }
  };

  // Submit demo score
  const submitDemoScore = () => {
    const score = {
      round: demoRound,
      red_score: scoreMode === 'simple' ? (selectedWinner === 'RED' ? 10 : selectedWinner === 'DRAW' ? 10 : 9) : redScore,
      blue_score: scoreMode === 'simple' ? (selectedWinner === 'BLUE' ? 10 : selectedWinner === 'DRAW' ? 10 : 9) : blueScore,
      winner: scoreMode === 'simple' ? selectedWinner : (redScore > blueScore ? 'RED' : blueScore > redScore ? 'BLUE' : 'DRAW')
    };
    setDemoScores([...demoScores, score]);
    setHasSubmitted(true);
    setDemoScoringOpen(false);
    toast.success(`Round ${demoRound} score submitted!`);
  };

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
        toast.success('Account created!');
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

  // Submit live score
  const handleSubmitScore = async () => {
    if (isDemoMode) {
      submitDemoScore();
      return;
    }
    
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

  // Calculate demo totals
  const demoTotals = demoScores.reduce((acc, s) => ({
    red: acc.red + s.red_score,
    blue: acc.blue + s.blue_score
  }), { red: 0, blue: 0 });

  // Share scorecard
  const shareScorecard = () => {
    const text = isDemoMode 
      ? `I scored ${demoFighters.fighter1} vs ${demoFighters.fighter2}: ${demoTotals.red}-${demoTotals.blue} on Fight Judge AI!`
      : 'Check out my scorecard on Fight Judge AI!';
    
    if (navigator.share) {
      navigator.share({
        title: 'My Fight Judge AI Scorecard',
        text: text,
        url: window.location.href
      });
    } else {
      navigator.clipboard.writeText(text);
      toast.success('Copied to clipboard!');
    }
  };

  // Reset for new round
  useEffect(() => {
    if (scoringOpen && !isDemoMode) {
      setHasSubmitted(false);
      setSelectedWinner(null);
      setRedScore(10);
      setBlueScore(9);
    }
  }, [activeEvent?.current_round, scoringOpen, isDemoMode]);

  const displayScoringOpen = isDemoMode ? demoScoringOpen : scoringOpen;
  const displayTimeRemaining = isDemoMode ? demoTimeRemaining : timeRemaining;
  const displayRound = isDemoMode ? demoRound : activeEvent?.current_round;
  const displayFighter1 = isDemoMode ? demoFighters.fighter1 : currentBout?.fighter1;
  const displayFighter2 = isDemoMode ? demoFighters.fighter2 : currentBout?.fighter2;
  const displayEventName = isDemoMode ? demoFighters.event : activeEvent?.event_name;
  const hasActiveContent = isDemoMode || activeEvent?.has_active_event;

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header with BIG Logo */}
      <header className="bg-gradient-to-b from-gray-900 to-black pt-8 pb-4 px-4">
        <div className="max-w-lg mx-auto text-center">
          <img 
            src={LOGO_URL} 
            alt="Fight Judge AI" 
            className="h-24 md:h-32 lg:h-40 mx-auto object-contain mb-4"
          />
          <p className="text-gray-500 text-sm">Score fights like a pro</p>
        </div>
      </header>

      <main className="max-w-lg mx-auto p-4 space-y-4">
        
        {/* No Active Event - Show Demo Option */}
        {!hasActiveContent && (
          <Card className="bg-gray-900 border-gray-700 p-8 text-center">
            <Clock className="w-16 h-16 mx-auto text-gray-600 mb-4" />
            <h2 className="text-xl font-bold text-gray-400 mb-2">No Live Event</h2>
            <p className="text-gray-500 mb-6">Check back during the next live event to score fights!</p>
            
            <Button 
              onClick={startDemo}
              className="w-full h-14 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-black font-bold text-lg"
            >
              <Play className="w-5 h-5 mr-2" />
              TRY DEMO MODE
            </Button>
            <p className="text-gray-600 text-xs mt-3">Practice scoring with sample fights</p>
          </Card>
        )}

        {/* Active Event or Demo */}
        {hasActiveContent && (
          <>
            {/* Event Header */}
            <Card className={`border-gray-700 p-4 ${isDemoMode ? 'bg-gradient-to-r from-orange-900/30 via-gray-900 to-amber-900/30 border-amber-600' : 'bg-gradient-to-r from-red-900/30 via-gray-900 to-blue-900/30'}`}>
              <div className="text-center">
                <Badge className={isDemoMode ? "bg-orange-600 mb-2" : "bg-green-600 mb-2"}>
                  {isDemoMode ? "DEMO MODE" : "LIVE"}
                </Badge>
                <h1 className="text-2xl font-bold">{displayEventName}</h1>
                {isDemoMode && (
                  <Button 
                    size="sm" 
                    variant="ghost" 
                    onClick={resetDemo}
                    className="text-gray-400 mt-2"
                  >
                    <RotateCcw className="w-4 h-4 mr-1" /> Exit Demo
                  </Button>
                )}
              </div>
            </Card>

            {/* Current Fight */}
            <Card className="bg-gray-900 border-gray-700 p-4">
              <div className="text-center text-gray-400 text-sm mb-2">
                Round {displayRound} of 3
              </div>
              <div className="flex items-center justify-between">
                <div className="text-center flex-1">
                  <div className="text-2xl md:text-3xl font-bold text-red-400">{displayFighter1?.split(' ')[0]}</div>
                  <div className="text-xs md:text-sm text-gray-500">{displayFighter1?.split(' ').slice(1).join(' ')}</div>
                  <Badge className="bg-red-600 mt-2">RED</Badge>
                </div>
                <div className="text-3xl md:text-4xl font-black text-gray-600 px-2 md:px-4">VS</div>
                <div className="text-center flex-1">
                  <div className="text-2xl md:text-3xl font-bold text-blue-400">{displayFighter2?.split(' ')[0]}</div>
                  <div className="text-xs md:text-sm text-gray-500">{displayFighter2?.split(' ').slice(1).join(' ')}</div>
                  <Badge className="bg-blue-600 mt-2">BLUE</Badge>
                </div>
              </div>
              
              {/* Running Total in Demo */}
              {isDemoMode && demoScores.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-700 text-center">
                  <div className="text-gray-500 text-xs mb-1">RUNNING TOTAL</div>
                  <div className="text-2xl font-bold">
                    <span className="text-red-400">{demoTotals.red}</span>
                    <span className="text-gray-600 mx-2">-</span>
                    <span className="text-blue-400">{demoTotals.blue}</span>
                  </div>
                </div>
              )}
            </Card>

            {/* Scoring Section */}
            {displayScoringOpen && !hasSubmitted && (
              <Card className="bg-gray-900 border-amber-500 border-2 p-4">
                {/* Timer */}
                <div className="text-center mb-4">
                  <div className="text-amber-400 text-sm font-bold mb-1">SCORING OPEN</div>
                  <div className="text-4xl font-black text-amber-400">
                    {displayTimeRemaining}s
                  </div>
                  <div className="w-full bg-gray-700 h-2 rounded-full mt-2">
                    <div 
                      className="bg-amber-500 h-2 rounded-full transition-all duration-100"
                      style={{ width: `${(displayTimeRemaining / 30) * 100}%` }}
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
                    <div className="text-center text-gray-400 text-sm mb-2">Who won Round {displayRound}?</div>
                    <Button 
                      className={`w-full h-16 text-xl font-bold ${selectedWinner === 'RED' ? 'bg-red-600' : 'bg-red-900/50 border border-red-600'}`}
                      onClick={() => setSelectedWinner('RED')}
                    >
                      {displayFighter1}
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
                      {displayFighter2}
                    </Button>
                  </div>
                )}

                {/* Detailed Mode */}
                {scoreMode === 'detailed' && (
                  <div className="space-y-4">
                    <div className="text-center text-gray-400 text-sm">Score Round {displayRound}</div>
                    
                    {/* Score Display */}
                    <div className="text-center text-5xl font-black">
                      <span className="text-red-400">{redScore}</span>
                      <span className="text-gray-600 mx-3">-</span>
                      <span className="text-blue-400">{blueScore}</span>
                    </div>
                    
                    {/* Red Score */}
                    <div className="flex items-center gap-2">
                      <Badge className="bg-red-600 w-20 justify-center">{displayFighter1?.split(' ')[0]}</Badge>
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
                      <Badge className="bg-blue-600 w-20 justify-center">{displayFighter2?.split(' ')[0]}</Badge>
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
                  Round {displayRound}: {scoreMode === 'simple' 
                    ? `You picked ${selectedWinner}` 
                    : `${redScore}-${blueScore}`
                  }
                </p>
                
                {isDemoMode && (
                  <Button 
                    onClick={nextDemoRound}
                    className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold"
                  >
                    {demoRound < 3 ? `Next Round (${demoRound + 1}/3)` : 'View Final Scorecard'}
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                )}
                
                {!isDemoMode && (
                  <p className="text-gray-500 text-sm">Waiting for next round...</p>
                )}
              </Card>
            )}

            {/* Waiting for Scoring (Demo) */}
            {isDemoMode && !demoScoringOpen && !hasSubmitted && (
              <Card className="bg-gray-900 border-gray-700 p-6 text-center">
                <Button 
                  onClick={() => { setDemoScoringOpen(true); setDemoTimeRemaining(30); }}
                  className="w-full h-14 bg-amber-500 hover:bg-amber-600 text-black font-bold text-lg"
                >
                  <Play className="w-5 h-5 mr-2" />
                  Start Round {demoRound} Scoring
                </Button>
              </Card>
            )}

            {/* Waiting for Scoring (Live) */}
            {!isDemoMode && !scoringOpen && !hasSubmitted && currentBout && (
              <Card className="bg-gray-900 border-gray-700 p-6 text-center">
                <Clock className="w-12 h-12 mx-auto text-gray-600 mb-4 animate-pulse" />
                <h2 className="text-xl font-bold text-gray-400 mb-2">Round In Progress</h2>
                <p className="text-gray-500">Scoring will open at the end of the round</p>
              </Card>
            )}

            {/* My Scorecard Button */}
            {isDemoMode && demoScores.length > 0 && (
              <Button 
                className="w-full bg-gray-800 hover:bg-gray-700"
                onClick={() => setShowScorecard(true)}
              >
                <Award className="w-4 h-4 mr-2" />
                View My Scorecard ({demoScores.length} rounds)
              </Button>
            )}
          </>
        )}

        {/* Demo CTA when no event */}
        {!isDemoMode && !activeEvent?.has_active_event && (
          <div className="text-center pt-4">
            <p className="text-gray-600 text-sm">Want to practice?</p>
            <Button 
              variant="link"
              onClick={startDemo}
              className="text-amber-400"
            >
              Try Demo Mode →
            </Button>
          </div>
        )}
      </main>

      {/* Register Dialog */}
      <Dialog open={showRegister} onOpenChange={setShowRegister}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-center">
              <img src={LOGO_URL} alt="Fight Judge AI" className="h-16 mx-auto mb-4" />
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
          </div>
        </DialogContent>
      </Dialog>

      {/* Scorecard Dialog */}
      <Dialog open={showScorecard} onOpenChange={setShowScorecard}>
        <DialogContent className="bg-gray-900 border-amber-500 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center">
              <img src={LOGO_URL} alt="Fight Judge AI" className="h-12 mx-auto mb-2" />
              My Scorecard
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Fight Info */}
            <div className="text-center">
              <div className="text-lg font-bold">
                <span className="text-red-400">{demoFighters.fighter1}</span>
                <span className="text-gray-500 mx-2">vs</span>
                <span className="text-blue-400">{demoFighters.fighter2}</span>
              </div>
              <div className="text-gray-500 text-sm">{demoFighters.event}</div>
            </div>

            {/* Final Score */}
            <Card className="bg-gray-800 p-6 text-center">
              <div className="text-gray-400 text-xs mb-2">YOUR FINAL SCORE</div>
              <div className="text-5xl font-black">
                <span className="text-red-400">{demoTotals.red}</span>
                <span className="text-gray-600 mx-3">-</span>
                <span className="text-blue-400">{demoTotals.blue}</span>
              </div>
              <div className="mt-2">
                <Badge className={`text-lg px-4 py-1 ${
                  demoTotals.red > demoTotals.blue ? 'bg-red-600' :
                  demoTotals.blue > demoTotals.red ? 'bg-blue-600' :
                  'bg-gray-600'
                }`}>
                  {demoTotals.red > demoTotals.blue ? demoFighters.fighter1 :
                   demoTotals.blue > demoTotals.red ? demoFighters.fighter2 :
                   'DRAW'}
                </Badge>
              </div>
            </Card>

            {/* Round by Round */}
            <div className="space-y-2">
              <div className="text-gray-400 text-xs">ROUND BY ROUND</div>
              {demoScores.map((score, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded bg-gray-800">
                  <span className="text-gray-400">Round {score.round}</span>
                  <span className="font-bold text-lg">
                    <span className="text-red-400">{score.red_score}</span>
                    <span className="text-gray-600 mx-2">-</span>
                    <span className="text-blue-400">{score.blue_score}</span>
                  </span>
                  <Badge className={
                    score.winner === 'RED' ? 'bg-red-600' :
                    score.winner === 'BLUE' ? 'bg-blue-600' :
                    'bg-gray-600'
                  }>
                    {score.winner}
                  </Badge>
                </div>
              ))}
            </div>

            {/* Share Button */}
            <Button 
              className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold"
              onClick={shareScorecard}
            >
              <Share2 className="w-4 h-4 mr-2" />
              Share Scorecard
            </Button>

            {/* Try Another Fight */}
            <Button 
              variant="outline"
              className="w-full border-gray-600 text-gray-400"
              onClick={() => {
                setShowScorecard(false);
                setDemoFighterIndex((demoFighterIndex + 1) % DEMO_FIGHTERS.length);
                setDemoRound(1);
                setDemoScores([]);
                setHasSubmitted(false);
                setDemoScoringOpen(true);
                setDemoTimeRemaining(30);
              }}
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Score Another Fight
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
