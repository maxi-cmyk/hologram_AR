import cv2
import numpy as np
import math
import time
import random

class Particle:
    def __init__(self, x, y, color):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-10, 10)
        self.vy = random.uniform(-15, 5)
        self.gravity = 1.0
        self.color = color
        self.life = 255
        
    def update(self):
        self.vy += self.gravity
        self.x += self.vx
        self.y += self.vy
        self.life -= 15
        return self.life > 0

    def draw(self, frame):
        if self.life > 0:
            cv2.circle(frame, (int(self.x), int(self.y)), 3, self.color, -1)

class Explosion:
    def __init__(self, x, y, color, count=30):
        self.particles = [Particle(x, y, color) for _ in range(count)]
        
    def draw(self, frame):
        active = []
        for p in self.particles:
            if p.update():
                p.draw(frame)
                active.append(p)
        self.particles = active
        return len(self.particles) > 0

class BeamParticle:
    def __init__(self, x, y, color, radial=False):
        self.x = float(x)
        self.y = float(y)
        if radial:
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(10, 40)
            self.vx = math.cos(angle) * speed
            self.vy = math.sin(angle) * speed
        else:
            self.vx = random.uniform(-2, 2)
            self.vy = random.uniform(-2, 2)
        self.color = color
        self.life = 255
        
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 20
        return self.life > 0

    def draw(self, frame):
        if self.life > 0:
            cv2.circle(frame, (int(self.x), int(self.y)), 2, self.color, -1)

class RepulsorBlast:
    def __init__(self, start_x, start_y, color=(0, 255, 255)):
        self.start = (start_x, start_y)
        self.color = color
        self.life = 255
        self.particles = []
        
        # Populate radial particles
        for _ in range(30):
            self.particles.append(BeamParticle(start_x, start_y, color, radial=True))

    def draw(self, frame):
        self.life -= 15
        if self.life > 0:
            # Flash the screen/camera!
            radius = int((1.0 - self.life / 255.0) * 800)
            thickness = max(1, int((self.life / 255.0) * 150))
            if thickness > 0:
                cv2.circle(frame, self.start, radius, (255, 255, 255), thickness)
                if thickness > 30:
                    cv2.circle(frame, self.start, radius, self.color, thickness - 30)
            
        active = []
        for p in self.particles:
            if p.update():
                p.draw(frame)
                active.append(p)
        self.particles = active
        return self.life > 0 or len(self.particles) > 0

class InteractiveCube:
    def __init__(self, x, y, size):
        self.anchor = (x, y)
        self.size = size
        self.angle = random.uniform(0, math.pi)
        self.spin_speed = 0.05
        self.hit_count = 0
        self.color = (0, 255, 0) # Green

        self.vertices = [[-1,-1,-1], [1,-1,-1], [1,1,-1], [-1,1,-1],
                         [-1,-1,1], [1,-1,1], [1,1,1], [-1,1,1]]
        self.edges = [(0,1), (1,2), (2,3), (3,0), (4,5), (5,6), (6,7), (7,4), (0,4), (1,5), (2,6), (3,7)]

    def hit(self):
        self.hit_count += 1
        if self.hit_count == 1:
            self.spin_speed = 0.4
            self.color = (0, 100, 255) # Turn orange
        return self.hit_count >= 2

    def draw(self, frame):
        # Apply hover physics
        x, y = self.anchor
        hover_y = y + int(math.sin(self.angle * 2) * 10)

        self.angle += self.spin_speed
        projected = []
        for v in self.vertices:
            rot_x = v[0] * math.cos(self.angle) + v[2] * math.sin(self.angle)
            rot_z = -v[0] * math.sin(self.angle) + v[2] * math.cos(self.angle)
            projected.append((int((rot_x * self.size) + x), int((v[1] * self.size) + hover_y)))
        for edge in self.edges:
            cv2.line(frame, projected[edge[0]], projected[edge[1]], self.color, 2)

class InteractiveCuboid:
    def __init__(self, x, y, width_size, height_size):
        self.anchor = (x, y)
        self.w_size = width_size
        self.h_size = height_size
        self.angle = random.uniform(0, math.pi)
        self.spin_speed = 0.05
        self.hit_count = 0
        self.color = (255, 165, 0) # Orange

        self.vertices = [[-1,-1,-1], [1,-1,-1], [1,1,-1], [-1,1,-1],
                         [-1,-1,1], [1,-1,1], [1,1,1], [-1,1,1]]
        self.edges = [(0,1), (1,2), (2,3), (3,0), (4,5), (5,6), (6,7), (7,4), (0,4), (1,5), (2,6), (3,7)]

    def hit(self):
        self.hit_count += 1
        if self.hit_count == 1:
            self.spin_speed = 0.4
            self.color = (0, 100, 255) # Turn orange
        return self.hit_count >= 2

    def draw(self, frame):
        x, y = self.anchor
        hover_y = y + int(math.sin(self.angle * 2) * 10)

        self.angle += self.spin_speed
        projected = []
        for v in self.vertices:
            rot_x = v[0] * math.cos(self.angle) + v[2] * math.sin(self.angle)
            rot_z = -v[0] * math.sin(self.angle) + v[2] * math.cos(self.angle)
            projected.append((int((rot_x * self.w_size) + x), int((v[1] * self.h_size) + hover_y)))
        for edge in self.edges:
            cv2.line(frame, projected[edge[0]], projected[edge[1]], self.color, 2)

class InteractivePrism:
    def __init__(self, x, y, size):
        self.anchor = (x, y)
        self.size = size
        self.angle = random.uniform(0, math.pi)
        self.spin_speed = 0.05
        self.hit_count = 0
        self.color = (0, 0, 255) # Red
        
        # 3D Triangular Prism (6 vertices)
        self.vertices = [[0, -1, -1], [-1, 1, -1], [1, 1, -1], 
                         [0, -1, 1], [-1, 1, 1], [1, 1, 1]]
        self.edges = [(0,1), (1,2), (2,0), (3,4), (4,5), (5,3), (0,3), (1,4), (2,5)]

    def hit(self):
        self.hit_count += 1
        if self.hit_count == 1:
            self.spin_speed = 0.4
            self.color = (0, 100, 255) # Turn orange
        return self.hit_count >= 2

    def draw(self, frame):
        x, y = self.anchor
        hover_y = y + int(math.sin(self.angle * 2) * 10)

        self.angle += self.spin_speed
        projected = []
        for v in self.vertices:
            rot_x = v[0] * math.cos(self.angle) + v[2] * math.sin(self.angle)
            rot_z = -v[0] * math.sin(self.angle) + v[2] * math.cos(self.angle)
            projected.append((int((rot_x * self.size) + x), int((v[1] * self.size) + hover_y)))
        for edge in self.edges:
            cv2.line(frame, projected[edge[0]], projected[edge[1]], self.color, 2) 

# --- THE CANVAS ENGINE ---

class ARCanvas:
    def __init__(self):
        self.stroke_path = []
        self.is_drawing = False
        self.spawned_shapes = []    
        self.dragged_shape = None  
        self.cooldown_until = 0.0   # Timestamp to pause drawing
        self.explosions = []        # Array of active particle systems
        self.beams = []             # Active repulsor beams

    def render_shapes(self, frame):
        # 1. RENDER LOOP (Painter's Algorithm)
        for shape in self.spawned_shapes: 
            shape.draw(frame)
            
        # Draw explosions
        active_explosions = []
        for exp in self.explosions:
            if exp.draw(frame):
                active_explosions.append(exp)
        self.explosions = active_explosions

        # Draw beams
        active_beams = []
        for beam in self.beams:
            if beam.draw(frame):
                active_beams.append(beam)
        self.beams = active_beams

    def process_interactions(self, frame, hand_landmarks):
        h, w, _ = frame.shape
        index_tip = hand_landmarks[8]
        thumb_tip = hand_landmarks[4]
        
        ix, iy = int(index_tip.x * w), int(index_tip.y * h)
        tx, ty = int(thumb_tip.x * w), int(thumb_tip.y * h)
        
        is_pinching = math.sqrt((ix - tx)**2 + (iy - ty)**2) < 40.0
        
        # 1.5 CHECK COOLDOWN (Don't allow grabbing or drawing yet)
        if time.time() < self.cooldown_until:
            return
        
        # 2. STATE OVERRIDE: Are we actively holding an object?
        if self.dragged_shape is not None:
            if is_pinching:
                # Keep dragging the locked shape with EMA smoothing to prevent jitter
                cx, cy = self.dragged_shape.anchor
                smooth_factor = 0.5
                new_x = int(cx * (1 - smooth_factor) + ix * smooth_factor)
                new_y = int(cy * (1 - smooth_factor) + iy * smooth_factor)
                
                self.dragged_shape.anchor = (new_x, new_y)
                self.dragged_shape.velocity_y = 0.0 # Reset gravity while holding!
                
                # Draw the pinch indicator at the raw hand coordinate
                cv2.circle(frame, (ix, iy), 10, (255, 255, 255), -1)
                
                # Visual feedback: if we drag into the "trash zone" (150px border), glow the screen red
                if ix < 150 or ix > w - 150 or iy < 150 or iy > h - 150:
                    cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 15)
                
                return # CRITICAL: Exit to prevent drawing lines
            else:
                cx, cy = self.dragged_shape.anchor
                
                # If the shape is within 150 pixels of ANY edge of the screen
                if cx < 150 or cx > w - 150 or cy < 150 or cy > h - 150:
                    # O(N) Array Deletion: Remove it from persistent memory
                    if self.dragged_shape in self.spawned_shapes:
                        self.spawned_shapes.remove(self.dragged_shape)
                
                # Clear the pointer
                self.dragged_shape = None

        # 3. Z-INDEX GRAB (Reverse Traversal)
        # If pinching, check if we grabbed an existing shape BEFORE drawing
        if is_pinching and not self.is_drawing:
            for shape in reversed(self.spawned_shapes):
                cx, cy = shape.anchor
                base_size = getattr(shape, 'size', getattr(shape, 'w_size', 50))
                
                # Make the grab radius big so it feels easy to catch falling objects
                if math.sqrt((ix - cx)**2 + (iy - cy)**2) < base_size * 3.0:
                    self.dragged_shape = shape
                    return # Exit to prevent drawing lines

        # 4. DRAWING MODE (With your custom auto-close physics)
        if is_pinching:
            if not self.is_drawing:
                self.is_drawing = True
            
            # Auto-close snap logic
            if len(self.stroke_path) > 20:
                start_x, start_y = self.stroke_path[0]
                if math.sqrt((ix - start_x)**2 + (iy - start_y)**2) < 30:
                    ix, iy = start_x, start_y
                    
            self.stroke_path.append((ix, iy))
            cv2.circle(frame, (ix, iy), 8, (255, 0, 255), -1) 
        
        elif self.is_drawing:
            self.is_drawing = False
            
            # Check if the loop is closed before spawning
            if len(self.stroke_path) > 20: 
                start_x, start_y = self.stroke_path[0]
                end_x, end_y = self.stroke_path[-1]
                
                contour = np.array(self.stroke_path, dtype=np.int32)
                bx, by, box_w, box_h = cv2.boundingRect(contour)
                close_threshold = max(box_w, box_h) * 0.15
                distance_to_start = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
                
                # If the loop is physically closed by the user
                if distance_to_start < close_threshold:
                    area = cv2.contourArea(contour)
                    
                    center_x = bx + (box_w // 2)
                    center_y = by + (box_h // 2)
                    aspect_ratio = float(box_w) / float(box_h) if box_h != 0 else 0
                    fill_ratio = area / (box_w * box_h) if box_w * box_h != 0 else 0
                    radius = max(box_w, box_h) // 2

                    new_shape = None
                    
                    # The Classifier (Use fill_ratio for robustness! Triangles take up ~50% of their bounding box)
                    if fill_ratio < 0.6:
                        new_shape = InteractivePrism(center_x, center_y, radius)
                    else:
                        if 0.75 <= aspect_ratio <= 1.25:
                            new_shape = InteractiveCube(center_x, center_y, radius)
                        else:
                            new_shape = InteractiveCuboid(center_x, center_y, box_w // 2, box_h // 2) 
                
                    # Successfully classified, append to the O(N) memory array
                    if new_shape:
                        self.spawned_shapes.append(new_shape)
                        self.stroke_path = [] # Clear memory only on success!

        # 5. Render the live stroke
        if len(self.stroke_path) > 1:
            for i in range(1, len(self.stroke_path)):
                cv2.line(frame, self.stroke_path[i-1], self.stroke_path[i], (255, 0, 255), 4)