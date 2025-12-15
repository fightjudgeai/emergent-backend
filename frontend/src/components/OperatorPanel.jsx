import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import firebase from 'firebase/compat/app';
import { db } from '@/firebase';
import syncManager from '@/utils/syncManager';
import deviceSyncManager from '@/utils/deviceSync';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { toast } from 'sonner';
import { Play, Pause, ChevronRight, Eye, Monitor, Zap, Wifi, WifiOff, Clock, Shield, Activity } from 'lucide-react';
import ICVSSMonitoringDashboard from '@/components/ICVSSMonitoringDashboard';

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
    rocked: 0,
    totalStrikes: 0,
    ssStrikes: 0,
    takedowns: 0,
    subAttempts: 0,
    controlTime: 0
  });
  const [judgeScores, setJudgeScores] = useState({});
  const [pendingJudges, setPendingJudges] = useState([]);
  const [connectedDevices, setConnectedDevices] = useState([]);
  const [showMonitoring, setShowMonitoring] = useState(false);
  const timerRef = useRef(null);
  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  // Keyboard shortcuts handler - using useCallback to access current state
  const handleKeyDown = useCallback(async (event) => {
      // Guard: Don't trigger shortcuts when typing in input fields
      const target = event.target;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return; // Allow normal typing in input fields
      }
      
      // Guard: Check if required state is loaded
      if (!bout) {
        console.log('Keyboard shortcut ignored - bout not loaded yet');
        return;
      }
      
      const key = event.key;
      const shiftPressed = event.shiftKey;
      
      // Prevent default for shortcut keys
      const shortcutKeys = ['1', '2', '3', '4', '5', '6', '7', 'v', 'b', 'a', 's', 'd', 'f', 'q', 'w', 'e', 'r', 'z', 'x', 'c', 'Escape', '/'];
      if (shortcutKeys.includes(key) || key.startsWith('F')) {
        event.preventDefault();
      }
      
      // Wrap all keyboard actions in try-catch for error handling
      try {
      
      // STRIKING - Numbers 1-6 (regular and significant with shift)
      if (key === '1' && !shiftPressed) {
        console.log('Keyboard: Logging Jab');
        await logEvent('Jab', { significant: false });
      } else if (key === '!' || (key === '1' && shiftPressed)) {
        console.log('Keyboard: Logging SS Jab');
        await logEvent('Jab', { significant: true });
      } else if (key === '2' && !shiftPressed) {
        await logEvent('Cross', { significant: false });
      } else if (key === '@' || (key === '2' && shiftPressed)) {
        await logEvent('Cross', { significant: true });
      } else if (key === '3' && !shiftPressed) {
        await logEvent('Hook', { significant: false });
      } else if (key === '#' || (key === '3' && shiftPressed)) {
        await logEvent('Hook', { significant: true });
      } else if (key === '4' && !shiftPressed) {
        await logEvent('Uppercut', { significant: false });
      } else if (key === '$' || (key === '4' && shiftPressed)) {
        await logEvent('Uppercut', { significant: true });
      } else if (key === '5' && !shiftPressed) {
        await logEvent('Elbow', { significant: false });
      } else if (key === '%' || (key === '5' && shiftPressed)) {
        await logEvent('Elbow', { significant: true });
      } else if (key === '6' && !shiftPressed) {
        await logEvent('Knee', { significant: false });
      } else if (key === '^' || (key === '6' && shiftPressed)) {
        await logEvent('Knee', { significant: true });
      } else if (key === '7' && !shiftPressed) {
        await logEvent('Kick', { significant: false });
      } else if (key === '&' || (key === '7' && shiftPressed)) {
        await logEvent('Kick', { significant: true });
      }
      
      // GRAPPLING - V and B
      else if (key === 'v' || key === 'V') {
        await logEvent('Takedown Landed');
      } else if (key === 'b' || key === 'B') {
        await logEvent('Takedown Stuffed');
      }
      
      // SUBMISSIONS - A, S, D, F
      else if (key === 'a' || key === 'A') {
        await logEvent('Submission Attempt', { tier: 'Light' });
      } else if (key === 's' || key === 'S') {
        await logEvent('Submission Attempt', { tier: 'Deep' });
      } else if (key === 'd' || key === 'D') {
        await logEvent('Submission Attempt', { tier: 'Near-Finish' });
      } else if (key === 'f' || key === 'F') {
        await logEvent('Sweep/Reversal');
      }
      
      // DAMAGE - Q, W, E, R
      else if (key === 'q' || key === 'Q') {
        await logEvent('Rocked/Stunned', { significant: true });
      } else if (key === 'w' || key === 'W') {
        await logEvent('KD', { tier: 'Flash' });
      } else if (key === 'e' || key === 'E') {
        await logEvent('KD', { tier: 'Hard' });
      } else if (key === 'r' || key === 'R') {
        await logEvent('KD', { tier: 'Near-Finish' });
      }
      
      // CONTROL TIMERS - Z, X, C (with shift to stop)
      else if (key === 'z' && !shiftPressed) {
        await handleControlToggle('Ground Top Control');
      } else if (key === 'Z' && shiftPressed) {
        await handleControlToggle('Ground Top Control');
      } else if (key === 'x' && !shiftPressed) {
        await handleControlToggle('Ground Back Control');
      } else if (key === 'X' && shiftPressed) {
        await handleControlToggle('Ground Back Control');
      } else if (key === 'c' && !shiftPressed) {
        await handleControlToggle('Cage Control Time');
      } else if (key === 'C' && shiftPressed) {
        await handleControlToggle('Cage Control Time');
      }
      
      // FUNCTION KEYS - F1-F7 (or G1-G7 on gaming keyboards)
      else if (key === 'F1') {
        await undoLastEvent();
      } else if (key === 'F2') {
        await startRound();
      } else if (key === 'F3') {
        await endRound();
      } else if (key === 'F4') {
        await nextRound();
      } else if (key === 'F5') {
        await handleMedicalTimeout();
      } else if (key === 'F6') {
        // -1 Point Deduction
        await handlePointDeductionQuick(1, 'Foul');
      } else if (key === 'F7') {
        // -2 Point Deduction
        await handlePointDeductionQuick(2, 'Serious Foul');
      } else if (key === 'F8') {
        // Warning (no deduction)
        await handlePointDeductionQuick(0, 'Warning');
      }
      
      // SPECIAL ACTIONS
      else if (key === '/') {
        // Save and Sync
        toast.success('Manual save triggered via keyboard');
      }
      } catch (error) {
        console.error('Keyboard shortcut error:', error);
        toast.error(`Keyboard action failed: ${error.message}`);
      }
    }, [bout, selectedFighter, controlTimers]);

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
    
    // Add keyboard event listener
    window.addEventListener('keydown', handleKeyDown);
    
    return () => {
      unsubscribe();
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [boutId, handleKeyDown]);

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

  useEffect(() => {
    // Periodically check judge lock status for current round
    if (bout && boutId) {
      checkJudgeLockStatus(bout.currentRound);
      
      const interval = setInterval(() => {
        checkJudgeLockStatus(bout.currentRound);
      }, 5000); // Check every 5 seconds
      
      return () => clearInterval(interval);
    }
  }, [bout, boutId]);

  useEffect(() => {
    // Initialize multi-device sync for operator
    const initOperatorSync = async () => {
      try {
        await deviceSyncManager.initializeDevice(boutId, 'operator', {
          role: 'operator',
          deviceType: /Mobile|Android|iPhone|iPad/.test(navigator.userAgent) ? 'tablet' : 'desktop'
        });

        // Listen for connected devices
        deviceSyncManager.listenToActiveDevices(boutId, (devices) => {
          setConnectedDevices(devices);
          console.log(`Operator: ${devices.length} devices connected`);
        });

        // Listen for real-time event updates from other devices
        deviceSyncManager.listenToCollection('events', { boutId }, (updates) => {
          updates.forEach(update => {
            if (!update.fromCurrentDevice) {
              console.log('Event synced from another device:', update.type);
            }
          });
        });

        console.log('Multi-device sync initialized for operator');
      } catch (error) {
        console.warn('Multi-device sync not available:', error.message);
      }
    };

    if (boutId) {
      initOperatorSync();
    }

    return () => {
      deviceSyncManager.cleanup();
    };
  }, [boutId]);

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

  const checkJudgeLockStatus = async (roundNum) => {
    try {
      const response = await fetch(`${backendUrl}/api/judge-scores/${boutId}/${roundNum}`);
      const data = await response.json();
      
      const pending = data.scores.filter(s => !s.locked).map(s => s.judge_name);
      setPendingJudges(pending);
      
      return data.all_judges_locked;
    } catch (error) {
      console.error('Error checking judge lock status:', error);
      return false;
    }
  };

  const logEvent = async (eventType, metadata = {}) => {
    try {
      // Guard: Check if bout is loaded
      if (!bout) {
        toast.error('Please wait for bout to load');
        return;
      }
      
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
      // Stop the current control - log event with duration and pause timer
      // Get the actual current time from state to ensure accuracy
      const actualCurrentTime = controlTimers[fighter].time;
      
      await logEvent(controlType, { 
        duration: actualCurrentTime,
        source: 'control-timer',
        type: 'stop'
      });
      
      // Update state to pause the timer (keep accumulated time)
      setControlTimers(prev => ({
        ...prev,
        [fighter]: {
          time: actualCurrentTime, // Keep accumulated time - don't reset!
          isRunning: false,
          startTime: null,
          controlType: null
        }
      }));
      
      toast.success(`${controlType} stopped - ${actualCurrentTime}s logged. Timer paused at: ${formatTime(actualCurrentTime)}`);
    } else {
      // Start the control - log start event and begin timer
      // Log the start event (required for backend tracking)
      await logEvent(controlType, { 
        startTime: currentTime,
        source: 'control-timer',
        type: 'start'
      });
      
      // Start/resume timer from current accumulated time
      setControlTimers(prev => ({
        ...prev,
        [fighter]: {
          time: currentTime,  // Continue from current time (or 0 if first start)
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
    
    let totalEvents = 0;
    
    // Log KDs with Flash tier (default for quick stats)
    const kdCount = quickStats.kd || 0;
    for (let i = 0; i < kdCount; i++) {
      await logEvent('KD', { tier: 'Flash', source: 'quick-input' });
      totalEvents++;
    }
    
    // Log Rocked events
    const rockedCount = quickStats.rocked || 0;
    for (let i = 0; i < rockedCount; i++) {
      await logEvent('Rocked/Stunned', { significant: true, source: 'quick-input' });
      totalEvents++;
    }
    
    // Log total strikes (non-significant strikes as Jab)
    const totalStrikesCount = quickStats.totalStrikes || 0;
    for (let i = 0; i < totalStrikesCount; i++) {
      await logEvent('Jab', { significant: false, source: 'quick-input' });
      totalEvents++;
    }
    
    // Log SS strikes (significant strikes as Cross)
    const ssStrikesCount = quickStats.ssStrikes || 0;
    for (let i = 0; i < ssStrikesCount; i++) {
      await logEvent('Cross', { significant: true, source: 'quick-input' });
      totalEvents++;
    }
    
    // Log takedowns
    const takedownCount = quickStats.takedowns || 0;
    for (let i = 0; i < takedownCount; i++) {
      await logEvent('Takedown Landed', { source: 'quick-input' });
      totalEvents++;
    }
    
    // Log submission attempts
    const subAttemptCount = quickStats.subAttempts || 0;
    for (let i = 0; i < subAttemptCount; i++) {
      await logEvent('Submission Attempt', { tier: 'Light', source: 'quick-input' });
      totalEvents++;
    }
    
    // Log control time if specified (in seconds)
    if (quickStats.controlTime > 0) {
      await logEvent('Ground Top Control', { duration: quickStats.controlTime, source: 'quick-input' });
    }

    toast.success(`Logged ${totalEvents} events + ${quickStats.controlTime || 0}s control time for ${fighterName}`);
    
    // Reset and close
    setQuickStats({
      kd: 0,
      rocked: 0,
      totalStrikes: 0,
      ssStrikes: 0,
      takedowns: 0,
      subAttempts: 0,
      controlTime: 0
    });
    setShowQuickStatsDialog(false);
  };

  const handlePointDeductionQuick = async (points, reason) => {
    if (!bout) {
      toast.error('Bout not loaded');
      return;
    }
    
    const fighterName = selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
    
    // Confirmation for point deductions
    if (points > 0) {
      const confirmed = window.confirm(
        `Deduct ${points} point(s) from ${fighterName}?\n\nReason: ${reason}\n\nThis will affect the round score.`
      );
      if (!confirmed) return;
    }
    
    await logEvent(points > 0 ? 'Point Deduction' : 'Warning', { 
      points,
      reason,
      fighter: selectedFighter
    });
    
    if (points > 0) {
      toast.error(`-${points} point deduction for ${fighterName}`, { duration: 5000 });
    } else {
      toast.warning(`Warning issued to ${fighterName}`, { duration: 4000 });
    }
  };

  const undoLastEvent = async () => {
    console.log('[Undo] Function called - Button clicked!');
    
    if (!bout || !boutId) {
      toast.error('Bout information not loaded');
      console.error('[Undo] Missing bout or boutId:', { bout, boutId });
      return;
    }
    
    if (!bout.currentRound) {
      toast.error('No current round set');
      console.error('[Undo] No current round:', bout);
      return;
    }
    
    try {
      console.log('[Undo] Starting undo for bout:', boutId, 'round:', bout.currentRound);
      
      // Get all events for this bout and current round
      // Note: We fetch all and sort in memory to avoid needing a Firebase composite index
      const eventsSnapshot = await db.collection('events')
        .where('boutId', '==', boutId)
        .where('round', '==', bout.currentRound)
        .get();
      
      console.log('[Undo] Found', eventsSnapshot.docs.length, 'events in round', bout.currentRound);
      
      if (eventsSnapshot.empty) {
        toast.info('No events to undo in this round');
        return;
      }

      // Sort by createdAt in memory and get the last one
      const events = eventsSnapshot.docs.map(doc => ({
        id: doc.id,
        ref: doc.ref,
        data: doc.data()
      }));
      
      console.log('[Undo] All events:', events.map(e => ({
        id: e.id,
        createdAt: e.data.createdAt,
        eventType: e.data.eventType || e.data.event_type,
        fighter: e.data.fighter
      })));
      
      // Sort by createdAt descending (most recent first)
      events.sort((a, b) => {
        const aTime = a.data.createdAt ? new Date(a.data.createdAt).getTime() : 0;
        const bTime = b.data.createdAt ? new Date(b.data.createdAt).getTime() : 0;
        return bTime - aTime;
      });
      
      const lastEvent = events[0];
      const eventData = lastEvent.data;
      
      console.log('[Undo] Most recent event:', {
        id: lastEvent.id,
        data: eventData
      });
      
      // Show confirmation with event details
      const fighterName = eventData.fighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
      const eventType = eventData.eventType || eventData.event_type;
      
      const confirmed = window.confirm(
        `Undo last event?\n\nRound: ${bout.currentRound}\nFighter: ${fighterName}\nEvent: ${eventType}\n\nThis cannot be undone.`
      );
      
      if (!confirmed) {
        toast.info('Undo cancelled');
        return;
      }

      console.log('[Undo] Deleting event from Firebase:', lastEvent.id);
      
      // Delete from Firebase
      await lastEvent.ref.delete();
      
      console.log('[Undo] Event deleted from Firebase');
      
      // Also delete from offline DB if it exists there
      try {
        await syncManager.deleteEvent(lastEvent.id);
        console.log('[Undo] Event deleted from offline DB');
      } catch (err) {
        console.warn('[Undo] Event not in offline DB or already synced:', err);
      }

      toast.success(`Undone: ${eventType} for ${fighterName} (Round ${bout.currentRound})`, { duration: 4000 });
      
      console.log('[Undo] Event successfully undone:', {
        id: lastEvent.id,
        fighter: fighterName,
        event: eventType,
        round: bout.currentRound
      });
    } catch (error) {
      console.error('Error undoing event:', error);
      toast.error(`Failed to undo event: ${error.message}`);
    }
  };

  const startRound = async () => {
    try {
      // Reset timers for new round
      setControlTimers({
        fighter1: { time: 0, isRunning: false, startTime: null, controlType: null },
        fighter2: { time: 0, isRunning: false, startTime: null, controlType: null }
      });
      
      toast.success(`Round ${bout.currentRound} started`);
    } catch (error) {
      console.error('Error starting round:', error);
      toast.error('Failed to start round');
    }
  };

  const endRound = async () => {
    try {
      // Check if all judges have locked their scores
      const allLocked = await checkJudgeLockStatus(bout.currentRound);
      
      if (!allLocked && pendingJudges.length > 0) {
        toast.error(`Cannot end round - waiting for judges to lock: ${pendingJudges.join(', ')}`, {
          duration: 5000
        });
        return;
      }
      
      // Stop any running timers
      setControlTimers({
        fighter1: { ...controlTimers.fighter1, isRunning: false },
        fighter2: { ...controlTimers.fighter2, isRunning: false }
      });
      
      toast.success(`Round ${bout.currentRound} ended - All judges locked`);
      setPendingJudges([]); // Clear pending judges list
    } catch (error) {
      console.error('Error ending round:', error);
      toast.error('Failed to end round');
    }
  };

  const handlePointDeduction = async () => {
    try {
      const fighterName = selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
      await logEvent('Point Deduction', { fighter: selectedFighter });
      toast.warning(`Point deduction for ${fighterName}`);
    } catch (error) {
      console.error('Error logging point deduction:', error);
      toast.error('Failed to log point deduction');
    }
  };

  const handleMedicalTimeout = async () => {
    try {
      // Pause all timers
      setControlTimers({
        fighter1: { ...controlTimers.fighter1, isRunning: false },
        fighter2: { ...controlTimers.fighter2, isRunning: false }
      });
      
      await logEvent('Medical Timeout', { round: bout.currentRound });
      toast.info('Medical timeout / Pause activated');
    } catch (error) {
      console.error('Error handling medical timeout:', error);
      toast.error('Failed to activate medical timeout');
    }
  };

  const nextRound = async () => {
    if (bout.currentRound < bout.totalRounds) {
      // Stop any running timers
      setControlTimers({
        fighter1: { time: 0, isRunning: false, startTime: null, controlType: null },
        fighter2: { time: 0, isRunning: false, startTime: null, controlType: null }
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
    { label: 'SS Knee', event: 'Knee', isSignificant: true },
    { label: 'Kick', event: 'Kick' },
    { label: 'SS Kick', event: 'Kick', isSignificant: true }
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
    { label: 'Sweep/Reversal', event: 'Sweep/Reversal' },
    { label: 'Guard Passing', event: 'Guard Passing' }
  ];

  // Control Events (with start/stop timers)
  const controlButtons = [
    { label: 'Top Control', event: 'Ground Top Control', isTimer: true },
    { label: 'Back Control', event: 'Ground Back Control', isTimer: true },
    { label: 'Cage Control', event: 'Cage Control Time', isTimer: true }
  ];

  // Point Deduction Events
  const pointDeductionButtons = [
    { label: '-1 Point (Foul)', event: 'Point Deduction', points: 1, reason: 'Foul' },
    { label: '-2 Points (Serious Foul)', event: 'Point Deduction', points: 2, reason: 'Serious Foul' },
    { label: 'Warning (No Deduction)', event: 'Warning', points: 0, reason: 'Warning' }
  ];

  const allEventButtons = [...strikingButtons, ...damageButtons, ...grapplingButtons, ...controlButtons, ...pointDeductionButtons];

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
                {/* Multi-Device Sync Indicator */}
                {connectedDevices.length > 1 && (
                  <div className="flex items-center gap-2 px-3 py-1 rounded-full text-sm font-semibold bg-blue-900/30 text-blue-400 border border-blue-500/30 animate-pulse">
                    <Monitor className="h-4 w-4" />
                    {connectedDevices.length} Devices Synced
                  </div>
                )}
              </div>
              <p className="text-gray-400 mt-1">{bout.fighter1} vs {bout.fighter2}</p>
            </div>
            <div className="flex gap-3">
              <Button
                data-testid="cv-systems-btn"
                onClick={() => navigate(`/cv-systems/${boutId}`)}
                className="bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-700 hover:to-blue-700 text-white font-semibold border-2 border-cyan-500"
                title="Open Computer Vision Systems"
              >
                <Eye className="mr-2 h-4 w-4" />
                CV Systems
              </Button>
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
              <Button
                onClick={() => window.open(`/supervisor/${boutId}`, '_blank')}
                className="bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 text-white font-semibold border-2 border-orange-500"
                title="Supervisor Panel - Monitor & Override Judge Scores"
              >
                <Shield className="mr-2 h-4 w-4" />
                Supervisor Panel
              </Button>
              <Button
                onClick={() => setShowMonitoring(!showMonitoring)}
                className={`${showMonitoring ? 'bg-gradient-to-r from-cyan-600 to-teal-600' : 'bg-gradient-to-r from-slate-600 to-slate-700'} hover:from-cyan-700 hover:to-teal-700 text-white font-semibold border-2 border-cyan-500`}
                title="ICVSS System Monitoring - Real-time Health Metrics"
              >
                <Activity className="mr-2 h-4 w-4" />
                {showMonitoring ? 'Hide' : 'Show'} Monitoring
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* ICVSS Monitoring Dashboard */}
      {showMonitoring && (
        <div className="max-w-7xl mx-auto mb-6">
          <ICVSSMonitoringDashboard />
        </div>
      )}


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
              
              {/* Undo Last Event Button */}
              <Button
                onClick={undoLastEvent}
                className="h-14 px-6 bg-red-900/30 hover:bg-red-900/50 text-red-400 border border-red-500/30 font-semibold"
                title="Undo last event in current round (F1)"
              >
                <svg className="mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                </svg>
                Undo (F1)
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

            {/* Pending Judges Indicator */}
            {pendingJudges.length > 0 && (
              <div className="mt-4 p-4 bg-yellow-900/20 border border-yellow-600 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="h-5 w-5 text-yellow-500" />
                  <span className="font-semibold text-yellow-500">Pending Judges ({pendingJudges.length})</span>
                </div>
                <div className="text-sm text-gray-300">
                  Waiting for judges to lock scores: <strong className="text-white">{pendingJudges.join(', ')}</strong>
                </div>
                <div className="text-xs text-gray-400 mt-2">
                  Round cannot be officially closed until all judges have locked their scores.
                </div>
              </div>
            )}
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
            {strikingButtons.map((btn, index) => {
              // Determine button color based on fighter selection and significance
              let buttonColor;
              if (btn.isSignificant) {
                buttonColor = selectedFighter === 'fighter1' 
                  ? 'from-orange-600 to-red-600'  // Red corner - significant
                  : 'from-blue-500 to-blue-700';   // Blue corner - significant
              } else {
                buttonColor = 'from-gray-600 to-gray-700';  // Non-significant (same for both)
              }
              
              return (
                <Button
                  key={`${btn.event}-${btn.isSignificant ? 'sig' : 'non'}`}
                  onClick={() => {
                    logEvent(btn.event, { significant: btn.isSignificant || false });
                    toast.success(`${btn.label} logged`);
                  }}
                  className={`h-16 text-sm font-bold bg-gradient-to-br ${buttonColor} hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
                >
                  {btn.label}
                </Button>
              );
            })}
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
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {grapplingButtons.map((btn, index) => (
              <Button
                key={`${btn.event}-${btn.tier || 'base'}`}
                onClick={() => {
                  if (btn.tier) {
                    logEvent(btn.event, { tier: btn.tier });
                  } else {
                    logEvent(btn.event);
                  }
                  toast.success(`${btn.label} logged`);
                }}
                className={`h-20 text-lg font-bold bg-gradient-to-br ${getButtonColor(index + 16)} hover:opacity-90 text-white shadow-lg transition-all active:scale-95`}
              >
                {btn.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Control Events */}
        <div>
          <h3 className="text-purple-500 font-bold text-lg mb-3">⏱️ Control</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {controlButtons.map((btn, index) => {
              const isActive = controlTimers[selectedFighter].isRunning && 
                              controlTimers[selectedFighter].controlType === btn.event;
              
              return (
                <Button
                  key={btn.event}
                  onClick={() => handleControlToggle(btn.event)}
                  className={`h-24 text-xl font-bold bg-gradient-to-br ${
                    isActive 
                      ? 'from-green-600 to-green-700 ring-4 ring-green-400 animate-pulse' 
                      : getButtonColor(index + 22)
                  } hover:opacity-90 text-white shadow-lg transition-all active:scale-95 relative`}
                >
                  <div className="flex flex-col items-center gap-1">
                    <span>{btn.label}</span>
                    <span className="text-sm opacity-75">{isActive ? '⏸ Stop' : '▶ Start'}</span>
                  </div>
                  {isActive && (
                    <span className="absolute top-2 right-2 flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                  )}
                </Button>
              );
            })}
          </div>
        </div>

        {/* Point Deductions */}
        <div>
          <h3 className="text-yellow-500 font-bold text-lg mb-3">⚠️ Point Deductions & Warnings</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {pointDeductionButtons.map((btn, index) => (
              <Button
                key={`${btn.event}-${btn.points}`}
                onClick={() => {
                  const fighterName = selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
                  
                  // Confirmation dialog for point deductions
                  if (btn.points > 0) {
                    const confirmed = window.confirm(
                      `Deduct ${btn.points} point(s) from ${fighterName}?\n\nReason: ${btn.reason}\n\nThis will affect the round score.`
                    );
                    if (!confirmed) return;
                  }
                  
                  logEvent(btn.event, { 
                    points: btn.points,
                    reason: btn.reason,
                    fighter: selectedFighter
                  });
                  
                  if (btn.points > 0) {
                    toast.error(`-${btn.points} point deduction for ${fighterName}`);
                  } else {
                    toast.warning(`Warning issued to ${fighterName}`);
                  }
                }}
                className={`h-20 text-lg font-bold ${
                  btn.points === 2 ? 'bg-gradient-to-br from-red-600 to-red-700' :
                  btn.points === 1 ? 'bg-gradient-to-br from-yellow-600 to-orange-600' :
                  'bg-gradient-to-br from-gray-600 to-gray-700'
                } hover:opacity-90 text-white shadow-lg transition-all active:scale-95 border-2 ${
                  btn.points > 0 ? 'border-red-400 animate-pulse' : 'border-gray-500'
                }`}
              >
                <div className="flex flex-col items-center gap-1">
                  <span className="text-2xl">{btn.points === 2 ? '🚫' : btn.points === 1 ? '⚠️' : '⚡'}</span>
                  <span>{btn.label}</span>
                </div>
              </Button>
            ))}
          </div>
          <div className="mt-3 p-3 bg-yellow-900/20 border border-yellow-600/30 rounded-lg text-sm text-yellow-200">
            <strong>⚠️ Important:</strong> Point deductions will be applied to the selected fighter's score for this round. 
            Confirm carefully before deducting points.
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
            
            {/* Quick Stats Input Fields */}
            <div className="space-y-3">
              <h4 className="text-amber-500 font-semibold text-sm uppercase tracking-wide">⚡ Quick Stats</h4>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label className="text-gray-300">Knockdowns (KD)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={quickStats.kd}
                    onChange={(e) => setQuickStats({...quickStats, kd: parseInt(e.target.value) || 0})}
                    className="bg-[#1a1d24] border-[#2a2d35] text-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-gray-300">Rocked</Label>
                  <Input
                    type="number"
                    min="0"
                    value={quickStats.rocked}
                    onChange={(e) => setQuickStats({...quickStats, rocked: parseInt(e.target.value) || 0})}
                    className="bg-[#1a1d24] border-[#2a2d35] text-white"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label className="text-gray-300">Total Strikes (Non-SS)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={quickStats.totalStrikes}
                    onChange={(e) => setQuickStats({...quickStats, totalStrikes: parseInt(e.target.value) || 0})}
                    className="bg-[#1a1d24] border-[#2a2d35] text-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-gray-300">SS Strikes</Label>
                  <Input
                    type="number"
                    min="0"
                    value={quickStats.ssStrikes}
                    onChange={(e) => setQuickStats({...quickStats, ssStrikes: parseInt(e.target.value) || 0})}
                    className="bg-[#1a1d24] border-[#2a2d35] text-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-gray-300">Takedowns</Label>
                  <Input
                    type="number"
                    min="0"
                    value={quickStats.takedowns}
                    onChange={(e) => setQuickStats({...quickStats, takedowns: parseInt(e.target.value) || 0})}
                    className="bg-[#1a1d24] border-[#2a2d35] text-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-gray-300">Sub Attempts</Label>
                  <Input
                    type="number"
                    min="0"
                    value={quickStats.subAttempts}
                    onChange={(e) => setQuickStats({...quickStats, subAttempts: parseInt(e.target.value) || 0})}
                    className="bg-[#1a1d24] border-[#2a2d35] text-white"
                  />
                </div>

                <div className="space-y-2 col-span-2">
                  <Label className="text-gray-300">Control Time (seconds)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={quickStats.controlTime}
                    onChange={(e) => setQuickStats({...quickStats, controlTime: parseInt(e.target.value) || 0})}
                    className="bg-[#1a1d24] border-[#2a2d35] text-white"
                    placeholder="e.g., 120 for 2 minutes"
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