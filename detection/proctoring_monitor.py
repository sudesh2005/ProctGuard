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
    def __init__(self, session_id):
        self.session_id = session_id
        
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
        
    def _detect_with_yolo(self, frame):
        """Use YOLO for comprehensive object detection"""
        violations = []
        
        try:
            # Use YOLO object detection from the imported module
            labels, processed_frame, person_count, detected_objects = detectObject(frame, confidence_threshold=0.6)
            
            # Check for multiple persons
            if person_count > 1:
                self.multiple_persons_frames += 1
                if self.multiple_persons_frames >= self.MULTIPLE_PERSONS_THRESHOLD:
                    violations.append({
                        'type': 'MULTIPLE_PERSONS',
                        'description': f'{person_count} persons detected in frame',
                        'severity': 'HIGH'
                    })
                    self.multiple_persons_frames = 0
            else:
                self.multiple_persons_frames = max(0, self.multiple_persons_frames - 1)
            
            # Check for no person detected
            if person_count == 0:
                violations.append({
                    'type': 'NO_PERSON_DETECTED',
                    'description': 'No person detected in frame',
                    'severity': 'HIGH'
                })
            
            # Check for cell phone detection
            if "cell phone" in detected_objects:
                self.phone_detected_frames += 1
                if self.phone_detected_frames >= self.PHONE_DETECTION_THRESHOLD:
                    violations.append({
                        'type': 'PHONE_DETECTED',
                        'description': 'Cell phone detected in frame',
                        'severity': 'HIGH'
                    })
                    self.phone_detected_frames = 0
            else:
                self.phone_detected_frames = max(0, self.phone_detected_frames - 1)
            
            # Check for book detection
            if "book" in detected_objects:
                self.book_detected_frames += 1
                if self.book_detected_frames >= self.BOOK_DETECTION_THRESHOLD:
                    violations.append({
                        'type': 'BOOK_DETECTED',
                        'description': 'Book or reading material detected',
                        'severity': 'MEDIUM'
                    })
                    self.book_detected_frames = 0
            else:
                self.book_detected_frames = max(0, self.book_detected_frames - 1)
                
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
                evidence_path = self._save_evidence(frame, violations)
                self._log_violations(violations, evidence_path)
            
            return violations
            
        except Exception as e:
            print(f"Error processing frame: {e}")
            return []
    
    def _detect_face_violations(self, rgb_frame):
        """Detect face-related violations"""
        violations = []
        results = self.face_detection.process(rgb_frame)
        
        if not results.detections:
            self.face_lost_frames += 1
            if self.face_lost_frames >= self.FACE_LOST_THRESHOLD:
                violations.append({
                    'type': 'FACE_NOT_VISIBLE',
                    'description': 'Student face not visible',
                    'severity': 'HIGH'
                })
                self.face_lost_frames = 0  # Reset to avoid spam
        else:
            self.face_lost_frames = 0
            
            # Check for multiple faces
            if len(results.detections) > 1:
                self.multiple_faces_frames += 1
                if self.multiple_faces_frames >= self.MULTIPLE_FACES_THRESHOLD:
                    violations.append({
                        'type': 'MULTIPLE_PERSONS',
                        'description': f'{len(results.detections)} faces detected',
                        'severity': 'HIGH'
                    })
                    self.multiple_faces_frames = 0
            else:
                self.multiple_faces_frames = 0
        
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
            
            # If head is tilted significantly or looking away
            if ear_diff > 0.05:  # Threshold for head tilt
                violations.append({
                    'type': 'SUSPICIOUS_HEAD_MOVEMENT',
                    'description': 'Suspicious head movement detected',
                    'severity': 'MEDIUM'
                })
        
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
        """Save screenshot as evidence"""
        try:
            evidence_dir = f"static/uploads/evidence/{self.session_id}"
            os.makedirs(evidence_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            evidence_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
            evidence_path = os.path.join(evidence_dir, evidence_filename)
            
            cv2.imwrite(evidence_path, frame)
            return evidence_path
        except Exception as e:
            print(f"Error saving evidence: {e}")
            return None
    
    def _log_violations(self, violations, evidence_path):
        """Log violations to database"""
        conn = get_db_connection()
        
        for violation in violations:
            conn.execute('''
                INSERT INTO cheating_logs 
                (session_id, violation_type, description, severity, timestamp, evidence_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.session_id, violation['type'], violation['description'],
                  violation['severity'], datetime.now().isoformat(), evidence_path))
        
        conn.commit()
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