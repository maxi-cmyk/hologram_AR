import cv2 
import numpy as np

class Exoskeleton:
    def __init__(self):
        self.finger_paths = [
            [1, 2, 3, 4],       # Thumb
            [5, 6, 7, 8],       # Index
            [9, 10, 11, 12],    # Middle
            [13, 14, 15, 16],   # Ring
            [17, 18, 19, 20]    # Pinky
        ]
        #main plate on back
        self.palm_path = [0, 5, 9, 13, 17]
        
    def draw (self, frame, hand_landmarks):
        #draw semi-transparent glove over hand

        # Darker Iron Man red
        base_red = (0, 0, 110)
        edge_red = (0, 0, 150)
        gold = (0, 200, 255)

        h, w, _ = frame.shape
        overlay = np.zeros((h, w, 3), dtype=np.uint8)

        points = []
        for lm in hand_landmarks:
            points.append((int(lm.x * w), int(lm.y * h)))
        
        # 1. Main Plate
        palm_pts = np.array([points[i] for i in self.palm_path], np.int32)
        palm_pts = palm_pts.reshape((-1, 1, 2))
        
        # Fill the palm plate
        cv2.fillPoly(overlay, [palm_pts], base_red)
        
        cv2.polylines(overlay, [palm_pts], True, base_red, 26)

        # Draw a gold rim around the now-wider palm plate
        cv2.polylines(overlay, [palm_pts], True, gold, 4)

        # 2. Knuckle connectors
        # Connect the palm plate to the base of each finger (except thumb)
        for i in [5, 9, 13, 17]:
            cv2.line(overlay, points[0], points[i], edge_red, 12)
            cv2.line(overlay, points[0], points[i], gold, 2)

        # 3. Finger Armor
        for path in self.finger_paths:
            for i in range(len(path) - 1):
                pt1 = points[path[i]]
                pt2 = points[path[i+1]]

                # Cylindrical finger armor (dark red)
                cv2.line(overlay, pt1, pt2, base_red, 22)
                
                # Outer highlight/rim 
                cv2.line(overlay, pt1, pt2, edge_red, 12)

                # Gold caps for joints 
                cv2.circle(overlay, pt1, 14, gold, -1)
                
            # Gold joint at fingertip
            cv2.circle(overlay, points[path[-1]], 14, gold, -1)

        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)