import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import urllib.request
import os
import math

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")

#constant float to control how high holograms float above the hand
#increase this value to make shapes float higher
HOLOGRAM_HOVER_MULTIPLIER = 1.5

#smoothing factor for Exponential Moving Average (EMA)
#lower = smoother but more lag. Higher = faster but more jitter. (Range: 0.0 - 1.0)
EMA_ALPHA = 0.5

class HandTracker:
    def __init__(self):
        #download model if not present
        if not os.path.exists(MODEL_PATH):
            print("Downloading hand landmarker model...")
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print("Download complete.")

        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        
        # State for EMA smoothing
        self.prev_x = None
        self.prev_y = None
        self.prev_scale = None
    
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
        """Returns (centroid_x, centroid_y, hand_span) or None."""
        # Convert the frame to a MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        
        # Detect hands
        results = self.detector.detect(mp_image)

        # No hand detected
        if not results.hand_landmarks:
            self.prev_x = self.prev_y = self.prev_scale = None
            return None
        
        hand_landmarks = results.hand_landmarks[0]

        # Indices: 5 (Index), 9 (Middle), 13 (Ring), 17 (Pinky)
        knuckles = [5, 9, 13, 17]

        h, w, _ = frame_rgb.shape
        sum_x, sum_y = 0, 0
        min_x, max_x = float('inf'), float('-inf')
        min_y, max_y = float('inf'), float('-inf')

        for idx in knuckles:
            lm = hand_landmarks[idx]
            px, py = lm.x * w, lm.y * h
            sum_x += px
            sum_y += py
            min_x, max_x = min(min_x, px), max(max_x, px)
            min_y, max_y = min(min_y, py), max(max_y, py)
        
        centroid_x = int(sum_x / 4)
        centroid_y = int(sum_y / 4)

        thumb = hand_landmarks[4]
        pinky = hand_landmarks[20]
        thumb_x, thumb_y = thumb.x * w, thumb.y * h
        pinky_x, pinky_y = pinky.x * w, pinky.y * h

        spread_pixels = math.sqrt((pinky_x - thumb_x)**2 + (pinky_y - thumb_y)**2)
        scale_multiplier = spread_pixels / 150
        handedness = results.handedness[0][0].category_name

        is_upright, palm_facing_camera = self._is_hand_upright(hand_landmarks, handedness)
        
        # If the hand is upright but the palm is facing you, don't show any shape
        if is_upright and not palm_facing_camera:
            self.prev_x = self.prev_y = self.prev_scale = None
            return None

        handedness_label = "Right"
        if results.handedness and len(results.handedness) > 0:
            handedness_label = results.handedness[0][0].category_name
        
        # Default state: Hand is closed or resting (Glove only, no weapons)
        pose_type = "NONE" 
        
        # Only check for weapons IF the palm is open
        if self._is_palm_open(hand_landmarks):
            is_upright, palm_facing_camera = self._is_hand_upright(hand_landmarks, handedness_label)
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
        else:
            # If state is "NONE", just lock the invisible anchor to the knuckles
            target_x = centroid_x
            target_y = centroid_y

        # Apply Exponential Moving Average (EMA) for smoothing
        is_firing = False
        speed = 0.0
        if self.prev_x is None:
            self.prev_x = target_x
            self.prev_y = target_y
            self.prev_scale = scale_multiplier
        else:
            # Thrust detection: check raw change before smoothing
            dx = target_x - self.prev_x
            dy = target_y - self.prev_y
            speed = math.sqrt(dx**2 + dy**2)
            d_scale = scale_multiplier - self.prev_scale
            
            if pose_type == "REPULSOR":
                if d_scale > 0.15:
                    is_firing = "CAMERA"
                elif speed > 50:
                    is_firing = "TARGET"
            
            self.prev_x = int(EMA_ALPHA * target_x + (1 - EMA_ALPHA) * self.prev_x)
            self.prev_y = int(EMA_ALPHA * target_y + (1 - EMA_ALPHA) * self.prev_y)
            self.prev_scale = EMA_ALPHA * scale_multiplier + (1 - EMA_ALPHA) * self.prev_scale
        
        return (self.prev_x, self.prev_y), self.prev_scale, pose_type, hand_landmarks, is_firing, speed