"""
Test Face Tracking Feature (VANTA-15)
Tests face_id consistency, multi-person tracking, and latency requirements.
"""
import sys
import asyncio
import time
from pathlib import Path

# Add service to path
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "emotion-detection"))

from app.face_tracker import FaceTracker
import cv2
import numpy as np

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def generate_test_frame(size=(640, 480), num_faces=2):
    """Generate a test frame with simulated faces."""
    frame = np.random.randint(50, 150, (size[1], size[0], 3), dtype=np.uint8)
    
    # Add simulated faces (rectangles with some texture)
    faces = []
    for i in range(num_faces):
        x = 100 + i * 200
        y = 150
        w, h = 120, 150
        
        # Draw face rectangle
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 200, 150), -1)
        
        # Add some features (eyes, nose, mouth simulation)
        cv2.circle(frame, (x+30, y+40), 10, (50, 50, 50), -1)  # Left eye
        cv2.circle(frame, (x+90, y+40), 10, (50, 50, 50), -1)  # Right eye
        cv2.ellipse(frame, (x+60, y+90), (20, 10), 0, 0, 180, (100, 50, 50), 2)  # Mouth
        
        faces.append((x, y, x+w, y+h, 0.95))
    
    return frame, faces


def test_face_id_assignment():
    """Test 1: Face ID assignment for first frame."""
    print(f"\n{BLUE}Test 1: Face ID Assignment{RESET}")
    
    tracker = FaceTracker()
    frame, detections = generate_test_frame(num_faces=3)
    
    result = tracker.track_faces(frame, detections)
    
    # Check sequential IDs
    expected_ids = ["face_0", "face_1", "face_2"]
    actual_ids = [r['face_id'] for r in result]
    
    if actual_ids == expected_ids:
        print(f"  {GREEN}✓ PASSED{RESET}: Sequential IDs assigned correctly")
        print(f"    IDs: {actual_ids}")
        return True
    else:
        print(f"  {RED}✗ FAILED{RESET}: Expected {expected_ids}, got {actual_ids}")
        return False


def test_face_id_persistence():
    """Test 2: Same face_id across 10+ frames."""
    print(f"\n{BLUE}Test 2: Face ID Persistence Across Frames{RESET}")
    
    tracker = FaceTracker()
    
    # Track same faces across 15 frames
    face_ids_per_frame = []
    num_frames = 15
    
    for frame_num in range(num_frames):
        # Generate frame with 2 faces at consistent positions (small variations)
        frame = np.random.randint(50, 150, (480, 640, 3), dtype=np.uint8)
        
        # Face 1: roughly at (100, 150)
        x1 = 100 + np.random.randint(-5, 5)
        y1 = 150 + np.random.randint(-5, 5)
        
        # Face 2: roughly at (300, 150)
        x2 = 300 + np.random.randint(-5, 5)
        y2 = 150 + np.random.randint(-5, 5)
        
        # Draw faces with features
        for x, y in [(x1, y1), (x2, y2)]:
            cv2.rectangle(frame, (x, y), (x+120, y+150), (255, 200, 150), -1)
            cv2.circle(frame, (x+30, y+40), 10, (50, 50, 50), -1)
            cv2.circle(frame, (x+90, y+40), 10, (50, 50, 50), -1)
            cv2.ellipse(frame, (x+60, y+90), (20, 10), 0, 0, 180, (100, 50, 50), 2)
        
        detections = [
            (x1, y1, x1+120, y1+150, 0.95),
            (x2, y2, x2+120, y2+150, 0.95)
        ]
        
        result = tracker.track_faces(frame, detections)
        frame_ids = [r['face_id'] for r in result]
        face_ids_per_frame.append(frame_ids)
    
    # Check consistency
    first_frame_ids = set(face_ids_per_frame[0])
    all_consistent = True
    
    for frame_num, ids in enumerate(face_ids_per_frame[1:], start=1):
        if set(ids) != first_frame_ids:
            all_consistent = False
            print(f"  {YELLOW}⚠ Frame {frame_num}: IDs changed{RESET}")
            print(f"    Expected: {first_frame_ids}, Got: {set(ids)}")
    
    if all_consistent:
        print(f"  {GREEN}✓ PASSED{RESET}: Face IDs consistent across {num_frames} frames")
        print(f"    Tracked faces: {first_frame_ids}")
        return True
    else:
        print(f"  {RED}✗ FAILED{RESET}: Face IDs not consistent across frames")
        return False


def test_new_face_detection():
    """Test 3: New person enters → new face_id."""
    print(f"\n{BLUE}Test 3: New Face Detection{RESET}")
    
    tracker = FaceTracker()
    
    # Frame 1: 2 faces
    frame1, detections1 = generate_test_frame(num_faces=2)
    result1 = tracker.track_faces(frame1, detections1)
    initial_ids = {r['face_id'] for r in result1}
    
    # Frame 2: 3 faces (same 2 + new one)
    frame2 = np.random.randint(50, 150, (480, 640, 3), dtype=np.uint8)
    
    # Same 2 faces
    for i in range(2):
        x = 100 + i * 200
        y = 150
        cv2.rectangle(frame2, (x, y), (x+120, y+150), (255, 200, 150), -1)
        cv2.circle(frame2, (x+30, y+40), 10, (50, 50, 50), -1)
        cv2.circle(frame2, (x+90, y+40), 10, (50, 50, 50), -1)
    
    # New face
    x_new = 500
    y_new = 150
    cv2.rectangle(frame2, (x_new, y_new), (x_new+120, y_new+150), (255, 200, 150), -1)
    cv2.circle(frame2, (x_new+30, y_new+40), 10, (50, 50, 50), -1)
    cv2.circle(frame2, (x_new+90, y_new+40), 10, (50, 50, 50), -1)
    
    detections2 = [
        (100, 150, 220, 300, 0.95),
        (300, 150, 420, 300, 0.95),
        (500, 150, 620, 300, 0.95)
    ]
    
    result2 = tracker.track_faces(frame2, detections2)
    new_ids = {r['face_id'] for r in result2}
    
    # Check: should have 3 faces, 2 old + 1 new
    if len(new_ids) == 3 and len(new_ids - initial_ids) == 1:
        print(f"  {GREEN}✓ PASSED{RESET}: New face detected with new ID")
        print(f"    Initial IDs: {initial_ids}")
        print(f"    New IDs: {new_ids}")
        print(f"    New face ID: {new_ids - initial_ids}")
        return True
    else:
        print(f"  {RED}✗ FAILED{RESET}: New face not detected correctly")
        print(f"    Initial: {initial_ids}, Current: {new_ids}")
        return False


def test_face_disappearance():
    """Test 4: Person leaves view → remove face_id."""
    print(f"\n{BLUE}Test 4: Face Disappearance{RESET}")
    
    tracker = FaceTracker(max_missing_frames=3)
    
    # Frame 1-5: 2 faces present
    for i in range(5):
        frame, detections = generate_test_frame(num_faces=2)
        result = tracker.track_faces(frame, detections)
    
    active_faces_with_2 = tracker.get_stats()["active_faces"]
    
    # Frame 6-10: Only 1 face (one person left)
    for i in range(5):
        frame, detections = generate_test_frame(num_faces=1)
        result = tracker.track_faces(frame, detections)
    
    active_faces_with_1 = tracker.get_stats()["active_faces"]
    
    if active_faces_with_2 == 2 and active_faces_with_1 == 1:
        print(f"  {GREEN}✓ PASSED{RESET}: Face removed after leaving view")
        print(f"    Active faces with 2: {active_faces_with_2}")
        print(f"    Active faces with 1: {active_faces_with_1}")
        return True
    else:
        print(f"  {RED}✗ FAILED{RESET}: Face not removed correctly")
        print(f"    Expected: 2→1, Got: {active_faces_with_2}→{active_faces_with_1}")
        return False


def test_tracking_latency():
    """Test 5: Tracking adds <50ms latency."""
    print(f"\n{BLUE}Test 5: Tracking Latency{RESET}")
    
    tracker = FaceTracker()
    
    # Measure tracking time over 50 frames
    times = []
    for i in range(50):
        frame, detections = generate_test_frame(num_faces=3)
        
        start = time.time()
        result = tracker.track_faces(frame, detections)
        elapsed = (time.time() - start) * 1000
        
        times.append(elapsed)
    
    avg_time = np.mean(times)
    p95_time = np.percentile(times, 95)
    
    if p95_time < 50:
        print(f"  {GREEN}✓ PASSED{RESET}: Tracking latency within 50ms")
        print(f"    Average: {avg_time:.2f}ms")
        print(f"    P95: {p95_time:.2f}ms")
        return True
    else:
        print(f"  {YELLOW}⚠ WARNING{RESET}: Tracking latency exceeds 50ms")
        print(f"    Average: {avg_time:.2f}ms")
        print(f"    P95: {p95_time:.2f}ms")
        return False


def test_multi_person_tracking():
    """Test 6: Track 5 people consistently."""
    print(f"\n{BLUE}Test 6: Multi-Person Tracking{RESET}")
    
    tracker = FaceTracker()
    
    # Generate 5 faces
    frame = np.random.randint(50, 150, (480, 640, 3), dtype=np.uint8)
    detections = []
    
    for i in range(5):
        x = 50 + i * 110
        y = 150
        w, h = 100, 120
        
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 200, 150), -1)
        cv2.circle(frame, (x+25, y+35), 8, (50, 50, 50), -1)
        cv2.circle(frame, (x+75, y+35), 8, (50, 50, 50), -1)
        
        detections.append((x, y, x+w, y+h, 0.95))
    
    result = tracker.track_faces(frame, detections)
    
    # Track for 20 frames
    initial_ids = {r['face_id'] for r in result}
    consistency_count = 0
    
    for _ in range(20):
        # Regenerate with slight movement
        frame = np.random.randint(50, 150, (480, 640, 3), dtype=np.uint8)
        detections_moved = []
        
        for i in range(5):
            x = 50 + i * 110 + np.random.randint(-3, 3)
            y = 150 + np.random.randint(-3, 3)
            w, h = 100, 120
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 200, 150), -1)
            cv2.circle(frame, (x+25, y+35), 8, (50, 50, 50), -1)
            cv2.circle(frame, (x+75, y+35), 8, (50, 50, 50), -1)
            
            detections_moved.append((x, y, x+w, y+h, 0.95))
        
        result = tracker.track_faces(frame, detections_moved)
        current_ids = {r['face_id'] for r in result}
        
        if current_ids == initial_ids:
            consistency_count += 1
    
    consistency_rate = consistency_count / 20 * 100
    
    if consistency_rate >= 90:
        print(f"  {GREEN}✓ PASSED{RESET}: Multi-person tracking consistent")
        print(f"    Tracked 5 faces: {initial_ids}")
        print(f"    Consistency: {consistency_rate:.0f}%")
        return True
    else:
        print(f"  {YELLOW}⚠ WARNING{RESET}: Multi-person tracking inconsistent")
        print(f"    Consistency: {consistency_rate:.0f}%")
        return False


def main():
    """Run all tracking tests."""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{'Face Tracking Tests (VANTA-15)':^70}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    tests = [
        ("Face ID Assignment", test_face_id_assignment),
        ("Face ID Persistence (10+ frames)", test_face_id_persistence),
        ("New Face Detection", test_new_face_detection),
        ("Face Disappearance", test_face_disappearance),
        ("Tracking Latency (<50ms)", test_tracking_latency),
        ("Multi-Person Tracking", test_multi_person_tracking)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"  {RED}✗ ERROR{RESET}: {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Test Summary{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = f"{GREEN}✓ PASSED{RESET}" if passed else f"{RED}✗ FAILED{RESET}"
        print(f"  {status}: {name}")
    
    print(f"\n{BLUE}Total: {passed_count}/{total_count} tests passed{RESET}")
    
    if passed_count == total_count:
        print(f"{GREEN}All tests passed!{RESET}\n")
        return 0
    else:
        print(f"{YELLOW}Some tests failed{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
