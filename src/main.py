import cv2
import time
import math
from hand_tracker import HandTracker
from diamond import HologramDiamond
from diamond import HologramDiamond
from repulsor import Repulsor
from exoskeleton import Exoskeleton
from canvas import ARCanvas, Explosion, RepulsorBlast
from audio_manager import AudioManager

def main():
    cap = cv2.VideoCapture(0)
    tracker = HandTracker()
    diamond = HologramDiamond(size=50)
    repulsor = Repulsor(base_radius=50)
    glove = Exoskeleton()
    canvas = ARCanvas()
    audio = AudioManager()

    draw_mode = False
    repulsor_cooldown_until = 0.0
    firing_armed = False # Prevent misfires on pose entry
    prev_pose = "NONE" # Track pose changes
    pending_fire_start = 0.0 # Time when thrust was initiated
    
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
        
        # Status tracking for HUD
        r_status, r_color = "INACTIVE", (0, 0, 255) # Red
        d_status, d_color = "INACTIVE", (0, 0, 255) # Red
        dm_status, dm_color = ("ACTIVE (Pinch to Draw)", (0, 255, 0)) if draw_mode else ("INACTIVE", (0, 0, 255))
        
        # Always draw the spawned shapes and explosions, even if no hand is detected
        canvas.render_shapes(frame)

        #draw the anchor if it exists
        if tracking_data is not None:
            anchor, scale_multiplier, pose_type, landmarks, is_firing, speed = tracking_data
            
            # Reset sequence if pose changes
            if pose_type != prev_pose and not draw_mode:
                pending_fire_start = 0.0
                if pose_type != "REPULSOR":
                    audio.stop_charge()
            prev_pose = pose_type

            if draw_mode:
                audio.stop_charge()
                # Suspend the HUD, route raw landmarks into the Canvas
                canvas.process_interactions(frame, landmarks)
            else:
                #Always draw the Exoskeleton, regardless of pose
                glove.draw(frame, landmarks)
            
                #Render weapons conditionally
                if pose_type == "REPULSOR":
                    repulsor.draw(frame, anchor, scale_multiplier)
                    
                    # Logic: If already charging to fire, handle the sequence
                    if pending_fire_start > 0:
                        elapsed = time.time() - pending_fire_start
                        
                        if elapsed < 0.6:
                            # Charging phase: Show progress and visuals
                            r_status, r_color = f"CHARGING... {int((elapsed/0.6)*100)}%", (0, 255, 255)
                            # Intense charging visual (growing energy ball)
                            ball_radius = int(20 + 60 * (elapsed / 0.6))
                            cv2.circle(frame, anchor, ball_radius, (255, 255, 255), 2)
                            cv2.circle(frame, anchor, int(ball_radius * 0.7), (0, 255, 255), -1)
                        else:
                            # FIRE ACTION!
                            audio.play_fire()
                            hx, hy = anchor
                            hit_shape = None
                            min_dist = float('inf')
                            
                            # Add a visual flash effect to the Repulsor for firing
                            cv2.circle(frame, anchor, int(100 * scale_multiplier), (255, 255, 255), 10)

                            # Target acquisition
                            for shape in canvas.spawned_shapes:
                                base_size = getattr(shape, 'size', getattr(shape, 'w_size', 50))
                                sx, sy = shape.anchor
                                dist = math.sqrt((hx - sx)**2 + (hy - sy)**2)
                                if dist < base_size * 2.5 and dist < min_dist:
                                    hit_shape = shape
                                    min_dist = dist
                                    
                            if hit_shape:
                                canvas.beams.append(RepulsorBlast(hx, hy))
                                destroyed = hit_shape.hit()
                                if destroyed:
                                    canvas.explosions.append(Explosion(hit_shape.anchor[0], hit_shape.anchor[1], hit_shape.color))
                                    canvas.spawned_shapes.remove(hit_shape)
                            else:
                                canvas.beams.append(RepulsorBlast(hx, hy))
                                
                            # Reset sequence
                            pending_fire_start = 0.0
                            repulsor_cooldown_until = time.time() + 2.0
                            r_status, r_color = "COOLDOWN", (0, 0, 255)
                    
                    else:
                        # Waiting for trigger
                        if time.time() < repulsor_cooldown_until:
                            r_status, r_color = "COOLDOWN", (0, 0, 255)
                        else:
                            r_status, r_color = "READY", (0, 255, 0)
                        
                        # Trigger detection
                        if not is_firing:
                            firing_armed = True
                            
                        if is_firing and firing_armed and time.time() > repulsor_cooldown_until:
                            pending_fire_start = time.time()
                            firing_armed = False
                            audio.start_charge()
                                
                elif pose_type == "DIAMOND":
                    diamond.draw(frame, anchor, scale_multiplier)
                    d_status, d_color = "ACTIVE", (0, 255, 0) # Green
                else:
                    audio.stop_charge()

                #draw a solid green dot at the exact (x, y) centroid
                cv2.circle(frame, anchor, 5, (0, 255, 0), -1)

        else:
            # If hand is completely off screen, silence weapons
            audio.stop_charge()

        #add text overlay
        cv2.putText(frame, "HOLOGRAM_AR", (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, f"REPULSOR:  {r_status}", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.2, r_color, 3, cv2.LINE_AA)
        cv2.putText(frame, f"DIAMOND:   {d_status}", (30, 170), cv2.FONT_HERSHEY_SIMPLEX, 1.2, d_color, 3, cv2.LINE_AA)
        cv2.putText(frame, f"DRAW MODE: {dm_status}", (30, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.2, dm_color, 3, cv2.LINE_AA)

        #show the live feed
        cv2.imshow('AR Interactive Hologram', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    audio.cleanup()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()