import cv2
import math
import time
import numpy as np

class EnergyShield:
    def __init__(self):
        # Default colors (can be overridden by theme)
        self.primary_color = (0, 255, 255) # Yellow/Gold
        self.secondary_color = (0, 200, 255)
        self.core_color = (0, 150, 255)

    def draw(self, frame, anchor, scale, theme=None):
        """Draws a rotating, multi-layered mandala energy shield."""
        # Use theme colors if provided
        primary = theme["shield_primary"] if theme else self.primary_color
        secondary = theme["shield_secondary"] if theme else self.secondary_color
        core = theme["shield_core"] if theme else self.core_color
        cx, cy = anchor
        base_radius = int(140 * scale)
        
        current_time = time.time()
        
        # Fast rotation
        rot1 = current_time * 2.5
        rot2 = -current_time * 2.0
        rot3 = current_time * 1.0

        # Draw glowing core
        cv2.circle(frame, (cx, cy), int(base_radius * 0.3), core, -1)
        cv2.circle(frame, (cx, cy), int(base_radius * 0.35), primary, 2)
        cv2.circle(frame, (cx, cy), int(base_radius * 0.4), primary, 1)

        # Draw Inner Hexagon
        self._draw_polygon(frame, cx, cy, int(base_radius * 0.7), 6, rot1, primary, 3, draw_spokes=True)
        
        # Draw Middle Octagon
        self._draw_polygon(frame, cx, cy, int(base_radius * 1.0), 8, rot2, secondary, 2, draw_spokes=False)
        
        # Draw Outer Dodecagon (12 sided)
        self._draw_polygon(frame, cx, cy, int(base_radius * 1.3), 12, rot3, primary, 1, draw_spokes=False)
        
        # Draw floating particles or energy rings
        for i in range(4):
            ring_radius = int(base_radius * 1.3) + int(math.sin(current_time * 5 + i) * 10 * scale)
            cv2.circle(frame, (cx, cy), ring_radius, secondary, 1)

    def _draw_polygon(self, frame, cx, cy, radius, sides, rotation, color, thickness, draw_spokes=False):
        pts = []
        for i in range(sides):
            angle = rotation + i * (2 * math.pi / sides)
            x = int(cx + radius * math.cos(angle))
            y = int(cy + radius * math.sin(angle))
            pts.append([x, y])
            
            if draw_spokes:
                cv2.line(frame, (cx, cy), (x, y), color, 1)
                
        pts_array = np.array(pts, np.int32)
        pts_array = pts_array.reshape((-1, 1, 2))
        cv2.polylines(frame, [pts_array], True, color, thickness)
