/**
 * REDRAGON Key Mapping System
 * 
 * Maps physical keyboard keys to fight events with position and target metadata.
 * Supports three position modes: distance, clinch, ground
 */

// Position modes
export const POSITIONS = {
  DISTANCE: 'distance',
  CLINCH: 'clinch',
  GROUND: 'ground'
};

// Strike targets
export const TARGETS = {
  HEAD: 'head',
  BODY: 'body',
  LEG: 'leg'
};

// Event source
export const SOURCE = {
  JUDGE_SOFTWARE: 'judge_software',
  STAT_OPERATOR: 'stat_operator',
  AI_CV: 'ai_cv',
  HYBRID: 'hybrid'
};

/**
 * REDRAGON KEY MAP
 * 
 * Structure: {
 *   key: {
 *     distance: { event_type, target, significant },
 *     clinch: { event_type, target, significant },
 *     ground: { event_type, target, significant }
 *   }
 * }
 */
export const REDRAGON_KEY_MAP = {
  // =========================================================================
  // NUMBER ROW - HEAD STRIKES (Significant with Shift)
  // =========================================================================
  
  // 1/! - Jab Head
  '1': {
    distance: { event_type: 'Jab', target: TARGETS.HEAD, significant: false },
    clinch: { event_type: 'Jab', target: TARGETS.HEAD, significant: false },
    ground: { event_type: 'Cross', target: TARGETS.HEAD, significant: false }
  },
  '!': {
    distance: { event_type: 'Jab', target: TARGETS.HEAD, significant: true },
    clinch: { event_type: 'Jab', target: TARGETS.HEAD, significant: true },
    ground: { event_type: 'Cross', target: TARGETS.HEAD, significant: true }
  },
  
  // 2/@ - Cross Head
  '2': {
    distance: { event_type: 'Cross', target: TARGETS.HEAD, significant: false },
    clinch: { event_type: 'Cross', target: TARGETS.HEAD, significant: false },
    ground: { event_type: 'Hook', target: TARGETS.HEAD, significant: false }
  },
  '@': {
    distance: { event_type: 'Cross', target: TARGETS.HEAD, significant: true },
    clinch: { event_type: 'Cross', target: TARGETS.HEAD, significant: true },
    ground: { event_type: 'Hook', target: TARGETS.HEAD, significant: true }
  },
  
  // 3/# - Hook Head
  '3': {
    distance: { event_type: 'Hook', target: TARGETS.HEAD, significant: false },
    clinch: { event_type: 'Hook', target: TARGETS.HEAD, significant: false },
    ground: { event_type: 'Uppercut', target: TARGETS.HEAD, significant: false }
  },
  '#': {
    distance: { event_type: 'Hook', target: TARGETS.HEAD, significant: true },
    clinch: { event_type: 'Hook', target: TARGETS.HEAD, significant: true },
    ground: { event_type: 'Uppercut', target: TARGETS.HEAD, significant: true }
  },
  
  // 4/$ - Uppercut Head
  '4': {
    distance: { event_type: 'Uppercut', target: TARGETS.HEAD, significant: false },
    clinch: { event_type: 'Uppercut', target: TARGETS.HEAD, significant: false },
    ground: { event_type: 'Elbow', target: TARGETS.HEAD, significant: false }
  },
  '$': {
    distance: { event_type: 'Uppercut', target: TARGETS.HEAD, significant: true },
    clinch: { event_type: 'Uppercut', target: TARGETS.HEAD, significant: true },
    ground: { event_type: 'Elbow', target: TARGETS.HEAD, significant: true }
  },
  
  // 5/% - Elbow Head
  '5': {
    distance: { event_type: 'Elbow', target: TARGETS.HEAD, significant: false },
    clinch: { event_type: 'Elbow', target: TARGETS.HEAD, significant: false },
    ground: { event_type: 'Elbow', target: TARGETS.HEAD, significant: false }
  },
  '%': {
    distance: { event_type: 'Elbow', target: TARGETS.HEAD, significant: true },
    clinch: { event_type: 'Elbow', target: TARGETS.HEAD, significant: true },
    ground: { event_type: 'Elbow', target: TARGETS.HEAD, significant: true }
  },
  
  // 6/^ - Knee Head
  '6': {
    distance: { event_type: 'Knee', target: TARGETS.HEAD, significant: false },
    clinch: { event_type: 'Knee', target: TARGETS.HEAD, significant: false },
    ground: { event_type: 'Knee', target: TARGETS.BODY, significant: false }
  },
  '^': {
    distance: { event_type: 'Knee', target: TARGETS.HEAD, significant: true },
    clinch: { event_type: 'Knee', target: TARGETS.HEAD, significant: true },
    ground: { event_type: 'Knee', target: TARGETS.BODY, significant: true }
  },
  
  // =========================================================================
  // Q-W-E ROW - BODY STRIKES
  // =========================================================================
  
  // Q - Jab Body
  'q': {
    distance: { event_type: 'Jab', target: TARGETS.BODY, significant: false },
    clinch: { event_type: 'Jab', target: TARGETS.BODY, significant: false },
    ground: { event_type: 'Cross', target: TARGETS.BODY, significant: false }
  },
  'Q': {
    distance: { event_type: 'Jab', target: TARGETS.BODY, significant: true },
    clinch: { event_type: 'Jab', target: TARGETS.BODY, significant: true },
    ground: { event_type: 'Cross', target: TARGETS.BODY, significant: true }
  },
  
  // W - Cross Body
  'w': {
    distance: { event_type: 'Cross', target: TARGETS.BODY, significant: false },
    clinch: { event_type: 'Cross', target: TARGETS.BODY, significant: false },
    ground: { event_type: 'Hook', target: TARGETS.BODY, significant: false }
  },
  'W': {
    distance: { event_type: 'Cross', target: TARGETS.BODY, significant: true },
    clinch: { event_type: 'Cross', target: TARGETS.BODY, significant: true },
    ground: { event_type: 'Hook', target: TARGETS.BODY, significant: true }
  },
  
  // E - Hook Body
  'e': {
    distance: { event_type: 'Hook', target: TARGETS.BODY, significant: false },
    clinch: { event_type: 'Hook', target: TARGETS.BODY, significant: false },
    ground: { event_type: 'Uppercut', target: TARGETS.BODY, significant: false }
  },
  'E': {
    distance: { event_type: 'Hook', target: TARGETS.BODY, significant: true },
    clinch: { event_type: 'Hook', target: TARGETS.BODY, significant: true },
    ground: { event_type: 'Uppercut', target: TARGETS.BODY, significant: true }
  },
  
  // R - Uppercut Body
  'r': {
    distance: { event_type: 'Uppercut', target: TARGETS.BODY, significant: false },
    clinch: { event_type: 'Uppercut', target: TARGETS.BODY, significant: false },
    ground: { event_type: 'Elbow', target: TARGETS.BODY, significant: false }
  },
  'R': {
    distance: { event_type: 'Uppercut', target: TARGETS.BODY, significant: true },
    clinch: { event_type: 'Uppercut', target: TARGETS.BODY, significant: true },
    ground: { event_type: 'Elbow', target: TARGETS.BODY, significant: true }
  },
  
  // T - Knee Body
  't': {
    distance: { event_type: 'Knee', target: TARGETS.BODY, significant: false },
    clinch: { event_type: 'Knee', target: TARGETS.BODY, significant: false },
    ground: { event_type: 'Knee', target: TARGETS.BODY, significant: false }
  },
  'T': {
    distance: { event_type: 'Knee', target: TARGETS.BODY, significant: true },
    clinch: { event_type: 'Knee', target: TARGETS.BODY, significant: true },
    ground: { event_type: 'Knee', target: TARGETS.BODY, significant: true }
  },
  
  // =========================================================================
  // A-S-D ROW - LEG STRIKES & KICKS
  // =========================================================================
  
  // A - Low Kick
  'a': {
    distance: { event_type: 'Low Kick', target: TARGETS.LEG, significant: false },
    clinch: { event_type: 'Low Kick', target: TARGETS.LEG, significant: false },
    ground: { event_type: 'Kick', target: TARGETS.LEG, significant: false }
  },
  'A': {
    distance: { event_type: 'Low Kick', target: TARGETS.LEG, significant: true },
    clinch: { event_type: 'Low Kick', target: TARGETS.LEG, significant: true },
    ground: { event_type: 'Kick', target: TARGETS.LEG, significant: true }
  },
  
  // S - Body Kick
  's': {
    distance: { event_type: 'Body Kick', target: TARGETS.BODY, significant: false },
    clinch: { event_type: 'Body Kick', target: TARGETS.BODY, significant: false },
    ground: { event_type: 'Kick', target: TARGETS.BODY, significant: false }
  },
  'S': {
    distance: { event_type: 'Body Kick', target: TARGETS.BODY, significant: true },
    clinch: { event_type: 'Body Kick', target: TARGETS.BODY, significant: true },
    ground: { event_type: 'Kick', target: TARGETS.BODY, significant: true }
  },
  
  // D - Head Kick
  'd': {
    distance: { event_type: 'Head Kick', target: TARGETS.HEAD, significant: false },
    clinch: { event_type: 'Head Kick', target: TARGETS.HEAD, significant: false },
    ground: { event_type: 'Kick', target: TARGETS.HEAD, significant: false }
  },
  'D': {
    distance: { event_type: 'Head Kick', target: TARGETS.HEAD, significant: true },
    clinch: { event_type: 'Head Kick', target: TARGETS.HEAD, significant: true },
    ground: { event_type: 'Kick', target: TARGETS.HEAD, significant: true }
  },
  
  // F - Front Kick
  'f': {
    distance: { event_type: 'Front Kick', target: TARGETS.BODY, significant: false },
    clinch: { event_type: 'Front Kick', target: TARGETS.BODY, significant: false },
    ground: { event_type: 'Kick', target: TARGETS.BODY, significant: false }
  },
  'F': {
    distance: { event_type: 'Front Kick', target: TARGETS.BODY, significant: true },
    clinch: { event_type: 'Front Kick', target: TARGETS.BODY, significant: true },
    ground: { event_type: 'Kick', target: TARGETS.BODY, significant: true }
  },
  
  // =========================================================================
  // Z-X-C ROW - POWER STRIKES & DAMAGE
  // =========================================================================
  
  // Z - Spinning Strike
  'z': {
    distance: { event_type: 'Spinning Strike', target: TARGETS.HEAD, significant: true },
    clinch: { event_type: 'Elbow', target: TARGETS.HEAD, significant: true },
    ground: { event_type: 'Elbow', target: TARGETS.HEAD, significant: true }
  },
  
  // X - Rocked/Stunned
  'x': {
    distance: { event_type: 'Rocked/Stunned', target: TARGETS.HEAD, significant: true },
    clinch: { event_type: 'Rocked/Stunned', target: TARGETS.HEAD, significant: true },
    ground: { event_type: 'Rocked/Stunned', target: TARGETS.HEAD, significant: true }
  },
  
  // C - Knockdown (opens dialog)
  'c': {
    distance: { event_type: 'KD', target: TARGETS.HEAD, significant: true, requiresDialog: true },
    clinch: { event_type: 'KD', target: TARGETS.HEAD, significant: true, requiresDialog: true },
    ground: { event_type: 'KD', target: TARGETS.HEAD, significant: true, requiresDialog: true }
  },
  
  // =========================================================================
  // GRAPPLING & CONTROL (V-B-N keys)
  // =========================================================================
  
  // V - Takedown Landed
  'v': {
    distance: { event_type: 'Takedown Landed', target: null, position: POSITIONS.GROUND },
    clinch: { event_type: 'Takedown Landed', target: null, position: POSITIONS.GROUND },
    ground: { event_type: 'Sweep/Reversal', target: null, position: POSITIONS.GROUND }
  },
  
  // B - Takedown Stuffed
  'b': {
    distance: { event_type: 'Takedown Stuffed', target: null },
    clinch: { event_type: 'Takedown Stuffed', target: null },
    ground: { event_type: 'Submission Attempt', target: null, requiresDialog: true }
  },
  
  // N - Submission Attempt (opens dialog)
  'n': {
    distance: { event_type: 'Submission Attempt', target: null, requiresDialog: true },
    clinch: { event_type: 'Submission Attempt', target: null, requiresDialog: true },
    ground: { event_type: 'Submission Attempt', target: null, requiresDialog: true }
  }
};

/**
 * Get event mapping for a key press
 * 
 * @param {string} key - The pressed key
 * @param {string} position - Current position mode (distance/clinch/ground)
 * @returns {Object|null} Event mapping or null if not found
 */
export function getEventMapping(key, position) {
  const keyMap = REDRAGON_KEY_MAP[key];
  
  if (!keyMap) {
    return null;
  }
  
  const positionMap = keyMap[position];
  
  if (!positionMap) {
    return null;
  }
  
  return {
    ...positionMap,
    source: SOURCE.JUDGE_SOFTWARE,
    position: positionMap.position || position,
    key: key  // Include original key for debugging
  };
}

/**
 * Check if a key is mapped
 */
export function isKeyMapped(key) {
  return key in REDRAGON_KEY_MAP;
}

/**
 * Get all mapped keys (for documentation/help)
 */
export function getAllMappedKeys() {
  return Object.keys(REDRAGON_KEY_MAP);
}

/**
 * Format event for logging
 * 
 * @param {Object} mapping - Event mapping from getEventMapping
 * @param {string} fighter - Fighter identifier
 * @param {number} timestamp - Current fight time
 * @returns {Object} Formatted event ready for logging
 */
export function formatEventForLogging(mapping, fighter, timestamp) {
  return {
    fighter: fighter,
    event_type: mapping.event_type,
    timestamp: timestamp,
    position: mapping.position,
    target: mapping.target,
    source: mapping.source,
    metadata: {
      significant: mapping.significant || false,
      key: mapping.key  // For debugging
    }
  };
}
