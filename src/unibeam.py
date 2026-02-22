import cv2
import math
import numpy as np
import time

class ArcReactor:
    def __init__(self, x, y):
        # We will dynamically position the reactor at (x, y) based on bottom-center of screen
        self.anchor = (int(x), int(y))
        self.radius = 40
        self.angle = 0.0

    def draw(self, frame, charge_level=0.0):
        # charge_level: 0.0 to 1.0
        x, y = self.anchor
        
        # Base Glow
        glow_radius = int(self.radius + 10 + (charge_level * 30))
        cv2.circle(frame, (x, y), glow_radius, (255, 255, 255), -1)
        
        # Outer Ring
        cv2.circle(frame, (x, y), self.radius, (255, 255, 0), max(2, int(6 + charge_level * 10)))
        
        # Inner Core
        inner_r = int(self.radius * 0.4)
        cv2.circle(frame, (x, y), inner_r, (255, 255, 0), -1)
        
        # Triangle Segments
        pts = []
        for i in range(3):
            theta = self.angle + i * (2 * math.pi / 3)
            tx = int(x + math.cos(theta) * self.radius * 0.8)
            ty = int(y + math.sin(theta) * self.radius * 0.8)
            pts.append([tx, ty])
        
        pts = np.array(pts, np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], True, (0, 0, 0), max(2, int(charge_level * 4)))

class UnibeamBlast:
    def __init__(self, start_x, start_y):
        self.anchor = (int(start_x), int(start_y))
        self.life = 1.0 # 1.0 seconds duration
        self.start_time = time.time()
        self.active = True

    def draw(self, frame):
        if not self.active:
            return False

        elapsed = time.time() - self.start_time
        if elapsed > self.life:
            self.active = False
            return False

        h, w, _ = frame.shape
        x, y = self.anchor

        # Phase 1: Expansion quickly (0 - 0.2s)
        # Phase 2: Hold full power (0.2s - 0.8s)
        # Phase 3: Fade out (0.8s - 1.0s)
        
        if elapsed < 0.2:
            scale = elapsed / 0.2
        elif elapsed < 0.8:
            scale = 1.0
        else:
            scale = 1.0 - ((elapsed - 0.8) / 0.2)

        beam_width = int(600 * scale) # Massive beam
        if beam_width <= 0:
            return True

        # Draw a huge beam cylinder going straight UP from the chest (y coordinate)
        
        cv2.circle(frame, (x, y), int(w * scale), (255, 255, 255), -1)
        
        # Screen shake flash vignette
        cv2.rectangle(frame, (0, 0), (w, h), (255, 255, 0), int(40 * scale))
        
        # Draw text
        cv2.putText(frame, "UNIBEAM MAXIMUM OUTPUT", (w//2 - 300, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 4, cv2.LINE_AA)

        return True
