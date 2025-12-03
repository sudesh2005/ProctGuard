import numpy as np
import base64
import wave
import io
import os
from datetime import datetime
import uuid
from models.database import get_db_connection

class AudioMonitor:
    def __init__(self, session_id):
        self.session_id = session_id
        self.sample_rate = 44100
        self.audio_buffer = []
        self.voice_activity_threshold = 0.02
        self.multiple_voice_threshold = 0.5
        self.background_noise_threshold = 0.01
        
        # Tracking variables
        self.voice_activity_frames = 0
        self.silence_frames = 0
        self.suspicious_audio_frames = 0
        
    def process_audio_chunk(self, audio_data):
        """Process audio chunk for violations"""
        violations = []
        
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            
            # Convert to numpy array (assuming 16-bit PCM)
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_normalized = audio_array.astype(np.float32) / 32768.0
            
            # Analyze audio features
            violations.extend(self._detect_voice_activity(audio_normalized))
            violations.extend(self._detect_multiple_voices(audio_normalized))
            violations.extend(self._detect_background_conversation(audio_normalized))
            
            # Save audio evidence if violations detected
            if violations:
                evidence_path = self._save_audio_evidence(audio_bytes, violations)
                self._log_audio_violations(violations, evidence_path)
            
        except Exception as e:
            print(f"Error processing audio: {e}")
        
        return violations
    
    def _detect_voice_activity(self, audio_array):
        """Detect voice activity patterns"""
        violations = []
        
        # Calculate RMS energy
        rms_energy = np.sqrt(np.mean(audio_array ** 2))
        
        if rms_energy > self.voice_activity_threshold:
            self.voice_activity_frames += 1
            self.silence_frames = 0
            
            # Check for suspicious voice patterns
            if self._is_suspicious_voice_pattern(audio_array):
                violations.append({
                    'type': 'SUSPICIOUS_AUDIO',
                    'description': 'Suspicious voice pattern detected',
                    'severity': 'MEDIUM'
                })
        else:
            self.silence_frames += 1
            self.voice_activity_frames = 0
        
        return violations
    
    def _detect_multiple_voices(self, audio_array):
        """Detect multiple voices using spectral analysis"""
        violations = []
        
        # Simple approach: analyze frequency spectrum
        fft = np.fft.fft(audio_array)
        magnitude_spectrum = np.abs(fft[:len(fft)//2])
        
        # Look for multiple fundamental frequency peaks
        # This is a simplified approach - real implementation would use more sophisticated methods
        peaks = self._find_peaks(magnitude_spectrum)
        
        if len(peaks) > 2:  # Multiple strong frequency components
            violations.append({
                'type': 'MULTIPLE_VOICES',
                'description': 'Multiple voices detected in audio',
                'severity': 'HIGH'
            })
        
        return violations
    
    def _detect_background_conversation(self, audio_array):
        """Detect background conversation or noise"""
        violations = []
        
        # Analyze for continuous background audio
        background_level = np.mean(np.abs(audio_array))
        
        if background_level > self.background_noise_threshold:
            # Check for conversation-like patterns
            if self._is_conversation_pattern(audio_array):
                violations.append({
                    'type': 'BACKGROUND_CONVERSATION',
                    'description': 'Background conversation detected',
                    'severity': 'HIGH'
                })
        
        return violations
    
    def _is_suspicious_voice_pattern(self, audio_array):
        """Check if voice pattern is suspicious (whispering, etc.)"""
        # Analyze frequency distribution
        fft = np.fft.fft(audio_array)
        magnitude_spectrum = np.abs(fft[:len(fft)//2])
        
        # Low frequency dominance might indicate whispering
        low_freq_energy = np.sum(magnitude_spectrum[:len(magnitude_spectrum)//4])
        total_energy = np.sum(magnitude_spectrum)
        
        if total_energy > 0:
            low_freq_ratio = low_freq_energy / total_energy
            return low_freq_ratio > 0.7  # Threshold for whispering
        
        return False
    
    def _is_conversation_pattern(self, audio_array):
        """Detect conversation-like audio patterns"""
        # Look for alternating voice activity patterns
        # This is a simplified implementation
        
        # Segment audio into chunks and analyze energy variations
        chunk_size = len(audio_array) // 10
        if chunk_size < 1:
            return False
        
        energy_chunks = []
        for i in range(0, len(audio_array), chunk_size):
            chunk = audio_array[i:i+chunk_size]
            energy = np.sqrt(np.mean(chunk ** 2))
            energy_chunks.append(energy)
        
        # Look for variations in energy (conversation pattern)
        if len(energy_chunks) > 1:
            energy_variation = np.std(energy_chunks)
            return energy_variation > 0.01
        
        return False
    
    def _find_peaks(self, spectrum, threshold=0.1):
        """Find peaks in frequency spectrum"""
        peaks = []
        for i in range(1, len(spectrum)-1):
            if (spectrum[i] > spectrum[i-1] and 
                spectrum[i] > spectrum[i+1] and 
                spectrum[i] > threshold * np.max(spectrum)):
                peaks.append(i)
        return peaks
    
    def _save_audio_evidence(self, audio_bytes, violations):
        """Save audio clip as evidence"""
        try:
            evidence_dir = f"static/uploads/audio_evidence/{self.session_id}"
            os.makedirs(evidence_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            evidence_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.wav"
            evidence_path = os.path.join(evidence_dir, evidence_filename)
            
            # Save as WAV file
            with wave.open(evidence_path, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_bytes)
            
            return evidence_path
        except Exception as e:
            print(f"Error saving audio evidence: {e}")
            return None
    
    def _log_audio_violations(self, violations, evidence_path):
        """Log audio violations to database"""
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