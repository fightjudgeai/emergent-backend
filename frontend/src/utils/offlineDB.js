/**
 * IndexedDB wrapper for offline event storage and sync
 */

const DB_NAME = 'CombatJudgingOfflineDB';
const DB_VERSION = 1;
const EVENT_QUEUE_STORE = 'event_queue';
const SYNC_LOG_STORE = 'sync_log';

class OfflineDB {
  constructor() {
    this.db = null;
  }

  /**
   * Initialize IndexedDB
   */
  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        console.error('Failed to open IndexedDB:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        console.log('IndexedDB initialized successfully');
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Create event queue store
        if (!db.objectStoreNames.contains(EVENT_QUEUE_STORE)) {
          const eventStore = db.createObjectStore(EVENT_QUEUE_STORE, {
            keyPath: 'id',
            autoIncrement: true
          });
          eventStore.createIndex('boutId', 'boutId', { unique: false });
          eventStore.createIndex('timestamp', 'timestamp', { unique: false });
          eventStore.createIndex('synced', 'synced', { unique: false });
        }

        // Create sync log store
        if (!db.objectStoreNames.contains(SYNC_LOG_STORE)) {
          const syncStore = db.createObjectStore(SYNC_LOG_STORE, {
            keyPath: 'id',
            autoIncrement: true
          });
          syncStore.createIndex('syncedAt', 'syncedAt', { unique: false });
        }
      };
    });
  }

  /**
   * Add event to queue
   */
  async addToQueue(eventData) {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([EVENT_QUEUE_STORE], 'readwrite');
      const store = transaction.objectStore(EVENT_QUEUE_STORE);

      const queueItem = {
        ...eventData,
        synced: false,
        queuedAt: new Date().toISOString(),
        retryCount: 0
      };

      const request = store.add(queueItem);

      request.onsuccess = () => {
        console.log('Event added to offline queue:', request.result);
        resolve(request.result);
      };

      request.onerror = () => {
        console.error('Failed to add event to queue:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Get all unsynced events
   */
  async getUnsyncedEvents() {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([EVENT_QUEUE_STORE], 'readonly');
      const store = transaction.objectStore(EVENT_QUEUE_STORE);
      const request = store.getAll();

      request.onsuccess = () => {
        // Filter for unsynced events in JavaScript instead of using index
        const unsyncedEvents = request.result.filter(event => event.synced === false);
        resolve(unsyncedEvents);
      };

      request.onerror = () => {
        console.error('Failed to get unsynced events:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Mark event as synced
   */
  async markAsSynced(eventId) {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([EVENT_QUEUE_STORE], 'readwrite');
      const store = transaction.objectStore(EVENT_QUEUE_STORE);
      const request = store.get(eventId);

      request.onsuccess = () => {
        const event = request.result;
        if (event) {
          event.synced = true;
          event.syncedAt = new Date().toISOString();
          const updateRequest = store.put(event);

          updateRequest.onsuccess = () => {
            resolve(true);
          };

          updateRequest.onerror = () => {
            reject(updateRequest.error);
          };
        } else {
          resolve(false);
        }
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  /**
   * Delete synced events (cleanup)
   */
  async deleteSyncedEvents() {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([EVENT_QUEUE_STORE], 'readwrite');
      const store = transaction.objectStore(EVENT_QUEUE_STORE);
      const index = store.index('synced');
      const request = index.openCursor(IDBKeyRange.only(true)); // Get synced events

      let deletedCount = 0;

      request.onsuccess = (event) => {
        const cursor = event.target.result;
        if (cursor) {
          cursor.delete();
          deletedCount++;
          cursor.continue();
        } else {
          console.log(`Deleted ${deletedCount} synced events from queue`);
          resolve(deletedCount);
        }
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  /**
   * Get queue count
   */
  async getQueueCount() {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([EVENT_QUEUE_STORE], 'readonly');
      const store = transaction.objectStore(EVENT_QUEUE_STORE);
      const request = store.getAll();

      request.onsuccess = () => {
        // Count unsynced events in JavaScript instead of using index
        const unsyncedCount = request.result.filter(event => event.synced === false).length;
        resolve(unsyncedCount);
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  /**
   * Log successful sync
   */
  async logSync(boutId, eventCount) {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db.transaction([SYNC_LOG_STORE], 'readwrite');
      const store = transaction.objectStore(SYNC_LOG_STORE);

      const logEntry = {
        boutId,
        eventCount,
        syncedAt: new Date().toISOString()
      };

      const request = store.add(logEntry);

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(request.error);
      };
    });
  }

  /**
   * Clear all data (for testing/reset)
   */
  async clearAll() {
    if (!this.db) await this.init();

    const stores = [EVENT_QUEUE_STORE, SYNC_LOG_STORE];
    
    for (const storeName of stores) {
      await new Promise((resolve, reject) => {
        const transaction = this.db.transaction([storeName], 'readwrite');
        const store = transaction.objectStore(storeName);
        const request = store.clear();

        request.onsuccess = () => resolve();
        request.onerror = () => reject(request.error);
      });
    }

    console.log('All offline data cleared');
  }
}

// Create singleton instance
const offlineDB = new OfflineDB();

export default offlineDB;
