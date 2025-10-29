/**
 * Sync Manager for handling online/offline event synchronization
 */

import offlineDB from './offlineDB';
import { db } from '@/firebase';

class SyncManager {
  constructor() {
    this.isOnline = navigator.onLine;
    this.isSyncing = false;
    this.listeners = [];
    
    // Setup online/offline listeners
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());
  }

  /**
   * Handle coming online
   */
  async handleOnline() {
    console.log('Connection restored - initiating sync');
    this.isOnline = true;
    this.notifyListeners({ type: 'online' });
    await this.syncAll();
  }

  /**
   * Handle going offline
   */
  handleOffline() {
    console.log('Connection lost - entering offline mode');
    this.isOnline = false;
    this.notifyListeners({ type: 'offline' });
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
   * Sync all queued events
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

      for (const event of unsyncedEvents) {
        try {
          // Add to flat events collection (matching JudgePanel structure)
          await db.collection('events').add({
            boutId: event.boutId,
            round: event.roundNum,
            fighter: event.fighter,
            event_type: event.event_type,
            timestamp: event.timestamp,
            metadata: event.metadata || {},
            createdAt: new Date().toISOString()
          });

          // Mark as synced
          await offlineDB.markAsSynced(event.id);
          syncedCount++;
        } catch (error) {
          console.error(`Failed to sync event ${event.id}:`, error);
          failedCount++;
        }
      }

      // Log sync
      if (syncedCount > 0) {
        await offlineDB.logSync('batch', syncedCount);
        
        // Cleanup old synced events (optional - keep last 100)
        await offlineDB.deleteSyncedEvents();
      }

      this.isSyncing = false;
      this.notifyListeners({ 
        type: 'syncComplete', 
        synced: syncedCount, 
        failed: failedCount,
        remaining: await offlineDB.getQueueCount()
      });

      console.log(`Sync complete: ${syncedCount} synced, ${failedCount} failed`);
      return { success: true, synced: syncedCount, failed: failedCount };
    } catch (error) {
      console.error('Sync error:', error);
      this.isSyncing = false;
      this.notifyListeners({ type: 'syncError', error });
      return { success: false, error: error.message };
    }
  }

  /**
   * Get current status
   */
  async getStatus() {
    return {
      isOnline: this.isOnline,
      isSyncing: this.isSyncing,
      queueCount: await offlineDB.getQueueCount()
    };
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
}

// Create singleton instance
const syncManager = new SyncManager();

export default syncManager;
