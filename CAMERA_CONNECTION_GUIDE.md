# Real Camera Connection Guide
## Connecting Real Cameras to the Real-Time CV System

This guide shows you how to connect actual cameras (IP cameras, webcams, streaming feeds) to the Real-Time CV System for live combat sports analysis.

---

## Table of Contents
1. [IP Camera Connection (RTSP)](#1-ip-camera-connection-rtsp)
2. [Webcam Connection](#2-webcam-connection)
3. [Streaming Feed (RTMP/HLS)](#3-streaming-feed-rtmphls)
4. [Video File Processing](#4-video-file-processing)
5. [Multiple Camera Setup](#5-multiple-camera-setup)
6. [Production Setup](#6-production-setup)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. IP Camera Connection (RTSP)

### What You Need:
- IP camera with RTSP support (most modern IP cameras)
- Camera IP address and credentials
- Network access to the camera

### Step 1: Find Your Camera's RTSP URL

Common RTSP URL formats:
```
rtsp://username:password@camera-ip:554/stream
rtsp://192.168.1.100:554/Streaming/Channels/101
rtsp://admin:password@192.168.1.100:554/h264
```

**How to find it:**
- Check camera manufacturer documentation
- Common ports: 554 (RTSP), 8554 (alternative)
- Test with VLC Media Player: `Media → Open Network Stream`

### Step 2: Configure in the UI

1. Go to **Operator Panel**
2. Find the **Real-Time CV System** section
3. Click **"Show Dashboard"**
4. In the "Start New Video Stream" section:
   - **Camera ID**: `main_camera` (or `corner_red`, `corner_blue`, `overhead`)
   - **Stream Type**: Select `RTSP (IP Camera)`
   - **Stream URL**: Enter your RTSP URL
     ```
     rtsp://admin:password@192.168.1.100:554/stream
     ```
   - **Target FPS**: 30 (or your camera's max FPS)
   - **Analysis FPS**: 10 (analyzes every 3rd frame to save resources)
5. Enable **Pose Estimation** and **Action Detection**
6. Click **"Start Video Stream Analysis"**

### Step 3: Verify Connection

Check the **Active Streams** section to see your camera connected.

---

## 2. Webcam Connection

### Step 1: Enable Webcam Access

For **local webcam** (computer's built-in or USB webcam):

#### Option A: Using Browser (Simple)
```javascript
// The frontend will use browser's MediaStream API
// No URL needed - just use camera ID "0"
```

#### Option B: Backend Processing (Better Performance)
```bash
# Install OpenCV for Python (backend)
pip install opencv-python

# Update backend cv_engine.py to use:
import cv2
cap = cv2.VideoCapture(0)  # 0 for default webcam, 1 for second camera
```

### Step 2: Configure in UI

1. **Camera ID**: `webcam_0`
2. **Stream Type**: `Webcam`
3. **Stream URL**: `0` (for first webcam) or `1` (for second)
4. Click **"Start Video Stream Analysis"**

---

## 3. Streaming Feed (RTMP/HLS)

For **live streams** from platforms like YouTube Live, Twitch, or custom RTMP servers:

### RTMP (Real-Time Messaging Protocol)
```
rtmp://live.example.com/live/stream-key
```

**Example: OBS Studio Output**
```
rtmp://your-server-ip:1935/live/streamkey
```

### HLS (HTTP Live Streaming)
```
http://example.com/live/stream.m3u8
https://cdn.example.com/hls/stream/index.m3u8
```

**Example: YouTube Live**
1. Get your YouTube Live stream URL
2. Use a tool like `youtube-dl` or `yt-dlp` to get the direct stream URL:
   ```bash
   yt-dlp -g "https://www.youtube.com/watch?v=VIDEO_ID"
   ```
3. Use the resulting URL in the CV System

### Configuration in UI:
- **Stream Type**: `RTMP (Streaming)` or `HTTP (Stream URL)`
- **Stream URL**: Your RTMP/HLS URL
- Analysis FPS: 5-10 (lower for internet streams to avoid lag)

---

## 4. Video File Processing

To **analyze recorded video files**:

### Option A: Frame-by-Frame Upload

1. Extract frames from video:
   ```bash
   ffmpeg -i fight_video.mp4 -vf fps=10 frame_%04d.jpg
   ```

2. Use the **Frame Upload** endpoint:
   ```bash
   curl -X POST http://backend-url/api/realtime-cv/frames/analyze/upload \
     -F "bout_id=fight_001" \
     -F "camera_id=main" \
     -F "timestamp_ms=1000" \
     -F "frame_number=1" \
     -F "frame_file=@frame_0001.jpg"
   ```

### Option B: Video Stream Processing

1. Serve the video file as a stream:
   ```bash
   ffmpeg -re -i fight_video.mp4 -f rtsp rtsp://localhost:8554/video
   ```

2. Connect to the stream URL: `rtsp://localhost:8554/video`

---

## 5. Multiple Camera Setup

For **multi-camera fight analysis** (recommended for professional events):

### Typical Setup:
- **Main Camera**: Wide angle of the ring/cage
- **Corner Red**: Close-up of red corner fighter
- **Corner Blue**: Close-up of blue corner fighter  
- **Overhead**: Top-down view for ground game

### Configuration:

**Start 4 separate streams:**

```javascript
// Camera 1: Main
{
  "bout_id": "ufc_301_main",
  "camera_id": "main_camera",
  "stream_url": "rtsp://192.168.1.100:554/stream"
}

// Camera 2: Red Corner
{
  "bout_id": "ufc_301_main",
  "camera_id": "corner_red",
  "stream_url": "rtsp://192.168.1.101:554/stream"
}

// Camera 3: Blue Corner
{
  "bout_id": "ufc_301_main",
  "camera_id": "corner_blue",
  "stream_url": "rtsp://192.168.1.102:554/stream"
}

// Camera 4: Overhead
{
  "bout_id": "ufc_301_main",
  "camera_id": "overhead",
  "stream_url": "rtsp://192.168.1.103:554/stream"
}
```

**Benefits:**
- Multiple angles for better detection accuracy
- Redundancy if one camera fails
- Different views for different action types (strikes vs ground game)

---

## 6. Production Setup

### Hardware Requirements:

**For Real-Time Analysis:**
- **CPU**: 8+ cores (for parallel frame processing)
- **GPU**: NVIDIA GPU with CUDA support (highly recommended)
  - RTX 3060 or better
  - Enables MediaPipe and YOLO acceleration
- **RAM**: 16GB minimum, 32GB recommended
- **Network**: Gigabit Ethernet for multiple cameras

### Software Setup:

#### Install GPU Acceleration (Ubuntu/Linux):

```bash
# Install NVIDIA drivers
sudo apt install nvidia-driver-535

# Install CUDA Toolkit
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub
sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /"
sudo apt update
sudo apt install cuda

# Install Python packages with GPU support
pip install tensorflow-gpu  # For custom models
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### Install OpenCV with CUDA:

```bash
# Build OpenCV with CUDA support
git clone https://github.com/opencv/opencv.git
cd opencv
mkdir build && cd build
cmake -D CMAKE_BUILD_TYPE=RELEASE \
      -D CMAKE_INSTALL_PREFIX=/usr/local \
      -D WITH_CUDA=ON \
      -D WITH_CUDNN=ON \
      -D OPENCV_DNN_CUDA=ON \
      ..
make -j8
sudo make install
```

### Network Configuration:

For **IP cameras on local network:**

```bash
# Ensure cameras are on the same subnet
# Example network: 192.168.1.0/24
# Backend server: 192.168.1.10
# Camera 1: 192.168.1.100
# Camera 2: 192.168.1.101
# Camera 3: 192.168.1.102

# Test camera connectivity
ping 192.168.1.100

# Test RTSP stream
ffplay rtsp://192.168.1.100:554/stream
```

### Performance Optimization:

**Backend Configuration** (`/app/backend/realtime_cv/cv_engine.py`):

```python
# Adjust these parameters based on your hardware:

# Frame Processing
analysis_fps = 10  # Lower = less CPU usage, slower detection
                    # Higher = more CPU usage, faster detection
                    
# Model Configuration
use_gpu = True  # Enable GPU acceleration
batch_size = 4  # Process multiple frames at once (GPU only)

# Detection Thresholds
confidence_threshold = 0.65  # Lower = more detections (more false positives)
                             # Higher = fewer detections (more accurate)
```

---

## 7. Troubleshooting

### Issue: "Failed to start stream"

**Possible causes:**
1. **Incorrect URL format**
   - Double-check RTSP URL
   - Verify username/password
   - Try without auth: `rtsp://camera-ip:554/stream`

2. **Network issues**
   ```bash
   # Test connectivity
   ping camera-ip
   
   # Test RTSP port
   telnet camera-ip 554
   ```

3. **Camera not responding**
   - Reboot the camera
   - Check camera's web interface
   - Verify stream is active

### Issue: "No detections found"

**Possible causes:**
1. **Poor video quality**
   - Increase camera resolution
   - Improve lighting
   - Reduce motion blur

2. **Wrong camera angle**
   - Ensure full view of fighters
   - Avoid extreme angles
   - Check for obstructions

3. **Low confidence threshold**
   ```python
   # Adjust in cv_engine.py
   confidence_threshold = 0.5  # Lower to get more detections
   ```

### Issue: "High CPU usage / Lag"

**Solutions:**
1. **Lower Analysis FPS**
   - Change from 10 FPS to 5 FPS
   - Analyzes fewer frames = less processing

2. **Reduce stream quality**
   ```bash
   # Transcode stream to lower resolution
   ffmpeg -i rtsp://camera-ip:554/stream -vf scale=1280:720 -f rtsp rtsp://localhost:8554/lowres
   ```

3. **Use GPU acceleration** (see Production Setup above)

### Issue: "Stream keeps disconnecting"

**Solutions:**
1. **Network stability**
   - Use wired connection instead of WiFi
   - Check for packet loss: `ping camera-ip -t`

2. **Camera timeout settings**
   - Increase timeout in camera settings
   - Enable keep-alive packets

3. **Add reconnection logic** (automatically handled by the system)

---

## Testing Your Setup

### Quick Test Checklist:

✅ **1. Test stream URL with VLC Player**
```bash
vlc rtsp://your-camera-url
```

✅ **2. Verify network connectivity**
```bash
ping camera-ip
telnet camera-ip 554
```

✅ **3. Start stream in UI**
- Should see "Stream started: {stream_id}"
- Check "Active Streams" section

✅ **4. Verify detections**
- Simulate frames OR
- Let real stream run for 30 seconds
- Check "Recent Detections" section
- Should see actions like "punch_thrown", "kick_thrown"

✅ **5. Check statistics**
- Total detections > 0
- Average confidence > 65%
- Action breakdown shows variety

---

## API Examples

### Start Multiple Cameras Programmatically:

```bash
# Start Main Camera
curl -X POST http://backend-url/api/realtime-cv/streams/start \
  -H "Content-Type: application/json" \
  -d '{
    "bout_id": "ufc_301_main",
    "camera_id": "main_camera",
    "stream_url": "rtsp://192.168.1.100:554/stream",
    "stream_type": "rtsp",
    "fps_target": 30,
    "analysis_fps": 10,
    "enable_pose_estimation": true,
    "enable_action_detection": true
  }'

# Start Red Corner Camera
curl -X POST http://backend-url/api/realtime-cv/streams/start \
  -H "Content-Type: application/json" \
  -d '{
    "bout_id": "ufc_301_main",
    "camera_id": "corner_red",
    "stream_url": "rtsp://192.168.1.101:554/stream",
    "stream_type": "rtsp",
    "fps_target": 30,
    "analysis_fps": 10,
    "enable_pose_estimation": true,
    "enable_action_detection": true
  }'
```

### Get All Active Streams:

```bash
curl http://backend-url/api/realtime-cv/streams/active
```

### Get Detections:

```bash
# All detections
curl http://backend-url/api/realtime-cv/detections/ufc_301_main

# Filtered by action type
curl "http://backend-url/api/realtime-cv/detections/ufc_301_main?action_type=strike_landed&limit=50"
```

### Stop All Streams:

```bash
# Get stream IDs
STREAMS=$(curl -s http://backend-url/api/realtime-cv/streams/active | jq -r '.active_streams[].stream_id')

# Stop each
for STREAM_ID in $STREAMS; do
  curl -X POST http://backend-url/api/realtime-cv/streams/stop/$STREAM_ID
done
```

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend logs: `tail -f /var/log/supervisor/backend.err.log`
3. Test camera connectivity independently
4. Verify all prerequisites are installed

**Common Camera Brands & Default URLs:**
- **Hikvision**: `rtsp://admin:password@ip:554/Streaming/Channels/101`
- **Dahua**: `rtsp://admin:password@ip:554/cam/realmonitor?channel=1&subtype=0`
- **Axis**: `rtsp://ip:554/axis-media/media.amp`
- **Foscam**: `rtsp://ip:554/videoMain`
- **Amcrest**: `rtsp://admin:password@ip:554/cam/realmonitor?channel=1&subtype=1`

---

**🎯 You're now ready to connect real cameras to your professional CV system!**
