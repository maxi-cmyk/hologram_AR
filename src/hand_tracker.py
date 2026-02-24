import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import os
import math

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")

POSE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
POSE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "pose_landmarker_lite.task")

#constant float to control how high holograms float above the hand
#increase this value to make shapes float higher
HOLOGRAM_HOVER_MULTIPLIER = 1.5

#smoothing factor for Exponential Moving Average (EMA)
#lower = smoother but more lag. Higher = faster but more jitter. (Range: 0.0 - 1.0)
EMA_ALPHA = 0.5

class HologramTracker:
    def __init__(self):
        #download models if not present
        if not os.path.exists(MODEL_PATH):
            print("Downloading hand landmarker model...")
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print("Download complete.")

        if not os.path.exists(POSE_MODEL_PATH):
            print("Downloading pose landmarker model...")
            urllib.request.urlretrieve(POSE_MODEL_URL, POSE_MODEL_PATH)
            print("Download complete.")

        # Initialize Hand Landmarker
        hand_base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        hand_options = vision.HandLandmarkerOptions(
            base_options=hand_base_options,
            num_hands=2,
            min_hand_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.hand_detector = vision.HandLandmarker.create_from_options(hand_options)

        # Initialize Pose Landmarker
        pose_base_options = python.BaseOptions(model_asset_path=POSE_MODEL_PATH)
        pose_options = vision.PoseLandmarkerOptions(
            base_options=pose_base_options,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.pose_detector = vision.PoseLandmarker.create_from_options(pose_options)
        
        # State for EMA smoothing (per hand)
        self.prev_x = {"Left": None, "Right": None}
        self.prev_y = {"Left": None, "Right": None}
        self.prev_scale = {"Left": None, "Right": None}

    def _is_thumbs_up(self, landmarks):
        """Check if the hand is doing a thumbs-up: thumb extended, all 4 fingers curled."""
        wrist = landmarks[0]
        
        # Check thumb is extended (tip further from wrist than IP joint)
        thumb_tip_dist = math.sqrt((landmarks[4].x - wrist.x)**2 + (landmarks[4].y - wrist.y)**2 + (landmarks[4].z - wrist.z)**2)
        thumb_ip_dist = math.sqrt((landmarks[3].x - wrist.x)**2 + (landmarks[3].y - wrist.y)**2 + (landmarks[3].z - wrist.z)**2)
        thumb_extended = thumb_tip_dist > thumb_ip_dist
        
        # Check 4 fingers are curled
        fingers = [(8, 6), (12, 10), (16, 14), (20, 18)]
        curled = 0
        for tip, pip in fingers:
            dist_tip = math.sqrt((landmarks[tip].x - wrist.x)**2 + (landmarks[tip].y - wrist.y)**2 + (landmarks[tip].z - wrist.z)**2)
            dist_pip = math.sqrt((landmarks[pip].x - wrist.x)**2 + (landmarks[pip].y - wrist.y)**2 + (landmarks[pip].z - wrist.z)**2)
            if dist_tip < dist_pip:
                curled += 1
        
        # Thumb must point upward (tip Y < IP Y in normalized coords)
        thumb_pointing_up = landmarks[4].y < landmarks[3].y
        
        return thumb_extended and curled >= 3 and thumb_pointing_up

    
    def _is_palm_open(self, landmarks):
        """Check if the hand is open by comparing 3D distance from wrist to fingertips vs PIP joints.
        If a finger is curled into a fist, the tip is closer to the wrist than the PIP joint."""
        fingers = [(8, 6), (12, 10), (16, 14), (20, 18)]
        wrist = landmarks[0]
        
        extended = 0
        for tip, pip in fingers:
            # 3D distance from wrist to tip
            dist_tip = math.sqrt((landmarks[tip].x - wrist.x)**2 + 
                                 (landmarks[tip].y - wrist.y)**2 + 
                                 (landmarks[tip].z - wrist.z)**2)
            # 3D distance from wrist to PIP
            dist_pip = math.sqrt((landmarks[pip].x - wrist.x)**2 + 
                                 (landmarks[pip].y - wrist.y)**2 + 
                                 (landmarks[pip].z - wrist.z)**2)
            
            # If the tip is further from the wrist than the PIP, it's extended
            if dist_tip > dist_pip:
                extended += 1
                
        return extended >= 3

    def _is_hand_upright(self, landmarks, handedness):
        """
        Checks if the hand is pointing straight up.
        Wrist (0) must be physically lower on the screen (higher Y value) 
        than the Middle Finger Base (9).
        """
        wrist = landmarks[0]
        middle_base = landmarks[9]
        thumb = landmarks[4]
        pinky = landmarks[17]
        
        # We add 0.1 (10% of the screen) as a strict buffer so it only
        # triggers when the hand is completely vertical like a stop sign.
        is_upright = wrist.y > middle_base.y + 0.1

        if handedness == "Left":
            # Mirrored Right Hand: Thumb must be on the left side of the screen
            palm_facing_camera = thumb.x < pinky.x
        else:
            # Mirrored Left Hand: Thumb must be on the right side of the screen
            palm_facing_camera = thumb.x > pinky.x

        return is_upright, palm_facing_camera

    def get_anchor_point(self, frame_rgb):
        """Returns a list of tracking data for each detected hand: 
           [(anchor, scale_multiplier, pose_type, landmarks, is_firing, speed, handedness), ...]"""
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        results = self.hand_detector.detect(mp_image)

        # Clear state for lost hands
        detected_hands = []
        if results.handedness:
            detected_hands = [h[0].category_name for h in results.handedness]
            
        for h_label in ["Left", "Right"]:
            if h_label not in detected_hands:
                self.prev_x[h_label] = None
                self.prev_y[h_label] = None
                self.prev_scale[h_label] = None

        if not results.hand_landmarks:
            return []
        
        tracking_list = []
        h, w, _ = frame_rgb.shape

        for i, hand_landmarks in enumerate(results.hand_landmarks):
            handedness = results.handedness[i][0].category_name
            
            knuckles = [5, 9, 13, 17]
            sum_x, sum_y = 0, 0
            for idx in knuckles:
                lm = hand_landmarks[idx]
                sum_x += lm.x * w
                sum_y += lm.y * h
            
            centroid_x = int(sum_x / 4)
            centroid_y = int(sum_y / 4)

            thumb = hand_landmarks[4]
            pinky = hand_landmarks[20]
            thumb_x, thumb_y = thumb.x * w, thumb.y * h
            pinky_x, pinky_y = pinky.x * w, pinky.y * h

            spread_pixels = math.sqrt((pinky_x - thumb_x)**2 + (pinky_y - thumb_y)**2)
            scale_multiplier = spread_pixels / 150

            pose_type = "NONE" 
            
            if not self._is_palm_open(hand_landmarks):
                # Shield: closed fists facing camera or knuckles pointing to camera
                wrist = hand_landmarks[0]
                index_mcp = hand_landmarks[5]
                pinky_mcp = hand_landmarks[17]
                
                # Z depth to see if knuckles are pointed at the camera (-Z is closer to camera)
                knuckles_forward = index_mcp.z < -0.015
                
                # Check 2D orientation to see if back of hand faces camera
                v1 = (index_mcp.x - wrist.x, index_mcp.y - wrist.y)
                v2 = (pinky_mcp.x - wrist.x, pinky_mcp.y - wrist.y)
                cross = v1[0] * v2[1] - v1[1] * v2[0]
                is_back_facing = (cross < 0) if handedness == "Left" else (cross > 0)
                
                if is_back_facing or knuckles_forward:
                    pose_type = "SHIELD"
            else:
                    is_upright, palm_facing_camera = self._is_hand_upright(hand_landmarks, handedness)
                    # Repulsor works on both hands (open palm facing camera)
                    if is_upright and palm_facing_camera:
                        pose_type = "REPULSOR"
                    elif is_upright and not palm_facing_camera:
                        pose_type = "NONE"
                    else:
                        pose_type = "DIAMOND"

            # --- THE ANCHOR TARGETS ---
            if pose_type == "REPULSOR":
                wrist = hand_landmarks[0]
                wrist_x, wrist_y = wrist.x * w, wrist.y * h
                target_x = int(centroid_x * 0.7 + wrist_x * 0.3)
                target_y = int(centroid_y * 0.7 + wrist_y * 0.3)
            elif pose_type == "DIAMOND":
                hover_offset = int(spread_pixels * HOLOGRAM_HOVER_MULTIPLIER)
                target_x = centroid_x
                target_y = centroid_y - hover_offset
            elif pose_type == "SHIELD":
                # Shield centers around the fist centroid
                target_x = centroid_x
                target_y = centroid_y
            else:
                target_x = centroid_x
                target_y = centroid_y

            # Apply Exponential Moving Average (EMA) for smoothing
            is_firing = False
            speed = 0.0
            
            if self.prev_x[handedness] is None:
                self.prev_x[handedness] = target_x
                self.prev_y[handedness] = target_y
                self.prev_scale[handedness] = scale_multiplier
            else:
                dx = target_x - self.prev_x[handedness]
                dy = target_y - self.prev_y[handedness]
                speed = math.sqrt(dx**2 + dy**2)
                d_scale = scale_multiplier - self.prev_scale[handedness]
                
                if pose_type == "REPULSOR":
                    if d_scale > 0.15:
                        is_firing = "CAMERA"
                    elif speed > 50:
                        is_firing = "TARGET"
                
                self.prev_x[handedness] = int(EMA_ALPHA * target_x + (1 - EMA_ALPHA) * self.prev_x[handedness])
                self.prev_y[handedness] = int(EMA_ALPHA * target_y + (1 - EMA_ALPHA) * self.prev_y[handedness])
                self.prev_scale[handedness] = EMA_ALPHA * scale_multiplier + (1 - EMA_ALPHA) * self.prev_scale[handedness]
            
            tracking_list.append(
                ((self.prev_x[handedness], self.prev_y[handedness]), 
                 self.prev_scale[handedness], 
                 pose_type, 
                 hand_landmarks, 
                 is_firing, 
                 speed, 
                 handedness)
            )
            
        return tracking_list

    def get_pose_data(self, frame_rgb):
        """Returns the approximate chest position based on shoulder landmarks."""
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        results = self.pose_detector.detect(mp_image)
        
        if not results.pose_landmarks:
            return None
            
        h, w, _ = frame_rgb.shape
        # Landmark 11: Left Shoulder, 12: Right Shoulder
        pose_landmarks = results.pose_landmarks[0]
        l_shoulder = pose_landmarks[11]
        r_shoulder = pose_landmarks[12]
        
        # Calculate midpoint
        mid_x = (l_shoulder.x + r_shoulder.x) / 2
        mid_y = (l_shoulder.y + r_shoulder.y) / 2
        
        # Offset down slightly to reach the center of the chest
        chest_x = int(mid_x * w)
        chest_y = int((mid_y + 0.15) * h) # 15% of height downward shift
        
        return (chest_x, chest_y)