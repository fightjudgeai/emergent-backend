/**
 * Multi-Judge Real-Time Sync System
 * Syncs events and scores from multiple judge devices to a central backend
 */

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

class JudgeSyncManager {
  constructor() {
    this.judgeId = null;
    this.judgeName = null;
    this.boutId = null;
    this.heartbeatInterval = null;
    this.listeners = new Set();
  }

  /**
   * Initialize sync for a judge
   */
  init(judgeId, judgeName, boutId) {
    this.judgeId = judgeId;
    this.judgeName = judgeName;
    this.boutId = boutId;
    
    // Start heartbeat
    this.startHeartbeat();
    
    console.log(`[JudgeSync] Initialized for ${judgeName} (${judgeId}) on bout ${boutId}`);
  }

  /**
   * Start sending heartbeats to track active judges
   */
  startHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
    
    const sendHeartbeat = async () => {
      if (!this.judgeId || !this.boutId) return;
      
      try {
        const response = await fetch(
          `${API_BASE}/api/sync/heartbeat?judge_id=${encodeURIComponent(this.judgeId)}&judge_name=${encodeURIComponent(this.judgeName)}&bout_id=${encodeURIComponent(this.boutId)}`,
          { method: 'POST' }
        );
        
        if (response.ok) {
          const data = await response.json();
          this.notifyListeners('heartbeat', data);
        }
      } catch (error) {
        console.error('[JudgeSync] Heartbeat failed:', error);
      }
    };
    
    // Send immediately and then every 10 seconds
    sendHeartbeat();
    this.heartbeatInterval = setInterval(sendHeartbeat, 10000);
  }

  /**
   * Stop heartbeats
   */
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Sync an event to the backend
   */
  async syncEvent(roundNum, fighter, eventType, metadata = {}) {
    if (!this.judgeId || !this.boutId) {
      console.warn('[JudgeSync] Not initialized');
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/api/sync/event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: this.boutId,
          round_num: roundNum,
          judge_id: this.judgeId,
          judge_name: this.judgeName,
          fighter: fighter,
          event_type: eventType,
          timestamp: Date.now() / 1000,
          metadata: metadata
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log(`[JudgeSync] Event synced: ${eventType} for ${fighter}`);
        this.notifyListeners('event', { eventType, fighter, ...data });
        return data;
      } else {
        console.error('[JudgeSync] Event sync failed:', response.status);
        return null;
      }
    } catch (error) {
      console.error('[JudgeSync] Event sync error:', error);
      return null;
    }
  }

  /**
   * Sync a round score to the backend
   */
  async syncRoundScore(roundNum, fighter1Score, fighter2Score, card, notes = '') {
    if (!this.judgeId || !this.boutId) {
      console.warn('[JudgeSync] Not initialized');
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/api/sync/round-score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: this.boutId,
          round_num: roundNum,
          judge_id: this.judgeId,
          judge_name: this.judgeName,
          fighter1_score: fighter1Score,
          fighter2_score: fighter2Score,
          card: card,
          notes: notes
        })
      });

      if (response.ok) {
        const data = await response.json();
        console.log(`[JudgeSync] Score synced: Round ${roundNum} = ${card}`);
        this.notifyListeners('score', { roundNum, fighter1Score, fighter2Score, card, ...data });
        return data;
      } else {
        console.error('[JudgeSync] Score sync failed:', response.status);
        return null;
      }
    } catch (error) {
      console.error('[JudgeSync] Score sync error:', error);
      return null;
    }
  }

  /**
   * Get sync status for a bout (all judges and their scores)
   */
  async getSyncStatus(boutId = null) {
    const targetBoutId = boutId || this.boutId;
    if (!targetBoutId) {
      console.warn('[JudgeSync] No bout ID');
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/api/sync/status/${targetBoutId}`);
      if (response.ok) {
        return await response.json();
      }
      return null;
    } catch (error) {
      console.error('[JudgeSync] Status fetch error:', error);
      return null;
    }
  }

  /**
   * Get synced events for a round
   */
  async getSyncedEvents(roundNum, judgeId = null) {
    if (!this.boutId) {
      console.warn('[JudgeSync] No bout ID');
      return null;
    }

    try {
      let url = `${API_BASE}/api/sync/events/${this.boutId}/${roundNum}`;
      if (judgeId) {
        url += `?judge_id=${encodeURIComponent(judgeId)}`;
      }
      
      const response = await fetch(url);
      if (response.ok) {
        return await response.json();
      }
      return null;
    } catch (error) {
      console.error('[JudgeSync] Events fetch error:', error);
      return null;
    }
  }

  /**
   * Add a listener for sync events
   */
  addListener(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  /**
   * Notify all listeners of an event
   */
  notifyListeners(type, data) {
    this.listeners.forEach(callback => {
      try {
        callback(type, data);
      } catch (error) {
        console.error('[JudgeSync] Listener error:', error);
      }
    });
  }

  /**
   * Cleanup
   */
  cleanup() {
    this.stopHeartbeat();
    this.listeners.clear();
    this.judgeId = null;
    this.judgeName = null;
    this.boutId = null;
  }
}

// Export singleton instance
const judgeSyncManager = new JudgeSyncManager();
export default judgeSyncManager;

/**
 * React hook for judge sync
 */
export function useJudgeSync(judgeId, judgeName, boutId) {
  const [activeJudges, setActiveJudges] = useState([]);
  const [syncStatus, setSyncStatus] = useState(null);

  useEffect(() => {
    if (judgeId && judgeName && boutId) {
      judgeSyncManager.init(judgeId, judgeName, boutId);
      
      const removeListener = judgeSyncManager.addListener((type, data) => {
        if (type === 'heartbeat') {
          setActiveJudges(data.judges || []);
        }
      });

      return () => {
        removeListener();
        judgeSyncManager.cleanup();
      };
    }
  }, [judgeId, judgeName, boutId]);

  const syncEvent = useCallback((roundNum, fighter, eventType, metadata) => {
    return judgeSyncManager.syncEvent(roundNum, fighter, eventType, metadata);
  }, []);

  const syncScore = useCallback((roundNum, f1Score, f2Score, card, notes) => {
    return judgeSyncManager.syncRoundScore(roundNum, f1Score, f2Score, card, notes);
  }, []);

  const refreshStatus = useCallback(async () => {
    const status = await judgeSyncManager.getSyncStatus();
    setSyncStatus(status);
    return status;
  }, []);

  return {
    activeJudges,
    syncStatus,
    syncEvent,
    syncScore,
    refreshStatus,
    manager: judgeSyncManager
  };
}

// Need to import these for the hook
import { useState, useEffect, useCallback } from 'react';
