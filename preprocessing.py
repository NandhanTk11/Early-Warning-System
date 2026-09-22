import cv2
import numpy as np
from collections import deque

class Preprocessor:
    def __init__(self, history_size=15):
        self.face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        
        # Median-based bounding box stabilization
        # Keeps a sliding window of recent detections; the median rejects
        # outlier jumps from the Haar cascade without creating EMA drift
        self.bbox_history = deque(maxlen=history_size)
        self.outlier_threshold = 50  # Max allowed pixel jump from current median

    def _get_stable_bbox(self):
        """Returns the median bounding box from the history buffer."""
        if len(self.bbox_history) == 0:
            return None
        coords = np.array(self.bbox_history)
        return np.median(coords, axis=0).astype(int)

    def extract_green_trace(self, frame):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        enhanced_gray = self.clahe.apply(gray_frame)
        faces = self.face_cascade.detectMultiScale(enhanced_gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
        
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            new_bbox = [x, y, w, h]
            
            # Outlier gate: only accept detection if it's within threshold
            # of the current median, OR if the history buffer is still filling
            current_median = self._get_stable_bbox()
            if current_median is None or (
                abs(x - current_median[0]) < self.outlier_threshold and
                abs(y - current_median[1]) < self.outlier_threshold
            ):
                self.bbox_history.append(new_bbox)
            # If outlier, simply skip adding it — median stays stable
                
        stable_bbox = self._get_stable_bbox()
        if stable_bbox is None:
            return None
            
        ex, ey, ew, eh = stable_bbox
        
        # Clamp ROI coordinates to frame boundaries
        frame_h, frame_w = frame.shape[:2]
        
        # Extract the exact ROI bounds (Forehead and Cheeks)
        fh_y1 = max(0, ey + int(eh * 0.1))
        fh_y2 = min(frame_h, ey + int(eh * 0.25))
        fh_x1 = max(0, ex + int(ew * 0.2))
        fh_x2 = min(frame_w, ex + int(ew * 0.8))
        
        lc_y1 = max(0, ey + int(eh * 0.55))
        lc_y2 = min(frame_h, ey + int(eh * 0.75))
        lc_x1 = max(0, ex + int(ew * 0.1))
        lc_x2 = min(frame_w, ex + int(ew * 0.35))
        
        rc_y1 = max(0, ey + int(eh * 0.55))
        rc_y2 = min(frame_h, ey + int(eh * 0.75))
        rc_x1 = max(0, ex + int(ew * 0.65))
        rc_x2 = min(frame_w, ex + int(ew * 0.9))
        
        forehead = frame[fh_y1:fh_y2, fh_x1:fh_x2, 1]
        left_cheek = frame[lc_y1:lc_y2, lc_x1:lc_x2, 1]
        right_cheek = frame[rc_y1:rc_y2, rc_x1:rc_x2, 1]
        
        # Concatenate all green pixels into a single stable array and calculate the float32 mean
        green_pixels = np.concatenate([forehead.flatten(), left_cheek.flatten(), right_cheek.flatten()])
        
        if green_pixels.size == 0:
            return None
            
        return np.mean(green_pixels.astype(np.float32))