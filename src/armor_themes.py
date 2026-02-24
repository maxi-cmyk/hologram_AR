"""
Armor color themes for the hologram AR suit.
Press 't' to cycle between themes at runtime.
"""

THEMES = {
    "mark_iii": {
        "name": "MARK III",
        # Exoskeleton
        "exo_base": (0, 0, 110),       # Dark Red
        "exo_edge": (0, 0, 150),       # Lighter Red
        "exo_accent": (0, 200, 255),   # Gold

        # Repulsor
        "repulsor_glow": (255, 255, 0),     # Cyan
        "repulsor_core": (255, 255, 255),   # White
        "repulsor_spark": (0, 165, 255),    # Orange

        # Shield
        "shield_primary": (0, 255, 255),    # Yellow/Gold
        "shield_secondary": (0, 200, 255),  # Orange
        "shield_core": (0, 150, 255),       # Deep Orange

        # Arc Reactor
        "reactor_glow": (255, 255, 255),    # White
        "reactor_ring": (255, 255, 0),      # Cyan
        "reactor_core": (255, 255, 0),      # Cyan

        # HUD
        "hud_accent": (0, 255, 255),        # Cyan (RGB for Pillow)
        "hud_title": (0, 255, 255),
    },
    "war_machine": {
        "name": "WAR MACHINE",
        # Exoskeleton
        "exo_base": (80, 80, 80),        # Gunmetal
        "exo_edge": (140, 140, 140),     # Silver
        "exo_accent": (180, 180, 180),   # Bright Silver

        # Repulsor
        "repulsor_glow": (255, 255, 255),    # White
        "repulsor_core": (255, 255, 255),    # White
        "repulsor_spark": (200, 200, 255),   # Light Blue-White

        # Shield
        "shield_primary": (255, 200, 150),   # Light Blue
        "shield_secondary": (255, 150, 100), # Blue
        "shield_core": (255, 100, 50),       # Deep Blue

        # Arc Reactor
        "reactor_glow": (255, 255, 255),     # White
        "reactor_ring": (255, 200, 150),     # Light Blue
        "reactor_core": (255, 200, 150),     # Light Blue

        # HUD
        "hud_accent": (75, 130, 40),         # Army Green (RGB for Pillow)
        "hud_title": (75, 130, 40),
    },
}

THEME_ORDER = ["mark_iii", "war_machine"]

class ThemeManager:
    def __init__(self):
        self.index = 0
    
    def cycle(self):
        """Cycle to the next armor theme."""
        self.index = (self.index + 1) % len(THEME_ORDER)
        return self.get()
    
    def get(self):
        """Return the current theme dict."""
        key = THEME_ORDER[self.index]
        return THEMES[key]
    
    def get_name(self):
        """Return the display name of the current theme."""
        return self.get()["name"]
