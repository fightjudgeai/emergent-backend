import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import firebase from 'firebase/compat/app';
import { db } from '@/firebase';
import syncManager from '@/utils/syncManager';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { Play, Pause, ChevronRight, Eye, Monitor, Zap, Wifi, WifiOff } from 'lucide-react';

export default function OperatorPanel() {
  const { boutId } = useParams();
  const navigate = useNavigate();
  const [bout, setBout] = useState(null);
  const [selectedFighter, setSelectedFighter] = useState('fighter1');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [queueCount, setQueueCount] = useState(0);
  const [controlTimers, setControlTimers] = useState({
    fighter1: { time: 0, isRunning: false, startTime: null, controlType: null },
    fighter2: { time: 0, isRunning: false, startTime: null, controlType: null }
  });
  const [showSubDialog, setShowSubDialog] = useState(false);
  const [subDepth, setSubDepth] = useState('light');
  const [showKdDialog, setShowKdDialog] = useState(false);
  const [kdTier, setKdTier] = useState('Flash');
  const [showQuickStatsDialog, setShowQuickStatsDialog] = useState(false);
  const [showStrikeDialog, setShowStrikeDialog] = useState(false);
  const [pendingStrikeEvent, setPendingStrikeEvent] = useState(null);
  const [isSignificantStrike, setIsSignificantStrike] = useState(true);
  const [quickStrikeMode, setQuickStrikeMode] = useState('significant'); // 'significant' or 'non-significant'
  const [quickStats, setQuickStats] = useState({
    kd: 0,
    ts: 0,
    issHead: 0,
    issBody: 0,
    issLeg: 0,
    takedown: 0,
    pass: 0,
    reversal: 0,
    cageControl: 0
  });
  const timerRef = useRef(null);

  useEffect(() => {
    loadBout();
    
    // Setup sync manager listener for connection status
    const unsubscribe = syncManager.addListener(async (status) => {
      if (status.type === 'online') {
        setIsOnline(true);
        toast.success('Connection restored - syncing events...');
      } else if (status.type === 'offline') {
        setIsOnline(false);
        toast.warning('Connection lost - events will be saved locally');
      } else if (status.type === 'syncComplete') {
        toast.success(`Synced ${status.synced} events successfully`);
      } else if (status.type === 'queued') {
        setQueueCount(status.count);
      }
    });
    
    // Get initial status
    syncManager.getStatus().then(status => {
      setIsOnline(status.isOnline);
      setQueueCount(status.queueCount);
    });
    
    return () => unsubscribe();
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
      
      // Use syncManager for offline-first event logging
      const result = await syncManager.addEvent(boutId, bout.currentRound, {
        fighter: selectedFighter,
        event_type: eventType,
        timestamp: currentTime,
        metadata
      });
      
      const fighterName = selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
      const modeIndicator = result.mode === 'offline' ? ' (saved locally)' : '';
      toast.success(`${eventType} logged for ${fighterName}${modeIndicator}`);
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

  const handleStrikeEvent = async () => {
    if (pendingStrikeEvent) {
      await logEvent(pendingStrikeEvent, { significant: isSignificantStrike });
      setShowStrikeDialog(false);
      setPendingStrikeEvent(null);
      setIsSignificantStrike(true); // Reset to default
    }
  };

  const handleControlToggle = async (controlType) => {
    const fighter = selectedFighter;
    const isCurrentlyRunning = controlTimers[fighter].isRunning;
    const currentControlType = controlTimers[fighter].controlType;
    const currentTime = controlTimers[fighter].time;
    
    // If a different control type is running, log the old one and switch
    if (isCurrentlyRunning && currentControlType !== controlType && currentControlType !== null) {
      await logEvent(currentControlType, { duration: currentTime, source: 'control-timer' });
      toast.info(`Switched from ${currentControlType} to ${controlType}`);
      
      // Switch to new control type, keeping timer running
      setControlTimers(prev => ({
        ...prev,
        [fighter]: {
          ...prev[fighter],
          controlType: controlType
        }
      }));
      return;
    }
    
    if (isCurrentlyRunning && currentControlType === controlType) {
      // Stop the current control - timer stays accumulated
      await logEvent(controlType, { 
        duration: currentTime,
        source: 'control-timer'
      });
      
      setControlTimers(prev => ({
        ...prev,
        [fighter]: {
          time: currentTime, // Keep accumulated time
          isRunning: false,
          startTime: null,
          controlType: null
        }
      }));
      
      toast.success(`${controlType} stopped - ${currentTime}s logged. Timer: ${formatTime(currentTime)}`);
    } else {
      // Start the control - continue from current accumulated time
      setControlTimers(prev => ({
        ...prev,
        [fighter]: {
          time: currentTime,  // Continue from current time
          isRunning: true,
          startTime: Date.now() - (currentTime * 1000),  // Adjust for accumulated time
          controlType: controlType
        }
      }));
      
      toast.info(`${controlType} timer started from ${formatTime(currentTime)}`);
    }
  };

  const handleQuickStats = async () => {
    const fighterName = selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
    
    // Log each stat type based on the count entered
    const statMap = {
      kd: 'KD',
      ts: 'TS',
      issHead: 'ISS Head',
      issBody: 'ISS Body',
      issLeg: 'ISS Leg',
      takedown: 'Takedown',
      pass: 'Pass',
      reversal: 'Reversal'
    };

    let totalEvents = 0;
    for (const [key, eventType] of Object.entries(statMap)) {
      const count = quickStats[key] || 0;
      for (let i = 0; i < count; i++) {
        await logEvent(eventType, { source: 'quick-input' });
        totalEvents++;
      }
    }

    // Log control time if specified (in seconds)
    if (quickStats.cageControl > 0) {
      await logEvent('CTRL_START', { source: 'quick-input', duration: quickStats.cageControl });
      await logEvent('CTRL_STOP', { source: 'quick-input', totalDuration: quickStats.cageControl });
    }

    toast.success(`Logged ${totalEvents} events + ${quickStats.cageControl || 0}s control time for ${fighterName}`);
    
    // Reset and close
    setQuickStats({
      kd: 0,
      ts: 0,
      issHead: 0,
      issBody: 0,
      issLeg: 0,
      takedown: 0,
      pass: 0,
      reversal: 0,
      cageControl: 0
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

  // Striking Events (regular and significant)
  const strikingButtons = [
    { label: 'Jab', event: 'Jab' },
    { label: 'SS Jab', event: 'Jab', isSignificant: true },
    { label: 'Cross', event: 'Cross' },
    { label: 'SS Cross', event: 'Cross', isSignificant: true },
    { label: 'Hook', event: 'Hook' },
    { label: 'SS Hook', event: 'Hook', isSignificant: true },
    { label: 'Uppercut', event: 'Uppercut' },
    { label: 'SS Uppercut', event: 'Uppercut', isSignificant: true },
    { label: 'Elbow', event: 'Elbow' },
    { label: 'SS Elbow', event: 'Elbow', isSignificant: true },
    { label: 'Knee', event: 'Knee' },
    { label: 'SS Knee', event: 'Knee', isSignificant: true }
  ];

  // Damage Events
  const damageButtons = [
    { label: 'Rocked', event: 'Rocked/Stunned' },
    { label: 'KD (Flash)', event: 'KD', tier: 'Flash' },
    { label: 'KD (Hard)', event: 'KD', tier: 'Hard' },
    { label: 'KD (NF)', event: 'KD', tier: 'Near-Finish' }
  ];

  // Grappling Events
  const grapplingButtons = [
    { label: 'TD Landed', event: 'Takedown Landed' },
    { label: 'TD Stuffed', event: 'Takedown Stuffed' },
    { label: 'SUB (Light)', event: 'Submission Attempt', tier: 'Light' },
    { label: 'SUB (Deep)', event: 'Submission Attempt', tier: 'Deep' },
    { label: 'SUB (NF)', event: 'Submission Attempt', tier: 'Near-Finish' },
    { label: 'Sweep/Reversal', event: 'Sweep/Reversal' }
  ];

  // Control Events (with start/stop timers)
  const controlButtons = [
    { label: 'Top Control', event: 'Ground Top Control', isTimer: true },
    { label: 'Back Control', event: 'Ground Back Control', isTimer: true },
    { label: 'Cage Control', event: 'Cage Control Time', isTimer: true }
  ];

  const allEventButtons = [...strikingButtons, ...damageButtons, ...grapplingButtons, ...controlButtons];

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <Card className="bg-[#13151a] border-[#2a2d35] p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-3xl font-bold text-amber-500">Operator Panel</h1>
                {/* Connection Status Indicator */}
                <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-semibold ${
                  isOnline 
                    ? 'bg-green-900/30 text-green-400 border border-green-500/30' 
                    : 'bg-red-900/30 text-red-400 border border-red-500/30'
                }`}>
                  {isOnline ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
                  {isOnline ? 'Online' : 'Offline'}
                  {queueCount > 0 && (
                    <span className="ml-2 bg-amber-500 text-white px-2 py-0.5 rounded-full text-xs">
                      {queueCount} queued
                    </span>
                  )}
                </div>
              </div>
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

          {/* Active Control Timer Display */}
          {(controlTimers.fighter1.isRunning || controlTimers.fighter2.isRunning) && (
            <div className="mt-4 p-4 bg-gradient-to-r from-green-900/30 to-emerald-900/30 border-2 border-green-500/50 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-4 w-4">
                    <span className="animate-ping absolute inline-flex h-4 w-4 rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-4 w-4 bg-green-500"></span>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-green-400">
                      {controlTimers.fighter1.isRunning ? controlTimers.fighter1.controlType : controlTimers.fighter2.controlType} Active
                    </div>
                    <div className="text-xs text-gray-400">
                      {controlTimers.fighter1.isRunning ? bout.fighter1 : bout.fighter2}
                    </div>
                  </div>
                </div>
                <div className="text-3xl font-bold text-green-300 font-mono">
                  {formatTime(controlTimers.fighter1.isRunning ? controlTimers.fighter1.time : controlTimers.fighter2.time)}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Event Buttons - Organized by Category */}
      <div className="max-w-7xl mx-auto mb-6 space-y-6">
        {/* Striking Events */}
        <div>
          <h3 className="text-amber-500 font-bold text-lg mb-3">⚡ Striking</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {strikingButtons.map((btn, index) => (
              <Button
                key={`${btn.event}-${btn.isSignificant ? 'sig' : 'non'}`}
                onClick={() => {
                  logEvent(btn.event, { significant: btn.isSignificant || false });
                  toast.success(`${btn.label} logged`);
                }}
                className={`h-16 text-sm font-bold bg-gradient-to-br ${
                  btn.isSignificant 
                    ? 'from-orange-600 to-red-600' 
                    : 'from-gray-600 to-gray-700'
                } hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
              >
                {btn.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Damage Events */}
        <div>
          <h3 className="text-red-500 font-bold text-lg mb-3">💥 Damage</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {damageButtons.map((btn, index) => (
              <Button
                key={`${btn.event}-${btn.tier || 'base'}`}
                onClick={() => {
                  if (btn.tier) {
                    logEvent(btn.event, { tier: btn.tier });
                  } else {
                    logEvent(btn.event, { significant: true });
                  }
                  toast.success(`${btn.label} logged`);
                }}
                className={`h-20 text-lg font-bold bg-gradient-to-br ${getButtonColor(index + 12)} hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
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
            {grapplingButtons.map((btn, index) => {
              const isControlType = btn.event === 'Ground Back Control' || btn.event === 'Ground Top Control';
              const isActive = controlTimers[selectedFighter].isRunning && 
                              controlTimers[selectedFighter].controlType === btn.event;
              
              return (
                <Button
                  key={btn.event}
                  data-testid={`event-${btn.event.toLowerCase().replace(/[/ ]/g, '-')}-btn`}
                  onClick={() => {
                    if (btn.event === 'Submission Attempt') {
                      setShowSubDialog(true);
                    } else if (isControlType) {
                      handleControlToggle(btn.event);
                    } else {
                      logEvent(btn.event);
                    }
                  }}
                  className={`h-20 text-lg font-bold bg-gradient-to-br ${
                    isActive 
                      ? 'from-green-600 to-green-700 ring-4 ring-green-400 animate-pulse' 
                      : getButtonColor(index + 12)
                  } hover:opacity-90 text-white shadow-lg transition-all active:scale-95 relative`}
                >
                  {btn.label}
                  {isActive && (
                    <span className="absolute top-1 right-1 flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                  )}
                </Button>
              );
            })}
          </div>
        </div>

        {/* Control/Aggression Events */}
        <div>
          <h3 className="text-purple-500 font-bold text-lg mb-3">🎯 Control & Aggression</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {controlButtons.map((btn, index) => {
              const isCageControl = btn.event === 'Cage Control Time';
              const isActive = controlTimers[selectedFighter].isRunning && 
                              controlTimers[selectedFighter].controlType === btn.event;
              
              return (
                <Button
                  key={btn.event}
                  data-testid={`event-${btn.event.toLowerCase().replace(/[/ ]/g, '-')}-btn`}
                  onClick={() => {
                    if (isCageControl) {
                      handleControlToggle(btn.event);
                    } else {
                      logEvent(btn.event);
                    }
                  }}
                  className={`h-20 text-lg font-bold bg-gradient-to-br ${
                    isActive 
                      ? 'from-green-600 to-green-700 ring-4 ring-green-400 animate-pulse' 
                      : getButtonColor(index + 17)
                  } hover:opacity-90 text-white shadow-lg transition-all active:scale-95 relative`}
                >
                  {btn.label}
                  {isActive && (
                    <span className="absolute top-1 right-1 flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                  )}
                </Button>
              );
            })}
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

      {/* Strike Significant Dialog */}
      <Dialog open={showStrikeDialog} onOpenChange={setShowStrikeDialog}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35]">
          <DialogHeader>
            <DialogTitle className="text-white">{pendingStrikeEvent}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex items-center space-x-3 p-4 bg-[#1a1d24] rounded-lg border border-[#2a2d35]">
              <Checkbox 
                id="significant"
                checked={isSignificantStrike}
                onCheckedChange={setIsSignificantStrike}
                className="border-amber-500 data-[state=checked]:bg-amber-500"
              />
              <div className="flex-1">
                <Label 
                  htmlFor="significant" 
                  className="text-gray-300 font-semibold cursor-pointer"
                >
                  Significant Strike
                </Label>
                <p className="text-xs text-gray-500 mt-1">
                  Check if this strike was significant (landed cleanly with impact)
                </p>
              </div>
            </div>
            <Button
              data-testid="submit-strike-btn"
              onClick={handleStrikeEvent}
              className={`w-full bg-gradient-to-r ${
                selectedFighter === 'fighter1'
                  ? 'from-red-600 to-red-700 hover:from-red-700 hover:to-red-800'
                  : 'from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800'
              } text-white font-bold`}
            >
              Log Strike
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
              Quick Stats Input
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4 max-h-[70vh] overflow-y-auto">
            {/* Fighter Selection */}
            <div className="space-y-2 pb-4 border-b border-[#2a2d35]">
              <Label className="text-gray-300 font-semibold">Select Fighter</Label>
              <Select value={selectedFighter} onValueChange={setSelectedFighter}>
                <SelectTrigger className="h-12 bg-[#1a1d24] border-[#2a2d35] text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1a1d24] border-[#2a2d35]">
                  <SelectItem value="fighter1" className="text-white hover:bg-red-900/20">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500"></div>
                      {bout?.fighter1} (Red Corner)
                    </div>
                  </SelectItem>
                  <SelectItem value="fighter2" className="text-white hover:bg-blue-900/20">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                      {bout?.fighter2} (Blue Corner)
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            
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