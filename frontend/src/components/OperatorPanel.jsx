import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import firebase from 'firebase/compat/app';
import { db } from '@/firebase';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { Play, Pause, ChevronRight, Eye, ChevronLeft, ArrowLeft, SkipForward, Wifi, WifiOff, Cloud, CloudOff, RefreshCw } from 'lucide-react';
import syncManager from '@/utils/syncManager';

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
  const [kdSeverity, setKdSeverity] = useState('flash');
  const timerRef = useRef(null);
  const [syncStatus, setSyncStatus] = useState({ isOnline: true, isSyncing: false, queueCount: 0 });

  useEffect(() => {
    loadBout();
    
    // Setup sync manager listener
    const unsubscribe = syncManager.addListener((status) => {
      console.log('Sync status update:', status);
      
      if (status.type === 'online') {
        toast.success('Back online - syncing data...');
        updateSyncStatus();
      } else if (status.type === 'offline') {
        toast.warning('Offline mode - events will be queued');
        updateSyncStatus();
      } else if (status.type === 'syncComplete') {
        if (status.synced > 0) {
          toast.success(`Synced ${status.synced} events`);
        }
        updateSyncStatus();
      } else if (status.type === 'queued') {
        updateSyncStatus();
      }
    });
    
    // Initial status load
    updateSyncStatus();
    
    return () => {
      unsubscribe();
    };
  }, [boutId]);

  const updateSyncStatus = async () => {
    try {
      const status = await syncManager.getStatus();
      setSyncStatus(status);
    } catch (error) {
      console.error('Error updating sync status:', error);
      // Set default status if error
      setSyncStatus({ isOnline: navigator.onLine, isSyncing: false, queueCount: 0 });
    }
  };

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

  const manualSync = async () => {
    const result = await syncManager.manualSync();
    if (result.success && result.synced > 0) {
      toast.success(`Synced ${result.synced} events`);
    } else if (result.success && result.synced === 0) {
      toast.info('No events to sync');
    } else {
      toast.error(result.message || 'Sync failed');
    }
    updateSyncStatus();
  };

  const logEvent = async (eventType, metadata = {}) => {
    try {
      if (!bout) {
        console.error('Bout not loaded, cannot log event');
        toast.error('Bout not loaded yet, please wait');
        return;
      }

      if (!bout.currentRound) {
        console.error('No current round set');
        toast.error('No active round');
        return;
      }
      
      const currentTime = controlTimers[selectedFighter].time;
      const eventData = {
        fighter: selectedFighter,
        event_type: eventType,
        timestamp: currentTime,
        metadata
      };

      console.log('Logging event:', eventType, 'for', selectedFighter, 'in round', bout.currentRound);
      
      // Use sync manager to handle online/offline
      await syncManager.addEvent(boutId, bout.currentRound, eventData);
      
      // Update queue count
      await updateSyncStatus();
      
      const fighterName = selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
      toast.success(`${eventType} logged for ${fighterName}`);
    } catch (error) {
      console.error('Error logging event:', error);
      toast.error(`Failed to log event: ${error.message}`);
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

  const handleKdAttempt = async () => {
    await logEvent('KD', { severity: kdSeverity });
    setShowKdDialog(false);
    setKdSeverity('flash');
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

  const previousRound = async () => {
    if (bout.currentRound > 1) {
      // Stop any running timers
      setControlTimers({
        fighter1: { time: 0, isRunning: false, startTime: null },
        fighter2: { time: 0, isRunning: false, startTime: null }
      });
      
      await db.collection('bouts').doc(boutId).update({
        currentRound: bout.currentRound - 1
      });
      
      loadBout();
      toast.success(`Back to Round ${bout.currentRound - 1}`);
    }
  };

  const goToRound = async (roundNum) => {
    if (roundNum >= 1 && roundNum <= bout.totalRounds && roundNum !== bout.currentRound) {
      // Stop any running timers
      setControlTimers({
        fighter1: { time: 0, isRunning: false, startTime: null },
        fighter2: { time: 0, isRunning: false, startTime: null }
      });
      
      await db.collection('bouts').doc(boutId).update({
        currentRound: roundNum
      });
      
      loadBout();
      toast.success(`Switched to Round ${roundNum}`);
    }
  };

  const goBackToFightList = async () => {
    if (bout?.eventId) {
      // Mark fight as completed if on last round
      if (bout.currentRound === bout.totalRounds) {
        await db.collection('bouts').doc(boutId).update({
          status: 'completed'
        });
      }
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
        
        navigate(`/operator/${nextFight.id}`);
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

  const eventButtons = [
    { label: 'SS Head', event: 'SS Head' },
    { label: 'SS Body', event: 'SS Body' },
    { label: 'SS Leg', event: 'SS Leg' },
    { label: 'Takedown', event: 'Takedown' },
    { label: 'Pass', event: 'Pass' },
    { label: 'Reversal', event: 'Reversal' }
  ];

  // Loading state
  if (!bout) {
    return (
      <div className="min-h-screen bg-[#0a0a0b] flex items-center justify-center">
        <div className="text-center">
          <div className="text-gray-400 text-xl mb-2">Loading fight data...</div>
          <div className="text-gray-500 text-sm">Please wait</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <Card className="bg-[#13151a] border-[#2a2d35] p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button
                data-testid="back-to-fights-btn"
                onClick={goBackToFightList}
                className="h-10 px-4 bg-[#1a1d24] hover:bg-[#22252d] text-gray-300 border border-[#2a2d35]"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Fights
              </Button>
              <div>
                <h1 className="text-3xl font-bold text-amber-500">Operator Panel</h1>
                <p className="text-gray-400 mt-1">{bout.fighter1} vs {bout.fighter2}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {/* Offline Status */}
              {!syncStatus.isOnline && (
                <div className="flex items-center gap-2">
                  <Badge className="bg-red-900/30 text-red-400 border-red-700/30 px-3 py-1">
                    <CloudOff className="w-3 h-3 mr-1" />
                    Offline {syncStatus.queueCount > 0 && `(${syncStatus.queueCount} queued)`}
                  </Badge>
                </div>
              )}
              {/* Online Status with Queue */}
              {syncStatus.isOnline && syncStatus.queueCount > 0 && (
                <div className="flex items-center gap-2">
                  <Badge className="bg-amber-900/30 text-amber-400 border-amber-700/30 px-3 py-1">
                    <Cloud className="w-3 h-3 mr-1" />
                    {syncStatus.isSyncing ? 'Syncing...' : `${syncStatus.queueCount} queued`}
                  </Badge>
                  {!syncStatus.isSyncing && (
                    <Button
                      onClick={manualSync}
                      size="sm"
                      className="h-8 px-3 bg-amber-600 hover:bg-amber-700 text-white"
                    >
                      <RefreshCw className="w-3 h-3 mr-1" />
                      Sync Now
                    </Button>
                  )}
                </div>
              )}
              {/* Online and Synced */}
              {syncStatus.isOnline && syncStatus.queueCount === 0 && (
                <Badge className="bg-green-900/30 text-green-400 border-green-700/30 px-3 py-1">
                  <Cloud className="w-3 h-3 mr-1" />
                  Online & Synced
                </Badge>
              )}
              <Button
                data-testid="next-fight-btn"
                onClick={goToNextFight}
                className="h-10 px-4 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white"
              >
                Next Fight
                <SkipForward className="ml-2 h-4 w-4" />
              </Button>
              <Button
                data-testid="view-judge-panel-btn"
                onClick={() => window.open(`/judge/${boutId}`, '_blank')}
                className="h-10 px-4 bg-[#1a1d24] hover:bg-[#22252d] text-amber-500 border border-amber-500/30"
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
            {/* Round Navigation */}
            <div className="flex items-center justify-center gap-4">
              <Button
                data-testid="prev-round-btn"
                onClick={previousRound}
                disabled={bout.currentRound === 1}
                className="h-10 px-4 bg-[#1a1d24] hover:bg-[#22252d] text-gray-300 border border-[#2a2d35] disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-5 w-5" />
              </Button>
              
              <div className="text-sm text-gray-400 font-medium min-w-[120px]">
                ROUND {bout.currentRound} of {bout.totalRounds}
              </div>
              
              <Button
                data-testid="next-round-btn"
                onClick={nextRound}
                disabled={bout.currentRound === bout.totalRounds}
                className="h-10 px-4 bg-[#1a1d24] hover:bg-[#22252d] text-gray-300 border border-[#2a2d35] disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronRight className="h-5 w-5" />
              </Button>
            </div>
            
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
          {/* KD Button with Dialog */}
          <Dialog open={showKdDialog} onOpenChange={setShowKdDialog}>
            <DialogTrigger asChild>
              <Button
                data-testid="event-kd-btn"
                className={`h-24 text-xl font-bold bg-gradient-to-br ${getButtonColor(0)} hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
              >
                KD
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#13151a] border-[#2a2d35]">
              <DialogHeader>
                <DialogTitle className="text-white">Knockdown Severity</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label className="text-gray-300">Severity Level</Label>
                  <Select value={kdSeverity} onValueChange={setKdSeverity}>
                    <SelectTrigger className="bg-[#1a1d24] border-[#2a2d35] text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1a1d24] border-[#2a2d35]">
                      <SelectItem value="flash">Flash</SelectItem>
                      <SelectItem value="hard">Hard</SelectItem>
                      <SelectItem value="near-finish">Near Finish</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  data-testid="submit-kd-btn"
                  onClick={handleKdAttempt}
                  className={`w-full bg-gradient-to-r ${
                    selectedFighter === 'fighter1'
                      ? 'from-red-600 to-red-700 hover:from-red-700 hover:to-red-800'
                      : 'from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800'
                  } text-white`}
                >
                  Log Knockdown
                </Button>
              </div>
            </DialogContent>
          </Dialog>
          
          {eventButtons.map((btn, index) => (
            <Button
              key={btn.event}
              data-testid={`event-${btn.event.toLowerCase().replace(/ /g, '-')}-btn`}
              onClick={() => logEvent(btn.event)}
              className={`h-24 text-xl font-bold bg-gradient-to-br ${getButtonColor(index)} hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
            >
              {btn.label}
            </Button>
          ))}
          
          <Dialog open={showSubDialog} onOpenChange={setShowSubDialog}>
            <DialogTrigger asChild>
              <Button
                data-testid="event-submission-btn"
                className={`h-24 text-xl font-bold bg-gradient-to-br ${
                  selectedFighter === 'fighter1' 
                    ? 'from-red-800 to-rose-900' 
                    : 'from-blue-800 to-cyan-900'
                } hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
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
        </div>
      </div>

    </div>
  );
}