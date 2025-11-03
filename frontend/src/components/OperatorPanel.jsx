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
import { Play, Pause, ChevronRight, Eye, ChevronLeft, ArrowLeft, SkipForward, Wifi, WifiOff, Cloud, CloudOff, RefreshCw, Columns2, Undo2, PauseCircle, PlayCircle, History, Trash2, Keyboard, QrCode, Users, Save, Upload, Mic, MicOff, Volume2 } from 'lucide-react';
import syncManager from '@/utils/syncManager';
import { QRCodeSVG } from 'qrcode.react';

export default function OperatorPanel() {
  const { boutId } = useParams();
  const navigate = useNavigate();
  const [bout, setBout] = useState(null);
  const [selectedFighter, setSelectedFighter] = useState('fighter1');
  const [splitScreenMode, setSplitScreenMode] = useState(false);
  const [controlTimers, setControlTimers] = useState({
    fighter1: { time: 0, isRunning: false, startTime: null, currentPosition: null, positionHistory: [] },
    fighter2: { time: 0, isRunning: false, startTime: null, currentPosition: null, positionHistory: [] }
  });
  const [showSubDialog, setShowSubDialog] = useState(false);
  const [subDepth, setSubDepth] = useState('light');
  const [showKdDialog, setShowKdDialog] = useState(false);
  const [kdSeverity, setKdSeverity] = useState('flash');
  const [showPositionDialog, setShowPositionDialog] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState('mount');
  const [lastEvent, setLastEvent] = useState(null);
  const [isPaused, setIsPaused] = useState(false);
  const [pauseStartTime, setPauseStartTime] = useState(null);
  const [totalPauseDuration, setTotalPauseDuration] = useState(0);
  const [eventHistory, setEventHistory] = useState([]);
  const [showEventHistory, setShowEventHistory] = useState(false);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [showQRCode, setShowQRCode] = useState(false);
  const [activeViewers, setActiveViewers] = useState(0);
  const [showBackupDialog, setShowBackupDialog] = useState(false);
  const [lastBackupTime, setLastBackupTime] = useState(null);
  const [showVoiceNotes, setShowVoiceNotes] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [voiceNotes, setVoiceNotes] = useState([]);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const timerRef = useRef(null);
  const fileInputRef = useRef(null);
  const audioChunksRef = useRef([]);
  const [syncStatus, setSyncStatus] = useState({ isOnline: true, isSyncing: false, queueCount: 0 });

  const positions = [
    { value: 'mount', label: 'Mount' },
    { value: 'back-control', label: 'Back Control' },
    { value: 'side-control', label: 'Side Control' },
    { value: 'half-guard', label: 'Half Guard' },
    { value: 'closed-guard', label: 'Closed Guard' },
    { value: 'open-guard', label: 'Open Guard' },
    { value: 'standing', label: 'Standing Control' }
  ];

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
    
    // Setup device session tracking
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const deviceType = /Mobile|Android|iPhone|iPad/.test(navigator.userAgent) ? 'mobile' : 'desktop';
    
    // Register this device session
    const sessionRef = db.collection('active_sessions').doc(sessionId);
    sessionRef.set({
      boutId,
      deviceType,
      role: 'operator',
      timestamp: firebase.firestore.FieldValue.serverTimestamp(),
      lastActive: firebase.firestore.FieldValue.serverTimestamp()
    });
    
    // Update lastActive every 30 seconds
    const activityInterval = setInterval(() => {
      sessionRef.update({
        lastActive: firebase.firestore.FieldValue.serverTimestamp()
      }).catch(err => console.log('Session update error:', err));
    }, 30000);
    
    // Listen for active viewers count
    const viewersUnsubscribe = db.collection('active_sessions')
      .where('boutId', '==', boutId)
      .onSnapshot((snapshot) => {
        // Filter out stale sessions (older than 2 minutes)
        const twoMinutesAgo = Date.now() - 2 * 60 * 1000;
        const activeSessions = snapshot.docs.filter(doc => {
          const data = doc.data();
          const lastActive = data.lastActive?.toMillis() || 0;
          return lastActive > twoMinutesAgo;
        });
        setActiveViewers(activeSessions.length);
      });
    
    return () => {
      unsubscribe();
      clearInterval(activityInterval);
      viewersUnsubscribe();
      // Remove session on unmount
      sessionRef.delete().catch(err => console.log('Session cleanup error:', err));
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
    if (bout && bout.currentRound) {
      loadEventHistory();
    }
  }, [bout?.currentRound]);

  useEffect(() => {
    if (isPaused) {
      // Stop all timers when paused
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

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
  }, [isPaused]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e) => {
      // Don't trigger shortcuts when typing in inputs
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
        return;
      }

      // Prevent default for handled shortcuts
      const key = e.key.toLowerCase();
      
      // Help dialog
      if (key === '?') {
        e.preventDefault();
        setShowKeyboardShortcuts(true);
        return;
      }

      // Pause/Resume (always available)
      if (key === 'p') {
        e.preventDefault();
        togglePause();
        return;
      }

      // Shortcuts disabled when paused (except P and ?)
      if (isPaused) {
        return;
      }

      // Fighter selection
      if (key === 'r') {
        e.preventDefault();
        setSelectedFighter('fighter1');
        toast.info(`Selected ${bout?.fighter1} (Red)`);
        return;
      }
      if (key === 'b') {
        e.preventDefault();
        setSelectedFighter('fighter2');
        toast.info(`Selected ${bout?.fighter2} (Blue)`);
        return;
      }

      // Event logging shortcuts (1-9)
      if (key === '1') {
        e.preventDefault();
        logEvent('HS');
        return;
      }
      if (key === '2') {
        e.preventDefault();
        logEvent('BS');
        return;
      }
      if (key === '3') {
        e.preventDefault();
        logEvent('LS');
        return;
      }
      if (key === '4') {
        e.preventDefault();
        logEvent('Takedown');
        return;
      }
      if (key === '5') {
        e.preventDefault();
        setShowKdDialog(true);
        return;
      }
      if (key === '6') {
        e.preventDefault();
        logEvent('Rocked');
        return;
      }
      if (key === '7') {
        e.preventDefault();
        setShowSubDialog(true);
        return;
      }
      if (key === '8') {
        e.preventDefault();
        logEvent('Pass');
        return;
      }
      if (key === '9') {
        e.preventDefault();
        logEvent('Reversal');
        return;
      }

      // Control timer toggle
      if (key === ' ') {
        e.preventDefault();
        toggleControl();
        return;
      }

      // Undo
      if (key === 'u') {
        e.preventDefault();
        undoLastEvent();
        return;
      }

      // History
      if (key === 'h') {
        e.preventDefault();
        setShowEventHistory(true);
        return;
      }

      // Judge Panel
      if (key === 'j') {
        e.preventDefault();
        window.open(`/judge/${boutId}`, '_blank');
        return;
      }

      // Round navigation
      if (key === '[') {
        e.preventDefault();
        previousRound();
        return;
      }
      if (key === ']') {
        e.preventDefault();
        nextRound();
        return;
      }

      // Split-screen toggle
      if (key === 's') {
        e.preventDefault();
        setSplitScreenMode(!splitScreenMode);
        toast.info(splitScreenMode ? 'Split-screen OFF' : 'Split-screen ON');
        return;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [bout, boutId, isPaused, selectedFighter, splitScreenMode]);

  const loadBout = async () => {
    try {
      const boutDoc = await db.collection('bouts').doc(boutId).get();
      if (boutDoc.exists) {
        const boutData = { id: boutDoc.id, ...boutDoc.data() };
        setBout(boutData);
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

  const undoLastEvent = async () => {
    if (!lastEvent) {
      toast.error('No event to undo');
      return;
    }

    try {
      // Query for the most recent event matching the last event data
      const eventsRef = db.collection('events')
        .where('boutId', '==', lastEvent.boutId)
        .where('round', '==', lastEvent.round)
        .orderBy('timestamp', 'desc')
        .limit(1);

      const snapshot = await eventsRef.get();
      
      if (!snapshot.empty) {
        const eventDoc = snapshot.docs[0];
        await eventDoc.ref.delete();
        
        const fighterName = lastEvent.eventData.fighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
        toast.success(`Undone: ${lastEvent.eventData.event_type} for ${fighterName}`);
        setLastEvent(null);
        // Reload event history after deletion
        await loadEventHistory();
      } else {
        toast.error('Event not found');
      }
    } catch (error) {
      console.error('Error undoing event:', error);
      toast.error('Failed to undo event');
    }
  };

  const loadEventHistory = async () => {
    if (!boutId) return;
    
    // Get current round from bout state or fetch it
    let currentRound = bout?.currentRound;
    if (!currentRound) {
      try {
        const boutDoc = await db.collection('bouts').doc(boutId).get();
        if (boutDoc.exists) {
          currentRound = boutDoc.data().currentRound;
        }
      } catch (error) {
        console.error('Error fetching bout for event history:', error);
        return;
      }
    }
    
    if (!currentRound) return;

    try {
      const eventsRef = db.collection('events')
        .where('boutId', '==', boutId)
        .where('round', '==', currentRound)
        .orderBy('timestamp', 'desc');

      const snapshot = await eventsRef.get();
      const events = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      
      setEventHistory(events);
    } catch (error) {
      console.error('Error loading event history:', error);
      toast.error('Failed to load event history');
    }
  };

  const deleteEvent = async (eventId, eventData) => {
    if (isPaused) {
      toast.warning('⏸️ Cannot delete events while fight is paused');
      return;
    }

    try {
      await db.collection('events').doc(eventId).delete();
      
      const fighterName = eventData.fighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
      toast.success(`Deleted: ${eventData.event_type} for ${fighterName}`);
      
      // Reload event history
      await loadEventHistory();
      
      // Clear lastEvent if it matches the deleted event
      if (lastEvent && lastEvent.timestamp === eventData.timestamp) {
        setLastEvent(null);
      }
    } catch (error) {
      console.error('Error deleting event:', error);
      toast.error('Failed to delete event');
    }
  };

  const exportBackup = async () => {
    try {
      // Fetch all bout data
      const boutDoc = await db.collection('bouts').doc(boutId).get();
      const boutData = boutDoc.data();

      // Fetch all events for this bout
      const eventsSnapshot = await db.collection('events')
        .where('boutId', '==', boutId)
        .get();
      const eventsData = eventsSnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));

      // Create backup object
      const backup = {
        version: '1.0',
        timestamp: new Date().toISOString(),
        bout: {
          id: boutId,
          ...boutData
        },
        events: eventsData,
        metadata: {
          totalEvents: eventsData.length,
          exportedBy: JSON.parse(localStorage.getItem('judgeProfile') || '{}').judgeId || 'unknown'
        }
      };

      // Convert to JSON and download
      const dataStr = JSON.stringify(backup, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `backup_${bout.fighter1}_vs_${bout.fighter2}_${Date.now()}.json`;
      link.click();
      URL.revokeObjectURL(url);

      setLastBackupTime(new Date());
      toast.success('Backup exported successfully');
    } catch (error) {
      console.error('Backup export error:', error);
      toast.error('Failed to export backup');
    }
  };

  const importBackup = async (file) => {
    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const backup = JSON.parse(e.target.result);
          
          // Validate backup
          if (!backup.version || !backup.bout || !backup.events) {
            toast.error('Invalid backup file format');
            return;
          }

          // Restore bout data
          const { id, ...boutData } = backup.bout;
          await db.collection('bouts').doc(boutId).update(boutData);

          // Restore events
          const batch = db.batch();
          backup.events.forEach(event => {
            const { id, ...eventData } = event;
            const eventRef = db.collection('events').doc();
            batch.set(eventRef, eventData);
          });
          await batch.commit();

          toast.success(`Backup restored: ${backup.events.length} events imported`);
          loadBout();
          loadEventHistory();
        } catch (parseError) {
          console.error('Backup parse error:', parseError);
          toast.error('Failed to parse backup file');
        }
      };
      reader.readAsText(file);
    } catch (error) {
      console.error('Backup import error:', error);
      toast.error('Failed to import backup');
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      importBackup(file);
    }
  };

  const startVoiceNote = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        audioChunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const timestamp = new Date().toISOString();
        
        const newNote = {
          id: Date.now(),
          audioUrl,
          audioBlob,
          timestamp,
          round: bout.currentRound,
          duration: 0
        };

        setVoiceNotes(prev => [...prev, newNote]);
        toast.success('Voice note saved');

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      toast.info('Recording voice note...');
    } catch (error) {
      console.error('Voice recording error:', error);
      toast.error('Failed to start recording. Check microphone permissions.');
    }
  };

  const stopVoiceNote = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      setMediaRecorder(null);
    }
  };

  const deleteVoiceNote = (id) => {
    setVoiceNotes(prev => {
      const note = prev.find(n => n.id === id);
      if (note) {
        URL.revokeObjectURL(note.audioUrl);
      }
      return prev.filter(n => n.id !== id);
    });
    toast.success('Voice note deleted');
  };

  const togglePause = () => {
    if (isPaused) {
      // Resume
      const pauseDuration = Date.now() - pauseStartTime;
      setTotalPauseDuration(prev => prev + pauseDuration);
      setIsPaused(false);
      setPauseStartTime(null);
      
      // Adjust control timer start times to account for pause
      setControlTimers(prev => {
        const updated = { ...prev };
        ['fighter1', 'fighter2'].forEach(fighter => {
          if (updated[fighter].isRunning) {
            updated[fighter] = {
              ...updated[fighter],
              startTime: Date.now() - (updated[fighter].time * 1000)
            };
          }
        });
        return updated;
      });
      
      toast.success(`Resumed after ${Math.floor(pauseDuration / 1000)}s pause`);
    } else {
      // Pause
      setPauseStartTime(Date.now());
      setIsPaused(true);
      toast.warning('⏸️ FIGHT PAUSED - Medical Timeout');
    }
  };

  const logEvent = async (eventType, metadata = {}) => {
    try {
      // Prevent logging when paused
      if (isPaused) {
        toast.warning('⏸️ Cannot log events while fight is paused');
        return;
      }

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
      
      // Store as last event for undo
      setLastEvent({
        boutId,
        round: bout.currentRound,
        eventData,
        timestamp: Date.now()
      });
      
      // Use sync manager to handle online/offline
      await syncManager.addEvent(boutId, bout.currentRound, eventData);
      
      // Update queue count
      await updateSyncStatus();
      
      // Reload event history
      await loadEventHistory();
      
      const fighterName = selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
      toast.success(`${eventType} logged for ${fighterName}`);
    } catch (error) {
      console.error('Error logging event:', error);
      toast.error(`Failed to log event: ${error.message}`);
    }
  };

  const startPosition = async (position) => {
    const fighter = selectedFighter;
    const currentTime = controlTimers[fighter].time;
    
    await logEvent('POSITION_START', { 
      position: position,
      time: currentTime
    });
    
    setControlTimers(prev => ({
      ...prev,
      [fighter]: {
        time: currentTime,
        isRunning: true,
        startTime: Date.now() - (currentTime * 1000),
        currentPosition: position,
        positionHistory: [...prev[fighter].positionHistory]
      }
    }));
    
    setShowPositionDialog(false);
    toast.info(`${position} started for ${fighter === 'fighter1' ? bout.fighter1 : bout.fighter2}`);
  };

  const changePosition = async (newPosition) => {
    const fighter = selectedFighter;
    const currentTime = controlTimers[fighter].time;
    const oldPosition = controlTimers[fighter].currentPosition;
    
    // Log position change
    await logEvent('POSITION_CHANGE', { 
      from: oldPosition,
      to: newPosition,
      time: currentTime
    });
    
    // Update position history
    setControlTimers(prev => ({
      ...prev,
      [fighter]: {
        ...prev[fighter],
        currentPosition: newPosition,
        positionHistory: [
          ...prev[fighter].positionHistory,
          { position: oldPosition, time: currentTime }
        ]
      }
    }));
    
    setShowPositionDialog(false);
    toast.info(`Position changed: ${oldPosition} → ${newPosition}`);
  };

  const stopPosition = async () => {
    const fighter = selectedFighter;
    const currentTime = controlTimers[fighter].time;
    const position = controlTimers[fighter].currentPosition;
    
    await logEvent('POSITION_STOP', { 
      position: position,
      duration: currentTime
    });
    
    setControlTimers(prev => ({
      ...prev,
      [fighter]: {
        time: 0,
        isRunning: false,
        startTime: null,
        currentPosition: null,
        positionHistory: [
          ...prev[fighter].positionHistory,
          { position: position, time: currentTime }
        ]
      }
    }));
    
    toast.info(`Position stopped: ${position} (${formatTime(currentTime)})`);
  };

  const toggleControl = async () => {
    // Prevent control changes when paused
    if (isPaused) {
      toast.warning('⏸️ Cannot change control while fight is paused');
      return;
    }

    // Open position dialog if not running, stop if running
    if (controlTimers[selectedFighter].isRunning) {
      await stopPosition();
    } else {
      setShowPositionDialog(true);
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
    { label: 'HS', event: 'HS' },
    { label: 'BS', event: 'BS' },
    { label: 'LS', event: 'LS' },
    { label: 'Rocked', event: 'Rocked' },
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
    <div className="min-h-screen bg-[#0a0a0b] p-4 relative">
      {/* PAUSED Banner Overlay */}
      {isPaused && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center backdrop-blur-sm">
          <div className="text-center animate-pulse">
            <div className="text-8xl font-bold text-red-500 mb-4">⏸️ PAUSED</div>
            <div className="text-2xl text-white mb-6">Medical Timeout / Doctor Stoppage</div>
            <div className="text-lg text-gray-400">All timers frozen</div>
            <Button
              onClick={togglePause}
              className="mt-8 h-16 px-8 bg-green-600 hover:bg-green-700 text-white text-xl font-bold"
            >
              <PlayCircle className="mr-3 h-8 w-8" />
              RESUME FIGHT
            </Button>
          </div>
        </div>
      )}
      
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
              {activeViewers > 0 && (
                <Badge className="bg-blue-900/30 text-blue-400 border-blue-700/30 px-3 py-1">
                  <Users className="w-3 h-3 mr-1" />
                  {activeViewers} Active {activeViewers === 1 ? 'Viewer' : 'Viewers'}
                </Badge>
              )}
              <Button
                onClick={() => setShowQRCode(true)}
                className="h-10 px-4 bg-indigo-600 hover:bg-indigo-700 text-white"
                title="QR Code for Multi-Device Access"
              >
                <QrCode className="mr-2 h-4 w-4" />
                QR Code
              </Button>
              <Button
                onClick={() => setShowKeyboardShortcuts(true)}
                className="h-10 px-4 bg-gray-700 hover:bg-gray-600 text-white"
                title="Keyboard Shortcuts (Press ?)"
              >
                <Keyboard className="mr-2 h-4 w-4" />
                Shortcuts
              </Button>
              <Button
                onClick={undoLastEvent}
                disabled={!lastEvent}
                className="h-10 px-4 bg-orange-600 hover:bg-orange-700 disabled:opacity-30 disabled:cursor-not-allowed text-white"
                title={lastEvent ? `Undo: ${lastEvent.eventData.event_type}` : 'No event to undo'}
              >
                <Undo2 className="mr-2 h-4 w-4" />
                Undo Last
              </Button>
              <Button
                onClick={() => setShowEventHistory(true)}
                className="h-10 px-4 bg-purple-600 hover:bg-purple-700 text-white"
                title={`View event history (${eventHistory.length} events)`}
              >
                <History className="mr-2 h-4 w-4" />
                History ({eventHistory.length})
              </Button>
              <Button
                onClick={togglePause}
                className={`h-10 px-4 ${
                  isPaused 
                    ? 'bg-green-600 hover:bg-green-700 animate-pulse' 
                    : 'bg-red-600 hover:bg-red-700'
                } text-white font-bold`}
              >
                {isPaused ? (
                  <>
                    <PlayCircle className="mr-2 h-5 w-5" />
                    RESUME
                  </>
                ) : (
                  <>
                    <PauseCircle className="mr-2 h-5 w-5" />
                    PAUSE
                  </>
                )}
              </Button>
              <Button
                onClick={() => setShowBackupDialog(true)}
                className="h-10 px-4 bg-cyan-600 hover:bg-cyan-700 text-white"
                title="Backup & Restore"
              >
                <Save className="mr-2 h-4 w-4" />
                Backup
              </Button>
              <Button
                onClick={() => setShowVoiceNotes(true)}
                className="h-10 px-4 bg-pink-600 hover:bg-pink-700 text-white"
                title="Voice Notes"
              >
                <Mic className="mr-2 h-4 w-4" />
                Voice Notes {voiceNotes.length > 0 && `(${voiceNotes.length})`}
              </Button>
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
        {/* YouTube Live Video - Picture in Picture */}
        {bout.videoUrl && (
          <div className="fixed top-4 right-4 z-50 w-80 rounded-lg overflow-hidden shadow-2xl border-2 border-amber-500">
            <div className="bg-[#13151a] p-2 border-b border-[#2a2d35] flex items-center justify-between">
              <div className="text-xs text-amber-400 font-semibold">LIVE VIDEO</div>
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
            </div>
            <iframe
              width="100%"
              height="180"
              src={`https://www.youtube.com/embed/${bout.videoUrl.includes('watch?v=') 
                ? bout.videoUrl.split('watch?v=')[1].split('&')[0] 
                : bout.videoUrl.split('/').pop()}`}
              title="Live Fight Video"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            ></iframe>
          </div>
        )}
        
        <Card className="bg-gradient-to-r from-[#1a1d24] to-[#13151a] border-[#2a2d35] p-8">
          <div className="text-center space-y-6">
            {/* Round Navigation + Split-Screen Toggle */}
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
              
              <div className="ml-4">
                <Button
                  onClick={() => setSplitScreenMode(!splitScreenMode)}
                  className={`h-10 px-4 ${
                    splitScreenMode
                      ? 'bg-amber-600 hover:bg-amber-700 text-white'
                      : 'bg-[#1a1d24] hover:bg-[#22252d] text-gray-300 border border-[#2a2d35]'
                  }`}
                >
                  <Columns2 className="mr-2 h-4 w-4" />
                  {splitScreenMode ? 'Split-Screen ON' : 'Split-Screen OFF'}
                </Button>
              </div>
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
                disabled={isPaused}
                className={`h-14 px-8 font-semibold text-lg transition-all ${
                  controlTimers[selectedFighter].isRunning
                    ? 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white shadow-lg'
                    : 'bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white'
                } disabled:opacity-30 disabled:cursor-not-allowed`}
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

      {/* Conditional: Split-Screen or Traditional Mode */}
      {splitScreenMode ? (
        /* Split-Screen Fighter Panels */
        <div className="max-w-7xl mx-auto mb-6">
          <div className="grid md:grid-cols-2 gap-4">
          {/* RED CORNER - Left Side */}
          <Card className="bg-gradient-to-br from-red-950/30 to-red-900/20 border-red-800/30 p-4">
            <div className="space-y-4">
              {/* Fighter Header */}
              <div className="text-center border-b border-red-800/30 pb-3">
                <div className="text-xs text-red-400 font-semibold uppercase tracking-wide">Red Corner</div>
                <div className="text-2xl font-bold text-white mt-1">{bout.fighter1}</div>
              </div>
              
              {/* Control Timer */}
              <div className="bg-red-900/30 rounded-lg p-4 border border-red-800/30">
                <div className="text-xs text-gray-400 mb-1">Control Time</div>
                <div className="text-4xl font-bold text-white tracking-wider text-center" style={{ fontFamily: 'Space Grotesk' }}>
                  {formatTime(controlTimers.fighter1.time)}
                </div>
                <div className="text-xs text-gray-500 mt-1 text-center">
                  {controlTimers.fighter1.isRunning ? (
                    <span className="text-green-400 font-semibold">{controlTimers.fighter1.currentPosition?.toUpperCase()}</span>
                  ) : 'Stopped'}
                </div>
                <div className="flex gap-2 mt-3">
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter1');
                      toggleControl();
                    }}
                    disabled={isPaused}
                    className={`flex-1 ${
                      controlTimers.fighter1.isRunning
                        ? 'bg-red-700 hover:bg-red-800'
                        : 'bg-green-600 hover:bg-green-700'
                    } text-white disabled:opacity-30 disabled:cursor-not-allowed`}
                  >
                    {controlTimers.fighter1.isRunning ? (
                      <><Pause className="mr-2 h-4 w-4" />Stop</>
                    ) : (
                      <><Play className="mr-2 h-4 w-4" />Start</>
                    )}
                  </Button>
                  {controlTimers.fighter1.isRunning && (
                    <Button
                      onClick={() => {
                        setSelectedFighter('fighter1');
                        setShowPositionDialog(true);
                      }}
                      disabled={isPaused}
                      className="bg-amber-600 hover:bg-amber-700 text-white px-3 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      Change
                    </Button>
                  )}
                </div>
              </div>
              
              {/* Event Buttons */}
              <div className="space-y-2">
                <div className="text-xs text-red-400 font-semibold uppercase tracking-wide">Log Events</div>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter1');
                      logEvent('HS');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-red-600 to-red-700 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    HS
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter1');
                      logEvent('BS');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-red-600 to-red-700 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    BS
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter1');
                      logEvent('LS');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-red-600 to-red-700 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    LS
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter1');
                      logEvent('Takedown');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-red-700 to-red-800 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Takedown
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter1');
                      setShowKdDialog(true);
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-red-800 to-red-900 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    KD
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter1');
                      logEvent('Rocked');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-red-700 to-red-800 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Rocked
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter1');
                      setShowSubDialog(true);
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-red-800 to-rose-900 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Sub Attempt
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter1');
                      logEvent('Pass');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-red-700 to-red-800 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Pass
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter1');
                      logEvent('Reversal');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-red-700 to-red-800 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Reversal
                  </Button>
                </div>
              </div>
            </div>
          </Card>
          
          {/* BLUE CORNER - Right Side */}
          <Card className="bg-gradient-to-br from-blue-950/30 to-blue-900/20 border-blue-800/30 p-4">
            <div className="space-y-4">
              {/* Fighter Header */}
              <div className="text-center border-b border-blue-800/30 pb-3">
                <div className="text-xs text-blue-400 font-semibold uppercase tracking-wide">Blue Corner</div>
                <div className="text-2xl font-bold text-white mt-1">{bout.fighter2}</div>
              </div>
              
              {/* Control Timer */}
              <div className="bg-blue-900/30 rounded-lg p-4 border border-blue-800/30">
                <div className="text-xs text-gray-400 mb-1">Control Time</div>
                <div className="text-4xl font-bold text-white tracking-wider text-center" style={{ fontFamily: 'Space Grotesk' }}>
                  {formatTime(controlTimers.fighter2.time)}
                </div>
                <div className="text-xs text-gray-500 mt-1 text-center">
                  {controlTimers.fighter2.isRunning ? (
                    <span className="text-green-400 font-semibold">{controlTimers.fighter2.currentPosition?.toUpperCase()}</span>
                  ) : 'Stopped'}
                </div>
                <div className="flex gap-2 mt-3">
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter2');
                      toggleControl();
                    }}
                    disabled={isPaused}
                    className={`flex-1 ${
                      controlTimers.fighter2.isRunning
                        ? 'bg-blue-700 hover:bg-blue-800'
                        : 'bg-green-600 hover:bg-green-700'
                    } text-white disabled:opacity-30 disabled:cursor-not-allowed`}
                  >
                    {controlTimers.fighter2.isRunning ? (
                      <><Pause className="mr-2 h-4 w-4" />Stop</>
                    ) : (
                      <><Play className="mr-2 h-4 w-4" />Start</>
                    )}
                  </Button>
                  {controlTimers.fighter2.isRunning && (
                    <Button
                      onClick={() => {
                        setSelectedFighter('fighter2');
                        setShowPositionDialog(true);
                      }}
                      disabled={isPaused}
                      className="bg-amber-600 hover:bg-amber-700 text-white px-3 disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      Change
                    </Button>
                  )}
                </div>
              </div>
              
              {/* Event Buttons */}
              <div className="space-y-2">
                <div className="text-xs text-blue-400 font-semibold uppercase tracking-wide">Log Events</div>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter2');
                      logEvent('HS');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-blue-600 to-blue-700 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    HS
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter2');
                      logEvent('BS');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-blue-600 to-blue-700 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    BS
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter2');
                      logEvent('LS');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-blue-600 to-blue-700 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    LS
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter2');
                      logEvent('Takedown');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-blue-700 to-blue-800 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Takedown
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter2');
                      setShowKdDialog(true);
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-blue-800 to-blue-900 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    KD
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter2');
                      logEvent('Rocked');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-blue-700 to-blue-800 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Rocked
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter2');
                      setShowSubDialog(true);
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-blue-800 to-cyan-900 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Sub Attempt
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter2');
                      logEvent('Pass');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-blue-700 to-blue-800 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Pass
                  </Button>
                  <Button
                    onClick={() => {
                      setSelectedFighter('fighter2');
                      logEvent('Reversal');
                    }}
                    disabled={isPaused}
                    className="h-16 text-sm font-bold bg-gradient-to-br from-blue-700 to-blue-800 hover:opacity-90 text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Reversal
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
      ) : (
        /* Traditional Mode: Fighter Selection + Shared Event Buttons */
        <>
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
              <Dialog open={showKdDialog && !splitScreenMode} onOpenChange={setShowKdDialog}>
                <Button
                  data-testid="event-kd-btn"
                  onClick={() => setShowKdDialog(true)}
                  disabled={isPaused}
                  className={`h-24 text-xl font-bold bg-gradient-to-br ${getButtonColor(0)} hover:opacity-90 text-white shadow-lg transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed`}
                >
                  KD
                </Button>
              </Dialog>
              
              {eventButtons.map((btn, index) => (
                <Button
                  key={btn.event}
                  data-testid={`event-${btn.event.toLowerCase().replace(/ /g, '-')}-btn`}
                  onClick={() => logEvent(btn.event)}
                  disabled={isPaused}
                  className={`h-24 text-xl font-bold bg-gradient-to-br ${getButtonColor(index + 1)} hover:opacity-90 text-white shadow-lg transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed`}
                >
                  {btn.label}
                </Button>
              ))}
              
              {/* Sub Attempt Button with Dialog */}
              <Dialog open={showSubDialog && !splitScreenMode} onOpenChange={setShowSubDialog}>
                <Button
                  data-testid="event-submission-btn"
                  onClick={() => setShowSubDialog(true)}
                  disabled={isPaused}
                  className={`h-24 text-xl font-bold bg-gradient-to-br ${
                    selectedFighter === 'fighter1' 
                      ? 'from-red-800 to-rose-900' 
                      : 'from-blue-800 to-cyan-900'
                  } hover:opacity-90 text-white shadow-lg transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed`}
                >
                  Sub Attempt
                </Button>
              </Dialog>
            </div>
          </div>
        </>
      )}

      {/* Dialogs for KD and Submission (shared between both modes) */}
      <Dialog open={showKdDialog} onOpenChange={setShowKdDialog}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35]">
          <DialogHeader>
            <DialogTitle className="text-white">Knockdown Severity - {selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2}</DialogTitle>
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
      
      <Dialog open={showSubDialog} onOpenChange={setShowSubDialog}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35]">
          <DialogHeader>
            <DialogTitle className="text-white">Submission Attempt - {selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2}</DialogTitle>
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

      {/* Position Selection Dialog */}
      <Dialog open={showPositionDialog} onOpenChange={setShowPositionDialog}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35]">
          <DialogHeader>
            <DialogTitle className="text-white">
              {controlTimers[selectedFighter].isRunning ? 'Change Position' : 'Start Position Control'} - {selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label className="text-gray-300">Select Position</Label>
              <Select value={selectedPosition} onValueChange={setSelectedPosition}>
                <SelectTrigger className="bg-[#1a1d24] border-[#2a2d35] text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1a1d24] border-[#2a2d35]">
                  {positions.map(pos => (
                    <SelectItem key={pos.value} value={pos.value}>{pos.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {controlTimers[selectedFighter].currentPosition && (
              <div className="p-3 bg-amber-900/20 border border-amber-700/30 rounded">
                <div className="text-xs text-amber-400 font-semibold">Current Position</div>
                <div className="text-white">{controlTimers[selectedFighter].currentPosition}</div>
              </div>
            )}
            
            <Button
              onClick={() => {
                if (controlTimers[selectedFighter].isRunning) {
                  changePosition(selectedPosition);
                } else {
                  startPosition(selectedPosition);
                }
              }}
              className={`w-full bg-gradient-to-r ${
                selectedFighter === 'fighter1'
                  ? 'from-red-600 to-red-700 hover:from-red-700 hover:to-red-800'
                  : 'from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800'
              } text-white`}
            >
              {controlTimers[selectedFighter].isRunning ? 'Change Position' : 'Start Position'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Event History Dialog */}
      <Dialog open={showEventHistory} onOpenChange={setShowEventHistory}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35] max-w-3xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <History className="h-5 w-5 text-purple-400" />
              Event History - Round {bout.currentRound}
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {eventHistory.length === 0 ? (
              <div className="text-center py-12">
                <History className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 text-lg">No events logged yet</p>
                <p className="text-gray-500 text-sm mt-2">Events will appear here as you log them</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[50vh] overflow-y-auto">
                {eventHistory.map((event, index) => {
                  const fighterName = event.fighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
                  const fighterColor = event.fighter === 'fighter1' ? 'text-red-400' : 'text-blue-400';
                  const bgColor = event.fighter === 'fighter1' ? 'bg-red-950/20 border-red-800/30' : 'bg-blue-950/20 border-blue-800/30';
                  
                  return (
                    <div
                      key={event.id}
                      className={`p-4 rounded-lg border ${bgColor} flex items-center justify-between`}
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <div className="text-xs text-gray-500 font-mono">
                            #{eventHistory.length - index}
                          </div>
                          <div className={`text-lg font-bold ${fighterColor}`}>
                            {fighterName}
                          </div>
                          <div className="text-amber-400 font-semibold">
                            {event.event_type}
                          </div>
                        </div>
                        <div className="text-xs text-gray-400 mt-1 flex gap-4">
                          <span>Time: {formatTime(event.timestamp)}</span>
                          {event.metadata && Object.keys(event.metadata).length > 0 && (
                            <span className="text-gray-500">
                              {Object.entries(event.metadata).map(([key, value]) => 
                                `${key}: ${value}`
                              ).join(', ')}
                            </span>
                          )}
                        </div>
                      </div>
                      <Button
                        onClick={() => deleteEvent(event.id, event)}
                        disabled={isPaused}
                        className="h-9 px-3 bg-red-900/50 hover:bg-red-900 text-red-200 border border-red-700/30 disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Delete this event"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Keyboard Shortcuts Help Dialog */}
      <Dialog open={showKeyboardShortcuts} onOpenChange={setShowKeyboardShortcuts}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35] max-w-4xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Keyboard className="h-5 w-5 text-gray-400" />
              Keyboard Shortcuts
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Event Logging */}
              <div className="space-y-3">
                <h3 className="text-amber-500 font-semibold text-sm uppercase tracking-wide border-b border-amber-900/30 pb-2">
                  Event Logging
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Head Strike (HS)</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">1</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Body Strike (BS)</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">2</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Leg Strike (LS)</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">3</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Takedown</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">4</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Knockdown (KD)</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">5</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Rocked</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">6</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Sub Attempt</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">7</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Pass</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">8</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Reversal</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">9</kbd>
                  </div>
                </div>
              </div>

              {/* Controls & Navigation */}
              <div className="space-y-3">
                <h3 className="text-amber-500 font-semibold text-sm uppercase tracking-wide border-b border-amber-900/30 pb-2">
                  Controls & Navigation
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Select Red Fighter</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">R</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Select Blue Fighter</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">B</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Toggle Control Timer</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">Space</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Pause / Resume</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">P</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Undo Last Event</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">U</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Event History</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">H</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Open Judge Panel</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">J</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Previous Round</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">[</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Next Round</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">]</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Toggle Split-Screen</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">S</kbd>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-[#1a1d24] rounded">
                    <span className="text-gray-300">Show This Help</span>
                    <kbd className="px-3 py-1 bg-gray-800 text-gray-300 rounded border border-gray-700 font-mono">?</kbd>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 p-4 bg-amber-900/20 border border-amber-700/30 rounded-lg">
              <p className="text-sm text-amber-200">
                <strong>Note:</strong> Most shortcuts (except Pause and Help) are disabled when the fight is paused. 
                Shortcuts won't work when typing in input fields.
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* QR Code Dialog for Multi-Device Access */}
      <Dialog open={showQRCode} onOpenChange={setShowQRCode}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35] max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <QrCode className="h-5 w-5 text-indigo-400" />
              Multi-Device Access
            </DialogTitle>
          </DialogHeader>
          <div className="py-6">
            <div className="text-center space-y-6">
              <div className="bg-white p-6 rounded-lg inline-block">
                <QRCodeSVG 
                  value={`${window.location.origin}/judge/${boutId}`}
                  size={256}
                  level="H"
                  includeMargin={true}
                />
              </div>
              
              <div className="space-y-3">
                <div className="text-sm text-gray-300">
                  <p className="font-semibold text-amber-500 mb-2">Scan to Open Judge Panel</p>
                  <p className="text-gray-400">Use your phone or tablet camera to scan this QR code and access the Judge Panel on another device.</p>
                </div>
                
                <div className="p-4 bg-[#1a1d24] rounded-lg border border-[#2a2d35]">
                  <div className="text-xs text-gray-500 mb-1">Judge Panel URL</div>
                  <div className="text-sm text-amber-400 font-mono break-all">
                    {window.location.origin}/judge/{boutId}
                  </div>
                </div>

                {activeViewers > 0 && (
                  <div className="flex items-center justify-center gap-2 p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
                    <Users className="w-4 h-4 text-blue-400" />
                    <span className="text-blue-300 text-sm font-semibold">
                      {activeViewers} Active {activeViewers === 1 ? 'Viewer' : 'Viewers'}
                    </span>
                  </div>
                )}

                <div className="text-xs text-gray-500 mt-4">
                  <p className="mb-1">✓ Real-time score updates</p>
                  <p className="mb-1">✓ Automatic synchronization</p>
                  <p>✓ Works on any device with internet</p>
                </div>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Backup & Restore Dialog */}
      <Dialog open={showBackupDialog} onOpenChange={setShowBackupDialog}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35] max-w-md">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Save className="h-5 w-5 text-cyan-400" />
              Backup & Restore
            </DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div className="space-y-3">
              <div className="p-4 bg-[#1a1d24] rounded-lg border border-[#2a2d35]">
                <h3 className="text-sm font-semibold text-gray-300 mb-2">Export Backup</h3>
                <p className="text-xs text-gray-400 mb-3">
                  Download all bout data, events, and scores as a JSON file for safekeeping.
                </p>
                <Button
                  onClick={exportBackup}
                  className="w-full bg-cyan-600 hover:bg-cyan-700 text-white"
                >
                  <Save className="mr-2 h-4 w-4" />
                  Export Backup
                </Button>
                {lastBackupTime && (
                  <p className="text-xs text-green-400 mt-2">
                    Last backup: {lastBackupTime.toLocaleString()}
                  </p>
                )}
              </div>

              <div className="p-4 bg-[#1a1d24] rounded-lg border border-[#2a2d35]">
                <h3 className="text-sm font-semibold text-gray-300 mb-2">Import/Restore Backup</h3>
                <p className="text-xs text-gray-400 mb-3">
                  Restore bout data from a previously exported backup file.
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full bg-orange-600 hover:bg-orange-700 text-white"
                >
                  <Upload className="mr-2 h-4 w-4" />
                  Import Backup
                </Button>
                <p className="text-xs text-amber-400 mt-2">
                  ⚠️ This will overwrite current data
                </p>
              </div>
            </div>

            <div className="p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
              <p className="text-xs text-blue-300">
                <strong>Tip:</strong> Export backups regularly to prevent data loss. Backups include all events, scores, and bout settings.
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Voice Notes Dialog */}
      <Dialog open={showVoiceNotes} onOpenChange={setShowVoiceNotes}>
        <DialogContent className="bg-[#13151a] border-[#2a2d35] max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Mic className="h-5 w-5 text-pink-400" />
              Voice Notes
            </DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            {/* Recording Controls */}
            <div className="p-4 bg-[#1a1d24] rounded-lg border border-[#2a2d35] text-center">
              {!isRecording ? (
                <Button
                  onClick={startVoiceNote}
                  className="bg-pink-600 hover:bg-pink-700 text-white px-6 py-3"
                >
                  <Mic className="mr-2 h-5 w-5" />
                  Start Recording
                </Button>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                    <span className="text-red-400 font-semibold">Recording...</span>
                  </div>
                  <Button
                    onClick={stopVoiceNote}
                    className="bg-red-600 hover:bg-red-700 text-white px-6 py-3"
                  >
                    <MicOff className="mr-2 h-5 w-5" />
                    Stop Recording
                  </Button>
                </div>
              )}
            </div>

            {/* Voice Notes List */}
            <div className="space-y-2 max-h-[40vh] overflow-y-auto">
              {voiceNotes.length === 0 ? (
                <div className="text-center py-8">
                  <Mic className="h-12 w-12 text-gray-600 mx-auto mb-3" />
                  <p className="text-gray-400">No voice notes yet</p>
                  <p className="text-gray-500 text-sm mt-1">Tap "Start Recording" to add notes</p>
                </div>
              ) : (
                voiceNotes.map((note, index) => (
                  <div
                    key={note.id}
                    className="p-3 bg-[#1a1d24] rounded-lg border border-[#2a2d35] flex items-center gap-3"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-gray-500">Note #{index + 1}</span>
                        <span className="text-xs text-pink-400">Round {note.round}</span>
                      </div>
                      <div className="text-xs text-gray-400">
                        {new Date(note.timestamp).toLocaleString()}
                      </div>
                      <audio
                        controls
                        src={note.audioUrl}
                        className="w-full mt-2"
                        style={{ height: '32px' }}
                      />
                    </div>
                    <Button
                      onClick={() => deleteVoiceNote(note.id)}
                      className="h-8 px-2 bg-red-900/50 hover:bg-red-900 text-red-200 border border-red-700/30"
                      title="Delete note"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))
              )}
            </div>

            <div className="p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg">
              <p className="text-xs text-blue-300">
                <strong>Tip:</strong> Voice notes are stored locally in this browser session. Export backup to save them permanently.
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>

    </div>
  );
}