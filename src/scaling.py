import cv2
import math

def process_scaling(frame, tracking_data, scale_mode, canvas, sm_status, sm_color):
    is_dual_scaling = False
    
    if tracking_data and scale_mode and len(tracking_data) == 2:
        h, w, _ = frame.shape
        pinching_hands = []
        for hand_data in tracking_data:
            landmarks = hand_data[3]
            ix, iy = int(landmarks[8].x * w), int(landmarks[8].y * h)
            tx, ty = int(landmarks[4].x * w), int(landmarks[4].y * h)
            # Expanded pinch sensitivity specifically for scaling mode so it doesn't drop
            if math.sqrt((ix - tx)**2 + (iy - ty)**2) < 70.0:
                pinching_hands.append((ix, iy))
        
        if len(pinching_hands) == 2:
            is_dual_scaling = True
            hx1, hy1 = pinching_hands[0]
            hx2, hy2 = pinching_hands[1]
            current_dist = math.sqrt((hx1 - hx2)**2 + (hy1 - hy2)**2)
            
            if canvas.scaling_shape is None:
                # Find a shape to scale based on the midpoint between both hands
                mid_x = (hx1 + hx2) // 2
                mid_y = (hy1 + hy2) // 2
                closest_shape = None
                min_dist = float('inf')
                
                for shape in canvas.spawned_shapes:
                    cx, cy = shape.anchor
                    dist = math.sqrt((mid_x - cx)**2 + (mid_y - cy)**2)
                    
                    # Generous grab area (within ~500 pixels of hand midpoint)
                    if dist < 500.0 and dist < min_dist:
                        closest_shape = shape
                        min_dist = dist
                        
                if closest_shape:
                    canvas.scaling_shape = closest_shape
                    canvas.initial_pinch_dist = current_dist
                    if hasattr(closest_shape, 'size'):
                        canvas.initial_shape_size = closest_shape.size
                    else:
                        canvas.initial_shape_size = (closest_shape.w_size, closest_shape.h_size)
                    canvas.dragged_shape = None # Cancel single drag
                    
            if canvas.scaling_shape is not None:
                scale_factor = current_dist / max(1.0, canvas.initial_pinch_dist)
                shape = canvas.scaling_shape
                # Apply scale within limits
                if hasattr(shape, 'size'):
                    shape.size = max(10, min(500, int(canvas.initial_shape_size * scale_factor)))
                else:
                    shape.w_size = max(10, min(500, int(canvas.initial_shape_size[0] * scale_factor)))
                    shape.h_size = max(10, min(500, int(canvas.initial_shape_size[1] * scale_factor)))
                
                # Draw a cool connecting line
                cv2.line(frame, (hx1, hy1), (hx2, hy2), (0, 255, 255), 3)
                cv2.circle(frame, (hx1, hy1), 12, (0, 255, 255), -1)
                cv2.circle(frame, (hx2, hy2), 12, (0, 255, 255), -1)
                sm_status, sm_color = "ENGAGED (Pull to Zoom)", (255, 255, 0)
        else:
            canvas.scaling_shape = None
    else:
        canvas.scaling_shape = None
        
    return is_dual_scaling, sm_status, sm_color
