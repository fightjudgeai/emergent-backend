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

// Explainability engine
export function generateExplainability(roundScore, events) {
  const bullets = [];
  const flags = [];
  
  // Check why 10-8 or 10-7
  if (roundScore.reasons.to_107) {
    bullets.push(`10-7 Dominance: Score gap ${roundScore.score_gap.toFixed(0)} points (>900)`);
    
    if (roundScore.reasons.gates_winner.finish_threat) {
      const kdEvents = events.filter(e => e.eventType === 'KD');
      if (kdEvents.length > 0) {
        bullets.push(`Knockdowns: ${kdEvents.length}x (Finish Threat)`);
      }
    }
  } else if (roundScore.reasons.to_108) {
    bullets.push(`10-8 Dominance: Score gap ${roundScore.score_gap.toFixed(0)} points (601-900)`);
    
    if (roundScore.reasons.gates_winner.finish_threat) {
      bullets.push('Finish Threat gate triggered');
    }
    if (roundScore.reasons.gates_winner.multi_cat_dom) {
      bullets.push('Multi-Category Dominance (3+ metrics ≥7.5)');
    }
    if (roundScore.reasons.gates_winner.control_dom) {
      bullets.push('Control Dominance (>50% control time)');
    }
  } else {
    bullets.push(`10-9 Close Round: Score gap ${roundScore.score_gap.toFixed(0)} points (<600)`);
  }
  
  // Add top subscore contributors
  const winner = roundScore.winner === 'fighter1' ? roundScore.fighter1_score : roundScore.fighter2_score;
  const topScores = Object.entries(winner.subscores)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  
  bullets.push(`Top metrics: ${topScores.map(([key, val]) => `${key}(${val.toFixed(1)})`).join(', ')}`);
  
  // Check for boundary cases
  const delta = roundScore.score_gap;
  if (Math.abs(delta - 600) < 50) {
    flags.push('boundary_case_10_9_10_8');
  }
  if (Math.abs(delta - 900) < 50) {
    flags.push('boundary_case_10_8_10_7');
  }
  
  // Check for discrepancies (would need official card to compare)
  // This would be populated post-event
  
  return {
    bullets,
    flags,
    delta: roundScore.score_gap,
    card: roundScore.card,
    gates: roundScore.reasons
  };
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
