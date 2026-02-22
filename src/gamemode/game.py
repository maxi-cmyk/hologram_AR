import cv2
import time
import math
import random
import numpy as np
from canvas import Explosion

class EnemyLaser:
    def __init__(self, start_x, start_y, target_x, target_y, speed=15):
        self.anchor = (int(start_x), int(start_y))
        
        # Calculate velocity vector towards target
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.sqrt(dx**2 + dy**2)
        
        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed
        self.active = True

    def update(self):
        new_x = self.anchor[0] + self.vx
        new_y = self.anchor[1] + self.vy
        self.anchor = (new_x, new_y)

    def draw(self, frame):
        if not self.active:
            return False
            
        x, y = int(self.anchor[0]), int(self.anchor[1])
        h, w, _ = frame.shape
        
        # Draw red laser bolt
        cv2.circle(frame, (x, y), 8, (0, 0, 255), -1)
        
        # Deactivate if it flies off-screen
        if x < 0 or x > w or y < 0 or y > h:
            self.active = False
            return False
            
        return True

class Drone:
    def __init__(self, frame_width, frame_height):
        # Spawn on left or right edge randomly
        self.anchor = (0 if random.random() > 0.5 else frame_width, random.randint(100, frame_height - 100))
        self.size = 60
        
        # Target is center screen
        target_x = frame_width // 2
        target_y = frame_height // 2
        
        # Slow drift towards center
        speed = random.uniform(2.0, 4.0)
        dx = target_x - self.anchor[0]
        dy = target_y - self.anchor[1]
        dist = math.sqrt(dx**2 + dy**2)
        
        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed
        
        self.color = (0, 0, 200) # Deep Red
        self.active = True
        self.last_fire_time = time.time() + random.uniform(1.0, 3.0) # Randomized initial delay
        
        # Strafing variables
        self.real_x = float(self.anchor[0])
        self.real_y = float(self.anchor[1])
        self.start_time = time.time()
        self.strafe_speed = random.uniform(2.0, 5.0)
        self.strafe_amplitude = random.uniform(10.0, 30.0)

    def hit(self):
        # Base drone is destroyed in 1 hit
        return True

    def update(self, frame_width, frame_height):
        # Move baseline
        self.real_x += self.vx
        self.real_y += self.vy
        
        # Stop moving if it reaches center (player)
        dist_to_center = math.sqrt((self.real_x - frame_width//2)**2 + (self.real_y - frame_height//2)**2)
        if dist_to_center < 100:
            self.vx, self.vy = 0, 0
            
        # Calculate strafe
        strafe_y = math.sin((time.time() - self.start_time) * self.strafe_speed) * self.strafe_amplitude
        self.anchor = (int(self.real_x), int(self.real_y + strafe_y))

    def fire_laser(self, frame_width, frame_height):
        # Fire every 2 to 4 seconds
        if time.time() - self.last_fire_time > random.uniform(2.0, 4.0):
            self.last_fire_time = time.time()
            # Fire from drone anchor to center of screen
            return EnemyLaser(self.anchor[0], self.anchor[1], frame_width//2, frame_height//2)
        return None

    def draw(self, frame):
        if not self.active:
            return False
            
        x, y = int(self.anchor[0]), int(self.anchor[1])
        s = self.size
        
        # Draw sci-fi aggressive triangle drone
        pts = np.array([[x, y - s], [x - s//2, y + s//2], [x + s//2, y + s//2]], np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.fillPoly(frame, [pts], (0, 0, 100))
        cv2.polylines(frame, [pts], True, (0, 0, 255), 3)
        
        # Cyclops glowing eye
        cv2.circle(frame, (x, y), 10, (0, 255, 255), -1)
        
        return True

class ShieldDrone(Drone):
    def __init__(self, frame_width, frame_height):
        super().__init__(frame_width, frame_height)
        self.shield_active = True
        self.hp = 2

    def hit(self):
        self.hp -= 1
        if self.hp <= 0:
            return True # Destroyed
        self.shield_active = False
        return False # Still alive

    def draw(self, frame):
        if not super().draw(frame):
            return False
            
        if self.shield_active:
            x, y = int(self.anchor[0]), int(self.anchor[1])
            cv2.circle(frame, (x, y), self.size + 15, (255, 150, 0), 2)
            cv2.circle(frame, (x, y), self.size + 25, (255, 100, 0), 1)
            
        return True

class BossDrone(Drone):
    def __init__(self, frame_width, frame_height):
        super().__init__(frame_width, frame_height)
        self.size = 150
        self.hp = 10
        self.color = (0, 0, 255)
        self.strafe_speed = 1.0 # Slower strafe
        self.strafe_amplitude = 50.0
        self.vx *= 0.3 # Moving very slow
        self.vy *= 0.3
        self.last_fire_time = time.time()
        self.fire_rate = 1.5 # Fires much faster!

    def fire_laser(self, frame_width, frame_height):
        if time.time() - self.last_fire_time > self.fire_rate:
            self.last_fire_time = time.time()
            return EnemyLaser(self.anchor[0], self.anchor[1], frame_width//2, frame_height//2, speed=25)
        return None

    def hit(self):
        self.hp -= 1
        return self.hp <= 0

    def draw(self, frame):
        if not super().draw(frame):
            return False
            
        x, y = int(self.anchor[0]), int(self.anchor[1])
        hp_pct = max(0, self.hp / 10.0)
        bar_w = 200
        
        cv2.rectangle(frame, (x - bar_w//2 - 2, y - self.size - 42), (x + bar_w//2 + 2, y - self.size - 28), (255, 255, 255), 2)
        cv2.rectangle(frame, (x - bar_w//2, y - self.size - 40), (x - bar_w//2 + int(bar_w * hp_pct), y - self.size - 30), (0, 0, 255), -1)
        cv2.circle(frame, (x, y), self.size + 40, (0, 0, 150), 3)
        return True

class GameManager:
    def __init__(self):
        self.game_mode = False
        self.game_start_time = 0.0
        self.score = 0
        self.player_health = 100
        self.last_drone_spawn = 0.0
        self.time_left = 0.0
        self.boss_spawned = False

    def toggle_game_mode(self, canvas):
        if not self.game_mode:
            self.game_mode = True
            self.game_start_time = time.time()
            self.score = 0
            self.player_health = 100
            canvas.drones = []
            canvas.enemy_lasers = []
            self.last_drone_spawn = time.time()
            self.boss_spawned = False
            print("--- DRONE SURVIVAL INITIATED ---")
        else:
            self.game_mode = False
            print("--- DRONE SURVIVAL TERMINATED ---")

    def update(self, frame, canvas):
        if not self.game_mode:
            return

        self.time_left = max(0, 20.0 - (time.time() - self.game_start_time))
        if self.time_left <= 0 or self.player_health <= 0:
            self.game_mode = False
            canvas.drones = []
            canvas.enemy_lasers = []
            print(f"GAME OVER! Score: {self.score} | Health: {self.player_health}%")
        else:
            h, w, _ = frame.shape
            
            # Boss spawn condition at 10 seconds left
            if self.time_left <= 10.0 and not self.boss_spawned:
                canvas.drones.append(BossDrone(w, h))
                self.boss_spawned = True
                print("--- WARNING! BOSS INCOMING ---")
            
            # Spawn a drone every ~1.5 seconds if we have fewer than 4
            elif time.time() - self.last_drone_spawn > 1.5 and len(canvas.drones) < 5:
                if random.random() > 0.7:
                    canvas.drones.append(ShieldDrone(w, h))
                else:
                    canvas.drones.append(Drone(w, h))
                self.last_drone_spawn = time.time()
                
            # Evaluate Laser Hits Against Player (Center of screen implies hit)
            h, w, _ = frame.shape
            active_lasers = []
            for laser in canvas.enemy_lasers:
                lx, ly = laser.anchor
                # Center of the screen represents the Player's body/face
                if math.sqrt((lx - w//2)**2 + (ly - h//2)**2) < 50:
                    self.player_health -= 15 # Take damage!
                    # Flash red vignette
                    cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 20)
                else:
                    active_lasers.append(laser)
            canvas.enemy_lasers = active_lasers

    def get_closest_drone(self, canvas, hx, hy, min_dist):
        closest_drone = None
        if self.game_mode:
            for drone in canvas.drones:
                dx, dy = drone.anchor
                dist = math.sqrt((hx - dx)**2 + (hy - dy)**2)
                if dist < 120 and dist < min_dist: # 120 detection radius for fast drones
                    closest_drone = drone
                    min_dist = dist
        return closest_drone, min_dist

    def process_repulsor_aoe(self, canvas, hx, hy):
        if not self.game_mode:
            return

        surviving_drones = []
        for drone in canvas.drones:
            dx, dy = drone.anchor
            dist = math.sqrt((hx - dx)**2 + (hy - dy)**2)
            # Repulsor has an AoE blast radius of ~200 pixels
            if dist < 200:
                destroyed = drone.hit()
                if destroyed:
                    canvas.explosions.append(Explosion(dx, dy, drone.color))
                    self.score += 10 # Kill score!
                else:
                    canvas.explosions.append(Explosion(dx, dy, (255, 200, 0), count=5)) # Shield hit spark
                    surviving_drones.append(drone)
                    self.score += 5 # Shield hit point
            else:
                surviving_drones.append(drone)
        canvas.drones = surviving_drones

    def process_shield_deflect(self, canvas, anchor, scale_multiplier):
        if not self.game_mode:
            return

        active_lasers = []
        for laser in canvas.enemy_lasers:
            lx, ly = laser.anchor
            dist_to_shield = math.sqrt((lx - anchor[0])**2 + (ly - anchor[1])**2)
            if dist_to_shield < int(150 * scale_multiplier):
                # Laser deflected! Explodes on shield
                canvas.explosions.append(Explosion(lx, ly, (0, 255, 255), count=10))
                self.score += 2 # Score for parrying
            else:
                active_lasers.append(laser)
        canvas.enemy_lasers = active_lasers

    def draw_hud_pillow(self, draw, title_font, frame_shape):
        if self.game_mode:
            msg = f"SURVIVE: {self.time_left:.1f}s | SCORE: {self.score} | HULL: {self.player_health}%"
            
            # Warn if health is low
            h_color = (255, 0, 0) # Red RGB if dangerous
            if self.player_health > 50:
                h_color = (0, 255, 0) # Green 
            elif self.player_health > 20:
                h_color = (255, 165, 0) # Orange
                
            draw.text((frame_shape[1] // 2 - 250, 40), msg, font=title_font, fill=h_color)

    def draw_hud_cv2(self, frame):
        if self.game_mode:
            msg = f"SURVIVE: {self.time_left:.1f}s | SCORE: {self.score} | HULL: {self.player_health}%"
            
            # Warn if health is low
            h_color = (0, 0, 255) # Red BGR if dangerous
            if self.player_health > 50:
                h_color = (0, 255, 0) # Green 
            elif self.player_health > 20:
                h_color = (0, 165, 255) # Orange
                
            cv2.putText(frame, msg, (frame.shape[1] // 2 - 250, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, h_color, 3, cv2.LINE_AA)
