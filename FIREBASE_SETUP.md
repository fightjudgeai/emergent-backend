# Firebase Firestore Setup Instructions

## Critical: Configure Firestore Security Rules

The application requires Firestore write permissions. Please follow these steps:

### 1. Go to Firebase Console
Visit: https://console.firebase.google.com/project/fight-judge-a-i-pro-y2jutw/firestore

### 2. Navigate to Firestore Database
- Click on "Firestore Database" in the left sidebar
- Click on the "Rules" tab

### 3. Update Security Rules

Replace the existing rules with the following:

```
rules_version = '2';

service cloud.firestore {
  match /databases/{database}/documents {
    
    // Allow read/write access to bouts collection
    match /bouts/{boutId} {
      allow read, write: if true;
    }
    
    // Allow read/write access to events collection
    match /events/{eventId} {
      allow read, write: if true;
    }
    
    // Allow read/write access to confirmedRounds collection
    match /confirmedRounds/{roundId} {
      allow read, write: if true;
    }
    
    // Keep existing status_checks for testing
    match /status_checks/{checkId} {
      allow read, write: if true;
    }
  }
}
```

### 4. Publish the Rules
- Click the "Publish" button to save and activate the rules

### 5. Alternative: Test Mode (Development Only)
For quick testing, you can temporarily enable "Test mode" which allows all reads and writes:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if true;
    }
  }
}
```

⚠️ **Warning**: Test mode allows unrestricted access. Use production rules for deployed applications.

## Collections Used

1. **bouts** - Stores bout information (fighters, rounds, status)
2. **events** - Logs all fight events in real-time (KD, ISS, takedowns, etc.)
3. **confirmedRounds** - Stores confirmed round scores

## After Setup

Once the security rules are configured, the application will work as expected:
- ✅ Create bouts
- ✅ Log events in operator panel
- ✅ View real-time scores in judge panel
- ✅ Confirm rounds
