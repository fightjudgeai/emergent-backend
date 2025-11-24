# Complete Real-Time CV System User Guide
## Professional Combat Sports Video Analysis

---

## 🎯 Quick Start

### What is the Real-Time CV System?

A professional-grade computer vision system that analyzes live video feeds from combat sports events to automatically detect:
- **Strikes** (punches, kicks, knees, elbows)
- **Takedowns** and takedown attempts
- **Clinch engagements**
- **Submissions** and submission attempts
- **Fighter poses** and movements (33 keypoint tracking)
- **Power estimation** and velocity analysis

---

## 📍 How to Access

### In the Operator Panel:

1. **Login** to your judge account
2. **Create an event** (fighter names, rounds)
3. **Complete Pre-Flight Checklist**
4. Scroll down to find the **"Real-Time CV System"** panel (purple/pink gradient)

You'll see:
- **Active Streams**: Number of connected cameras
- **Loaded Models**: MediaPipe, YOLO, Custom Action (3 models)
- **Total Detections**: Number of actions detected
- **"Simulate CV Detection"** button (for testing without cameras)
- **"Show Dashboard"** button (opens full management interface)

---

## 🎮 Using the System (3 Ways)

### Method 1: Quick Test (No Camera Required)

**Perfect for testing the system:**

1. Click **"Simulate CV Detection"** button
2. System will simulate 10 frames of video analysis
3. You'll see a popup: "Simulated 10 frames: X detections found"
4. Detections appear in the **"Recent Detections"** section below
5. Each detection shows:
   - Action type (punch, kick, etc.)
   - Fighter ID
   - Confidence percentage
   - Power rating (⚡ symbol)

**What's happening:**
- Backend analyzes simulated video frames
- MediaPipe detects fighter poses
- YOLO identifies actions
- System logs detections with confidence scores

---

### Method 2: Connect Real Cameras (Professional Setup)

**For live events with actual camera feeds:**

1. Click **"Show Dashboard"** to open CV Management Dashboard
2. In the **"Start New Video Stream"** section, configure:

   **Camera Settings:**
   - **Camera ID**: `main_camera`, `corner_red`, `corner_blue`, or `overhead`
   - **Stream Type**: Select your camera type
     - `RTSP (IP Camera)` - Most professional cameras
     - `RTMP (Streaming)` - Live streaming platforms
     - `HTTP (Stream URL)` - Web-based streams
     - `Webcam` - Computer's built-in camera

   **Stream URL Examples:**
   ```
   RTSP: rtsp://192.168.1.100:554/stream
   RTMP: rtmp://live.example.com/live/stream-key
   HTTP: http://camera-url/stream.m3u8
   Webcam: 0 (for first webcam)
   ```

   **Performance Settings:**
   - **Target FPS**: 30 (camera's frame rate)
   - **Analysis FPS**: 10 (analyze every 3rd frame)
     - Lower = less CPU usage
     - Higher = more detections, higher accuracy

   **Enable Features:**
   - ✅ **Pose Estimation** (track fighter movements)
   - ✅ **Action Detection** (detect strikes, takedowns)

3. Click **"Start Video Stream Analysis"**
4. Stream appears in **"Active Streams"** section
5. Detections start appearing automatically

**To Stop:**
- Find your stream in "Active Streams"
- Click the red **"Stop"** button

---

### Method 3: Upload Video Frames

**For analyzing recorded fights or specific moments:**

Use the API directly:
```bash
curl -X POST http://backend-url/api/realtime-cv/frames/analyze/upload \
  -F "bout_id=fight_001" \
  -F "camera_id=main" \
  -F "timestamp_ms=1000" \
  -F "frame_number=1" \
  -F "frame_file=@your_frame.jpg"
```

---

## 📊 Understanding the Dashboard

### CV Management Dashboard Features:

#### 1. **Stream Configuration Panel**
- Start new video streams
- Configure camera settings
- Enable/disable CV features

#### 2. **Loaded CV Models** (3 models)

**MediaPipe Pose:**
- Framework: MediaPipe
- Type: Pose estimation
- Function: Tracks 33 body keypoints per fighter
- Inference time: ~15ms
- Accuracy: 85%

**YOLOv8:**
- Framework: YOLO
- Type: Object detection
- Function: Identifies fighters and equipment
- Inference time: ~25ms
- Accuracy: 80%

**Custom Action Recognition:**
- Framework: Custom
- Type: Action recognition
- Function: Classifies combat actions
- Inference time: ~30ms
- Status: Training (placeholder for now)

#### 3. **Detection Statistics**
- **Total Detections**: All actions detected
- **Average Confidence**: Detection accuracy (aim for >65%)
- **Action Breakdown**: Count by type
  - punch_thrown
  - kick_thrown
  - knee_thrown
  - takedown_attempt
  - strike_landed
  - clinch_engaged
  - submission_attempt
  - block
  - slip

#### 4. **Recent Detections Feed**
- Last 10 detected actions
- Color-coded by type
- Shows fighter, confidence, power rating

---

## 🎥 Multiple Camera Setup

**For professional events, use 4 cameras:**

### Recommended Setup:

1. **Main Camera** (Wide Angle)
   - Position: Cage-side, elevated
   - Purpose: Full view of action
   - Stream ID: `main_camera`

2. **Red Corner Camera**
   - Position: Close-up on red corner fighter
   - Purpose: Detailed strike analysis
   - Stream ID: `corner_red`

3. **Blue Corner Camera**
   - Position: Close-up on blue corner fighter
   - Purpose: Detailed strike analysis
   - Stream ID: `corner_blue`

4. **Overhead Camera**
   - Position: Above the cage
   - Purpose: Ground game analysis
   - Stream ID: `overhead`

### Benefits:
- Multiple angles = higher accuracy
- Redundancy if one camera fails
- Different views for different action types

### How to Set Up:

1. Click **"Show Dashboard"** 4 times (once per camera)
2. Configure each camera with different:
   - Camera ID
   - Stream URL
3. Start all 4 streams
4. System automatically fuses detections from all cameras

---

## 📈 Detection Quality

### What Makes Good Detections:

✅ **Confidence > 65%** - Reliable detection
⚠️ **Confidence 50-65%** - Possible detection, verify
❌ **Confidence < 50%** - Likely false positive

### Factors Affecting Quality:

**Good:**
- Bright, even lighting
- Clear view of fighters
- 1080p or higher resolution
- 30 FPS video
- Stable camera position

**Bad:**
- Dim lighting or shadows
- Obstructed view
- Low resolution (<720p)
- Low frame rate (<20 FPS)
- Shaky camera

---

## 🔧 Common Use Cases

### Use Case 1: Live Event Scoring
**Goal:** Assist judges with real-time strike detection

1. Set up 2-4 cameras around the cage
2. Start all streams before the fight
3. System detects strikes automatically
4. Judges can reference CV detections alongside manual scoring
5. Stop streams after the fight

### Use Case 2: Fighter Analysis
**Goal:** Analyze fighter performance post-fight

1. Upload fight video or connect to recording
2. Let system analyze entire fight
3. Review detection statistics:
   - Total strikes thrown
   - Strike accuracy
   - Power distribution
   - Action patterns
4. Export data for fighter training

### Use Case 3: Replay Review
**Goal:** Verify close calls or controversial moments

1. Upload specific fight moments as frames
2. Analyze frame-by-frame
3. Review detections with confidence scores
4. Use for official scoring disputes

---

## 🚀 Performance Tips

### For Best Results:

**Camera Setup:**
- Use 1080p resolution minimum
- 30 FPS for smooth analysis
- Wired network connection (not WiFi)
- Direct line of sight to fighters

**System Configuration:**
- Lower Analysis FPS if CPU usage is high
- Use GPU acceleration for real-time analysis (see CAMERA_CONNECTION_GUIDE.md)
- Start streams before fighters enter (warm-up period)

**Network:**
- Gigabit Ethernet for multiple cameras
- Local network (same subnet as backend)
- Low latency (<50ms ping to cameras)

---

## 📊 Data & Statistics

### What You Can Track:

**Per Fight:**
- Total detections by action type
- Average confidence
- Detections per fighter
- Power distribution

**Per Round:**
- Action counts (strikes, takedowns, etc.)
- Dominant fighter (by detection count)
- Action intensity (detections per minute)

**Per Fighter:**
- Strike accuracy
- Power levels
- Action patterns
- Ground vs stand-up time

### Accessing Data:

**Via UI:**
- View in "Recent Detections"
- Check "Detection Statistics"

**Via API:**
```bash
# Get all detections
curl http://backend-url/api/realtime-cv/detections/bout_id

# Get statistics
curl http://backend-url/api/realtime-cv/stats/bout_id

# Filter by action type
curl "http://backend-url/api/realtime-cv/detections/bout_id?action_type=strike_landed"
```

---

## 🎓 Training Data Collection

### Build Your Own CV Models:

The system includes a **Data Collection System** for training custom models:

**Available Datasets** (pre-configured):
1. UFC Fight Video Dataset
2. MMA Action Recognition
3. Combat Sports Pose Estimation
4. Fight Detection Dataset
5. OpenPose Combat Sports

**How to Use:**

Via API:
```bash
# List available datasets
curl http://backend-url/api/cv-data/datasets

# Download a dataset
curl -X POST http://backend-url/api/cv-data/datasets/github_combat_dataset_1/download

# Process dataset (train/val/test split)
curl -X POST http://backend-url/api/cv-data/datasets/github_combat_dataset_1/process

# Get collection statistics
curl http://backend-url/api/cv-data/stats
```

**Next Steps:**
- Collected data can be used to train custom action recognition models
- Fine-tune existing models for specific fight styles
- Improve detection accuracy over time

---

## 🆘 Troubleshooting

### Problem: "No detections appearing"

**Solutions:**
1. Check camera connection
2. Verify stream is active (check "Active Streams")
3. Ensure good lighting and clear view
4. Lower confidence threshold in backend
5. Try "Simulate CV Detection" to test system

### Problem: "Stream won't start"

**Solutions:**
1. Verify stream URL format
2. Test URL in VLC Player first
3. Check network connectivity (`ping camera-ip`)
4. Verify camera credentials
5. See CAMERA_CONNECTION_GUIDE.md

### Problem: "Too many false detections"

**Solutions:**
1. Increase confidence threshold
2. Improve camera angle
3. Better lighting
4. Use higher resolution camera
5. Filter detections by confidence in UI

### Problem: "System is slow/laggy"

**Solutions:**
1. Lower Analysis FPS (10 → 5)
2. Reduce number of cameras
3. Use GPU acceleration
4. Lower camera resolution (1080p → 720p)
5. Check CPU usage on backend server

---

## 🔗 Related Documentation

- **CAMERA_CONNECTION_GUIDE.md** - Detailed camera setup instructions
- **Backend API Documentation** - Full API reference
- **test_realtime_cv.py** - API usage examples

---

## 💡 Pro Tips

1. **Test Before Live Events**
   - Use "Simulate CV Detection" to verify system
   - Test camera connections 1 hour before event
   - Have backup cameras ready

2. **Optimize for Your Hardware**
   - Adjust Analysis FPS based on CPU
   - Use GPU for multiple cameras
   - Monitor backend logs for performance

3. **Review Detections Post-Fight**
   - Export detection data
   - Analyze patterns
   - Train custom models over time

4. **Combine with Manual Scoring**
   - CV is an assist, not a replacement
   - Use for strike counting
   - Verify close calls
   - Reference during scoring disputes

5. **Start Simple**
   - Begin with 1 camera
   - Test with simulations
   - Add more cameras as you get comfortable
   - Build confidence in the system

---

## ✅ Quick Checklist

Before a live event:

- [ ] Cameras connected and tested
- [ ] Stream URLs configured correctly
- [ ] Network connection stable (wired recommended)
- [ ] Backend server running
- [ ] GPU acceleration enabled (if available)
- [ ] Test streams started and detections appearing
- [ ] Backup camera(s) ready
- [ ] Confidence threshold set appropriately
- [ ] Storage space available for detections

---

**🥊 You're ready to use professional CV analysis for combat sports!**

For technical support, check backend logs:
```bash
tail -f /var/log/supervisor/backend.err.log
```
