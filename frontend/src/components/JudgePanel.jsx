import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import firebase from 'firebase/compat/app';
import { db } from '@/firebase';
import axios from 'axios';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { Shield, Check, TrendingUp, ArrowLeft, SkipForward, Download, Printer, Users, Monitor, Lock, Unlock, Wifi, StickyNote, Edit, Trash2, Save, X } from 'lucide-react';
import ExplainabilityCard from '@/components/ExplainabilityCard';
import deviceSyncManager from '@/utils/deviceSync';
import { Textarea } from '@/components/ui/textarea';
import ICVSSPanel from '@/components/ICVSSPanel';
import { RoundWinner } from '@/components/broadcast/RoundWinner.jsx';
import { FinalResult } from '@/components/broadcast/FinalResult.jsx';
import '@/styles/broadcast.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function JudgePanel() {
  const { boutId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [bout, setBout] = useState(null);
  const [scores, setScores] = useState({});
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState([]);
  const [activeViewers, setActiveViewers] = useState(0);
  const [judgeInfo, setJudgeInfo] = useState(null); // { judgeId, judgeName }
  const [lockedRounds, setLockedRounds] = useState({}); // { roundNum: boolean }
  const [connectedDevices, setConnectedDevices] = useState([]);
  
  // Round Notes State
  const [roundNotes, setRoundNotes] = useState({}); // { roundNum: [notes] }
  const [newNoteText, setNewNoteText] = useState({}); // { roundNum: text }
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [editNoteText, setEditNoteText] = useState('');

  // Broadcast Display State
  const [showRoundResult, setShowRoundResult] = useState(null); // {round, scores}
  const [showFinalResult, setShowFinalResult] = useState(false);
  const [allRounds, setAllRounds] = useState([]);

  // Check for end-fight mode from URL params
  const isEndFightMode = searchParams.get('mode') === 'end-fight';

  useEffect(() => {
    loadBout();
    setupEventListener();
    setupDeviceSession();
    loadJudgeInfo();
    initializeMultiDeviceSync();
    
    return () => {
      // Cleanup on unmount
      deviceSyncManager.cleanup();
    };
  }, [boutId]);

  // Auto-show final results if in end-fight mode
  useEffect(() => {
    if (isEndFightMode && bout && Object.keys(scores).length > 0) {
      // Prepare all rounds data for display
      const roundsData = [];
      for (let i = 1; i <= bout.totalRounds; i++) {
        if (scores[i]) {
          roundsData.push({
            round: i,
            fighter1Score: scores[i]?.card?.split('-')[0] || '10',
            fighter2Score: scores[i]?.card?.split('-')[1] || '9',
            winner: scores[i]?.winner || 'DRAW'
          });
        }
      }
      setAllRounds(roundsData);
      setShowFinalResult(true);
      toast.info('End Fight Mode - Displaying final scores');
    }
  }, [isEndFightMode, bout, scores]);

  useEffect(() => {
    // Recalculate scores whenever events change (including deletions)
    if (bout) {
      console.log('[JudgePanel] Events changed, recalculating scores. Event count:', events.length);
      calculateScores();
    }
  }, [events, bout]);

  useEffect(() => {
    // Load locked rounds status from backend
    if (judgeInfo && boutId) {
      loadLockedRounds();
    }
  }, [judgeInfo, boutId]);

  const loadBout = async () => {
    try {
      const boutDoc = await db.collection('bouts').doc(boutId).get();
      if (boutDoc.exists) {
        setBout({ id: boutDoc.id, ...boutDoc.data() });
      }
    } catch (error) {
      console.error('Error loading bout:', error);
    }
  };

  const setupDeviceSession = () => {
    const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const deviceType = /Mobile|Android|iPhone|iPad/.test(navigator.userAgent) ? 'mobile' : 'desktop';
    
    // Register this device session
    const sessionRef = db.collection('active_sessions').doc(sessionId);
    sessionRef.set({
      boutId,
      deviceType,
      role: 'judge',
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
    
    // Cleanup
    window.addEventListener('beforeunload', () => {
      sessionRef.delete().catch(err => console.log('Session cleanup error:', err));
    });
    
    return () => {
      clearInterval(activityInterval);
      viewersUnsubscribe();
      sessionRef.delete().catch(err => console.log('Session cleanup error:', err));
    };
  };

  const loadJudgeInfo = () => {
    try {
      const storedProfile = localStorage.getItem('judgeProfile');
      console.log('Loading judge profile from localStorage:', storedProfile);
      
      if (storedProfile) {
        const profile = JSON.parse(storedProfile);
        console.log('Parsed judge profile:', profile);
        
        // Check if profile has the required fields
        if (profile.judgeId && profile.judgeName) {
          setJudgeInfo({
            judgeId: profile.judgeId,
            judgeName: profile.judgeName
          });
          console.log('Judge info set successfully:', { judgeId: profile.judgeId, judgeName: profile.judgeName });
        } else {
          console.error('Judge profile missing required fields:', profile);
          toast.error('Invalid judge profile. Please log in again.');
        }
      } else {
        console.warn('No judge profile found in localStorage');
        toast.error('Please log in to access this page');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      }
    } catch (error) {
      console.error('Error loading judge info:', error);
      toast.error('Error loading judge information');
    }
  };

  const initializeMultiDeviceSync = async () => {
    try {
      const storedProfile = localStorage.getItem('judgeProfile');
      const profile = storedProfile ? JSON.parse(storedProfile) : {};
      
      // Initialize device with metadata
      await deviceSyncManager.initializeDevice(boutId, 'judge', {
        judgeName: profile.judgeName || 'Anonymous Judge',
        judgeId: profile.judgeId || 'unknown',
        userAgent: navigator.userAgent,
        deviceType: /Mobile|Android|iPhone|iPad/.test(navigator.userAgent) ? 'tablet' : 'desktop'
      });

      // Listen for other active devices
      deviceSyncManager.listenToActiveDevices(boutId, (devices) => {
        setConnectedDevices(devices);
        console.log(`Connected devices: ${devices.length}`, devices);
      });

      // Listen for real-time event updates
      deviceSyncManager.listenToCollection('events', { boutId }, (updates) => {
        updates.forEach(update => {
          if (update.type === 'added' && !update.fromCurrentDevice) {
            // Event added from another device - recalculate scores
            console.log('New event from another device:', update.data.event_type);
            toast.info(`New event logged from another device`, { duration: 2000 });
          }
        });
      });

      // Listen for real-time judge score updates
      deviceSyncManager.listenToCollection('judge_scores', { boutId }, (updates) => {
        updates.forEach(update => {
          if ((update.type === 'added' || update.type === 'modified') && !update.fromCurrentDevice) {
            console.log('Judge score updated from another device');
            loadLockedRounds(); // Refresh locked status
          }
        });
      });

      console.log('Multi-device sync initialized successfully');
    } catch (error) {
      console.warn('Multi-device sync not available:', error.message);
      // Don't show error toast - app works fine without device presence tracking
    }
  };

  const loadLockedRounds = async () => {
    if (!judgeInfo || !boutId) return;
    
    try {
      const response = await fetch(`${API}/judge-scores/${boutId}`);
      const data = await response.json();
      
      // Build locked rounds map
      const locked = {};
      Object.keys(data.rounds || {}).forEach(roundNum => {
        const roundScores = data.rounds[roundNum];
        const myScore = roundScores.find(s => s.judge_id === judgeInfo.judgeId);
        if (myScore && myScore.locked) {
          locked[parseInt(roundNum)] = true;
        }
      });
      
      setLockedRounds(locked);
    } catch (error) {
      console.error('Error loading locked rounds:', error);
    }
  };

  const handleLockScore = async (roundNum) => {
    // Try to reload judge info if it's missing
    if (!judgeInfo) {
      console.warn('Judge info missing, attempting to reload from localStorage...');
      const storedProfile = localStorage.getItem('judgeProfile');
      
      if (storedProfile) {
        try {
          const profile = JSON.parse(storedProfile);
          if (profile.judgeId && profile.judgeName) {
            // Use the reloaded info directly for this request
            await lockScoreWithInfo(roundNum, {
              judgeId: profile.judgeId,
              judgeName: profile.judgeName
            });
            // Also update state for future requests
            setJudgeInfo({
              judgeId: profile.judgeId,
              judgeName: profile.judgeName
            });
            return;
          }
        } catch (e) {
          console.error('Error parsing stored profile:', e);
        }
      }
      
      toast.error('Judge information not found. Please log in again.');
      return;
    }

    await lockScoreWithInfo(roundNum, judgeInfo);
  };

  const lockScoreWithInfo = async (roundNum, judgeData) => {
    const roundScore = scores[roundNum];
    if (!roundScore) {
      toast.error('No score available to lock');
      return;
    }

    try {
      // Parse the card to get individual scores (e.g., "10-9" -> fighter1=10, fighter2=9)
      const card = roundScore.card;
      let fighter1Score, fighter2Score;
      
      if (card.includes('-')) {
        const parts = card.split('-');
        fighter1Score = parseInt(parts[0]);
        fighter2Score = parseInt(parts[1]);
      } else {
        // Shouldn't happen, but fallback
        toast.error('Invalid score card format');
        return;
      }

      console.log('Locking score:', { roundNum, card, fighter1Score, fighter2Score, judgeData });

      const response = await fetch(`${API}/judge-scores/lock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          round_num: roundNum,
          judge_id: judgeData.judgeId,
          judge_name: judgeData.judgeName,
          fighter1_score: fighter1Score,
          fighter2_score: fighter2Score,
          card: card
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Lock score error:', errorData);
        throw new Error(errorData.detail || 'Failed to lock score');
      }

      const result = await response.json();
      
      setLockedRounds(prev => ({ ...prev, [roundNum]: true }));
      toast.success(`Round ${roundNum} score locked successfully`);
      
      if (result.all_judges_locked) {
        toast.success('All judges have locked their scores for this round!', { duration: 5000 });
      }
    } catch (error) {
      console.error('Error locking score:', error);
      toast.error(`Failed to lock score: ${error.message}`);
    }
  };

  const setupEventListener = () => {
    console.log('[JudgePanel] Setting up real-time event listener for bout:', boutId);
    
    const unsubscribe = db.collection('events')
      .where('boutId', '==', boutId)
      .onSnapshot((snapshot) => {
        console.log('[JudgePanel] Events snapshot received, doc count:', snapshot.docs.length);
        
        const eventsList = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));
        
        console.log('[JudgePanel] Updating events state with', eventsList.length, 'events');
        setEvents(eventsList);
      }, (error) => {
        console.error('[JudgePanel] Error in event listener:', error);
      });

    return unsubscribe;
  };

  const calculateScores = async () => {
    console.log('[JudgePanel] calculateScores called with', events.length, 'total events');
    setLoading(true);
    try {
      const roundScores = {};
      
      for (let round = 1; round <= (bout?.totalRounds || 3); round++) {
        const roundEvents = events.filter(e => e.round === round);
        
        console.log(`[JudgePanel] Round ${round}: ${roundEvents.length} events`);
        
        if (roundEvents.length === 0) {
          console.log(`[JudgePanel] Round ${round}: No events, setting score to null`);
          roundScores[round] = null;
          continue;
        }

        const formattedEvents = roundEvents.map(e => ({
          bout_id: boutId,
          round_num: round,
          fighter: e.fighter,
          event_type: e.eventType,
          timestamp: e.timestamp || 0,
          metadata: e.metadata || {}
        }));

        const response = await axios.post(`${API}/calculate-score-v2`, {
          bout_id: boutId,
          round_num: round,
          events: formattedEvents,
          round_duration: 300
        });

        console.log('=== CALCULATE SCORE RESPONSE ===');
        console.log('Round:', round);
        console.log('Fighter1 event_counts:', response.data.fighter1_score?.event_counts);
        console.log('Fighter2 event_counts:', response.data.fighter2_score?.event_counts);
        console.log('Full response:', JSON.stringify(response.data, null, 2));

        roundScores[round] = response.data;
      }

      setScores(roundScores);
    } catch (error) {
      console.error('Error calculating scores:', error);
      toast.error('Failed to calculate scores');
    } finally {
      setLoading(false);
    }
  };

  const confirmRound = async (roundNum) => {
    try {
      await db.collection('confirmedRounds').doc(`${boutId}_${roundNum}`).set({
        boutId,
        round: roundNum,
        confirmedAt: new Date().toISOString(),
        scores: scores[roundNum]
      });
      toast.success(`Round ${roundNum} confirmed and locked`);
    } catch (error) {
      console.error('Error confirming round:', error);
      toast.error('Failed to confirm round');
    }
  };

  // ============================================================================
  // ROUND NOTES HANDLERS (System 2)
  // ============================================================================

  const loadRoundNotes = async (roundNum) => {
    if (!judgeInfo || !boutId) return;
    
    try {
      const response = await axios.get(`${API}/round-notes/${boutId}/${roundNum}`, {
        params: { judge_id: judgeInfo.judgeId }
      });
      
      setRoundNotes(prev => ({
        ...prev,
        [roundNum]: response.data.notes || []
      }));
    } catch (error) {
      console.error('Error loading round notes:', error);
    }
  };

  const handleAddNote = async (roundNum) => {
    if (!judgeInfo || !boutId || !newNoteText[roundNum]?.trim()) {
      toast.error('Please enter a note');
      return;
    }
    
    try {
      const response = await axios.post(`${API}/round-notes`, {
        bout_id: boutId,
        round_num: roundNum,
        judge_id: judgeInfo.judgeId,
        judge_name: judgeInfo.judgeName,
        note_text: newNoteText[roundNum].trim()
      });
      
      // Reload notes for this round
      await loadRoundNotes(roundNum);
      
      // Clear input
      setNewNoteText(prev => ({ ...prev, [roundNum]: '' }));
      
      toast.success('Note added successfully');
    } catch (error) {
      console.error('Error adding note:', error);
      toast.error('Failed to add note');
    }
  };

  const handleUpdateNote = async (noteId, roundNum) => {
    if (!editNoteText.trim()) {
      toast.error('Please enter note text');
      return;
    }
    
    try {
      const formData = new FormData();
      formData.append('note_text', editNoteText.trim());
      
      await axios.put(`${API}/round-notes/${noteId}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      // Reload notes
      await loadRoundNotes(roundNum);
      
      // Clear edit state
      setEditingNoteId(null);
      setEditNoteText('');
      
      toast.success('Note updated successfully');
    } catch (error) {
      console.error('Error updating note:', error);
      toast.error('Failed to update note');
    }
  };

  const handleDeleteNote = async (noteId, roundNum) => {
    try {
      await axios.delete(`${API}/round-notes/${noteId}`);
      await loadRoundNotes(roundNum);
      toast.success('Note deleted');
    } catch (error) {
      console.error('Error deleting note:', error);
      toast.error('Failed to delete note');
    }
  };

  // Handle End Round - Show round score
  const handleEndRound = async () => {
    if (!bout || !bout.currentRound) {
      toast.error('No active round');
      return;
    }

    try {
      // Fetch the current round score from API
      const response = await axios.get(`${API}/live/${boutId}`);
      const liveData = response.data;
      
      if (!liveData || !liveData.rounds || liveData.rounds.length === 0) {
        toast.error('No round data available');
        return;
      }

      const currentRound = liveData.rounds[liveData.rounds.length - 1];
      
      setShowRoundResult({
        round: liveData.rounds.length,
        unified_red: currentRound.fighter1_score || currentRound.fighter1_total || 0,
        unified_blue: currentRound.fighter2_score || currentRound.fighter2_total || 0
      });

      // Auto-hide after 10 seconds
      setTimeout(() => {
        setShowRoundResult(null);
      }, 10000);

      toast.success(`Round ${liveData.rounds.length} ended`);
    } catch (error) {
      console.error('Error ending round:', error);
      toast.error('Failed to load round scores');
    }
  };

  // Handle End Fight - Show all rounds and final result
  const handleEndFight = async () => {
    if (!bout) {
      toast.error('No bout data');
      return;
    }

    try {
      // Fetch all round data
      const response = await axios.get(`${API}/live/${boutId}`);
      const liveData = response.data;
      
      if (!liveData || !liveData.rounds || liveData.rounds.length === 0) {
        toast.error('No round data available');
        return;
      }

      // Store all rounds
      setAllRounds(liveData.rounds);
      
      // Show final result
      setShowFinalResult(true);

      toast.success('Fight ended - Showing final results');
    } catch (error) {
      console.error('Error ending fight:', error);
      toast.error('Failed to load fight scores');
    }
  };

  const startEditNote = (note) => {
    setEditingNoteId(note.id);
    setEditNoteText(note.note_text);
  };

  const cancelEditNote = () => {
    setEditingNoteId(null);
    setEditNoteText('');
  };

  // Load notes when judge info or bout changes
  useEffect(() => {
    if (judgeInfo && boutId && bout) {
      // Load notes for all rounds
      for (let i = 1; i <= (bout.totalRounds || 3); i++) {
        loadRoundNotes(i);
      }
    }
  }, [judgeInfo, boutId, bout]);

  const goBackToFightList = async () => {
    if (bout?.eventId) {
      navigate(`/event/${bout.eventId}/fights`);
    } else {
      navigate('/');
    }
  };

  const handleExportScorecard = () => {
    // Create a printable scorecard
    const judgeInfo = JSON.parse(localStorage.getItem('judgeProfile') || '{}');
    const printWindow = window.open('', '', 'width=800,height=600');
    
    // Generate HTML for scorecard
    let html = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Official Scorecard - ${bout.fighter1} vs ${bout.fighter2}</title>
        <style>
          @media print {
            body { margin: 0; padding: 20px; }
            .no-print { display: none; }
          }
          body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: white;
            color: black;
          }
          .header {
            text-align: center;
            border-bottom: 3px solid #000;
            padding-bottom: 20px;
            margin-bottom: 20px;
          }
          .header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: bold;
          }
          .header p {
            margin: 5px 0;
            font-size: 14px;
          }
          .fighters {
            display: flex;
            justify-content: space-between;
            margin: 20px 0;
            padding: 15px;
            background: #f5f5f5;
            border: 2px solid #000;
          }
          .fighter {
            text-align: center;
            flex: 1;
          }
          .fighter-name {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 5px;
          }
          .corner {
            font-size: 14px;
            color: #666;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
          }
          th, td {
            border: 1px solid #000;
            padding: 10px;
            text-align: center;
          }
          th {
            background: #333;
            color: white;
            font-weight: bold;
          }
          .winner {
            background: #ffeb3b;
            font-weight: bold;
          }
          .total-row {
            background: #f0f0f0;
            font-weight: bold;
            font-size: 16px;
          }
          .stats-section {
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #ccc;
            background: #f9f9f9;
          }
          .stats-section h3 {
            margin-top: 0;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
          }
          .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
          }
          .stat-item {
            padding: 8px;
            background: white;
            border: 1px solid #ddd;
          }
          .stat-label {
            font-weight: bold;
            font-size: 12px;
            color: #666;
          }
          .stat-value {
            font-size: 18px;
            color: #000;
          }
          .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #000;
            display: flex;
            justify-content: space-between;
          }
          .signature {
            width: 45%;
          }
          .signature-line {
            border-bottom: 1px solid #000;
            margin-top: 40px;
            margin-bottom: 5px;
          }
          .button-container {
            text-align: center;
            margin: 20px 0;
          }
          button {
            padding: 10px 20px;
            margin: 0 10px;
            font-size: 16px;
            cursor: pointer;
            border: none;
            border-radius: 4px;
          }
          .print-btn {
            background: #4CAF50;
            color: white;
          }
          .close-btn {
            background: #f44336;
            color: white;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>OFFICIAL SCORECARD</h1>
          <p><strong>${bout.eventName || 'Combat Event'}</strong></p>
          <p>${new Date().toLocaleDateString()} - ${new Date().toLocaleTimeString()}</p>
        </div>

        <div class="fighters">
          <div class="fighter" style="color: #c00;">
            <div class="fighter-name">${bout.fighter1}</div>
            <div class="corner">RED CORNER</div>
          </div>
          <div style="text-align: center; padding: 0 20px; display: flex; align-items: center; font-size: 24px; font-weight: bold;">VS</div>
          <div class="fighter" style="color: #00c;">
            <div class="fighter-name">${bout.fighter2}</div>
            <div class="corner">BLUE CORNER</div>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Round</th>
              <th>${bout.fighter1} (Red)</th>
              <th>${bout.fighter2} (Blue)</th>
              <th>Winner</th>
            </tr>
          </thead>
          <tbody>
    `;

    // Add rounds
    let fighter1Total = 0;
    let fighter2Total = 0;
    
    for (let i = 1; i <= bout.totalRounds; i++) {
      const roundScore = scores[i];
      if (roundScore && roundScore.card) {
        // Parse card like "10-9" or "9-10" or "10-10"
        const [f1Score, f2Score] = roundScore.card.split('-').map(Number);
        fighter1Total += f1Score;
        fighter2Total += f2Score;
        
        const winner = f1Score > f2Score ? bout.fighter1 : f2Score > f1Score ? bout.fighter2 : 'Draw';
        const winnerClass = f1Score !== f2Score ? 'winner' : '';
        
        html += `
          <tr>
            <td><strong>Round ${i}</strong></td>
            <td class="${f1Score > f2Score ? winnerClass : ''}">${f1Score}</td>
            <td class="${f2Score > f1Score ? winnerClass : ''}">${f2Score}</td>
            <td>${winner}</td>
          </tr>
        `;
      }
    }

    // Total row
    const overallWinner = fighter1Total > fighter2Total ? bout.fighter1 : fighter2Total > fighter1Total ? bout.fighter2 : 'Draw';
    html += `
            <tr class="total-row">
              <td>TOTAL</td>
              <td>${fighter1Total}</td>
              <td>${fighter2Total}</td>
              <td>${overallWinner}</td>
            </tr>
          </tbody>
        </table>

        <div class="footer">
          <div class="signature">
            <div><strong>Judge:</strong> ${judgeInfo.name || 'N/A'}</div>
            <div><strong>ID:</strong> ${judgeInfo.judgeId || 'N/A'}</div>
            <div class="signature-line"></div>
            <div style="text-align: center; font-size: 12px;">Judge Signature</div>
          </div>
          <div class="signature">
            <div><strong>Date:</strong> ${new Date().toLocaleDateString()}</div>
            <div><strong>Time:</strong> ${new Date().toLocaleTimeString()}</div>
            <div class="signature-line"></div>
            <div style="text-align: center; font-size: 12px;">Official Signature</div>
          </div>
        </div>

        <div class="button-container no-print">
          <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
          <button class="close-btn" onclick="window.close()">Close</button>
        </div>
      </body>
      </html>
    `;

    printWindow.document.write(html);
    printWindow.document.close();
    
    toast.success('Scorecard opened in new window');
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
        
        navigate(`/judge/${nextFight.id}`);
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

  if (!bout) return <div className="min-h-screen flex items-center justify-center bg-[#0a0a0b]"><p className="text-gray-400">Loading...</p></div>;

  // Distraction-free mode removed

  const renderSubscores = (subscores, eventCounts, label) => {
    if (!subscores) return null;
    
    // Mapping from subscore keys to display categories
    const categoryMap = {
      "SS": "Significant Strikes",
      "GCQ": "Grappling Control",
      "AGG": "Aggression",
      "DMG": "Damage",
      "TD": "Takedowns"
    };
    
    return (
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">{label}</h4>
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(subscores).map(([key, value]) => {
            const categoryName = categoryMap[key] || key;
            const eventCount = eventCounts?.[categoryName] || 0;
            
            return (
              <div key={key} className="bg-[#1a1d24] rounded-lg p-3 border border-[#2a2d35]">
                <div className="text-xs text-gray-500 mb-1">{categoryName}</div>
                <div className="flex items-baseline gap-1">
                  <div className="text-lg font-bold text-white">{value.toFixed(2)}</div>
                  <div className="text-xs text-gray-500">({eventCount})</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderPositionHistory = (roundNum, fighter) => {
    const roundEvents = events.filter(e => e.round === roundNum && e.fighter === fighter);
    const positionEvents = roundEvents.filter(e => 
      ['POSITION_START', 'POSITION_CHANGE', 'POSITION_STOP'].includes(e.eventType)
    );

    if (positionEvents.length === 0) return null;

    const formatTimestamp = (timestamp) => {
      const minutes = Math.floor(timestamp / 60);
      const seconds = Math.floor(timestamp % 60);
      return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    };

    return (
      <div className="mt-3 pt-3 border-t border-gray-700">
        <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Position History</div>
        <div className="space-y-1">
          {positionEvents.map((event, idx) => (
            <div key={idx} className="text-xs text-gray-500 flex items-center gap-2">
              <span className="text-amber-500">•</span>
              <span className="text-gray-600 font-mono">{formatTimestamp(event.timestamp || 0)}</span>
              <span>
                {event.eventType === 'POSITION_START' && `Started in ${event.metadata?.position}`}
                {event.eventType === 'POSITION_CHANGE' && `${event.metadata?.from} → ${event.metadata?.to}`}
                {event.eventType === 'POSITION_STOP' && `Ended ${event.metadata?.position} (${Math.floor(event.metadata?.duration || 0)}s)`}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] p-4 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <Card className="bg-gradient-to-r from-[#1a1d24] to-[#13151a] border-[#2a2d35] p-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <Button
                data-testid="back-to-fights-btn-judge"
                onClick={goBackToFightList}
                className="h-10 px-4 bg-[#1a1d24] hover:bg-[#22252d] text-gray-300 border border-[#2a2d35]"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Button>
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-amber-500 to-orange-600 rounded-xl flex items-center justify-center">
                  <Shield className="w-7 h-7 text-white" />
                </div>
                <div>
                  <h1 className="text-4xl font-bold text-white">Judge Panel</h1>
                  <p className="text-gray-400 mt-1 text-lg">{bout.fighter1} vs {bout.fighter2}</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {connectedDevices.length > 0 && (
                <div className="flex flex-col gap-1">
                  <Badge className="bg-green-900/30 text-green-400 border-green-700/30 px-3 py-1 animate-pulse">
                    <Wifi className="w-3 h-3 mr-1" />
                    {connectedDevices.length} Device{connectedDevices.length > 1 ? 's' : ''} Synced
                  </Badge>
                  <div className="text-xs text-gray-400">
                    {connectedDevices.filter(d => d.deviceType === 'judge').length} Judge{connectedDevices.filter(d => d.deviceType === 'judge').length !== 1 ? 's' : ''}, {' '}
                    {connectedDevices.filter(d => d.deviceType === 'operator').length} Operator{connectedDevices.filter(d => d.deviceType === 'operator').length !== 1 ? 's' : ''}
                  </div>
                </div>
              )}
              {activeViewers > 0 && (
                <Badge className="bg-blue-900/30 text-blue-400 border-blue-700/30 px-3 py-1">
                  <Users className="w-3 h-3 mr-1" />
                  {activeViewers} Active
                </Badge>
              )}
              <Button
                onClick={handleEndRound}
                className="h-10 px-4 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 text-white font-semibold"
                title="End Current Round and Show Scores"
              >
                <Check className="mr-2 h-4 w-4" />
                End Round
              </Button>
              <Button
                onClick={handleEndFight}
                className="h-10 px-4 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white font-semibold"
                title="End Fight and Show Final Results"
              >
                <TrendingUp className="mr-2 h-4 w-4" />
                End Fight
              </Button>
              <Button
                onClick={handleExportScorecard}
                className="h-10 px-4 bg-purple-600 hover:bg-purple-700 text-white"
                title="Export Official Scorecard"
              >
                <Download className="mr-2 h-4 w-4" />
                Export Scorecard
              </Button>
              <Button
                onClick={() => window.open(`/arena/${boutId}`, '_blank')}
                className="h-10 px-4 bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700 text-white"
                title="Open Arena Display for Big Screen"
              >
                <Monitor className="mr-2 h-4 w-4" />
                🎥 Arena Display
              </Button>
              <Button
                data-testid="next-fight-btn-judge"
                onClick={goToNextFight}
                className="h-10 px-4 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white"
              >
                Next Fight
                <SkipForward className="ml-2 h-4 w-4" />
              </Button>
              <Badge className="bg-amber-500/20 text-amber-500 border-amber-500/30 px-4 py-2 text-base">
                View Only
              </Badge>
            </div>
          </div>
        </Card>
      </div>

      {/* Detailed Event Type Breakdown */}
      {events.length > 0 && (
        <div className="max-w-7xl mx-auto mb-6">
          <Card className="bg-gradient-to-br from-[#1a1d24] to-[#13151a] border-purple-500/30 overflow-hidden">
            <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 border-b border-purple-500/30 px-6 py-3">
              <h2 className="text-lg font-bold text-purple-400 flex items-center gap-2">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Event Type Breakdown (All Rounds)
              </h2>
            </div>
            <div className="grid md:grid-cols-2 divide-x divide-[#2a2d35]">
              {/* RED CORNER */}
              <div className="p-6 bg-gradient-to-br from-red-900/10 to-transparent">
                <div className="text-center mb-4">
                  <div className="text-xs text-red-400 font-semibold uppercase">Red Corner</div>
                  <div className="text-xl font-bold text-white">{bout.fighter1}</div>
                </div>
                <div className="space-y-2">
                  {(() => {
                    const eventCounts = {};
                    events.filter(e => e.fighter === 'fighter1').forEach(e => {
                      const type = e.eventType;
                      eventCounts[type] = (eventCounts[type] || 0) + 1;
                    });
                    
                    // Sort by count descending
                    const sortedEvents = Object.entries(eventCounts).sort((a, b) => b[1] - a[1]);
                    
                    return sortedEvents.length > 0 ? (
                      sortedEvents.map(([type, count]) => (
                        <div key={type} className="flex justify-between items-center px-3 py-2 bg-red-950/20 rounded border border-red-800/20">
                          <span className="text-sm text-gray-300 font-medium">{type}</span>
                          <span className="text-base font-bold text-red-400">{count}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-center text-gray-500 py-4">No events logged</div>
                    );
                  })()}
                </div>
              </div>

              {/* BLUE CORNER */}
              <div className="p-6 bg-gradient-to-br from-blue-900/10 to-transparent">
                <div className="text-center mb-4">
                  <div className="text-xs text-blue-400 font-semibold uppercase">Blue Corner</div>
                  <div className="text-xl font-bold text-white">{bout.fighter2}</div>
                </div>
                <div className="space-y-2">
                  {(() => {
                    const eventCounts = {};
                    events.filter(e => e.fighter === 'fighter2').forEach(e => {
                      const type = e.eventType;
                      eventCounts[type] = (eventCounts[type] || 0) + 1;
                    });
                    
                    // Sort by count descending
                    const sortedEvents = Object.entries(eventCounts).sort((a, b) => b[1] - a[1]);
                    
                    return sortedEvents.length > 0 ? (
                      sortedEvents.map(([type, count]) => (
                        <div key={type} className="flex justify-between items-center px-3 py-2 bg-blue-950/20 rounded border border-blue-800/20">
                          <span className="text-sm text-gray-300 font-medium">{type}</span>
                          <span className="text-base font-bold text-blue-400">{count}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-center text-gray-500 py-4">No events logged</div>
                    );
                  })()}
                </div>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Round Scores */}
      <div className="max-w-7xl mx-auto space-y-8">
        {Array.from({ length: bout?.totalRounds || 3 }, (_, i) => i + 1).map((roundNum) => {
          const roundScore = scores[roundNum];
          
          return (
            <Card key={roundNum} className="bg-[#13151a] border-[#2a2d35] p-6 md:p-8" data-testid={`round-${roundNum}-card`}>
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                  <h2 className="text-2xl font-bold text-amber-500">Round {roundNum}</h2>
                  {roundScore && (
                    <div className="flex items-center gap-3">
                      {/* Fighter 1 Event Count */}
                      <div className="flex items-center gap-2 px-3 py-1 bg-red-950/30 border border-red-700/30 rounded-lg">
                        <span className="text-xs text-red-400 font-semibold uppercase">
                          {bout.fighter1}
                        </span>
                        <span className="text-sm font-bold text-red-300">
                          {(() => {
                            const f1Events = events.filter(e => e.round === roundNum && e.fighter === 'fighter1');
                            return f1Events.length;
                          })()} events
                        </span>
                      </div>
                      
                      {/* Fighter 2 Event Count */}
                      <div className="flex items-center gap-2 px-3 py-1 bg-blue-950/30 border border-blue-700/30 rounded-lg">
                        <span className="text-xs text-blue-400 font-semibold uppercase">
                          {bout.fighter2}
                        </span>
                        <span className="text-sm font-bold text-blue-300">
                          {(() => {
                            const f2Events = events.filter(e => e.round === roundNum && e.fighter === 'fighter2');
                            return f2Events.length;
                          })()} events
                        </span>
                      </div>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {roundScore && (
                    <ExplainabilityCard 
                      roundScore={roundScore} 
                      events={events.filter(e => e.round === roundNum)} 
                      roundNum={roundNum}
                    />
                  )}
                  {roundScore && (
                    lockedRounds[roundNum] ? (
                      <Badge className="bg-green-600 text-white px-4 py-2">
                        <Lock className="mr-2 h-4 w-4" />
                        Score Locked
                      </Badge>
                    ) : (
                      <Button
                        onClick={() => handleLockScore(roundNum)}
                        className="bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-700 hover:to-amber-800 text-white"
                      >
                        <Lock className="mr-2 h-4 w-4" />
                        Lock Score
                      </Button>
                    )
                  )}
                  {roundScore && (
                    <Button
                      data-testid={`confirm-round-${roundNum}-btn`}
                      onClick={() => confirmRound(roundNum)}
                      className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white"
                    >
                      <Check className="mr-2 h-4 w-4" />
                      Confirm Round
                    </Button>
                  )}
                </div>
              </div>

              {loading && <p className="text-gray-400">Calculating scores...</p>}

              {!loading && !roundScore && (
                <p className="text-gray-500 text-center py-8">No events logged for this round yet</p>
              )}

              {!loading && roundScore && (
                <div className="space-y-6">
                  {/* Split-Screen Scoring: Red vs Blue */}
                  <div className="grid md:grid-cols-2 gap-4">
                    {/* RED CORNER - Left Side */}
                    <Card className="bg-gradient-to-br from-red-900/20 to-red-950/20 border-red-800/30 p-4">
                      <div className="space-y-4">
                        {/* Fighter Header */}
                        <div className="text-center border-b border-red-800/30 pb-3">
                          <div className="text-xs text-red-400 font-semibold uppercase tracking-wide">Red Corner</div>
                          <div className="text-2xl font-bold text-white mt-1">{bout.fighter1}</div>
                        </div>
                        
                        {/* Strength Score */}
                        <div className="text-center bg-red-900/30 rounded-lg p-4 border border-red-800/30">
                          <div className="text-4xl font-bold text-red-400" style={{ fontFamily: 'Space Grotesk' }}>
                            {roundScore.fighter1_score.final_score.toFixed(2)}
                          </div>
                          <div className="text-xs text-gray-400 mt-1">Strength Score</div>
                        </div>
                        
                        {/* Subscores with Event Counts */}
                        <div className="space-y-2">
                          <div className="text-xs text-red-400 font-semibold uppercase tracking-wide mb-2">Category Scores</div>
                          {Object.entries(roundScore.fighter1_score.subscores).map(([key, value]) => {
                            const categoryMap = {
                              "SS": "Significant Strikes",
                              "GCQ": "Grappling Control",
                              "AGG": "Aggression",
                              "DMG": "Damage",
                              "TD": "Takedowns"
                            };
                            const categoryName = categoryMap[key] || key;
                            const eventCount = roundScore.fighter1_score.event_counts?.[categoryName] || 0;
                            
                            console.log(`Red Fighter - ${key} (${categoryName}):`, eventCount, 'from', roundScore.fighter1_score.event_counts);
                            
                            return (
                              <div key={key} className="bg-red-950/30 rounded p-2 border border-red-900/30 flex items-center justify-between">
                                <div className="text-xs text-gray-400">{categoryName}</div>
                                <div className="flex items-baseline gap-1">
                                  <div className="text-base font-bold text-white">{value.toFixed(1)}</div>
                                  <div className="text-xs text-gray-500">({eventCount})</div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        
                        {/* Dominance Gates */}
                        {roundScore.winner === 'fighter1' && (
                          <div className="border-t border-red-800/30 pt-3">
                            <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Dominance Gates</div>
                            <div className="flex flex-wrap gap-2">
                              {roundScore.reasons.gates_winner.finish_threat && (
                                <Badge className="bg-red-700 text-white text-xs">Finish Threat</Badge>
                              )}
                              {roundScore.reasons.gates_winner.control_dom && (
                                <Badge className="bg-red-700 text-white text-xs">Control Dom</Badge>
                              )}
                              {roundScore.reasons.gates_winner.multi_cat_dom && (
                                <Badge className="bg-red-700 text-white text-xs">Multi-Cat Dom</Badge>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* Position History */}
                        {renderPositionHistory(roundNum, 'fighter1')}
                      </div>
                    </Card>
                    
                    {/* BLUE CORNER - Right Side */}
                    <Card className="bg-gradient-to-br from-blue-900/20 to-blue-950/20 border-blue-800/30 p-4">
                      <div className="space-y-4">
                        {/* Fighter Header */}
                        <div className="text-center border-b border-blue-800/30 pb-3">
                          <div className="text-xs text-blue-400 font-semibold uppercase tracking-wide">Blue Corner</div>
                          <div className="text-2xl font-bold text-white mt-1">{bout.fighter2}</div>
                        </div>
                        
                        {/* Strength Score */}
                        <div className="text-center bg-blue-900/30 rounded-lg p-4 border border-blue-800/30">
                          <div className="text-4xl font-bold text-blue-400" style={{ fontFamily: 'Space Grotesk' }}>
                            {roundScore.fighter2_score.final_score.toFixed(2)}
                          </div>
                          <div className="text-xs text-gray-400 mt-1">Strength Score</div>
                        </div>
                        
                        {/* Subscores with Event Counts */}
                        <div className="space-y-2">
                          <div className="text-xs text-blue-400 font-semibold uppercase tracking-wide mb-2">Category Scores</div>
                          {Object.entries(roundScore.fighter2_score.subscores).map(([key, value]) => {
                            const categoryMap = {
                              "SS": "Significant Strikes",
                              "GCQ": "Grappling Control",
                              "AGG": "Aggression",
                              "DMG": "Damage",
                              "TD": "Takedowns"
                            };
                            const categoryName = categoryMap[key] || key;
                            const eventCount = roundScore.fighter2_score.event_counts?.[categoryName] || 0;
                            
                            return (
                              <div key={key} className="bg-blue-950/30 rounded p-2 border border-blue-900/30 flex items-center justify-between">
                                <div className="text-xs text-gray-400">{categoryName}</div>
                                <div className="flex items-baseline gap-1">
                                  <div className="text-base font-bold text-white">{value.toFixed(1)}</div>
                                  <div className="text-xs text-gray-500">({eventCount})</div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        
                        {/* Dominance Gates */}
                        {roundScore.winner === 'fighter2' && (
                          <div className="border-t border-blue-800/30 pt-3">
                            <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Dominance Gates</div>
                            <div className="flex flex-wrap gap-2">
                              {roundScore.reasons.gates_winner.finish_threat && (
                                <Badge className="bg-blue-700 text-white text-xs">Finish Threat</Badge>
                              )}
                              {roundScore.reasons.gates_winner.control_dom && (
                                <Badge className="bg-blue-700 text-white text-xs">Control Dom</Badge>
                              )}
                              {roundScore.reasons.gates_winner.multi_cat_dom && (
                                <Badge className="bg-blue-700 text-white text-xs">Multi-Cat Dom</Badge>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* Position History */}
                        {renderPositionHistory(roundNum, 'fighter2')}
                      </div>
                    </Card>
                  </div>

                  {/* 10-Point-Must Card - Centered */}
                  <Card className="bg-gradient-to-r from-amber-900/30 to-orange-900/30 border-amber-700/50 p-6">
                    <div className="text-center space-y-3">
                      <div className="text-xs text-amber-400 font-semibold uppercase tracking-wide">Official Score Card</div>
                      <div className="text-5xl font-bold text-white" style={{ fontFamily: 'Space Grotesk' }}>
                        {roundScore.card}
                      </div>
                      <div className="flex items-center justify-center gap-3 flex-wrap">
                        {roundScore.winner === 'DRAW' ? (
                          <Badge className="bg-gray-600 text-white border-gray-500 px-4 py-2">
                            Round Draw
                          </Badge>
                        ) : (
                          <>
                            <Badge className={`${
                              roundScore.winner === 'fighter1' 
                                ? 'bg-red-600 border-red-500' 
                                : 'bg-blue-600 border-blue-500'
                            } text-white px-4 py-2`}>
                              Winner: {roundScore.winner === 'fighter1' ? bout.fighter1 : bout.fighter2}
                            </Badge>
                            {roundScore.reasons.to_107 && (
                              <Badge className="bg-red-900 border-red-700 text-white px-3 py-1">10-7 Dominance</Badge>
                            )}
                            {roundScore.reasons.to_108 && !roundScore.reasons.to_107 && (
                              <Badge className="bg-orange-900 border-orange-700 text-white px-3 py-1">10-8 Dominance</Badge>
                            )}
                          </>
                        )}
                      </div>
                      <div className="flex items-center justify-center gap-2 text-sm text-gray-400">
                        <TrendingUp className="w-4 h-4 text-amber-500" />
                        <span>Score Delta: {roundScore.reasons.delta.toFixed(2)} points</span>
                      </div>
                    </div>
                  </Card>

                  {/* Uncertainty Band */}
                  {roundScore.uncertainty && (
                    <Card className={`p-4 border ${
                      roundScore.uncertainty === 'high_confidence' 
                        ? 'bg-green-900/20 border-green-700/50' 
                        : roundScore.uncertainty === 'medium_confidence'
                        ? 'bg-amber-900/20 border-amber-700/50'
                        : 'bg-red-900/20 border-red-700/50'
                    }`}>
                      <div className="flex items-start gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          roundScore.uncertainty === 'high_confidence'
                            ? 'bg-green-600'
                            : roundScore.uncertainty === 'medium_confidence'
                            ? 'bg-amber-600'
                            : 'bg-red-600'
                        }`}>
                          <TrendingUp className="w-5 h-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-base font-bold ${
                              roundScore.uncertainty === 'high_confidence'
                                ? 'text-green-400'
                                : roundScore.uncertainty === 'medium_confidence'
                                ? 'text-amber-400'
                                : 'text-red-400'
                            }`}>
                              {roundScore.uncertainty === 'high_confidence' && 'High Confidence'}
                              {roundScore.uncertainty === 'medium_confidence' && 'Medium Confidence'}
                              {roundScore.uncertainty === 'low_confidence' && 'Low Confidence'}
                            </span>
                            <Badge className={`text-xs ${
                              roundScore.uncertainty === 'high_confidence'
                                ? 'bg-green-900/30 text-green-400 border-green-700/30'
                                : roundScore.uncertainty === 'medium_confidence'
                                ? 'bg-amber-900/30 text-amber-400 border-amber-700/30'
                                : 'bg-red-900/30 text-red-400 border-red-700/30'
                            }`}>
                              Uncertainty Band
                            </Badge>
                          </div>
                          <div className="text-sm text-gray-300 mb-2">
                            {roundScore.uncertainty === 'high_confidence' && 
                              'This score is highly confident. The decision is clear with significant separation from scoring thresholds.'}
                            {roundScore.uncertainty === 'medium_confidence' && 
                              'This score has moderate confidence. Consider reviewing for potential edge cases.'}
                            {roundScore.uncertainty === 'low_confidence' && 
                              'This score has low confidence. The round was very close or had complicating factors.'}
                          </div>
                          {roundScore.uncertainty_factors && roundScore.uncertainty_factors.length > 0 && (
                            <div className="space-y-1">
                              <div className="text-xs text-gray-400 uppercase tracking-wide">Factors:</div>
                              {roundScore.uncertainty_factors.map((factor, idx) => (
                                <div key={idx} className="text-xs text-gray-400 flex items-start gap-2">
                                  <span className="text-amber-500">•</span>
                                  <span>{factor}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </Card>
                  )}
                  
                  {/* Event Log with Timestamps */}
                  <Card className="bg-[#1a1d24] border-[#2a2d35] p-4 mt-6">
                    <div className="text-sm text-gray-400 uppercase tracking-wide mb-3">Round Event Log</div>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {events.filter(e => e.round === roundNum).map((event, idx) => {
                        const formatTimestamp = (timestamp) => {
                          const minutes = Math.floor(timestamp / 60);
                          const seconds = Math.floor(timestamp % 60);
                          return `${minutes}:${seconds.toString().padStart(2, '0')}`;
                        };
                        
                        const fighterName = event.fighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
                        const fighterColor = event.fighter === 'fighter1' ? 'text-red-400' : 'text-blue-400';
                        
                        return (
                          <div key={idx} className="flex items-center gap-3 text-xs p-2 bg-[#13151a] rounded border border-[#2a2d35]">
                            <span className="text-amber-500 font-mono font-semibold min-w-[40px]">
                              {formatTimestamp(event.timestamp || 0)}
                            </span>
                            <span className={`${fighterColor} font-semibold min-w-[100px]`}>
                              {fighterName}
                            </span>
                            <span className="text-white font-semibold">
                              {event.eventType}
                            </span>
                            {event.metadata && Object.keys(event.metadata).length > 0 && (
                              <span className="text-gray-500 text-xs">
                                {JSON.stringify(event.metadata).slice(0, 50)}...
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </Card>

                  {/* Round Notes (System 2) */}
                  <Card className="bg-gradient-to-br from-purple-950/20 to-purple-900/10 border-purple-800/30 p-4 mt-6">
                    <div className="flex items-center gap-2 mb-4">
                      <StickyNote className="w-4 h-4 text-purple-400" />
                      <div className="text-sm text-purple-400 uppercase tracking-wide font-semibold">Round Notes</div>
                      <Badge className="bg-purple-900/30 text-purple-300 border-purple-700/30 text-xs">
                        {roundNotes[roundNum]?.length || 0} notes
                      </Badge>
                    </div>

                    {/* Add New Note */}
                    <div className="mb-4">
                      <Textarea
                        placeholder="Add a note for this round... (e.g., 'Fighter 1 dominated striking', 'Close round, slight edge to Fighter 2')"
                        value={newNoteText[roundNum] || ''}
                        onChange={(e) => setNewNoteText(prev => ({ ...prev, [roundNum]: e.target.value }))}
                        className="bg-[#13151a] border-purple-800/30 text-white placeholder:text-gray-500 min-h-[80px] mb-2"
                      />
                      <Button
                        onClick={() => handleAddNote(roundNum)}
                        disabled={!newNoteText[roundNum]?.trim()}
                        className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white"
                      >
                        <StickyNote className="mr-2 h-4 w-4" />
                        Add Note
                      </Button>
                    </div>

                    {/* Display Existing Notes */}
                    <div className="space-y-3">
                      {roundNotes[roundNum]?.length > 0 ? (
                        roundNotes[roundNum].map((note) => (
                          <div key={note.id} className="bg-[#1a1d24] border border-purple-800/20 rounded-lg p-3">
                            {editingNoteId === note.id ? (
                              // Edit Mode
                              <div className="space-y-2">
                                <Textarea
                                  value={editNoteText}
                                  onChange={(e) => setEditNoteText(e.target.value)}
                                  className="bg-[#13151a] border-purple-800/30 text-white min-h-[60px]"
                                />
                                <div className="flex gap-2">
                                  <Button
                                    onClick={() => handleUpdateNote(note.id, roundNum)}
                                    className="bg-green-600 hover:bg-green-700 text-white text-xs"
                                  >
                                    <Save className="mr-1 h-3 w-3" />
                                    Save
                                  </Button>
                                  <Button
                                    onClick={cancelEditNote}
                                    className="bg-gray-600 hover:bg-gray-700 text-white text-xs"
                                  >
                                    <X className="mr-1 h-3 w-3" />
                                    Cancel
                                  </Button>
                                </div>
                              </div>
                            ) : (
                              // View Mode
                              <div>
                                <div className="text-sm text-white mb-2">
                                  {note.note_text}
                                </div>
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-3 text-xs text-gray-500">
                                    <span className="text-purple-400 font-semibold">{note.judge_name}</span>
                                    <span>•</span>
                                    <span>{new Date(note.timestamp).toLocaleString()}</span>
                                  </div>
                                  <div className="flex gap-2">
                                    <Button
                                      onClick={() => startEditNote(note)}
                                      className="bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border-blue-600/30 text-xs h-7 px-2"
                                    >
                                      <Edit className="h-3 w-3" />
                                    </Button>
                                    <Button
                                      onClick={() => handleDeleteNote(note.id, roundNum)}
                                      className="bg-red-600/20 hover:bg-red-600/30 text-red-400 border-red-600/30 text-xs h-7 px-2"
                                    >
                                      <Trash2 className="h-3 w-3" />
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <div className="text-center text-gray-500 text-sm py-4">
                          No notes yet. Add your first note above.
                        </div>
                      )}
                    </div>
                  </Card>
                </div>
              )}
            </Card>
          );
        })}

        {/* Total Score After All Rounds */}
        {bout && bout.currentRound >= bout.totalRounds && (
          <Card className="bg-gradient-to-br from-amber-950/40 to-amber-900/20 border-2 border-amber-600/50 p-8 max-w-7xl mx-auto mt-8">
            <div className="text-center">
              <h2 className="text-3xl font-bold text-amber-500 mb-6">
                Final Score After {bout.totalRounds} Rounds
              </h2>
              <div className="flex items-center justify-center gap-12">
                {/* Fighter 1 Total */}
                <div className="flex flex-col items-center">
                  <div className="text-red-400 text-lg font-semibold mb-2">
                    {bout.fighter1} (Red)
                  </div>
                  <div className="text-6xl font-black text-white">
                    {(() => {
                      let total = 0;
                      for (let i = 1; i <= bout.totalRounds; i++) {
                        const roundScore = scores[i];
                        if (roundScore && roundScore.card) {
                          // Parse card like "10-9" or "9-10" or "10-10"
                          const [score1, score2] = roundScore.card.split('-').map(Number);
                          total += score1;
                        }
                      }
                      return total;
                    })()}
                  </div>
                </div>

                {/* VS Divider */}
                <div className="text-4xl font-bold text-gray-500">-</div>

                {/* Fighter 2 Total */}
                <div className="flex flex-col items-center">
                  <div className="text-blue-400 text-lg font-semibold mb-2">
                    {bout.fighter2} (Blue)
                  </div>
                  <div className="text-6xl font-black text-white">
                    {(() => {
                      let total = 0;
                      for (let i = 1; i <= bout.totalRounds; i++) {
                        const roundScore = scores[i];
                        if (roundScore && roundScore.card) {
                          // Parse card like "10-9" or "9-10" or "10-10"
                          const [score1, score2] = roundScore.card.split('-').map(Number);
                          total += score2;
                        }
                      }
                      return total;
                    })()}
                  </div>
                </div>
              </div>

              {/* Winner Declaration */}
              <div className="mt-8">
                {(() => {
                  let f1Total = 0, f2Total = 0;
                  for (let i = 1; i <= bout.totalRounds; i++) {
                    const roundScore = scores[i];
                    if (roundScore && roundScore.card) {
                      // Parse card like "10-9" or "9-10" or "10-10"
                      const [score1, score2] = roundScore.card.split('-').map(Number);
                      f1Total += score1;
                      f2Total += score2;
                    }
                  }
                  const winner = f1Total > f2Total ? bout.fighter1 : f2Total > f1Total ? bout.fighter2 : 'Draw';
                  const winnerColor = f1Total > f2Total ? 'text-red-500' : f2Total > f1Total ? 'text-blue-500' : 'text-gray-400';
                  
                  return (
                    <div className={`text-2xl font-bold ${winnerColor}`}>
                      {winner === 'Draw' ? 'DRAW' : `WINNER: ${winner.toUpperCase()}`}
                    </div>
                  );
                })()}
              </div>
            </div>
          </Card>
        )}
      </div>

      {/* Broadcast Display Overlays */}
      {showRoundResult && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-8">
          <div className="max-w-4xl w-full">
            <div className="flex justify-end mb-4">
              <Button
                onClick={() => setShowRoundResult(null)}
                className="bg-gray-700 hover:bg-gray-600"
              >
                <X className="h-4 w-4 mr-2" />
                Close
              </Button>
            </div>
            <RoundWinner
              round={showRoundResult}
              roundNumber={showRoundResult.round}
              redName={bout?.fighter1 || 'Fighter 1'}
              blueName={bout?.fighter2 || 'Fighter 2'}
              isVisible={true}
            />
          </div>
        </div>
      )}

      {showFinalResult && (
        <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-8 overflow-y-auto">
          <div className="max-w-4xl w-full">
            <div className="flex justify-end mb-4">
              <Button
                onClick={() => setShowFinalResult(false)}
                className="bg-gray-700 hover:bg-gray-600"
              >
                <X className="h-4 w-4 mr-2" />
                Close
              </Button>
            </div>

            {/* Show all rounds */}
            <div className="mb-6 space-y-4">
              {allRounds.map((round, idx) => (
                <RoundWinner
                  key={idx}
                  round={{
                    round: idx + 1,
                    unified_red: round.fighter1_score || round.fighter1_total || 0,
                    unified_blue: round.fighter2_score || round.fighter2_total || 0
                  }}
                  roundNumber={idx + 1}
                  redName={bout?.fighter1 || 'Fighter 1'}
                  blueName={bout?.fighter2 || 'Fighter 2'}
                  isVisible={true}
                />
              ))}
            </div>

            {/* Show final result */}
            <FinalResult
              total={{
                red: allRounds.reduce((sum, r) => sum + (r.fighter1_score || r.fighter1_total || 0), 0),
                blue: allRounds.reduce((sum, r) => sum + (r.fighter2_score || r.fighter2_total || 0), 0)
              }}
              winner={(() => {
                const redTotal = allRounds.reduce((sum, r) => sum + (r.fighter1_score || r.fighter1_total || 0), 0);
                const blueTotal = allRounds.reduce((sum, r) => sum + (r.fighter2_score || r.fighter2_total || 0), 0);
                return redTotal > blueTotal ? 'red' : blueTotal > redTotal ? 'blue' : 'draw';
              })()}
              redName={bout?.fighter1 || 'Fighter 1'}
              blueName={bout?.fighter2 || 'Fighter 2'}
              isVisible={true}
            />
          </div>
        </div>
      )}
    </div>
  );
}