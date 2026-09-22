"""
Diagnostic: Visualize face detection and ROI extraction on sample frames.
Saves annotated frames + logs detection stability metrics.
"""
import cv2
import numpy as np

cap = cv2.VideoCapture(r"D:\Projects\Main Project\rppg_base_pipeline\vid.avi")
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

# Track detection stats
detections = []
no_face_frames = []
bbox_coords = []
green_values_raw = []

output_dir = r"D:\Projects\Main Project\rppg_base_pipeline"
save_frames = [0, 10, 30, 60, 100, 150, 200, 250, 299]  # Frames to save as images

frame_index = 0
total_frames = 300

print("Analyzing face detection on first 300 frames...\n")

while frame_index < total_frames:
    ret, frame = cap.read()
    if not ret:
        break
    
    h_frame, w_frame = frame.shape[:2]
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    enhanced_gray = clahe.apply(gray_frame)
    
    faces = face_cascade.detectMultiScale(enhanced_gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
    
    detected = len(faces) > 0
    detections.append(detected)
    
    if not detected:
        no_face_frames.append(frame_index)
        if frame_index in save_frames:
            cv2.putText(frame, f"Frame {frame_index}: NO FACE DETECTED", (30, 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            cv2.imwrite(f"{output_dir}\\debug_frame_{frame_index:03d}.png", frame)
    else:
        (x, y, w, h) = faces[0]
        bbox_coords.append((x, y, w, h))
        
        # Calculate ROI bounds (same as preprocessing.py)
        forehead_y1, forehead_y2 = y + int(h * 0.1), y + int(h * 0.25)
        forehead_x1, forehead_x2 = x + int(w * 0.2), x + int(w * 0.8)
        
        lcheek_y1, lcheek_y2 = y + int(h * 0.55), y + int(h * 0.75)
        lcheek_x1, lcheek_x2 = x + int(w * 0.1), x + int(w * 0.35)
        
        rcheek_y1, rcheek_y2 = y + int(h * 0.55), y + int(h * 0.75)
        rcheek_x1, rcheek_x2 = x + int(w * 0.65), x + int(w * 0.9)
        
        # Extract green values for this frame
        forehead_roi = frame[forehead_y1:forehead_y2, forehead_x1:forehead_x2, 1]
        lcheek_roi = frame[lcheek_y1:lcheek_y2, lcheek_x1:lcheek_x2, 1]
        rcheek_roi = frame[rcheek_y1:rcheek_y2, rcheek_x1:rcheek_x2, 1]
        
        all_green = np.concatenate([forehead_roi.flatten(), lcheek_roi.flatten(), rcheek_roi.flatten()])
        green_mean = np.mean(all_green.astype(np.float32)) if all_green.size > 0 else 0
        green_values_raw.append(green_mean)
        
        # Save annotated frames
        if frame_index in save_frames:
            # Draw face bounding box (yellow)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
            
            # Draw forehead ROI (green)
            cv2.rectangle(frame, (forehead_x1, forehead_y1), (forehead_x2, forehead_y2), (0, 255, 0), 2)
            cv2.putText(frame, "Forehead", (forehead_x1, forehead_y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Draw left cheek ROI (blue)
            cv2.rectangle(frame, (lcheek_x1, lcheek_y1), (lcheek_x2, lcheek_y2), (255, 0, 0), 2)
            cv2.putText(frame, "L Cheek", (lcheek_x1, lcheek_y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
            
            # Draw right cheek ROI (red)
            cv2.rectangle(frame, (rcheek_x1, rcheek_y1), (rcheek_x2, rcheek_y2), (0, 0, 255), 2)
            cv2.putText(frame, "R Cheek", (rcheek_x1, rcheek_y1 - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            
            # Add frame info
            cv2.putText(frame, f"Frame {frame_index} | Green Avg: {green_mean:.2f} | BBox: ({x},{y},{w},{h})", 
                       (10, h_frame - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imwrite(f"{output_dir}\\debug_frame_{frame_index:03d}.png", frame)
            print(f"  Saved debug_frame_{frame_index:03d}.png")
    
    frame_index += 1

cap.release()

# === Analysis ===
print(f"\n{'='*50}")
print(f"FACE DETECTION ANALYSIS ({total_frames} frames)")
print(f"{'='*50}")

detection_rate = sum(detections) / len(detections) * 100
print(f"Detection rate: {detection_rate:.1f}% ({sum(detections)}/{len(detections)} frames)")
print(f"Missed frames: {len(no_face_frames)}")
if no_face_frames:
    print(f"  First 20 missed: {no_face_frames[:20]}")

if len(bbox_coords) > 1:
    coords = np.array(bbox_coords)
    print(f"\n--- Bounding Box Stability ---")
    print(f"  X: mean={np.mean(coords[:,0]):.1f}, std={np.std(coords[:,0]):.1f}, range={np.ptp(coords[:,0])}")
    print(f"  Y: mean={np.mean(coords[:,1]):.1f}, std={np.std(coords[:,1]):.1f}, range={np.ptp(coords[:,1])}")
    print(f"  W: mean={np.mean(coords[:,2]):.1f}, std={np.std(coords[:,2]):.1f}, range={np.ptp(coords[:,2])}")
    print(f"  H: mean={np.mean(coords[:,3]):.1f}, std={np.std(coords[:,3]):.1f}, range={np.ptp(coords[:,3])}")
    
    # Frame-to-frame jumps
    diffs = np.diff(coords, axis=0)
    print(f"\n--- Frame-to-Frame BBox Jumps ---")
    print(f"  X jumps: mean={np.mean(np.abs(diffs[:,0])):.1f}, max={np.max(np.abs(diffs[:,0]))}")
    print(f"  Y jumps: mean={np.mean(np.abs(diffs[:,1])):.1f}, max={np.max(np.abs(diffs[:,1]))}")
    print(f"  W jumps: mean={np.mean(np.abs(diffs[:,2])):.1f}, max={np.max(np.abs(diffs[:,2]))}")
    print(f"  H jumps: mean={np.mean(np.abs(diffs[:,3])):.1f}, max={np.max(np.abs(diffs[:,3]))}")
    
    large_jumps = np.sum(np.abs(diffs[:,0]) > 20) + np.sum(np.abs(diffs[:,1]) > 20)
    print(f"  Large jumps (>20px in X or Y): {large_jumps}")

if green_values_raw:
    gv = np.array(green_values_raw)
    print(f"\n--- Green Channel Signal Quality ---")
    print(f"  Mean: {np.mean(gv):.2f}")
    print(f"  Std:  {np.std(gv):.4f}")
    print(f"  Range: {np.ptp(gv):.4f}")
    print(f"  CoV: {np.std(gv)/np.mean(gv)*100:.4f}%")
    
    # Frame-to-frame changes
    gdiffs = np.abs(np.diff(gv))
    print(f"  Frame-to-frame change: mean={np.mean(gdiffs):.4f}, max={np.max(gdiffs):.4f}")
    large_changes = np.sum(gdiffs > 5.0)
    print(f"  Large jumps (>5 pixel): {large_changes} out of {len(gdiffs)} frames")

print(f"\nCheck the saved debug_frame_*.png files to visually inspect ROI placement!")
