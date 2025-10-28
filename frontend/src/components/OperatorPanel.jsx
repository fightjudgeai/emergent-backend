import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import firebase from 'firebase/compat/app';
import { db } from '@/firebase';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Play, Pause, ChevronRight, Eye } from 'lucide-react';

export default function OperatorPanel() {
  const { boutId } = useParams();
  const navigate = useNavigate();
  const [bout, setBout] = useState(null);
  const [selectedFighter, setSelectedFighter] = useState('fighter1');
  const [controlTimers, setControlTimers] = useState({
    fighter1: { time: 0, isRunning: false, startTime: null },
    fighter2: { time: 0, isRunning: false, startTime: null }
  });
  const [showSubDialog, setShowSubDialog] = useState(false);
  const [subDepth, setSubDepth] = useState('light');
  const timerRef = useRef(null);

  useEffect(() => {
    loadBout();
  }, [boutId]);

  useEffect(() => {
    // Update control timers every 100ms for smooth display
    timerRef.current = setInterval(() => {
      setControlTimers(prev => {
        const newTimers = { ...prev };
        
        if (newTimers.fighter1.isRunning) {
          const elapsed = Math.floor((Date.now() - newTimers.fighter1.startTime) / 1000);
          newTimers.fighter1.time = elapsed;
        }
        
        if (newTimers.fighter2.isRunning) {
          const elapsed = Math.floor((Date.now() - newTimers.fighter2.startTime) / 1000);
          newTimers.fighter2.time = elapsed;
        }
        
        return newTimers;
      });
    }, 100);
    
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const loadBout = async () => {
    try {
      const boutDoc = await db.collection('bouts').doc(boutId).get();
      if (boutDoc.exists) {
        setBout({ id: boutDoc.id, ...boutDoc.data() });
      } else {
        toast.error('Bout not found');
        navigate('/');
      }
    } catch (error) {
      console.error('Error loading bout:', error);
      toast.error('Failed to load bout');
    }
  };

  const logEvent = async (eventType, metadata = {}) => {
    try {
      // Get current control time for the selected fighter
      const currentTime = controlTimers[selectedFighter].time;
      
      await db.collection('events').add({
        boutId,
        round: bout.currentRound,
        fighter: selectedFighter,
        eventType,
        timestamp: currentTime,
        metadata,
        createdAt: firebase.firestore.FieldValue.serverTimestamp()
      });
      toast.success(`${eventType} logged for ${selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2}`);
    } catch (error) {
      console.error('Error logging event:', error);
      toast.error('Failed to log event');
    }
  };

  const toggleControl = async () => {
    const fighter = selectedFighter;
    const isCurrentlyRunning = controlTimers[fighter].isRunning;
    
    if (isCurrentlyRunning) {
      // Stop control timer
      const duration = controlTimers[fighter].time;
      
      await logEvent('CTRL_STOP', { 
        duration,
        position: 'top'
      });
      
      setControlTimers(prev => ({
        ...prev,
        [fighter]: {
          ...prev[fighter],
          isRunning: false
        }
      }));
      
      toast.info(`Control stopped for ${fighter === 'fighter1' ? bout.fighter1 : bout.fighter2}`);
    } else {
      // Start control timer
      await logEvent('CTRL_START', { 
        time: controlTimers[fighter].time 
      });
      
      setControlTimers(prev => ({
        ...prev,
        [fighter]: {
          time: 0,
          isRunning: true,
          startTime: Date.now()
        }
      }));
      
      toast.info(`Control started for ${fighter === 'fighter1' ? bout.fighter1 : bout.fighter2}`);
    }
  };

  const handleSubAttempt = async () => {
    const duration = controlTimers[selectedFighter].isRunning ? controlTimers[selectedFighter].time : 0;
    await logEvent('Submission Attempt', { depth: subDepth, duration });
    setShowSubDialog(false);
    setSubDepth('light');
  };

  const nextRound = async () => {
    if (bout.currentRound < bout.totalRounds) {
      // Stop any running timers
      setControlTimers({
        fighter1: { time: 0, isRunning: false, startTime: null },
        fighter2: { time: 0, isRunning: false, startTime: null }
      });
      
      await db.collection('bouts').doc(boutId).update({
        currentRound: bout.currentRound + 1
      });
      
      loadBout();
      toast.success(`Moving to Round ${bout.currentRound + 1}`);
    } else {
      toast.info('All rounds completed');
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!bout) return <div className="min-h-screen flex items-center justify-center bg-[#0a0a0b]"><p className="text-gray-400">Loading...</p></div>;

  const eventButtons = [
    { label: 'KD', event: 'KD', color: 'from-red-600 to-red-700' },
    { label: 'ISS Head', event: 'ISS Head', color: 'from-orange-600 to-orange-700' },
    { label: 'ISS Body', event: 'ISS Body', color: 'from-amber-600 to-amber-700' },
    { label: 'ISS Leg', event: 'ISS Leg', color: 'from-yellow-600 to-yellow-700' },
    { label: 'Takedown', event: 'Takedown', color: 'from-blue-600 to-blue-700' },
    { label: 'Pass', event: 'Pass', color: 'from-purple-600 to-purple-700' },
    { label: 'Reversal', event: 'Reversal', color: 'from-pink-600 to-pink-700' }
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <Card className="bg-[#13151a] border-[#2a2d35] p-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-amber-500">Operator Panel</h1>
              <p className="text-gray-400 mt-1">{bout.fighter1} vs {bout.fighter2}</p>
            </div>
            <Button
              data-testid="view-judge-panel-btn"
              onClick={() => window.open(`/judge/${boutId}`, '_blank')}
              className="bg-[#1a1d24] hover:bg-[#22252d] text-amber-500 border border-amber-500/30"
            >
              <Eye className="mr-2 h-4 w-4" />
              Judge Panel
            </Button>
          </div>
        </Card>
      </div>

      {/* Round Timer */}
      <div className="max-w-7xl mx-auto mb-6">
        <Card className="bg-gradient-to-r from-[#1a1d24] to-[#13151a] border-[#2a2d35] p-8">
          <div className="text-center space-y-4">
            <div className="text-sm text-gray-400 font-medium">ROUND {bout.currentRound} of {bout.totalRounds}</div>
            <div className="text-7xl font-bold text-white tracking-wider" style={{ fontFamily: 'Space Grotesk' }}>
              {formatTime(roundTime)}
            </div>
            <div className="flex items-center justify-center gap-4">
              <Button
                data-testid="timer-toggle-btn"
                onClick={() => setIsRunning(!isRunning)}
                className="h-14 px-8 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white font-semibold"
              >
                {isRunning ? <><Pause className="mr-2 h-5 w-5" />Pause</> : <><Play className="mr-2 h-5 w-5" />Start</>}
              </Button>
              {bout.currentRound < bout.totalRounds && (
                <Button
                  data-testid="next-round-btn"
                  onClick={nextRound}
                  className="h-14 px-8 bg-[#1a1d24] hover:bg-[#22252d] text-amber-500 border border-amber-500/30"
                >
                  Next Round <ChevronRight className="ml-2 h-5 w-5" />
                </Button>
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* Fighter Selection */}
      <div className="max-w-7xl mx-auto mb-6">
        <Card className="bg-[#13151a] border-[#2a2d35] p-6">
          <Label className="text-gray-300 mb-3 block">Select Fighter</Label>
          <div className="grid grid-cols-2 gap-4">
            <Button
              data-testid="select-fighter1-btn"
              onClick={() => setSelectedFighter('fighter1')}
              className={`h-16 text-lg font-semibold transition-all ${
                selectedFighter === 'fighter1'
                  ? 'bg-gradient-to-r from-red-600 to-red-700 text-white shadow-lg scale-105'
                  : 'bg-[#1a1d24] text-gray-400 hover:bg-[#22252d]'
              }`}
            >
              {bout.fighter1} (Red)
            </Button>
            <Button
              data-testid="select-fighter2-btn"
              onClick={() => setSelectedFighter('fighter2')}
              className={`h-16 text-lg font-semibold transition-all ${
                selectedFighter === 'fighter2'
                  ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg scale-105'
                  : 'bg-[#1a1d24] text-gray-400 hover:bg-[#22252d]'
              }`}
            >
              {bout.fighter2} (Blue)
            </Button>
          </div>
        </Card>
      </div>

      {/* Event Buttons */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {eventButtons.map((btn) => (
            <Button
              key={btn.event}
              data-testid={`event-${btn.event.toLowerCase().replace(/ /g, '-')}-btn`}
              onClick={() => logEvent(btn.event)}
              className={`h-24 text-xl font-bold bg-gradient-to-br ${btn.color} hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
            >
              {btn.label}
            </Button>
          ))}
          
          <Dialog open={showSubDialog} onOpenChange={setShowSubDialog}>
            <DialogTrigger asChild>
              <Button
                data-testid="event-submission-btn"
                className="h-24 text-xl font-bold bg-gradient-to-br from-indigo-600 to-indigo-700 hover:opacity-90 text-white shadow-lg transition-all active:scale-95"
              >
                Sub Attempt
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#13151a] border-[#2a2d35]">
              <DialogHeader>
                <DialogTitle className="text-white">Submission Attempt</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label className="text-gray-300">Depth</Label>
                  <Select value={subDepth} onValueChange={setSubDepth}>
                    <SelectTrigger className="bg-[#1a1d24] border-[#2a2d35] text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1a1d24] border-[#2a2d35]">
                      <SelectItem value="light">Light</SelectItem>
                      <SelectItem value="tight">Tight</SelectItem>
                      <SelectItem value="fight-ending">Fight-Ending</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  data-testid="submit-sub-attempt-btn"
                  onClick={handleSubAttempt}
                  className="w-full bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white"
                >
                  Log Submission
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Control Timer */}
      <div className="max-w-7xl mx-auto">
        <Card className="bg-[#13151a] border-[#2a2d35] p-6">
          <Button
            data-testid="control-timer-btn"
            onClick={toggleControl}
            className={`w-full h-20 text-xl font-bold transition-all ${
              controlTimer
                ? 'bg-gradient-to-r from-cyan-600 to-cyan-700 hover:from-cyan-700 hover:to-cyan-800 text-white shadow-lg'
                : 'bg-[#1a1d24] hover:bg-[#22252d] text-gray-300 border border-[#2a2d35]'
            }`}
          >
            {controlTimer ? `Control Active (${formatTime(roundTime - controlTimer)})` : 'Start Control Timer'}
          </Button>
        </Card>
      </div>
    </div>
  );
}