import pygame

SOUNDS = ["death", "eaten", "eyes", "frightened", "ready", "life"]


class Audio:
    def __init__(self) -> None:
        self.sound_dic = {}
        self.working = True
        try:
            pygame.mixer.pre_init(44100, -16, 2, 256)
            pygame.mixer.init()
            pygame.mixer.set_reserved(1)
            self.chan = pygame.mixer.Channel(0)
            self.chan.set_volume(0.02)
        except Exception as e:
            print(f"audio unavailable: {e}")
            self.working = False
        try:
            for s in SOUNDS:
                new_sound = pygame.mixer.Sound(f"audio/{s}.wav")
                self.sound_dic[s] = new_sound
        except Exception as e:
            print(f"problem while loading track: {e}")
            self.working = False

    def play_sound(self, sound: str) -> None:
        if self.working:
            self.sound_dic[sound].play()
