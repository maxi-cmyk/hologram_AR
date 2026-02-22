# Hologram AR - Interactive Exoskeleton System

Hologram AR is my attempt at an immersive Augmented Reality application that uses your webcam and AI-powered hand tracking to overlay a futuristic exoskeleton and interactive holograms onto your live video feed.

## 🚀 Features

- **Dynamic Interactive Exoskeleton:** A real-time metallic armor overlay that follows your hand movements.
- **Hologram Diamond:** A floating holographic diamond that you can scale with pinch gestures.
- **Repulsor Weapon System:**
  - **Auto-Charge:** Open your palm to activate the weapon.
  - **Thrust Firing:** Thrust your hand forward to initiate a 0.6s charge sequence followed by a powerful blast.
  - **Dynamic HUD:** Real-time feedback on weapon status and charging progress.
- **Creative Canvas:** Enter "Draw Mode" to sketch 3D-like floating shapes in the air.
- **Physics-Based Targets:** Shapes you draw float in the air and react to being hit by the Repulsor (spinning and exploding into particles).
- **Custom Sound Effects:** Synchronized audio for repulsor charging and firing.

## 🛠 Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/your-username/hologram_AR.git
   cd hologram_AR
   ```

2. **Install dependencies:**
   Make sure you have Python 3.10+ installed.
   ```bash
   pip install -r requirement.txt
   ```

## 🎮 How to Use

Run the main application:

```bash
python src/main.py
```

### Controls:

- **'q'**: Quit the application.
- **'d'**: Toggle **Draw Mode**.
  - _When ON:_ Pinch your thumb and index finger to draw in 3D space.
- **'c'**: Clear the canvas (removes all drawings).
- **'REPULSOR' Pose**: Open your palm wide to activate the repulsor.
  - **Thrust**: Move your hand quickly toward the screen/extend fingers to fire.
- **'DIAMOND' Pose**: flip palm up to summon the Diamond.
  - **Scale**: Spread/pinch fingers to resize the diamond.

## 📁 Project Structure

- `src/`: Core Python source code.
- `assets/sounds/`: External audio files for immersive SFX.
- `requirement.txt`: Python package dependencies.

## ⚖️ License

MIT License - feel free to build upon and modify!
