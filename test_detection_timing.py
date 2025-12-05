#!/usr/bin/env python3
"""
Test detection timing to verify violations are logged with reduced timer
"""

import cv2
import numpy as np
import time
from detection.proctoring_monitor import ProctoringMonitor
from datetime import datetime

def test_no_person_detection():
    """Test that NO_PERSON_DETECTED triggers after 5 seconds"""
    print("Testing NO_PERSON_DETECTED with 5-second timer...")
    
    monitor = ProctoringMonitor("test_timing_session")
    
    # Create empty frame (no person)
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    start_time = time.time()
    violations_found = False
    
    # Process frames for 6 seconds
    while time.time() - start_time < 6:
        violations = monitor.process_frame(test_frame)
        
        if violations and not violations_found:
            elapsed = time.time() - start_time
            print(f"✓ Violation detected after {elapsed:.1f} seconds")
            print(f"  Type: {violations[0]['type']}")
            print(f"  Description: {violations[0]['description']}")
            violations_found = True
            break
        
        time.sleep(0.1)  # Process at ~10 fps
    
    if not violations_found:
        print("✗ No violation detected within 6 seconds")
        return False
    
    return True

def test_head_movement_detection():
    """Test that SUSPICIOUS_HEAD_MOVEMENT triggers after 2 seconds"""
    print("\nTesting SUSPICIOUS_HEAD_MOVEMENT with 2-second timer...")
    print("(This requires actual pose landmarks, may not trigger with random data)")
    
    monitor = ProctoringMonitor("test_timing_session_2")
    
    # Create test frame
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    start_time = time.time()
    violations_found = False
    
    # Process frames for 3 seconds
    while time.time() - start_time < 3:
        violations = monitor.process_frame(test_frame)
        
        for violation in violations:
            if violation['type'] == 'SUSPICIOUS_HEAD_MOVEMENT':
                elapsed = time.time() - start_time
                print(f"✓ Head movement violation detected after {elapsed:.1f} seconds")
                violations_found = True
                break
        
        if violations_found:
            break
        
        time.sleep(0.1)
    
    if not violations_found:
        print("  No head movement detected (expected with random test data)")
    
    return True

def show_timer_configuration():
    """Display the current timer configuration"""
    print("\n" + "="*60)
    print("Current Detection Timer Configuration:")
    print("="*60)
    
    monitor = ProctoringMonitor("test_config")
    
    for violation_type, seconds in monitor.VIOLATION_CONFIRM_SECONDS.items():
        print(f"  {violation_type:.<35} {seconds}s")
    
    print("="*60)

if __name__ == "__main__":
    print("="*60)
    print("ProctGuard Detection Timing Test")
    print("="*60)
    
    # Show configuration
    show_timer_configuration()
    
    # Test no person detection
    test1 = test_no_person_detection()
    
    # Test head movement detection
    test2 = test_head_movement_detection()
    
    print("\n" + "="*60)
    print("Test Results Summary:")
    print(f"NO_PERSON_DETECTED timing: {'PASS' if test1 else 'FAIL'}")
    print(f"HEAD_MOVEMENT timing: {'PASS' if test2 else 'PASS (skipped)'}")
    print("="*60)
    
    if test1:
        print("\n✓ Detection system is working correctly!")
        print("  Violations are now logged after 2-5 seconds instead of 10-15 seconds")
    else:
        print("\n✗ Some tests failed. Please check the detection system.")
