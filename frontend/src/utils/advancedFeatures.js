// Per-promotion tuning profiles
export const PROMOTION_PROFILES = {
  UFC: {
    name: 'UFC',
    weights: {
      KD: 0.30,
      ISS: 0.20,
      TSR: 0.15,
      GCQ: 0.10,
      TDQ: 0.08,
      OC: 0.06,
      SUBQ: 0.05,
      AGG: 0.05,
      RP: 0.01
    },
    thresholds: {
      draw: 0, // Exact match only
      tenNine: 600,
      tenEight: 900,
      tenSeven: 1000
    },
    gates: {
      finishThreat: { KD: 1, SUBQ: 8.0, ISS: 9.0 },
      controlDom: { GCQ: 7.5, timeShare: 0.5 },
      multiCatDom: { threshold: 7.5, count: 3 }
    }
  },
  Bellator: {
    name: 'Bellator',
    weights: {
      KD: 0.28,
      ISS: 0.22,
      TSR: 0.14,
      GCQ: 0.12,
      TDQ: 0.10,
      OC: 0.05,
      SUBQ: 0.06,
      AGG: 0.02,
      RP: 0.01
    },
    thresholds: {
      draw: 0,
      tenNine: 550,
      tenEight: 850,
      tenSeven: 1000
    },
    gates: {
      finishThreat: { KD: 1, SUBQ: 7.5, ISS: 8.5 },
      controlDom: { GCQ: 7.0, timeShare: 0.5 },
      multiCatDom: { threshold: 7.0, count: 3 }
    }
  },
  ONE: {
    name: 'ONE Championship',
    weights: {
      KD: 0.32,
      ISS: 0.18,
      TSR: 0.12,
      GCQ: 0.08,
      TDQ: 0.12,
      OC: 0.06,
      SUBQ: 0.08,
      AGG: 0.03,
      RP: 0.01
    },
    thresholds: {
      draw: 0,
      tenNine: 650,
      tenEight: 950,
      tenSeven: 1000
    },
    gates: {
      finishThreat: { KD: 1, SUBQ: 8.5, ISS: 9.5 },
      controlDom: { GCQ: 8.0, timeShare: 0.6 },
      multiCatDom: { threshold: 8.0, count: 3 }
    }
  },
  PFL: {
    name: 'PFL',
    weights: {
      KD: 0.30,
      ISS: 0.20,
      TSR: 0.15,
      GCQ: 0.10,
      TDQ: 0.08,
      OC: 0.06,
      SUBQ: 0.05,
      AGG: 0.05,
      RP: 0.01
    },
    thresholds: {
      draw: 0,
      tenNine: 600,
      tenEight: 900,
      tenSeven: 1000
    },
    gates: {
      finishThreat: { KD: 1, SUBQ: 8.0, ISS: 9.0 },
      controlDom: { GCQ: 7.5, timeShare: 0.5 },
      multiCatDom: { threshold: 7.5, count: 3 }
    }
  },
  Regional: {
    name: 'Regional',
    weights: {
      KD: 0.30,
      ISS: 0.20,
      TSR: 0.15,
      GCQ: 0.10,
      TDQ: 0.08,
      OC: 0.06,
      SUBQ: 0.05,
      AGG: 0.05,
      RP: 0.01
    },
    thresholds: {
      draw: 0,
      tenNine: 600,
      tenEight: 900,
      tenSeven: 1000
    },
    gates: {
      finishThreat: { KD: 1, SUBQ: 8.0, ISS: 9.0 },
      controlDom: { GCQ: 7.5, timeShare: 0.5 },
      multiCatDom: { threshold: 7.5, count: 3 }
    }
  }
};

export function getPromotionProfile(org = 'UFC') {
  return PROMOTION_PROFILES[org] || PROMOTION_PROFILES.UFC;
}

// Enhanced Explainability engine
export function generateExplainability(roundScore, events) {
  const bullets = [];
  const flags = [];
  
  // Determine winner and loser
  const winner = roundScore.winner === 'fighter1' ? roundScore.fighter1_score : roundScore.fighter2_score;
  const loser = roundScore.winner === 'fighter1' ? roundScore.fighter2_score : roundScore.fighter1_score;
  const winnerName = roundScore.winner === 'fighter1' ? 'Fighter 1 (Red)' : 'Fighter 2 (Blue)';
  
  // Count specific events for winner
  const winnerEvents = events.filter(e => 
    (roundScore.winner === 'fighter1' && e.fighter === 'fighter1') ||
    (roundScore.winner === 'fighter2' && e.fighter === 'fighter2')
  );
  
  const kdCount = winnerEvents.filter(e => e.eventType === 'KD').length;
  const ssCount = winnerEvents.filter(e => e.eventType?.startsWith('SS')).length;
  const tdCount = winnerEvents.filter(e => e.eventType === 'Takedown').length;
  const subCount = winnerEvents.filter(e => e.eventType === 'Submission Attempt').length;
  const passCount = winnerEvents.filter(e => e.eventType === 'Pass').length;
  const reversalCount = winnerEvents.filter(e => e.eventType === 'Reversal').length;
  
  // Main score explanation
  if (roundScore.reasons.to_107) {
    bullets.push(`🔴 10-7 LEVEL DOMINANCE: Massive ${roundScore.score_gap.toFixed(0)}-point gap (threshold: 900+)`);
    bullets.push(`${winnerName} achieved near-finish level control throughout the round`);
    
    if (roundScore.reasons.gates_winner.finish_threat) {
      if (kdCount > 0) {
        bullets.push(`• ${kdCount} Knockdown${kdCount > 1 ? 's' : ''} with significant damage`);
      }
      if (subCount > 0) {
        bullets.push(`• ${subCount} Deep submission attempt${subCount > 1 ? 's' : ''} threatening finish`);
      }
    }
  } else if (roundScore.reasons.to_108) {
    bullets.push(`🟠 10-8 DOMINANCE: Clear ${roundScore.score_gap.toFixed(0)}-point advantage (threshold: 601-900)`);
    
    if (roundScore.reasons.gates_winner.finish_threat) {
      bullets.push(`• Finish Threat Gate: ${kdCount > 0 ? `${kdCount} KD(s)` : ''} ${subCount > 0 ? `${subCount} SUB(s)` : ''} ${ssCount >= 15 ? `${ssCount} heavy strikes` : ''}`);
    }
    if (roundScore.reasons.gates_winner.multi_cat_dom) {
      const dominantMetrics = Object.entries(winner.subscores)
        .filter(([key, val]) => val >= 7.5)
        .map(([key]) => key);
      bullets.push(`• Multi-Category Dominance: Dominated in ${dominantMetrics.length} metrics (${dominantMetrics.join(', ')})`);
    }
    if (roundScore.reasons.gates_winner.control_dom) {
      bullets.push(`• Control Dominance: ${winner.subscores.GCQ.toFixed(1)} GCQ score (>50% round control)`);
    }
  } else if (roundScore.reasons.draw) {
    bullets.push(`🟡 10-10 DRAW: Even round with ${roundScore.score_gap.toFixed(0)}-point difference (within draw threshold)`);
    bullets.push(`Neither fighter established clear control or damage advantage`);
  } else {
    bullets.push(`🟢 10-9 COMPETITIVE: ${roundScore.score_gap.toFixed(0)}-point edge (threshold: 1-600)`);
    bullets.push(`${winnerName} won the round but opponent remained competitive`);
  }
  
  // Event breakdown for winner
  const eventSummary = [];
  if (kdCount > 0) eventSummary.push(`${kdCount} KD`);
  if (ssCount > 0) eventSummary.push(`${ssCount} SS`);
  if (tdCount > 0) eventSummary.push(`${tdCount} TD`);
  if (subCount > 0) eventSummary.push(`${subCount} SUB`);
  if (passCount > 0) eventSummary.push(`${passCount} Pass`);
  if (reversalCount > 0) eventSummary.push(`${reversalCount} Rev`);
  
  if (eventSummary.length > 0) {
    bullets.push(`📊 Key Events: ${eventSummary.join(', ')}`);
  }
  
  // Top subscore contributors with detailed breakdown
  const topScores = Object.entries(winner.subscores)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  
  bullets.push(`📈 Top Scoring Metrics: ${topScores.map(([key, val]) => `${key} (${val.toFixed(1)}/10)`).join(', ')}`);
  
  // Add loser's best metric to show competitiveness
  const loserBest = Object.entries(loser.subscores)
    .sort((a, b) => b[1] - a[1])[0];
  if (loserBest && loserBest[1] > 5.0) {
    bullets.push(`⚔️ Opponent's Best: ${loserBest[0]} (${loserBest[1].toFixed(1)}/10)`);
  }
  
  // Timestamp markers for key events (for video review)
  const keyEventTimestamps = [];
  if (kdCount > 0) {
    const kdEvents = winnerEvents.filter(e => e.eventType === 'KD');
    kdEvents.forEach(kd => {
      keyEventTimestamps.push(`KD at ${formatTimestamp(kd.timestamp)}`);
    });
  }
  
  if (keyEventTimestamps.length > 0) {
    bullets.push(`🎥 Review Timestamps: ${keyEventTimestamps.join(', ')}`);
  }
  
  // Check for boundary cases (close to threshold)
  const delta = roundScore.score_gap;
  if (Math.abs(delta - 600) < 50) {
    flags.push('boundary_10_9_vs_10_8');
    bullets.push(`⚠️ Boundary Case: Score is ${delta < 600 ? 'just below' : 'just above'} 10-8 threshold`);
  }
  if (Math.abs(delta - 900) < 50) {
    flags.push('boundary_10_8_vs_10_7');
    bullets.push(`⚠️ Boundary Case: Score is ${delta < 900 ? 'just below' : 'just above'} 10-7 threshold`);
  }
  
  // Check for controversial patterns
  if (roundScore.winner !== 'DRAW' && delta < 100 && !roundScore.reasons.to_108) {
    flags.push('very_close_decision');
  }
  
  if (roundScore.reasons.to_108 && !roundScore.reasons.gates_winner.finish_threat && 
      !roundScore.reasons.gates_winner.control_dom && !roundScore.reasons.gates_winner.multi_cat_dom) {
    flags.push('10_8_without_gate');
  }
  
  return {
    bullets,
    flags,
    delta: roundScore.score_gap,
    card: roundScore.card,
    gates: roundScore.reasons,
    eventCounts: { kdCount, ssCount, tdCount, subCount, passCount, reversalCount }
  };
}

// Helper function to format timestamp for video review
function formatTimestamp(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Offline queue manager
export class OfflineQueueManager {
  constructor() {
    this.dbName = 'FightJudgeOfflineDB';
    this.storeName = 'eventQueue';
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, 1);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName, { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }

  async addToQueue(event) {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.add({
        ...event,
        timestamp: Date.now(),
        synced: false
      });
      
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async getQueue() {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.storeName], 'readonly');
      const store = transaction.objectStore(this.storeName);
      const request = store.getAll();
      
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async markAsSynced(id) {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction([this.storeName], 'readwrite');
      const store = transaction.objectStore(this.storeName);
      const request = store.delete(id);
      
      request.onsuccess = () => resolve();
      request.onerror = () => reject(request.error);
    });
  }

  async syncQueue(firebaseDb) {
    const queue = await this.getQueue();
    const results = [];
    
    for (const item of queue) {
      try {
        // Replay to Firestore
        await firebaseDb.collection(item.collection).add(item.data);
        await this.markAsSynced(item.id);
        results.push({ id: item.id, success: true });
      } catch (error) {
        results.push({ id: item.id, success: false, error: error.message });
      }
    }
    
    return results;
  }
}

// Cryptographic signature generator
export async function generateRoundSignature(roundData, judgeProfile) {
  const data = JSON.stringify({
    ...roundData,
    judgeId: judgeProfile.judgeId,
    timestamp: Date.now()
  });
  
  // Generate hash using Web Crypto API
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(data);
  const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  
  return {
    judgeId: judgeProfile.judgeId,
    judgeName: judgeProfile.judgeName,
    deviceId: navigator.userAgent,
    signedHash: hashHex,
    timestamp: Date.now()
  };
}
