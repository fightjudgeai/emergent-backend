import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { db } from '@/firebase';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Lock, Unlock, CheckCircle, Clock, AlertTriangle } from 'lucide-react';

export default function SupervisorPanel() {
  const { boutId } = useParams();
  const navigate = useNavigate();
  const [bout, setBout] = useState(null);
  const [judgeScores, setJudgeScores] = useState({});
  const [loading, setLoading] = useState(true);
  const [supervisorCode, setSupervisorCode] = useState('');
  const [showUnlockDialog, setShowUnlockDialog] = useState(false);
  const [selectedJudge, setSelectedJudge] = useState(null);
  const [selectedRound, setSelectedRound] = useState(null);
  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  useEffect(() => {
    if (boutId) {
      loadBout();
      loadAllJudgeScores();
      
      // Real-time listener for judge scores
      const unsubscribe = db.collection('judgeScores')
        .where('boutId', '==', boutId)
        .onSnapshot((snapshot) => {
          const scores = {};
          snapshot.docs.forEach(doc => {
            const data = doc.data();
            const roundNum = data.roundNum;
            if (!scores[roundNum]) {
              scores[roundNum] = [];
            }
            scores[roundNum].push({ id: doc.id, ...data });
          });
          setJudgeScores(scores);
        });

      return () => unsubscribe();
    }
  }, [boutId]);

  const loadBout = async () => {
    try {
      const boutDoc = await db.collection('bouts').doc(boutId).get();
      if (boutDoc.exists) {
        setBout({ id: boutDoc.id, ...boutDoc.data() });
      }
    } catch (error) {
      console.error('Error loading bout:', error);
      toast.error('Failed to load bout');
    } finally {
      setLoading(false);
    }
  };

  const loadAllJudgeScores = async () => {
    try {
      console.log('[Supervisor] Loading judge scores for bout:', boutId);
      const response = await fetch(`${backendUrl}/api/judge-scores/${boutId}`);
      
      if (!response.ok) {
        console.error('[Supervisor] Failed to fetch scores:', response.status);
        return;
      }
      
      const data = await response.json();
      console.log('[Supervisor] Received data from API:', data);
      
      // Convert to the format expected by state
      const scores = {};
      if (data.rounds) {
        Object.keys(data.rounds).forEach(roundNum => {
          scores[parseInt(roundNum)] = data.rounds[roundNum];
        });
        console.log('[Supervisor] Converted scores:', scores);
        setJudgeScores(scores);
      } else {
        console.warn('[Supervisor] No rounds data in response');
      }
    } catch (error) {
      console.error('[Supervisor] Error loading judge scores:', error);
    }
  };

  const handleUnlockScore = async () => {
    if (!supervisorCode || !selectedJudge || selectedRound === null) {
      toast.error('Please enter supervisor code');
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/judge-scores/unlock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          round_num: selectedRound,
          judge_id: selectedJudge.judge_id,
          supervisor_code: supervisorCode
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to unlock score');
      }

      toast.success(`Unlocked score for ${selectedJudge.judge_name}`);
      setShowUnlockDialog(false);
      setSupervisorCode('');
      setSelectedJudge(null);
      setSelectedRound(null);
      loadAllJudgeScores();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const handleForceCloseRound = async (roundNum) => {
    if (!supervisorCode) {
      toast.error('Please enter supervisor code first');
      return;
    }

    if (!window.confirm(`Force close round ${roundNum}? This will allow the operator to end the round even with pending judges.`)) {
      return;
    }

    try {
      const response = await fetch(`${backendUrl}/api/rounds/force-close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          round_num: roundNum,
          supervisor_code: supervisorCode,
          closed_by: 'Supervisor'
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to force close round');
      }

      toast.success(`Round ${roundNum} force-closed successfully`);
      setSupervisorCode('');
    } catch (error) {
      toast.error(error.message);
    }
  };

  const getRoundStatus = (roundNum) => {
    const scores = judgeScores[roundNum] || [];
    const lockedCount = scores.filter(s => s.locked).length;
    const totalCount = scores.length;
    
    if (totalCount === 0) return { status: 'no-judges', label: 'No Judges', color: 'gray' };
    if (lockedCount === totalCount) return { status: 'complete', label: 'Complete', color: 'green' };
    if (lockedCount > 0) return { status: 'partial', label: `${lockedCount}/${totalCount} Locked`, color: 'yellow' };
    return { status: 'pending', label: 'Pending', color: 'red' };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading supervisor panel...</p>
        </div>
      </div>
    );
  }

  if (!bout) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Card className="p-8">
          <p className="text-red-600 mb-4">Bout not found</p>
          <Button onClick={() => navigate('/')}>Return Home</Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Button
            variant="outline"
            onClick={() => navigate(`/operator/${boutId}`)}
            className="mb-4"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Operator Panel
          </Button>
          
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>🎯 Supervisor Panel</span>
                <Badge variant="outline" className="text-lg">
                  {bout.fighter1} vs {bout.fighter2}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4 items-center">
                <div>
                  <p className="text-sm text-gray-600">Event</p>
                  <p className="font-semibold">{bout.eventName}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Current Round</p>
                  <p className="font-semibold">Round {bout.currentRound} of {bout.totalRounds}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Supervisor Code Input */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Supervisor Authentication</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 items-end">
              <div className="flex-1">
                <label className="block text-sm font-medium mb-2">Supervisor Code</label>
                <Input
                  type="password"
                  value={supervisorCode}
                  onChange={(e) => setSupervisorCode(e.target.value)}
                  placeholder="Enter supervisor code"
                  className="max-w-xs"
                />
              </div>
              {supervisorCode && (
                <Badge variant="outline" className="bg-green-50 text-green-700">
                  Code Entered ✓
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Round-by-Round Judge Scores */}
        <div className="space-y-6">
          {Array.from({ length: bout.totalRounds }, (_, i) => i + 1).map((roundNum) => {
            const scores = judgeScores[roundNum] || [];
            const status = getRoundStatus(roundNum);
            
            return (
              <Card key={roundNum}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-3">
                      Round {roundNum}
                      {status.status === 'complete' && (
                        <Badge className="bg-green-500">
                          <CheckCircle className="mr-1 h-3 w-3" />
                          All Locked
                        </Badge>
                      )}
                      {status.status === 'partial' && (
                        <Badge className="bg-yellow-500">
                          <Clock className="mr-1 h-3 w-3" />
                          {status.label}
                        </Badge>
                      )}
                      {status.status === 'pending' && (
                        <Badge className="bg-red-500">
                          <AlertTriangle className="mr-1 h-3 w-3" />
                          Pending
                        </Badge>
                      )}
                    </CardTitle>
                    {status.status !== 'complete' && supervisorCode && (
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleForceCloseRound(roundNum)}
                      >
                        Force Close Round
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {scores.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">No judge scores submitted yet</p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b">
                            <th className="text-left py-2 px-4">Judge</th>
                            <th className="text-center py-2 px-4">{bout.fighter1}</th>
                            <th className="text-center py-2 px-4">{bout.fighter2}</th>
                            <th className="text-center py-2 px-4">Score Card</th>
                            <th className="text-center py-2 px-4">Status</th>
                            <th className="text-center py-2 px-4">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {scores.map((score) => (
                            <tr key={score.judge_id} className="border-b hover:bg-gray-50">
                              <td className="py-3 px-4 font-medium">{score.judge_name}</td>
                              <td className="text-center py-3 px-4 text-lg">{score.fighter1_score}</td>
                              <td className="text-center py-3 px-4 text-lg">{score.fighter2_score}</td>
                              <td className="text-center py-3 px-4">
                                <Badge variant="outline" className="text-base">
                                  {score.card}
                                </Badge>
                              </td>
                              <td className="text-center py-3 px-4">
                                {score.locked ? (
                                  <Badge className="bg-green-500">
                                    <Lock className="mr-1 h-3 w-3" />
                                    Locked
                                  </Badge>
                                ) : (
                                  <Badge className="bg-yellow-500">
                                    <Clock className="mr-1 h-3 w-3" />
                                    Pending
                                  </Badge>
                                )}
                              </td>
                              <td className="text-center py-3 px-4">
                                {score.locked && supervisorCode && (
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                      setSelectedJudge(score);
                                      setSelectedRound(roundNum);
                                      setShowUnlockDialog(true);
                                    }}
                                  >
                                    <Unlock className="mr-1 h-3 w-3" />
                                    Unlock
                                  </Button>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Unlock Confirmation Dialog */}
        {showUnlockDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Unlock Judge Score</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p>
                  Are you sure you want to unlock the score for <strong>{selectedJudge?.judge_name}</strong> in Round {selectedRound}?
                </p>
                <p className="text-sm text-gray-600">
                  This will allow the judge to modify their score again.
                </p>
                <div className="flex gap-2 justify-end">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowUnlockDialog(false);
                      setSelectedJudge(null);
                      setSelectedRound(null);
                    }}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleUnlockScore}>
                    Confirm Unlock
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
