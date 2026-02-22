import cv2
import time
import math
import random
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from hand_tracker import HologramTracker
from diamond import HologramDiamond
from repulsor import Repulsor
from exoskeleton import Exoskeleton
from shield import EnergyShield
from canvas import ARCanvas, Explosion, RepulsorBlast
from audio_manager import AudioManager
from gamemode.game import GameManager, Drone, EnemyLaser
from scaling import process_scaling
from unibeam import ArcReactor, UnibeamBlast

def draw_target_brackets(frame, center, size=30, color=(255, 255, 0), thickness=2):
    x, y = center
    l = size // 2
    # Top-Left
    cv2.line(frame, (x - l, y - l), (x - l + l//2, y - l), color, thickness)
    cv2.line(frame, (x - l, y - l), (x - l, y - l + l//2), color, thickness)
    # Top-Right
    cv2.line(frame, (x + l, y - l), (x + l - l//2, y - l), color, thickness)
    cv2.line(frame, (x + l, y - l), (x + l, y - l + l//2), color, thickness)
    # Bottom-Left
    cv2.line(frame, (x - l, y + l), (x - l + l//2, y + l), color, thickness)
    cv2.line(frame, (x - l, y + l), (x - l, y + l - l//2), color, thickness)
    # Bottom-Right
    cv2.line(frame, (x + l, y + l), (x + l - l//2, y + l), color, thickness)
    cv2.line(frame, (x + l, y + l), (x + l, y + l - l//2), color, thickness)

def main():
    cap = cv2.VideoCapture(0)
    tracker = HologramTracker()
    diamond = HologramDiamond(size=50)
    repulsor = Repulsor(base_radius=50)
    glove = Exoskeleton()
    shield = EnergyShield()
    canvas = ARCanvas()
    audio = AudioManager()

    try:
        hud_font = ImageFont.truetype("assets/fonts/Orbitron.ttf", 24)
        title_font = ImageFont.truetype("assets/fonts/Orbitron.ttf", 32)
    except IOError:
        print("Font not found, using default OpenCV font")
        hud_font = None
        title_font = None

    draw_mode = False
    scale_mode = False
    game = GameManager()
    
    arc_reactor = ArcReactor(0, 0)
    unibeam_blasts = []
    wrists_crossed = False
    unibeam_charging = False
    unibeam_charge_start_time = 0.0
    u_status, u_color = "STANDBY", (100, 100, 0) # Unibeam Status
    unibeam_cooldown_until = 0.0
    
    repulsor_cooldown_until = {"Left": 0.0, "Right": 0.0}
    firing_armed = {"Left": False, "Right": False} # Prevent misfires on pose entry
    prev_pose = {"Left": "NONE", "Right": "NONE"} # Track pose changes
    pending_fire_start = {"Left": 0.0, "Right": 0.0} # Time when thrust was initiated
    
    print("--- AR INTERACTIVE HOLOGRAM BOOTING ---")
    print("1. Show your open palm to the camera.")
    print("2. Spread your fingers wide to grow the diamond.")
    print("3. Pinch your fingers together to shrink it.")
    print("4. Press 'q' to quit.")
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success: continue
        
        #flip the frame horizontally for a natural mirror-like AR experience
        frame = cv2.flip(frame, 1)
        
        #convert to RGB for the AI
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        #anchor coordinates
        tracking_data = tracker.get_anchor_point(frame_rgb)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('d'):
            draw_mode = not draw_mode 
            print(f"Draw Mode: {'ON' if draw_mode else 'OFF'}")
        elif key == ord('c'):
            canvas.spawned_shapes = [] # Delete all 3D objects from memory
            canvas.stroke_path = []
            canvas.cooldown_until = time.time() + 2.0 # 2 second draw cooldown
        
        # Status tracking for HUD - Iron Man Theme (Cyan)
        r_status, r_color = "STANDBY", (100, 100, 0) # Dark Cyan
        d_status, d_color = "STANDBY", (100, 100, 0) # Dark Cyan
        s_status, s_color = "STANDBY", (100, 100, 0) # Dark Cyan
        dm_status, dm_color = ("ACTIVE (Pinch to Draw)", (255, 255, 0)) if draw_mode else ("STANDBY", (100, 100, 0))
        sm_status, sm_color = ("ACTIVE (Dual Pinch)", (255, 255, 0)) if scale_mode else ("STANDBY", (100, 100, 0))
        gm_status, gm_color = ("ACTIVE (Defend!)", (0, 0, 255)) if game.game_mode else ("STANDBY (Press G)", (100, 100, 0))
        
        # --- GAME MODE SYSTEM ---
        game.update(frame, canvas)

        # Always draw the spawned shapes and explosions, even if no hand is detected
        canvas.render_shapes(frame)

        # --- TWO-HANDED SCALING LOGIC ---
        is_dual_scaling, sm_status, sm_color = process_scaling(
            frame, tracking_data, scale_mode, canvas, sm_status, sm_color
        )

        is_crossed_now = False # Default state
        #draw the anchor if it exists
        if tracking_data:
            # --- PRE-LOOP GESTURE DETECTION (UNIBEAM) ---
            if len(tracking_data) == 2:
                left_wrist, right_wrist = None, None
                for hand_data in tracking_data:
                    handedness = hand_data[6]
                    if handedness == "Left":
                        left_wrist = hand_data[3][0]
                    else:
                        right_wrist = hand_data[3][0]
                
                if left_wrist and right_wrist:
                    if left_wrist.x > right_wrist.x:
                        is_crossed_now = True

            any_repulsor_active = False
            for hand_data in tracking_data:
                anchor, scale_multiplier, pose_type, landmarks, is_firing, speed, handedness = hand_data
                
                # Reset sequence if pose changes
                if pose_type != prev_pose[handedness] and not draw_mode:
                    pending_fire_start[handedness] = 0.0
                prev_pose[handedness] = pose_type

                # Always draw the Exoskeleton, regardless of mode or pose
                glove.draw(frame, landmarks)

                if draw_mode:
                    # Route raw landmarks into the Canvas
                    canvas.process_interactions(frame, landmarks)
                elif scale_mode:
                    # Suspend weapons and drawing, but allow grabbing/moving shapes
                    if not is_dual_scaling:
                        canvas.process_interactions(frame, landmarks, allow_drawing=False)
                elif not (wrists_crossed or is_crossed_now or unibeam_charging):
                    # Render weapons conditionally (Suppressed if Unibeam is active/charging)
                    if pose_type == "REPULSOR":
                        any_repulsor_active = True
                        repulsor.draw(frame, anchor, scale_multiplier)
                        
                        # Find closest target to aim at
                        hx, hy = anchor
                        closest_shape = None
                        min_dist = float('inf')
                        for shape in canvas.spawned_shapes:
                            base_size = getattr(shape, 'size', getattr(shape, 'w_size', 50))
                            sx, sy = shape.anchor
                            dist = math.sqrt((hx - sx)**2 + (hy - sy)**2)
                            if dist < base_size * 2.5 and dist < min_dist: # 2.5 detection radius
                                closest_shape = shape
                                min_dist = dist
                                
                        closest_drone, min_dist = game.get_closest_drone(canvas, hx, hy, min_dist)
                        if closest_drone:
                            closest_shape = None # Prioritize drones over shapes
                                
                        if closest_shape:
                            # Draw locked-on red reticle over shape target
                            cx, cy = closest_shape.anchor
                            radius = int(getattr(closest_shape, 'size', getattr(closest_shape, 'w_size', 50)) * 1.5)
                            cv2.circle(frame, (cx, cy), radius, (0, 0, 255), 2)
                            cv2.line(frame, (cx - radius - 10, cy), (cx - radius + 10, cy), (0, 0, 255), 2)
                            cv2.line(frame, (cx + radius + 10, cy), (cx + radius - 10, cy), (0, 0, 255), 2)
                            cv2.line(frame, (cx, cy - radius - 10), (cx, cy - radius + 10), (0, 0, 255), 2)
                            cv2.line(frame, (cx, cy + radius + 10), (cx, cy + radius - 10), (0, 0, 255), 2)
                            
                        elif closest_drone:
                            # Draw locked-on red reticle over drone target
                            cx, cy = int(closest_drone.anchor[0]), int(closest_drone.anchor[1])
                            radius = int(closest_drone.size * 1.5)
                            cv2.circle(frame, (cx, cy), radius, (0, 0, 255), 2)
                            cv2.line(frame, (cx - radius - 10, cy), (cx - radius + 10, cy), (0, 0, 255), 2)
                            cv2.line(frame, (cx + radius + 10, cy), (cx + radius - 10, cy), (0, 0, 255), 2)
                            cv2.line(frame, (cx, cy - radius - 10), (cx, cy - radius + 10), (0, 0, 255), 2)
                            cv2.line(frame, (cx, cy + radius + 10), (cx, cy + radius - 10), (0, 0, 255), 2)

                        # Logic: If already charging to fire, handle the sequence
                        if pending_fire_start[handedness] > 0:
                            elapsed = time.time() - pending_fire_start[handedness]
                            
                            if elapsed < 0.3:
                                # Charging phase: Show progress and visuals
                                r_status, r_color = f"CHARGING... {int((elapsed/0.3)*100)}%", (255, 255, 0)
                                # Intense charging visual (growing energy ball)
                                ball_radius = int(20 + 60 * (elapsed / 0.3))
                                cv2.circle(frame, anchor, ball_radius, (255, 255, 255), 2)
                                cv2.circle(frame, anchor, int(ball_radius * 0.7), (255, 255, 0), -1)
                            else:
                                # FIRE ACTION!
                                audio.play_fire()
                                hx, hy = anchor
                                
                                # Add a visual flash effect to the Repulsor for firing
                                cv2.circle(frame, anchor, int(100 * scale_multiplier), (255, 255, 255), 10)

                                canvas.beams.append(RepulsorBlast(hx, hy))
                                
                                # Process Shape Hits
                                if closest_shape:
                                    destroyed = closest_shape.hit()
                                    if destroyed:
                                        canvas.explosions.append(Explosion(closest_shape.anchor[0], closest_shape.anchor[1], closest_shape.color))
                                        canvas.spawned_shapes.remove(closest_shape)
                                
                                # Process AoE Drone Destruction
                                game.process_repulsor_aoe(canvas, hx, hy)
                                    
                                # Reset sequence
                                pending_fire_start[handedness] = 0.0
                                repulsor_cooldown_until[handedness] = time.time() + 0.4
                                r_status, r_color = "COOLDOWN", (0, 0, 255)
                        
                        else:
                            # Waiting for trigger
                            if time.time() < repulsor_cooldown_until[handedness]:
                                r_status, r_color = "COOLING DOWN", (0, 150, 255) # Orange Warning
                            else:
                                r_status, r_color = "ENGAGED", (255, 255, 0) # Cyan Ready
                            
                            # Trigger detection
                            if not is_firing:
                                firing_armed[handedness] = True
                                
                            if is_firing and firing_armed[handedness] and time.time() > repulsor_cooldown_until[handedness]:
                                pending_fire_start[handedness] = time.time()
                                firing_armed[handedness] = False
                                
                    elif pose_type == "DIAMOND":
                        diamond.draw(frame, anchor, scale_multiplier)
                        d_status, d_color = "ACTIVATED", (255, 255, 0) # Cyan
                        
                    elif pose_type == "SHIELD":
                        shield.draw(frame, anchor, scale_multiplier)
                        s_status, s_color = "DEPLOYED", (255, 255, 0) # Cyan
                        
                        # Evaluate Deflecting Lasers
                        game.process_shield_deflect(canvas, anchor, scale_multiplier)

                #draw a sci-fi brackets tracking reticle and a faint center dot
                draw_target_brackets(frame, anchor, size=40, color=(255, 255, 0), thickness=2)
                cv2.circle(frame, anchor, 2, (0, 255, 255), -1)
                
            if any_repulsor_active:
                audio.start_charge()
            else:
                audio.stop_charge()

        else:
            # If hand is completely off screen, silence weapons
            audio.stop_charge()

        # --- POSE/CHEST TRACKING ---
        chest_pos = tracker.get_pose_data(frame_rgb)

        # --- UNIBEAM LOGIC ---
        # (is_crossed_now is pre-calculated above the hand loop)
        chest_x = frame.shape[1] // 2
        chest_y = int(frame.shape[0] * 0.8)

        if chest_pos:
            chest_x, chest_y = chest_pos

        if tracking_data and len(tracking_data) == 2:
            left_wrist, right_wrist = None, None
            for hand_data in tracking_data:
                handedness = hand_data[6]
                if handedness == "Left":
                    left_wrist = hand_data[3][0] # Landmark 0 is the wrist
                else:
                    right_wrist = hand_data[3][0]
            
            if left_wrist and right_wrist:
                w, h = frame.shape[1], frame.shape[0]
                
                # If pose is not detection, FALL BACK to wrist midpoint for chest position
                if not chest_pos:
                    chest_x = int((left_wrist.x + right_wrist.x) * w / 2)
                    chest_y = int((left_wrist.y + right_wrist.y) * h / 2) + 400



        arc_reactor.anchor = (chest_x, chest_y)
        charge_level = 0.0
        
        if time.time() < unibeam_cooldown_until:
            u_status, u_color = "COOLING DOWN", (0, 150, 255) # Orange Warning
            unibeam_charging = False
            wrists_crossed = False
        elif unibeam_charging:
            # Autonomous charging phase
            charge_duration = time.time() - unibeam_charge_start_time
            charge_level = min(1.0, charge_duration / 1.0)
            u_status, u_color = f"CHARGING... {int(charge_level*100)}%", (255, 255, 0)
            
            if charge_level >= 1.0:
                # FIRE!
                audio.play_fire()
                unibeam_blasts.append(UnibeamBlast(chest_x, chest_y))
                unibeam_cooldown_until = time.time() + 3.0
                unibeam_charging = False
                audio.stop_charge()
                
                if game.game_mode:
                    # Full Screen Wipe!
                    for drone in canvas.drones:
                        canvas.explosions.append(Explosion(drone.anchor[0], drone.anchor[1], drone.color))
                        game.score += 20
                    canvas.drones = []
        else:
            # Handle Pulse Trigger
            if is_crossed_now:
                if not wrists_crossed:
                    wrists_crossed = True
                    u_status, u_color = "SYSTEM ARMED", (0, 255, 255) # Cyan
            else:
                if wrists_crossed:
                    # PULSE DETECTED (Crossed then Uncrossed)
                    unibeam_charging = True
                    unibeam_charge_start_time = time.time()
                    audio.start_charge()
                    wrists_crossed = False
            
            if len(unibeam_blasts) > 0:
                u_status, u_color = "FIRING", (0, 0, 255)
            elif not wrists_crossed and time.time() > unibeam_cooldown_until:
                u_status, u_color = "STANDBY", (100, 100, 0)
            elif wrists_crossed:
                u_status, u_color = "SYSTEM ARMED", (0, 100, 255)


        # Draw Reactor
        arc_reactor.draw(frame, charge_level)
        
        # Draw Blasts
        active_blasts = []
        for blast in unibeam_blasts:
            if blast.draw(frame):
                active_blasts.append(blast)
        unibeam_blasts = active_blasts

        #add text overlay
        if hud_font and title_font:
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)
            
            # Using RGB colors for Pillow since we converted to RGB
            draw.text((30, 40), "HOLOGRAM AR SYSTEM", font=title_font, fill=(0, 255, 255))
            draw.text((30, 90), f"REPULSOR SYS:   {r_status}", font=hud_font, fill=r_color[::-1])
            draw.text((30, 130), f"UNIBEAM  SYS:   {u_status}", font=hud_font, fill=u_color[::-1])
            draw.text((30, 170), f"DIAMOND  SYS:   {d_status}", font=hud_font, fill=d_color[::-1])
            draw.text((30, 210), f"SHIELD   SYS:   {s_status}", font=hud_font, fill=s_color[::-1])
            draw.text((30, 250), f"DRAW     MODE:  {dm_status}", font=hud_font, fill=dm_color[::-1])
            draw.text((30, 290), f"SCALE    MODE:  {sm_status}", font=hud_font, fill=sm_color[::-1])
            draw.text((30, 330), f"GAME     MODE:  {gm_status}", font=hud_font, fill=gm_color[::-1])
            
            # --- MISSION HUD OVERLAY ---
            game.draw_hud_pillow(draw, title_font, frame.shape)
            
            frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            cv2.putText(frame, "HOLOGRAM AR SYSTEM", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(frame, f"REPULSOR SYS:   {r_status}", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, r_color, 2, cv2.LINE_AA)
            cv2.putText(frame, f"UNIBEAM  SYS:   {u_status}", (30, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, u_color, 2, cv2.LINE_AA)
            cv2.putText(frame, f"DIAMOND  SYS:   {d_status}", (30, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, d_color, 2, cv2.LINE_AA)
            cv2.putText(frame, f"SHIELD   SYS:   {s_status}", (30, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.8, s_color, 2, cv2.LINE_AA)
            cv2.putText(frame, f"DRAW     MODE:  {dm_status}", (30, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.8, dm_color, 2, cv2.LINE_AA)
            cv2.putText(frame, f"SCALE    MODE:  {sm_status}", (30, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, sm_color, 2, cv2.LINE_AA)
            cv2.putText(frame, f"GAME     MODE:  {gm_status}", (30, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.8, gm_color, 2, cv2.LINE_AA)
            
            # --- MISSION HUD OVERLAY ---
            game.draw_hud_cv2(frame)

        #show the live feed
        cv2.imshow('AR Interactive Hologram', frame)

        # Keyboard inputs
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('d'):
            draw_mode = not draw_mode
            if draw_mode:
                scale_mode = False # Disable scaling to prevent overlap
                canvas.stroke_path = [] # Reset any lingering strokes
        elif key == ord('s'):
            scale_mode = not scale_mode
            if scale_mode:
                draw_mode = False # Disable drawing to prevent overlap
                canvas.stroke_path = []
        elif key == ord('g'):
            game.toggle_game_mode(canvas)

    audio.cleanup()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()