import { db } from '@/firebase';
import firebase from 'firebase/compat/app';

/**
 * Device Synchronization Manager
 * Handles multi-device presence, real-time sync, and conflict resolution
 */

class DeviceSyncManager {
  constructor() {
    this.deviceId = null;
    this.listeners = [];
    this.presenceRef = null;
  }

  /**
   * Initialize device presence and sync
   */
  async initializeDevice(boutId, deviceType = 'judge', metadata = {}) {
    // Generate unique device ID
    this.deviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const deviceData = {
      deviceId: this.deviceId,
      boutId,
      deviceType, // 'judge', 'operator', 'broadcast'
      ...metadata,
      status: 'online',
      lastHeartbeat: firebase.firestore.FieldValue.serverTimestamp(),
      connectedAt: firebase.firestore.FieldValue.serverTimestamp()
    };

    // Create device presence document
    this.presenceRef = db.collection('device_presence').doc(this.deviceId);
    await this.presenceRef.set(deviceData);

    // Set up heartbeat (every 5 seconds)
    this.heartbeatInterval = setInterval(() => {
      this.presenceRef.update({
        lastHeartbeat: firebase.firestore.FieldValue.serverTimestamp(),
        status: 'online'
      }).catch(err => console.error('Heartbeat error:', err));
    }, 5000);

    // Handle disconnect
    this.presenceRef.onDisconnect().update({
      status: 'offline',
      disconnectedAt: firebase.firestore.FieldValue.serverTimestamp()
    });

    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
      this.cleanup();
    });

    return this.deviceId;
  }

  /**
   * Get all active devices for a bout
   */
  listenToActiveDevices(boutId, callback) {
    const unsubscribe = db.collection('device_presence')
      .where('boutId', '==', boutId)
      .where('status', '==', 'online')
      .onSnapshot((snapshot) => {
        const devices = [];
        const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;

        snapshot.docs.forEach(doc => {
          const data = doc.data();
          const lastHeartbeat = data.lastHeartbeat?.toMillis() || 0;
          
          // Only include devices with recent heartbeat
          if (lastHeartbeat > fiveMinutesAgo) {
            devices.push({
              id: doc.id,
              ...data,
              isCurrentDevice: doc.id === this.deviceId
            });
          }
        });

        callback(devices);
      });

    this.listeners.push(unsubscribe);
    return unsubscribe;
  }

  /**
   * Sync data across all devices
   */
  broadcastUpdate(collection, documentId, data) {
    return db.collection(collection).doc(documentId).set(data, { merge: true });
  }

  /**
   * Listen for real-time updates from other devices
   */
  listenToCollection(collection, query, callback) {
    let ref = db.collection(collection);
    
    // Apply query filters
    if (query) {
      Object.keys(query).forEach(key => {
        ref = ref.where(key, '==', query[key]);
      });
    }

    const unsubscribe = ref.onSnapshot(
      (snapshot) => {
        const updates = [];
        snapshot.docChanges().forEach((change) => {
          updates.push({
            type: change.type, // 'added', 'modified', 'removed'
            id: change.doc.id,
            data: change.doc.data(),
            fromCurrentDevice: change.doc.data().deviceId === this.deviceId
          });
        });
        callback(updates);
      },
      (error) => {
        console.error('Sync listener error:', error);
      }
    );

    this.listeners.push(unsubscribe);
    return unsubscribe;
  }

  /**
   * Update device metadata
   */
  updateDeviceMetadata(metadata) {
    if (this.presenceRef) {
      return this.presenceRef.update({
        ...metadata,
        lastHeartbeat: firebase.firestore.FieldValue.serverTimestamp()
      });
    }
  }

  /**
   * Clean up device presence
   */
  async cleanup() {
    // Clear heartbeat
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    // Remove all listeners
    this.listeners.forEach(unsubscribe => {
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    });
    this.listeners = [];

    // Mark device as offline
    if (this.presenceRef) {
      try {
        await this.presenceRef.update({
          status: 'offline',
          disconnectedAt: firebase.firestore.FieldValue.serverTimestamp()
        });
      } catch (err) {
        console.error('Cleanup error:', err);
      }
    }
  }

  /**
   * Get current device ID
   */
  getDeviceId() {
    return this.deviceId;
  }
}

// Singleton instance
const deviceSyncManager = new DeviceSyncManager();

export default deviceSyncManager;
