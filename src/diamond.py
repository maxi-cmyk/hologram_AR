import cv2
import math

class HologramDiamond:
    def __init__(self, center=None, size=50):
        self.size = size
        self.angle = 0.0
        # Diamond (octahedron): top point, 4 equator points, bottom point
        self.vertices = [
            [ 0, -2.5,  0],   # 0 - top
            [-1,  0, -1],     # 1 - front-left
            [ 1,  0, -1],     # 2 - front-right
            [ 1,  0,  1],     # 3 - back-right
            [-1,  0,  1],     # 4 - back-left
            [ 0,  2.5,  0],   # 5 - bottom
        ]
        self.edges = [
            (0,1), (0,2), (0,3), (0,4), # top to equator
            (5,1), (5,2), (5,3), (5,4), # bottom to equator
            (1,2), (2,3), (3,4), (4,1), # equator ring
        ]
    
    def draw(self, frame, anchor, scale_multiplier=1.0):
        #rotating, scaling 3D vertices onto 2D frame
        self.angle += 0.05
        angle_x = self.angle * 0.7
        angle_y = self.angle * 1.0
        angle_z = self.angle * 1.3
        anchor_x, anchor_y = anchor
        projected_points = []

        #matrix transformation
        for v in self.vertices:
            x, y, z = v[0], v[1], v[2]

            # --- Pitch (X-axis rotation) ---
            # X stays the same
            temp_y = y * math.cos(angle_x) - z * math.sin(angle_x)
            temp_z = y * math.sin(angle_x) + z * math.cos(angle_x)
            
            # --- Yaw (Y-axis rotation) ---
            # Y stays the same (we use temp_y)
            temp_x = x * math.cos(angle_y) + temp_z * math.sin(angle_y)
            final_z = -x * math.sin(angle_y) + temp_z * math.cos(angle_y)
            final_y = temp_y
            
            # --- Roll (Z-axis rotation) ---
            # Z stays the same (we use final_z)
            final_x = temp_x * math.cos(angle_z) - final_y * math.sin(angle_z)
            final_y = temp_x * math.sin(angle_z) + final_y * math.cos(angle_z)

            # 3. Dynamic Scaling 
            current_size = self.size * scale_multiplier
            scaled_x = final_x * current_size
            scaled_y = final_y * current_size
            
            # 4. Projecting 3D to 2D
            screen_x = int(scaled_x + anchor_x)
            screen_y = int(scaled_y + anchor_y)

            projected_points.append((screen_x, screen_y))

        for edge in self.edges:
            pt1 = projected_points[edge[0]]
            pt2 = projected_points[edge[1]]
            
            #draw a bright cyan line between the two projected vertices
            cv2.line(frame, pt1, pt2, (255, 255, 0), 2)
            



