import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { getEventMapping, POSITIONS, formatEventForLogging } from '@/utils/redragonKeyMap';
import syncManager from '@/utils/syncManager';

/**
 * Enhanced Event Logger Hook
 * 
 * Provides REDRAGON key mapping with position/target/source fields
 * Ensures exactly one event per key press with zero duplicates
 */
export function useEnhancedEventLogger(boutId, bout, selectedFighter, controlTimers) {
  const [position, setPosition] = useState(POSITIONS.DISTANCE);
  const [lastEventKey, setLastEventKey] = useState(null);
  const [eventInProgress, setEventInProgress] = useState(false);
  
  // Debounce to prevent duplicate events
  const DEBOUNCE_MS = 300;
  
  /**
   * Log event with position, target, and source
   */
  const logEnhancedEvent = useCallback(async (eventType, options = {}) => {
    // Prevent duplicate submissions
    if (eventInProgress) {
      console.log('[EventLogger] Event already in progress, skipping');
      return;
    }
    
    try {
      setEventInProgress(true);
      
      // Guard: Check if bout is loaded
      if (!bout) {
        toast.error('Please wait for bout to load');
        return;
      }
      
      // Get current control time for the selected fighter
      const currentTime = controlTimers[selectedFighter].time;
      
      // Prepare event data
      const eventData = {
        fighter: selectedFighter,
        event_type: eventType,
        timestamp: currentTime,
        position: options.position || position,
        target: options.target || null,
        source: options.source || 'judge_software',
        metadata: {
          ...options.metadata,
          significant: options.significant !== undefined ? options.significant : false
        }
      };
      
      // Use syncManager for offline-first event logging
      const result = await syncManager.addEvent(boutId, bout.currentRound, eventData);
      
      const fighterName = selectedFighter === 'fighter1' ? bout.fighter1 : bout.fighter2;
      const modeIndicator = result.mode === 'offline' ? ' (saved locally)' : '';
      
      // Success toast with position indicator
      const positionBadge = eventData.position ? `[${eventData.position.toUpperCase()}]` : '';
      const targetBadge = eventData.target ? ` → ${eventData.target}` : '';
      
      toast.success(`${positionBadge} ${eventType}${targetBadge} for ${fighterName}${modeIndicator}`);
      
      return result;
      
    } catch (error) {
      console.error('Error logging enhanced event:', error);
      toast.error('Failed to log event');
    } finally {
      // Release lock after debounce period
      setTimeout(() => {
        setEventInProgress(false);
      }, DEBOUNCE_MS);
    }
  }, [bout, boutId, selectedFighter, controlTimers, position, eventInProgress]);
  
  /**
   * Handle REDRAGON key press
   */
  const handleRedragonKey = useCallback(async (key) => {
    // Prevent duplicate events from same key
    if (lastEventKey === key) {
      console.log('[EventLogger] Duplicate key detected, skipping:', key);
      return;
    }
    
    // Get event mapping
    const mapping = getEventMapping(key, position);
    
    if (!mapping) {
      console.log('[EventLogger] No mapping found for key:', key, 'position:', position);
      return;
    }
    
    // Set last event key
    setLastEventKey(key);
    setTimeout(() => setLastEventKey(null), DEBOUNCE_MS);
    
    // Check if this event requires a dialog
    if (mapping.requiresDialog) {
      console.log('[EventLogger] Event requires dialog:', mapping.event_type);
      // Return mapping so parent can handle dialog
      return { requiresDialog: true, mapping };
    }
    
    // Log event
    await logEnhancedEvent(mapping.event_type, {
      position: mapping.position,
      target: mapping.target,
      source: mapping.source,
      significant: mapping.significant,
      metadata: {
        key: mapping.key
      }
    });
    
  }, [position, lastEventKey, logEnhancedEvent]);
  
  /**
   * Switch position mode
   */
  const switchPosition = useCallback((newPosition) => {
    setPosition(newPosition);
    toast.info(`Switched to ${newPosition.toUpperCase()} mode`);
  }, []);
  
  /**
   * Cycle position (Distance → Clinch → Ground → Distance)
   */
  const cyclePosition = useCallback(() => {
    const positions = [POSITIONS.DISTANCE, POSITIONS.CLINCH, POSITIONS.GROUND];
    const currentIndex = positions.indexOf(position);
    const nextIndex = (currentIndex + 1) % positions.length;
    switchPosition(positions[nextIndex]);
  }, [position, switchPosition]);
  
  return {
    position,
    setPosition: switchPosition,
    cyclePosition,
    logEnhancedEvent,
    handleRedragonKey,
    eventInProgress
  };
}

/**
 * Position Mode Switcher UI Component
 */
export function PositionModeSwitcher({ position, onPositionChange }) {
  const positions = [
    { value: POSITIONS.DISTANCE, label: 'Distance', color: 'bg-blue-500', icon: '↔️' },
    { value: POSITIONS.CLINCH, label: 'Clinch', color: 'bg-orange-500', icon: '🤼' },
    { value: POSITIONS.GROUND, label: 'Ground', color: 'bg-green-500', icon: '⬇️' }
  ];
  
  return (
    <div className="flex items-center gap-2 p-3 bg-gray-800 rounded-lg border border-gray-700">
      <div className="text-sm font-medium text-gray-300 mr-2">Position Mode:</div>
      {positions.map(pos => (
        <button
          key={pos.value}
          onClick={() => onPositionChange(pos.value)}
          className={`
            px-4 py-2 rounded-lg font-semibold transition-all
            ${position === pos.value 
              ? `${pos.color} text-white scale-105 shadow-lg` 
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }
          `}
        >
          <span className="mr-2">{pos.icon}</span>
          {pos.label}
        </button>
      ))}
      <div className="ml-4 text-xs text-gray-400">
        Press <kbd className="px-2 py-1 bg-gray-700 rounded">Tab</kbd> to cycle
      </div>
    </div>
  );
}

/**
 * Event Logging Status Indicator
 */
export function EventLoggerStatus({ position, eventInProgress, isOnline, queueCount }) {
  return (
    <div className="flex items-center gap-4 p-2 bg-gray-900 rounded-lg border border-gray-700">
      {/* Position Indicator */}
      <div className="flex items-center gap-2">
        <div className={`
          w-3 h-3 rounded-full
          ${position === POSITIONS.DISTANCE ? 'bg-blue-500' : ''}
          ${position === POSITIONS.CLINCH ? 'bg-orange-500' : ''}
          ${position === POSITIONS.GROUND ? 'bg-green-500' : ''}
        `}></div>
        <span className="text-sm font-medium text-gray-300">
          {position.toUpperCase()}
        </span>
      </div>
      
      {/* Event Status */}
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${eventInProgress ? 'bg-yellow-500 animate-pulse' : 'bg-gray-600'}`}></div>
        <span className="text-xs text-gray-400">
          {eventInProgress ? 'Logging...' : 'Ready'}
        </span>
      </div>
      
      {/* Online Status */}
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}></div>
        <span className="text-xs text-gray-400">
          {isOnline ? 'Online' : 'Offline'}
        </span>
      </div>
      
      {/* Queue Count */}
      {queueCount > 0 && (
        <div className="px-2 py-1 bg-orange-900 rounded text-xs text-orange-200">
          {queueCount} queued
        </div>
      )}
    </div>
  );
}

export default { useEnhancedEventLogger, PositionModeSwitcher, EventLoggerStatus };
