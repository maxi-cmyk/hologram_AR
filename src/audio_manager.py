import pygame
import os

class AudioManager:
    def __init__(self):
        # Initialize the pygame mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # Load sound assets
        base_path = "assets/sounds"
        self.sfx_boom = pygame.mixer.Sound(os.path.join(base_path, "repulsor_boom.wav"))
        self.sfx_charge = pygame.mixer.Sound(os.path.join(base_path, "repulsor_charge.mp3"))
        
        # Configure channels for concurrent audio
        self.weapon_channel = pygame.mixer.Channel(1)
        
        # State tracking
        self.is_charging = False

    def play_fire(self):
        """Plays the deep repulsor boom, interrupting any active charge sound."""
        self.is_charging = False
        self.weapon_channel.play(self.sfx_boom)
        
    def start_charge(self):
        """Starts the rising repulsor charge whine if not already playing."""
        if not self.is_charging and not self.weapon_channel.get_busy():
            self.weapon_channel.play(self.sfx_charge)
            self.is_charging = True

    def stop_charge(self):
        """Stops the charge sound if the user lowers their hand without firing."""
        if self.is_charging:
            self.weapon_channel.fadeout(200) # Quick fade out instead of hard cut
            self.is_charging = False

    def cleanup(self):
        pygame.mixer.quit()
