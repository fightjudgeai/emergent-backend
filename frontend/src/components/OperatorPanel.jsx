import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import firebase from 'firebase/compat/app';
import { db } from '@/firebase';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Play, Pause, ChevronRight, Eye, Monitor, Zap } from 'lucide-react';

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
  const [showKdDialog, setShowKdDialog] = useState(false);
  const [kdTier, setKdTier] = useState('Flash');
  const [showQuickStatsDialog, setShowQuickStatsDialog] = useState(false);
  const [quickStats, setQuickStats] = useState({
    // Striking
    kd: 0,
    rocked: 0,
    headKick: 0,
    elbow: 0,
    knee: 0,
    hook: 0,
    cross: 0,
    uppercut: 0,
    bodyKick: 0,
    lowKick: 0,
    jab: 0,
    frontKick: 0,
    // Grappling
    subAttempt: 0,
    backControl: 0,
    takedown: 0,
    topControl: 0,
    sweep: 0,
    // Control
    cageControl: 0,
    tdStuffed: 0
  });
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
      // Stop control timer - keep accumulated time
      const currentTime = controlTimers[fighter].time;
      
      await logEvent('CTRL_STOP', { 
        duration: currentTime,
        position: 'top'
      });
      
      setControlTimers(prev => ({
        ...prev,
        [fighter]: {
          ...prev[fighter],
          isRunning: false,
          startTime: null
        }
      }));
      
      toast.info(`Control stopped for ${fighter === 'fighter1' ? bout.fighter1 : bout.fighter2} at ${formatTime(currentTime)}`);
    } else {
      // Start control timer - continue from current accumulated time
      const currentTime = controlTimers[fighter].time;
      
      await logEvent('CTRL_START', { 
        time: currentTime 
      });
      
      setControlTimers(prev => ({
        ...prev,
        [fighter]: {
          time: currentTime,  // Keep current time, don't reset
          isRunning: true,
          startTime: Date.now() - (currentTime * 1000)  // Adjust startTime to account for accumulated time
        }
      }));
      
      toast.info(`Control started for ${fighter === 'fighter1' ? bout.fighter1 : bout.fighter2} from ${formatTime(currentTime)}`);
    }
  };

  const handleSubAttempt = async () => {
    const duration = controlTimers[selectedFighter].isRunning ? controlTimers[selectedFighter].time : 0;
    await logEvent('Submission Attempt', { depth: subDepth, duration });
    setShowSubDialog(false);
    setSubDepth('light');
  };

  const handleKnockdown = async () => {
    await logEvent('KD', { tier: kdTier });
    setShowKdDialog(false);
    setKdTier('Flash');
  };

  const handleQuickStats = async () => {
    // Log each stat type based on the count entered
    const statMap = {
      // Striking
      kd: 'KD',
      rocked: 'Rocked/Stunned',
      headKick: 'Head Kick',
      elbow: 'Elbow',
      knee: 'Knee',
      hook: 'Hook',
      cross: 'Cross',
      uppercut: 'Uppercut',
      bodyKick: 'Body Kick',
      lowKick: 'Low Kick',
      jab: 'Jab',
      frontKick: 'Front Kick/Teep',
      // Grappling
      subAttempt: 'Submission Attempt',
      backControl: 'Ground Back Control',
      takedown: 'Takedown Landed',
      topControl: 'Ground Top Control',
      sweep: 'Sweep/Reversal',
      // Control
      cageControl: 'Cage Control Time',
      tdStuffed: 'Takedown Stuffed'
    };

    for (const [key, eventType] of Object.entries(statMap)) {
      const count = quickStats[key];
      for (let i = 0; i < count; i++) {
        await logEvent(eventType, { source: 'quick-input' });
      }
    }

    // Log control time if specified (in seconds)
    if (quickStats.controlTime > 0) {
      await logEvent('CTRL_START', { source: 'quick-input', duration: quickStats.controlTime });
      await logEvent('CTRL_STOP', { source: 'quick-input', totalDuration: quickStats.controlTime });
    }

    const totalEvents = Object.entries(quickStats).reduce((sum, [key, val]) => {
      return key === 'controlTime' ? sum : sum + val;
    }, 0);
    toast.success(`Logged ${totalEvents} events + ${quickStats.controlTime}s control time via Quick Stats`);
    
    // Reset and close
    setQuickStats({
      kd: 0, rocked: 0, headKick: 0, elbow: 0, knee: 0, hook: 0,
      cross: 0, uppercut: 0, bodyKick: 0, lowKick: 0, jab: 0, frontKick: 0,
      subAttempt: 0, backControl: 0, takedown: 0, topControl: 0, sweep: 0,
      cageControl: 0, tdStuffed: 0
    });
    setShowQuickStatsDialog(false);
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

  // Dynamic button colors based on selected fighter
  const getButtonColor = (index) => {
    if (selectedFighter === 'fighter1') {
      // Red theme for fighter1
      const redColors = [
        'from-red-600 to-red-700',
        'from-red-500 to-red-600',
        'from-red-700 to-red-800',
        'from-rose-600 to-rose-700',
        'from-red-600 to-rose-700',
        'from-rose-700 to-rose-800',
        'from-red-500 to-rose-600'
      ];
      return redColors[index % redColors.length];
    } else {
      // Blue theme for fighter2
      const blueColors = [
        'from-blue-600 to-blue-700',
        'from-blue-500 to-blue-600',
        'from-blue-700 to-blue-800',
        'from-cyan-600 to-cyan-700',
        'from-blue-600 to-cyan-700',
        'from-cyan-700 to-cyan-800',
        'from-blue-500 to-cyan-600'
      ];
      return blueColors[index % blueColors.length];
    }
  };

  // Striking Events
  const strikingButtons = [
    { label: 'KD', event: 'KD', hasDialog: true },
    { label: 'Rocked', event: 'Rocked/Stunned' },
    { label: 'Head Kick', event: 'Head Kick' },
    { label: 'Elbow', event: 'Elbow' },
    { label: 'Knee', event: 'Knee' },
    { label: 'Hook', event: 'Hook' },
    { label: 'Cross', event: 'Cross' },
    { label: 'Uppercut', event: 'Uppercut' },
    { label: 'Body Kick', event: 'Body Kick' },
    { label: 'Low Kick', event: 'Low Kick' },
    { label: 'Jab', event: 'Jab' },
    { label: 'Front Kick', event: 'Front Kick/Teep' }
  ];

  // Grappling Events
  const grapplingButtons = [
    { label: 'Sub Attempt', event: 'Submission Attempt', hasDialog: true },
    { label: 'Back Control', event: 'Ground Back Control' },
    { label: 'Takedown', event: 'Takedown Landed' },
    { label: 'Top Control', event: 'Ground Top Control' },
    { label: 'Sweep/Reversal', event: 'Sweep/Reversal' }
  ];

  // Control/Aggression Events
  const controlButtons = [
    { label: 'Cage Control', event: 'Cage Control Time' },
    { label: 'TD Stuffed', event: 'Takedown Stuffed' }
  ];

  const allEventButtons = [...strikingButtons, ...grapplingButtons, ...controlButtons];

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
            <div className="flex gap-3">
              <Button
                data-testid="quick-stats-btn"
                onClick={() => setShowQuickStatsDialog(true)}
                className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold"
                title="Quick Stats Input"
              >
                <Zap className="mr-2 h-4 w-4" />
                Quick Stats
              </Button>
              <Button
                data-testid="view-broadcast-btn"
                onClick={() => window.open(`/broadcast/${boutId}`, '_blank')}
                className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold border-2 border-purple-500"
                title="Open Broadcast Mode for Arena Display"
              >
                <Monitor className="mr-2 h-4 w-4" />
                Broadcast Mode
              </Button>
              <Button
                data-testid="view-judge-panel-btn"
                onClick={() => window.open(`/judge/${boutId}`, '_blank')}
                className="bg-[#1a1d24] hover:bg-[#22252d] text-amber-500 border border-amber-500/30"
              >
                <Eye className="mr-2 h-4 w-4" />
                Judge Panel
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Control Timers */}
      <div className="max-w-7xl mx-auto mb-6">
        <Card className="bg-gradient-to-r from-[#1a1d24] to-[#13151a] border-[#2a2d35] p-8">
          <div className="text-center space-y-6">
            <div className="text-sm text-gray-400 font-medium">ROUND {bout.currentRound} of {bout.totalRounds}</div>
            
            <div className="grid md:grid-cols-2 gap-6">
              {/* Fighter 1 Control Timer */}
              <div className={`p-6 rounded-xl border-2 transition-all ${
                selectedFighter === 'fighter1' 
                  ? 'bg-red-950/30 border-red-600' 
                  : 'bg-[#1a1d24] border-[#2a2d35]'
              }`}>
                <div className="text-sm text-red-400 font-medium mb-2">{bout.fighter1} (Red)</div>
                <div className="text-5xl font-bold text-white tracking-wider" style={{ fontFamily: 'Space Grotesk' }}>
                  {formatTime(controlTimers.fighter1.time)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {controlTimers.fighter1.isRunning ? 'CONTROL ACTIVE' : 'Stopped'}
                </div>
              </div>
              
              {/* Fighter 2 Control Timer */}
              <div className={`p-6 rounded-xl border-2 transition-all ${
                selectedFighter === 'fighter2' 
                  ? 'bg-blue-950/30 border-blue-600' 
                  : 'bg-[#1a1d24] border-[#2a2d35]'
              }`}>
                <div className="text-sm text-blue-400 font-medium mb-2">{bout.fighter2} (Blue)</div>
                <div className="text-5xl font-bold text-white tracking-wider" style={{ fontFamily: 'Space Grotesk' }}>
                  {formatTime(controlTimers.fighter2.time)}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {controlTimers.fighter2.isRunning ? 'CONTROL ACTIVE' : 'Stopped'}
                </div>
              </div>
            </div>
            
            <div className="flex items-center justify-center gap-4 pt-4">
              <Button
                data-testid="control-timer-btn"
                onClick={toggleControl}
                className={`h-14 px-8 font-semibold text-lg transition-all ${
                  controlTimers[selectedFighter].isRunning
                    ? 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white shadow-lg'
                    : 'bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white'
                }`}
              >
                {controlTimers[selectedFighter].isRunning ? (
                  <><Pause className="mr-2 h-5 w-5" />Stop Control</>
                ) : (
                  <><Play className="mr-2 h-5 w-5" />Start Control</>
                )}
              </Button>
              
              {bout.currentRound < bout.totalRounds && (
                <Button
                  data-testid="next-round-btn"
                  onClick={nextRound}
                  className="h-14 px-8 bg-[#1a1d24] hover:bg-[#22252d] text-amber-500 border border-amber-500/30 font-semibold"
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

      {/* Event Buttons - Organized by Category */}
      <div className="max-w-7xl mx-auto mb-6 space-y-6">
        {/* Striking Events */}
        <div>
          <h3 className="text-amber-500 font-bold text-lg mb-3">⚡ Striking</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {strikingButtons.map((btn, index) => (
              <Button
                key={btn.event}
                data-testid={`event-${btn.event.toLowerCase().replace(/[/ ]/g, '-')}-btn`}
                onClick={() => {
                  if (btn.event === 'KD') {
                    setShowKdDialog(true);
                  } else {
                    logEvent(btn.event);
                  }
                }}
                className={`h-20 text-lg font-bold bg-gradient-to-br ${getButtonColor(index)} hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
              >
                {btn.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Grappling Events */}
        <div>
          <h3 className="text-blue-500 font-bold text-lg mb-3">🤼 Grappling</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {grapplingButtons.map((btn, index) => (
              <Button
                key={btn.event}
                data-testid={`event-${btn.event.toLowerCase().replace(/[/ ]/g, '-')}-btn`}
                onClick={() => {
                  if (btn.event === 'Submission Attempt') {
                    setShowSubDialog(true);
                  } else {
                    logEvent(btn.event);
                  }
                }}
                className={`h-20 text-lg font-bold bg-gradient-to-br ${getButtonColor(index + 12)} hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
              >
                {btn.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Control/Aggression Events */}
        <div>
          <h3 className="text-purple-500 font-bold text-lg mb-3">🎯 Control & Aggression</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {controlButtons.map((btn, index) => (
              <Button
                key={btn.event}
                data-testid={`event-${btn.event.toLowerCase().replace(/[/ ]/g, '-')}-btn`}
                onClick={() => logEvent(btn.event)}
                className={`h-20 text-lg font-bold bg-gradient-to-br ${getButtonColor(index + 17)} hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
              >
                {btn.label}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Old Sub Attempt Dialog Button - Now integrated above */}
      <div className="hidden">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {allEventButtons.map((btn, index) => (
            <Button
              key={btn.event}
              data-testid={`event-${btn.event.toLowerCase().replace(/ /g, '-')}-btn`}
              onClick={() => {
                if (btn.event === 'KD') {
                  setShowKdDialog(true);
                } else if (btn.event === 'Submission Attempt') {
                  setShowSubDialog(true);
                } else {
                  logEvent(btn.event);
                }
              }}
              className={`h-24 text-xl font-bold bg-gradient-to-br ${getButtonColor(index)} hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
            >
              {btn.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Submission Attempt Dialog */}
      <Dialog open={showSubDialog} onOpenChange={setShowSubDialog}>
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
                  <SelectItem value="deep">Deep</SelectItem>
                  <SelectItem value="near_finish">Near-Finish</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button
              data-testid="submit-sub-attempt-btn"
              onClick={handleSubAttempt}
              className={`w-full bg-gradient-to-r ${
                selectedFighter === 'fighter1'
                  ? 'from-red-600 to-red-700 hover:from-red-700 hover:to-red-800'
                  : 'from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800'
              } text-white`}
            >
              Log Submission
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* KD Dialog */}
      <Dialog open={showKdDialog} onOpenChange={setShowKdDialog}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35]">
          <DialogHeader>
            <DialogTitle className="text-white">Knockdown</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label className="text-gray-300">KD Tier</Label>
              <Select value={kdTier} onValueChange={setKdTier}>
                <SelectTrigger className="bg-[#1a1d24] border-[#2a2d35] text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1a1d24] border-[#2a2d35]">
                  <SelectItem value="Flash">Flash KD</SelectItem>
                  <SelectItem value="Hard">Hard KD</SelectItem>
                  <SelectItem value="Near-Finish">Near-Finish KD</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button
              data-testid="submit-kd-btn"
              onClick={handleKnockdown}
              className={`w-full bg-gradient-to-r ${
                selectedFighter === 'fighter1'
                  ? 'from-red-600 to-red-700 hover:from-red-700 hover:to-red-800'
                  : 'from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800'
              } text-white font-bold`}
            >
              Log Knockdown
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Quick Stats Input Dialog */}
      <Dialog open={showQuickStatsDialog} onOpenChange={setShowQuickStatsDialog}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35] max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Zap className="h-5 w-5 text-green-500" />
              Quick Stats Input for {selectedFighter === 'fighter1' ? bout?.fighter1 : bout?.fighter2}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4 max-h-[70vh] overflow-y-auto">
            <p className="text-sm text-gray-400 mb-4">Enter the total count for each event type to log them all at once:</p>
            
            {/* Striking Events */}
            <div className="space-y-3">
              <h4 className="text-amber-500 font-semibold text-sm uppercase tracking-wide">⚡ Striking</h4>
              <div className="grid grid-cols-3 gap-3">
              <div className="space-y-2">
                <Label className="text-gray-300">Knockdowns</Label>
                <Input
                  type="number"
                  min="0"
                  value={quickStats.kd}
                  onChange={(e) => setQuickStats({...quickStats, kd: parseInt(e.target.value) || 0})}
                  className="bg-[#1a1d24] border-[#2a2d35] text-white"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-gray-300">Total Strikes (TS)</Label>
                <Input
                  type="number"
                  min="0"
                  value={quickStats.ts}
                  onChange={(e) => setQuickStats({...quickStats, ts: parseInt(e.target.value) || 0})}
                  className="bg-[#1a1d24] border-[#2a2d35] text-white"
                />
              </div>
              
              <div className="space-y-2">
                <Label className="text-gray-300">ISS Head</Label>
                <Input
                  type="number"
                  min="0"
                  value={quickStats.issHead}
                  onChange={(e) => setQuickStats({...quickStats, issHead: parseInt(e.target.value) || 0})}
                  className="bg-[#1a1d24] border-[#2a2d35] text-white"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-gray-300">ISS Body</Label>
                <Input
                  type="number"
                  min="0"
                  value={quickStats.issBody}
                  onChange={(e) => setQuickStats({...quickStats, issBody: parseInt(e.target.value) || 0})}
                  className="bg-[#1a1d24] border-[#2a2d35] text-white"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-gray-300">ISS Leg</Label>
                <Input
                  type="number"
                  min="0"
                  value={quickStats.issLeg}
                  onChange={(e) => setQuickStats({...quickStats, issLeg: parseInt(e.target.value) || 0})}
                  className="bg-[#1a1d24] border-[#2a2d35] text-white"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-gray-300">Takedowns</Label>
                <Input
                  type="number"
                  min="0"
                  value={quickStats.takedown}
                  onChange={(e) => setQuickStats({...quickStats, takedown: parseInt(e.target.value) || 0})}
                  className="bg-[#1a1d24] border-[#2a2d35] text-white"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-gray-300">Passes</Label>
                <Input
                  type="number"
                  min="0"
                  value={quickStats.pass}
                  onChange={(e) => setQuickStats({...quickStats, pass: parseInt(e.target.value) || 0})}
                  className="bg-[#1a1d24] border-[#2a2d35] text-white"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-gray-300">Reversals</Label>
                <Input
                  type="number"
                  min="0"
                  value={quickStats.reversal}
                  onChange={(e) => setQuickStats({...quickStats, reversal: parseInt(e.target.value) || 0})}
                  className="bg-[#1a1d24] border-[#2a2d35] text-white"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-gray-300">Control Time (seconds)</Label>
                <Input
                  type="number"
                  min="0"
                  value={quickStats.cageControl}
                  onChange={(e) => setQuickStats({...quickStats, cageControl: parseInt(e.target.value) || 0})}
                  className="bg-[#1a1d24] border-[#2a2d35] text-white"
                  placeholder="e.g., 120 for 2 min"
                />
              </div>
              </div>
            </div>

            <div className="pt-4 flex gap-3">
              <Button
                onClick={() => setShowQuickStatsDialog(false)}
                variant="outline"
                className="flex-1 bg-[#1a1d24] border-[#2a2d35] text-gray-300 hover:bg-[#22252d]"
              >
                Cancel
              </Button>
              <Button
                data-testid="submit-quick-stats-btn"
                onClick={handleQuickStats}
                className={`flex-1 bg-gradient-to-r ${
                  selectedFighter === 'fighter1'
                    ? 'from-red-600 to-red-700 hover:from-red-700 hover:to-red-800'
                    : 'from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800'
                } text-white font-bold`}
              >
                Log All Stats ({Object.values(quickStats).reduce((a, b) => a + b, 0)} events)
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

    </div>
  );
}