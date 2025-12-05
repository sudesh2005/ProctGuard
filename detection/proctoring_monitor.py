import cv2
import mediapipe as mp
import numpy as np
import base64
from datetime import datetime
import os
import uuid
from models.database import get_db_connection
from models.object_detection import detectObject

class ProctoringMonitor:
    def __init__(self, session_id, storage_mode='disk'):
        self.session_id = session_id
        # storage_mode determines whether evidence is saved to 'disk' or 'db'
        self.storage_mode = storage_mode
        
        # Initialize MediaPipe for face detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        # Tracking variables for violations
        self.face_lost_frames = 0
        self.multiple_faces_frames = 0
        self.phone_detected_frames = 0
        self.book_detected_frames = 0
        self.multiple_persons_frames = 0
        self.head_pose_violations = 0
        
        # Thresholds for triggering violations
        self.FACE_LOST_THRESHOLD = 30  # 1 second at 30fps
        self.MULTIPLE_FACES_THRESHOLD = 15  # 0.5 seconds
        self.PHONE_DETECTION_THRESHOLD = 10  # ~0.33 seconds
        self.BOOK_DETECTION_THRESHOLD = 10  # ~0.33 seconds
        self.MULTIPLE_PERSONS_THRESHOLD = 15  # 0.5 seconds
        self.HEAD_POSE_ANGLE_THRESHOLD = 30  # degrees

        # Time-based confirmation window for violations (3-5 seconds for better responsiveness)
        self.VIOLATION_CONFIRM_SECONDS = {
            'NO_PERSON_DETECTED': 5,  # 5 seconds to confirm no person
            'PHONE_DETECTED': 3,      # 3 seconds to confirm phone
            'BOOK_DETECTED': 3,       # 3 seconds to confirm book
            'MULTIPLE_PERSONS': 3,    # 3 seconds to confirm multiple persons
            'MULTIPLE_FACES': 3,      # 3 seconds to confirm multiple faces
            'FACE_NOT_VISIBLE': 5,    # 5 seconds to confirm face lost
            'SUSPICIOUS_HEAD_MOVEMENT': 2  # 2 seconds for head movement
        }
        # Track first detection timestamps per violation type
        self._first_detection_time = {}
        
    def _detect_with_yolo(self, frame):
        """Use YOLO for comprehensive object detection"""
        violations = []
        
        try:
            # Use YOLO object detection from the imported module
            labels, processed_frame, person_count, detected_objects = detectObject(frame, confidence_threshold=0.6)
            
            # Check for multiple persons (with timer confirmation)
            if person_count > 1:
                self._start_or_check_timer('MULTIPLE_PERSONS')
                if self._timer_matured('MULTIPLE_PERSONS'):
                    violations.append({
                        'type': 'MULTIPLE_PERSONS',
                        'description': f'{person_count} persons detected in frame',
                        'severity': 'HIGH'
                    })
            else:
                self._clear_timer('MULTIPLE_PERSONS')
            
            # Check for no person detected (with timer confirmation)
            if person_count == 0:
                self._start_or_check_timer('NO_PERSON_DETECTED')
                if self._timer_matured('NO_PERSON_DETECTED'):
                    violations.append({
                        'type': 'NO_PERSON_DETECTED',
                        'description': 'No person detected in frame',
                        'severity': 'HIGH'
                    })
            else:
                self._clear_timer('NO_PERSON_DETECTED')
            
            # Check for cell phone detection (with timer confirmation)
            if "cell phone" in detected_objects:
                self._start_or_check_timer('PHONE_DETECTED')
                if self._timer_matured('PHONE_DETECTED'):
                    violations.append({
                        'type': 'PHONE_DETECTED',
                        'description': 'Cell phone detected in frame',
                        'severity': 'HIGH'
                    })
            else:
                self._clear_timer('PHONE_DETECTED')
            
            # Check for book detection (with timer confirmation)
            if "book" in detected_objects:
                self._start_or_check_timer('BOOK_DETECTED')
                if self._timer_matured('BOOK_DETECTED'):
                    violations.append({
                        'type': 'BOOK_DETECTED',
                        'description': 'Book or reading material detected',
                        'severity': 'MEDIUM'
                    })
            else:
                self._clear_timer('BOOK_DETECTED')
                
        except Exception as e:
            print(f"YOLO detection error: {e}")
            # Fall back to basic detection if YOLO fails
            pass
        
        return violations
    
    def process_frame(self, frame_data):
        """Process a single video frame and detect violations using YOLO and MediaPipe"""
        try:
            # Handle different input types
            if isinstance(frame_data, str):
                # Decode base64 frame (from web interface)
                frame_bytes = base64.b64decode(frame_data.split(',')[1])
                frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
            elif isinstance(frame_data, np.ndarray):
                # Direct numpy array (for testing)
                frame = frame_data
            else:
                raise ValueError("Unsupported frame data type")
            
            violations = []
            
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # YOLO Object Detection (primary detection method)
            yolo_violations = self._detect_with_yolo(frame)
            violations.extend(yolo_violations)
            
            # MediaPipe Face detection (supplementary)
            face_violations = self._detect_face_violations(rgb_frame)
            violations.extend(face_violations)
            
            # Head pose estimation
            pose_violations = self._detect_head_pose_violations(rgb_frame)
            violations.extend(pose_violations)
            
            # Save evidence if violations detected
            if violations:
                evidence_path, evidence_blob = self._save_evidence(frame, violations)
                self._log_violations(violations, evidence_path, evidence_blob)
            
            return violations
            
        except Exception as e:
            print(f"Error processing frame: {e}")
            return []
    
    def _detect_face_violations(self, rgb_frame):
        """Detect face-related violations"""
        violations = []
        results = self.face_detection.process(rgb_frame)
        
        if not results.detections:
            self._start_or_check_timer('FACE_NOT_VISIBLE')
            if self._timer_matured('FACE_NOT_VISIBLE'):
                violations.append({
                    'type': 'FACE_NOT_VISIBLE',
                    'description': 'Student face not visible',
                    'severity': 'HIGH'
                })
        else:
            self._clear_timer('FACE_NOT_VISIBLE')
            
            # Check for multiple faces (with timer confirmation)
            if len(results.detections) > 1:
                self._start_or_check_timer('MULTIPLE_FACES')
                if self._timer_matured('MULTIPLE_FACES'):
                    violations.append({
                        'type': 'MULTIPLE_PERSONS',
                        'description': f'{len(results.detections)} faces detected',
                        'severity': 'HIGH'
                    })
            else:
                self._clear_timer('MULTIPLE_FACES')
        
        return violations
    
    def _detect_head_pose_violations(self, rgb_frame):
        """Detect head pose violations using pose estimation"""
        violations = []
        results = self.pose.process(rgb_frame)
        
        if results.pose_landmarks:
            # Get key points for head pose estimation
            nose = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.NOSE]
            left_ear = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.LEFT_EAR]
            right_ear = results.pose_landmarks.landmark[self.mp_pose.PoseLandmark.RIGHT_EAR]
            
            # Calculate head rotation (simplified)
            ear_diff = abs(left_ear.y - right_ear.y)
            
            # If head is tilted significantly or looking away (with timer confirmation)
            if ear_diff > 0.05:  # Threshold for head tilt
                self._start_or_check_timer('SUSPICIOUS_HEAD_MOVEMENT')
                if self._timer_matured('SUSPICIOUS_HEAD_MOVEMENT'):
                    violations.append({
                        'type': 'SUSPICIOUS_HEAD_MOVEMENT',
                        'description': 'Suspicious head movement detected',
                        'severity': 'MEDIUM'
                    })
            else:
                self._clear_timer('SUSPICIOUS_HEAD_MOVEMENT')
        
        return violations
    
    def _detect_multiple_persons(self, rgb_frame):
        """Detect multiple persons in frame using MediaPipe face detection"""
        violations = []
        
        # Use MediaPipe face detection for person counting
        results = self.face_detection.process(rgb_frame)
        
        if results.detections and len(results.detections) > 1:
            violations.append({
                'type': 'MULTIPLE_PERSONS',
                'description': f'{len(results.detections)} persons detected',
                'severity': 'HIGH'
            })
        
        return violations
    
    def _save_evidence(self, frame, violations):
        """Save screenshot as evidence to disk or prepare as BLOB for DB"""
        try:
            # Encode frame to JPEG for DB storage if needed
            ok, buffer = cv2.imencode('.jpg', frame)
            if not ok:
                raise RuntimeError('Failed to encode frame as JPEG')
            evidence_blob = buffer.tobytes()

            evidence_path = None
            if self.storage_mode == 'disk':
                evidence_dir = f"static/uploads/evidence/{self.session_id}"
                os.makedirs(evidence_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                evidence_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
                evidence_path = os.path.join(evidence_dir, evidence_filename)
                # Normalize path to use forward slashes for URL compatibility
                evidence_path = evidence_path.replace('\\', '/')
                cv2.imwrite(evidence_path, frame)

            return evidence_path, evidence_blob
        except Exception as e:
            print(f"Error saving evidence: {e}")
            return None, None
    
    def _log_violations(self, violations, evidence_path, evidence_blob):
        """Log violations to database with evidence path or BLOB depending on storage_mode"""
        conn = get_db_connection()
        try:
            for violation in violations:
                conn.execute('''
                    INSERT INTO cheating_logs 
                    (session_id, violation_type, description, severity, timestamp, evidence_path, evidence_blob)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.session_id,
                    violation['type'],
                    violation['description'],
                    violation['severity'],
                    datetime.now().isoformat(),
                    evidence_path if self.storage_mode == 'disk' else None,
                    evidence_blob if self.storage_mode == 'db' else None
                ))
            conn.commit()
        finally:
            conn.close()
    
    def process_audio(self, audio_data):
        """Process audio data for violations"""
        # This would be implemented with librosa for audio analysis
        violations = []
        
        try:
            # Placeholder for audio processing
            # In a real implementation, you would:
            # 1. Decode audio data
            # 2. Use librosa to detect multiple voices
            # 3. Analyze audio patterns for suspicious activity
            # 4. Detect background noise/conversation
            
            # For now, return empty violations
            pass
            
        except Exception as e:
            print(f"Error processing audio: {e}")
        
        return violations

    def _start_or_check_timer(self, violation_type):
        """Start a timer for a violation type if not already started"""
        now = datetime.now()
        if violation_type not in self._first_detection_time:
            self._first_detection_time[violation_type] = now

    def _clear_timer(self, violation_type):
        """Clear the timer for a violation type when condition is no longer present"""
        if violation_type in self._first_detection_time:
            del self._first_detection_time[violation_type]

    def _timer_matured(self, violation_type):
        """Return True if the violation has persisted long enough based on type"""
        start = self._first_detection_time.get(violation_type)
        if not start:
            return False
        elapsed = (datetime.now() - start).total_seconds()
        required_seconds = self.VIOLATION_CONFIRM_SECONDS.get(violation_type, 3)
        return elapsed >= required_seconds