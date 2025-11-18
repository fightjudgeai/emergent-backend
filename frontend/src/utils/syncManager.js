/**
 * Sync Manager for handling online/offline event synchronization
 * Enhanced with retry logic, network monitoring, and queue health metrics
 */

import offlineDB from './offlineDB';
import { db } from '@/firebase';

class SyncManager {
  constructor() {
    this.isOnline = navigator.onLine;
    this.isSyncing = false;
    this.listeners = [];
    this.retryTimer = null;
    this.maxRetries = 5;
    this.baseRetryDelay = 2000; // 2 seconds base delay
    this.networkCheckInterval = null;
    
    // Setup online/offline listeners
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());
    
    // Start periodic network quality checks
    this.startNetworkMonitoring();
  }

  /**
   * Start periodic network quality monitoring
   */
  startNetworkMonitoring() {
    // Check network every 30 seconds
    this.networkCheckInterval = setInterval(async () => {
      await this.checkNetworkQuality();
    }, 30000);
  }

  /**
   * Check network quality and connection
   */
  async checkNetworkQuality() {
    try {
      const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      
      const quality = {
        online: navigator.onLine,
        effectiveType: connection?.effectiveType || 'unknown',
        downlink: connection?.downlink || 'unknown',
        rtt: connection?.rtt || 'unknown',
        saveData: connection?.saveData || false
      };
      
      this.notifyListeners({ type: 'networkQuality', quality });
      
      // Auto-trigger sync if online and queue has items
      if (quality.online && !this.isSyncing) {
        const queueCount = await offlineDB.getQueueCount();
        if (queueCount > 0) {
          console.log(`Network available with ${queueCount} queued events - auto-syncing`);
          await this.syncAll();
        }
      }
      
      return quality;
    } catch (error) {
      console.error('Network quality check failed:', error);
      return null;
    }
  }

  /**
   * Handle coming online
   */
  async handleOnline() {
    console.log('Connection restored - initiating sync');
    this.isOnline = true;
    this.notifyListeners({ type: 'online' });
    
    // Clear any pending retry timers
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    
    // Check network quality before syncing
    await this.checkNetworkQuality();
    await this.syncAll();
  }

  /**
   * Handle going offline
   */
  handleOffline() {
    console.log('Connection lost - entering offline mode');
    this.isOnline = false;
    this.notifyListeners({ type: 'offline' });
    
    // Schedule retry attempts with exponential backoff
    this.scheduleRetrySync(1);
  }

  /**
   * Schedule retry sync with exponential backoff
   */
  scheduleRetrySync(attempt) {
    if (attempt > this.maxRetries) {
      console.log('Max retry attempts reached');
      return;
    }
    
    // Exponential backoff: 2s, 4s, 8s, 16s, 32s
    const delay = this.baseRetryDelay * Math.pow(2, attempt - 1);
    
    console.log(`Scheduling sync retry #${attempt} in ${delay}ms`);
    
    this.retryTimer = setTimeout(async () => {
      if (!this.isOnline) {
        // Check if connection is back
        const isActuallyOnline = navigator.onLine;
        if (isActuallyOnline) {
          await this.handleOnline();
        } else {
          this.scheduleRetrySync(attempt + 1);
        }
      }
    }, delay);
  }

  /**
   * Add event (online or offline)
   */
  async addEvent(boutId, roundNum, eventData) {
    if (this.isOnline) {
      try {
        // Write to flat events collection (matching JudgePanel read structure)
        // Use eventType field name to match JudgePanel expectations
        await db.collection('events').add({
          boutId,
          round: roundNum,
          fighter: eventData.fighter,
          eventType: eventData.event_type,
          timestamp: eventData.timestamp,
          metadata: eventData.metadata || {},
          createdAt: new Date().toISOString()
        });
        
        console.log('Event added to Firebase directly');
        return { success: true, mode: 'online' };
      } catch (error) {
        console.error('Failed to add to Firebase, queuing offline:', error);
        // Fall back to offline queue
        this.isOnline = false; // Network might be down
      }
    }

    // Add to offline queue
    await offlineDB.addToQueue({
      boutId,
      roundNum,
      ...eventData
    });
    
    this.notifyListeners({ type: 'queued', count: await offlineDB.getQueueCount() });
    return { success: true, mode: 'offline' };
  }

  /**
   * Delete event (for undo functionality)
   */
  async deleteEvent(eventId) {
    try {
      // Try to delete from offline DB first
      await offlineDB.removeFromQueue(eventId);
      console.log('Event removed from offline queue:', eventId);
      return { success: true };
    } catch (error) {
      console.warn('Event not in offline queue or already synced:', error);
      throw error;
    }
  }

  /**
   * Sync all queued events with enhanced retry logic
   */
  async syncAll() {
    if (this.isSyncing) {
      console.log('Sync already in progress');
      return { success: false, message: 'Sync in progress' };
    }

    if (!this.isOnline) {
      console.log('Cannot sync while offline');
      return { success: false, message: 'Offline' };
    }

    this.isSyncing = true;
    this.notifyListeners({ type: 'syncing' });

    try {
      const unsyncedEvents = await offlineDB.getUnsyncedEvents();
      
      if (unsyncedEvents.length === 0) {
        console.log('No events to sync');
        this.isSyncing = false;
        this.notifyListeners({ type: 'synced', count: 0 });
        return { success: true, count: 0 };
      }

      console.log(`Syncing ${unsyncedEvents.length} queued events`);
      let syncedCount = 0;
      let failedCount = 0;
      const failedEvents = [];

      for (const event of unsyncedEvents) {
        try {
          // Add to flat events collection (matching JudgePanel structure)
          // Use eventType field name to match what JudgePanel reads
          await db.collection('events').add({
            boutId: event.boutId,
            round: event.roundNum,
            fighter: event.fighter,
            eventType: event.event_type,
            timestamp: event.timestamp,
            metadata: event.metadata || {},
            createdAt: new Date().toISOString()
          });

          // Mark as synced and reset retry count
          await offlineDB.markAsSynced(event.id);
          syncedCount++;
        } catch (error) {
          console.error(`Failed to sync event ${event.id}:`, error);
          
          // Increment retry count for this event
          await offlineDB.incrementRetryCount(event.id);
          failedCount++;
          failedEvents.push({
            id: event.id,
            error: error.message,
            retryCount: event.retryCount + 1
          });
        }
      }

      // Log sync
      if (syncedCount > 0) {
        await offlineDB.logSync('batch', syncedCount);
        
        // Cleanup old synced events (optional - keep last 100)
        await offlineDB.deleteSyncedEvents();
      }

      this.isSyncing = false;
      
      const result = {
        type: 'syncComplete', 
        synced: syncedCount, 
        failed: failedCount,
        remaining: await offlineDB.getQueueCount(),
        failedEvents: failedEvents
      };
      
      this.notifyListeners(result);

      console.log(`Sync complete: ${syncedCount} synced, ${failedCount} failed`);
      
      // Schedule retry for failed events if any
      if (failedCount > 0 && this.isOnline) {
        console.log(`Scheduling retry for ${failedCount} failed events`);
        this.scheduleRetrySync(1);
      }
      
      return { success: true, synced: syncedCount, failed: failedCount, failedEvents };
    } catch (error) {
      console.error('Sync error:', error);
      this.isSyncing = false;
      this.notifyListeners({ type: 'syncError', error });
      
      // Schedule retry on error
      this.scheduleRetrySync(1);
      
      return { success: false, error: error.message };
    }
  }

  /**
   * Get queue health metrics
   */
  async getQueueHealthMetrics() {
    try {
      const queueStats = await offlineDB.getQueueStats();
      const syncHistory = await offlineDB.getRecentSyncHistory(10);
      const networkQuality = await this.checkNetworkQuality();
      
      return {
        queueStats,
        syncHistory,
        networkQuality,
        isHealthy: queueStats.failedEvents === 0 && this.isOnline
      };
    } catch (error) {
      console.error('Failed to get queue health metrics:', error);
      return null;
    }
  }

  /**
   * Get current status with enhanced metrics
   */
  async getStatus() {
    return {
      isOnline: this.isOnline,
      isSyncing: this.isSyncing,
      queueCount: await offlineDB.getQueueCount(),
      healthMetrics: await this.getQueueHealthMetrics()
    };
  }

  /**
   * Force clear failed events (emergency recovery)
   */
  async clearFailedEvents() {
    try {
      await offlineDB.clearFailedEvents();
      this.notifyListeners({ type: 'failedEventsCleared' });
      return { success: true };
    } catch (error) {
      console.error('Failed to clear failed events:', error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Add status listener
   */
  addListener(callback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }

  /**
   * Notify all listeners
   */
  notifyListeners(status) {
    this.listeners.forEach(callback => callback(status));
  }

  /**
   * Manual sync trigger
   */
  async manualSync() {
    return await this.syncAll();
  }

  /**
   * Cleanup - call this when component unmounts
   */
  cleanup() {
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
    }
    if (this.networkCheckInterval) {
      clearInterval(this.networkCheckInterval);
    }
  }
}

// Create singleton instance
const syncManager = new SyncManager();

export default syncManager;
