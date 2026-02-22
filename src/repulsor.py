import cv2 
import math 
import time 
import random 

class Sparks:
    def __init__(self):
        self.active = False
        self.x, self.y = 0.0, 0.0
        self.dx, self.dy = 0.0, 0.0
        self.life = 0

class Repulsor:
    def __init__(self, base_radius=50, max_sparks=100):
        self.base_radius = base_radius
        self.sparks = [Sparks() for _ in range(max_sparks)]
        self.gravity = 1.5 

    def emit_sparks(self, start_x, start_y):
        #random sparks 
        for spark in self.sparks:
            if not spark.active:
                spark.active = True
                spark.x, spark.y = start_x, start_y

                #pdf distribution 
                spark.dx = random.gauss(0, 5.0)
                spark.dy = random.gauss(-15.0, 3.0)
                spark.life = random.randint(10, 20)
                break

    def draw (self, frame, anchor, scale_multiplier):
        # Reduced physical bobbing/pulsing
        x, y = anchor 
        pulse = 1.0 + 0.02 * math.sin(time.time() * 5)
        current_radius = int(self.base_radius * scale_multiplier * pulse)

        # Color intensity pulse for the glow effect (oscillates 0-255)
        glow = int(127 + 128 * math.sin(time.time() * 15))
        
        # BGR Format: Cyan is (255, 255, 0), White is (255, 255, 255)
        # Adding the glow to the Red channel fades it between Cyan and White
        glow_color = (255, 255, glow)

        # Faint outer aura glow
        cv2.circle(frame, (x, y), int(current_radius * 1.15), (255, 255, 0), 2)

        # Outer ring
        cv2.circle(frame, (x,y), current_radius, glow_color, 4)

        # Middle ring
        cv2.circle(frame, (x, y), int(current_radius * 0.75), glow_color, 2)
        
        # Inner white-hot core
        cv2.circle(frame, (x, y), int(current_radius * 0.4), (255, 255, 255), -1)

        # Emit a few sparks every frame
        sparks_to_spawn = int(2 * scale_multiplier)
        for _ in range(sparks_to_spawn):
            self.emit_sparks(x, y)

        #sparks 
        for spark in self.sparks:
            if spark.active:
                spark.dy += self.gravity 
                spark.x += spark.dx 
                spark.y += spark.dy 
                spark.life -= 1

                if spark.life <= 0:
                    spark.active = False
                else:
                    cv2.circle(frame, (int(spark.x), int(spark.y)), 4, (0, 165, 255), -1)
