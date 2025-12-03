# ProctGuard - Enhanced Online Proctoring System with YOLO Integration

A comprehensive online proctoring system that provides real-time monitoring of test-takers using advanced AI technologies including YOLO object detection, MediaPipe computer vision, and audio analysis.

## 🆕 Recent Enhancements

**NEW: YOLO Integration** - The system has been enhanced with YOLOv11s object detection for superior accuracy in detecting persons, phones, and prohibited materials.

## Features

### 🔍 Advanced Detection Capabilities
- **YOLO Object Detection**: Enhanced detection of persons, phones, and books using YOLOv11s
- **Face Detection**: Real-time face monitoring using MediaPipe
- **Head Pose Analysis**: Suspicious head movement detection
- **Multiple Person Detection**: Alerts when multiple people are detected
- **Phone Detection**: Advanced detection of mobile devices using YOLO
- **Book Detection**: Identification of prohibited reading materials
- **Audio Monitoring**: Framework for detecting multiple voices and background noise

### For Students:
- **Secure Test Interface**: Clean, distraction-free test environment
- **Real-time Monitoring**: Enhanced AI-powered detection system
- **Violation Alerts**: Immediate feedback when monitoring issues are detected
- **Progress Tracking**: Visual progress indicator and timer

### For Administrators:
- **Live Monitoring Dashboard**: Real-time view of active test sessions with enhanced AI detection
- **Cheating Score Analysis**: AI-powered probability scoring based on violations
- **Evidence Review**: Screenshot capture of violations with YOLO detection annotations
- **Test Management**: Create and manage tests with multiple-choice questions
- **Detailed Reports**: Comprehensive session reports with enhanced violation logs

### Enhanced Monitoring Capabilities:
- **YOLO-Powered Object Detection**: Superior accuracy in detecting prohibited items
- **Face Detection**: Ensures student identity and presence using MediaPipe
- **Advanced Phone Detection**: YOLO-based mobile device identification
- **Multiple Person Detection**: AI-enhanced detection of additional people
- **Book Detection**: YOLO-based identification of reading materials
- **Audio Monitoring**: Detects conversations and suspicious audio patterns
- **Tab Switching**: Logs when students navigate away from the test
- **Head Pose Analysis**: Tracks suspicious head movements with MediaPipe

## Installation

### Prerequisites
- Python 3.12 or higher (recommended for YOLO support)
- Webcam and microphone access
- Modern web browser with WebRTC support (Chrome, Firefox, Safari)
- Adequate system resources for AI model inference

### Setup Instructions

1. **Clone or Download the Project**
   ```bash
   cd C:\Users\sudba\OneDrive\Desktop\Project\Proctoring_system\ProctGuard
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # macOS/Linux
   ```

3. **Install Dependencies** (Updated with YOLO support)
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database**
   The database will be automatically created when you first run the application.

5. **Run the Application**
   ```bash
   python app.py
   ```

6. **Access the System**
   - Open your browser and go to: `http://localhost:5000`
   - Use the role selection page to access either:
     - **Student Portal**: Take tests with AI-powered monitoring
     - **Admin Dashboard**: Manage tests and review AI-enhanced results

### Quick Start (Windows)
Simply double-click `run.bat` to automatically set up and start the enhanced system.

## Enhanced Detection System

### YOLO Integration Benefits
1. **Improved Accuracy**: Higher precision in object detection compared to traditional methods
2. **Real-Time Performance**: Fast inference suitable for live monitoring
3. **Robust Detection**: Better handling of various lighting conditions and angles
4. **Extensible**: Easy to add detection for new object classes

### Detection Thresholds (Enhanced)
- **Person Detection**: Confidence > 0.3, 10 consecutive frames (YOLO-powered)
- **Phone Detection**: Confidence > 0.5, 15 consecutive frames (YOLO-powered)
- **Book Detection**: Confidence > 0.4, 10 consecutive frames (YOLO-powered)
- **Face Lost**: 30 consecutive frames without face detection (MediaPipe)
- **Multiple Faces**: 5 consecutive frames with multiple faces (MediaPipe)

### Violation Types and Severity
- **HIGH Severity**: Multiple persons, phone detected, no person detected
- **MEDIUM Severity**: Suspicious head movement, book detected
- **LOW Severity**: Face temporarily lost

## Technical Architecture (Enhanced)

### Backend Technologies:
- **Flask 2.3.3**: Web framework with enhanced real-time capabilities
- **Flask-SocketIO 5.3.6**: Real-time communication (threading mode)
- **OpenCV 4.8.1.78**: Computer vision processing
- **MediaPipe 0.10.21**: Face and pose detection
- **Ultralytics YOLO**: Advanced object detection (YOLOv11s)
- **SQLite Database**: Enhanced data storage with violation evidence

### AI/ML Components:
- **YOLOv11s Model**: Pre-trained object detection model (yolo11s.pt)
- **MediaPipe Face Detection**: Google's face detection solution
- **MediaPipe Pose**: Body pose estimation for head tracking
- **Custom Violation Logic**: Intelligent threshold-based detection

### Frontend Components:
- **Bootstrap 5**: Responsive, modern interface
- **JavaScript**: Enhanced real-time monitoring and WebSocket communication
- **WebRTC**: Browser media access for monitoring
- **Custom CSS**: Enhanced styling for AI monitoring interface

### Database Schema (Enhanced):
- **tests**: Test definitions and questions
- **test_sessions**: Student test attempts with AI-powered scoring
- **cheating_logs**: Detailed violation records with YOLO detection evidence

## Configuration (Enhanced)

### YOLO Detection Settings:
```python
PERSON_CONFIDENCE_THRESHOLD = 0.3
PHONE_CONFIDENCE_THRESHOLD = 0.5
BOOK_CONFIDENCE_THRESHOLD = 0.4
PERSON_DETECTION_FRAMES = 10
PHONE_DETECTION_FRAMES = 15
BOOK_DETECTION_FRAMES = 10
```

### Camera Settings:
- Resolution: 640x480 (optimized for YOLO inference)
- Frame rate: 30 FPS
- Format: Compatible with OpenCV and YOLO processing

### Performance Optimization:
- **YOLO Model**: YOLOv11s for optimal speed/accuracy balance
- **Frame Processing**: Efficient multi-threaded processing
- **Memory Management**: Optimized for continuous operation

## Testing and Validation

### Automated Testing
Run the included YOLO integration test:
```bash
python test_yolo_integration.py
```

Expected output:
```
✓ YOLO Detection Function: PASS
✓ ProctGuard Integration: PASS
✓ All tests passed! YOLO integration is working correctly.
```

## Development Notes (Enhanced)

### File Structure:
```
ProctGuard/
├── app.py                          # Main Flask application (enhanced)
├── requirements.txt                # Updated dependencies with YOLO
├── test_yolo_integration.py       # YOLO integration test
├── run.bat                        # Windows startup script
├── models/
│   ├── database.py               # Enhanced database operations
│   ├── object_detection.py       # YOLO detection implementation
│   └── yolo11s.pt               # Pre-trained YOLO model
├── detection/
│   └── proctoring_monitor.py     # Enhanced monitoring with YOLO
├── templates/                     # Enhanced HTML templates
├── static/
│   ├── css/                      # Enhanced styling
│   ├── js/                       # Enhanced monitoring scripts
│   └── uploads/evidence/         # YOLO-annotated evidence storage
└── README.md                     # This enhanced documentation
```

### Adding New YOLO Classes:
1. Update the YOLO model with new object classes
2. Modify `detectObject` function in `object_detection.py`
3. Add new violation types in `proctoring_monitor.py`
4. Update UI to display new violation types

### Performance Monitoring:
- Monitor system resources during AI inference
- Adjust detection thresholds based on hardware capabilities
- Optimize frame processing pipeline for specific use cases

## System Status: ✅ FULLY OPERATIONAL

**Current Version**: Enhanced with YOLO Integration (v2.0)  
**Last Updated**: November 29, 2024  
**AI Models**: YOLOv11s + MediaPipe  
**Test Results**: All integration tests passing  
**Dependencies**: Successfully installed and configured  

The ProctGuard system is now ready for production use with state-of-the-art AI-powered monitoring capabilities.

## License

This is a prototype/demonstration project enhanced with AI capabilities. Please ensure compliance with privacy laws and institutional policies when implementing proctoring systems.

## Support

This enhanced system includes comprehensive AI integration. For production deployment, additional considerations for model optimization, hardware requirements, and privacy compliance may be necessary.