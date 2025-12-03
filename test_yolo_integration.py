#!/usr/bin/env python3
"""
Test script to verify YOLO integration with ProctGuard
"""

import cv2
import numpy as np
from detection.proctoring_monitor import ProctoringMonitor

def test_yolo_integration():
    """Test YOLO object detection integration"""
    print("Testing YOLO Integration with ProctGuard...")
    
    try:
        # Initialize proctoring monitor
        monitor = ProctoringMonitor("test_session_123")
        print("✓ ProctoringMonitor initialized successfully")
        
        # Create a test frame (640x480 RGB image)
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        print("✓ Test frame created")
        
        # Test frame processing
        violations = monitor.process_frame(test_frame)
        print(f"✓ Frame processed successfully. Violations detected: {len(violations)}")
        
        # Print detected violations
        if violations:
            print("\nDetected violations:")
            for i, violation in enumerate(violations, 1):
                print(f"  {i}. Type: {violation['type']}")
                print(f"     Description: {violation['description']}")
                print(f"     Severity: {violation['severity']}")
        else:
            print("  No violations detected in test frame")
        
        print("\n✓ YOLO integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error during YOLO integration test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_yolo_detection_function():
    """Test the YOLO detection function directly"""
    print("\nTesting YOLO detection function directly...")
    
    try:
        from models.object_detection import detectObject
        
        # Create a test image
        test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        
        # Test YOLO detection
        labels_this_frame, processed_frame, person_count, detected_objects = detectObject(test_image)
        print(f"✓ YOLO detection function works. Detected {len(labels_this_frame)} objects")
        print(f"✓ Person count: {person_count}")
        print(f"✓ Objects of interest: {detected_objects}")
        
        # Print detection details
        if labels_this_frame:
            print("Detection details:")
            for label, confidence in labels_this_frame[:3]:  # Show first 3 detections
                print(f"  - Class: {label}, Confidence: {confidence:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing YOLO detection function: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ProctGuard YOLO Integration Test")
    print("=" * 60)
    
    # Test YOLO detection function
    yolo_test = test_yolo_detection_function()
    
    # Test ProctGuard integration
    integration_test = test_yolo_integration()
    
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print(f"YOLO Detection Function: {'PASS' if yolo_test else 'FAIL'}")
    print(f"ProctGuard Integration:  {'PASS' if integration_test else 'FAIL'}")
    print("=" * 60)
    
    if yolo_test and integration_test:
        print("✓ All tests passed! YOLO integration is working correctly.")
    else:
        print("✗ Some tests failed. Please check the error messages above.")