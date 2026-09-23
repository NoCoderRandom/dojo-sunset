"""Original synthesis and supplied recordings, preloaded for combat playback."""
import math
from pathlib import Path

import numpy as np
import pygame


class Audio:
    RATE = 44100

    def __init__(self, volume=.55):
        self.enabled = False
        self.sounds = {}
        self.volume = volume
        self.ambient = None
        self.hit_sequence = 0
        self.loaded_external = []
        try:
            pygame.mixer.init(self.RATE, -16, 2, 256, allowedchanges=0)
            pygame.mixer.set_num_channels(12)
            pygame.mixer.set_reserved(3)
            self.enabled = True
            self.build()
            self.load_recordings()
            self.set_volume(volume)
        except (pygame.error, ValueError):
            self.enabled = False

    def sound(self, wave):
        samples = np.clip(wave * 16000, -32767, 32767).astype(np.int16)
        stereo = np.column_stack((samples, samples))
        return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))

    def tone(self, frequency, duration, decay=8):
        t = np.arange(int(self.RATE * duration)) / self.RATE
        wave = np.sin(2 * math.pi * frequency * t)
        wave += .22 * np.sin(2 * math.pi * frequency * 2.01 * t)
        return wave * np.exp(-t * decay) * np.minimum(1, t * 120)

    def build(self):
        rng = np.random.default_rng(74)
        t = np.arange(int(self.RATE * .20)) / self.RATE
        noise = rng.uniform(-1, 1, len(t))
        hit = (.6 * noise + .8 * np.sin(2 * math.pi * (100 * t - 160 * t * t)))
        self.sounds['hit'] = self.sound(hit * np.exp(-t * 26))
        self.sounds['block'] = self.sound(self.tone(530, .17, 24))
        t = np.arange(int(self.RATE * .18)) / self.RATE
        noise = rng.uniform(-1, 1, len(t))
        soft = np.convolve(noise, np.ones(7) / 7, mode='same')
        self.sounds['swing'] = self.sound(soft * np.sin(np.pi * t / .18) * .9)
        self.sounds['menu'] = self.sound(self.tone(660, .075, 25) * .32)
        self.sounds['accept'] = self.sound(self.tone(880, .16, 14) * .4)
        bell = self.tone(523.25, 1.4, 3)
        bell += .5 * self.tone(783.99, 1.4, 3.8)
        bell += .25 * self.tone(1046.5, 1.4, 4)
        self.sounds['bell'] = self.sound(bell * .4)
        self.sounds['point'] = self.sound(self.tone(1174.66, .26, 13) * .32)
        self.sounds['win'] = self.sound(self.tone(659.25, 1, 4) * .45)
        duration = 8
        t = np.arange(self.RATE * duration) / self.RATE
        pad = np.zeros_like(t)
        for frequency, level in [(130.81, .09), (196, .04), (261.63, .035), (392, .022)]:
            pad += level * np.sin(2 * math.pi * frequency * t)
        envelope = np.minimum(1, t / .6) * np.minimum(1, (duration - t) / .6)
        self.sounds['ambience'] = self.sound(pad * envelope)
        self.ambient = pygame.mixer.Channel(0)
        self.ambient.play(self.sounds['ambience'], loops=-1)

    def load_recordings(self):
        directory = Path(__file__).resolve().parent.parent / 'assets' / 'audio'
        for name in ('block', 'hit_light', 'hit_heavy', 'hit_chop', 'round_swing',
                     'miss', 'nunchaku_spin', 'kiai', 'defeat'):
            path = directory / (name + '.wav')
            if not path.is_file():
                continue
            try:
                self.sounds[name] = pygame.mixer.Sound(str(path))
                self.loaded_external.append(name)
            except pygame.error:
                continue

    def set_volume(self, volume):
        self.volume = volume
        if not self.enabled:
            return
        for name, sound in self.sounds.items():
            sound.set_volume(volume * (.30 if name == 'ambience' else .7))

    def play(self, name):
        if not self.enabled:
            return
        if name == 'nunchaku_stop':
            pygame.mixer.Channel(2).fadeout(35)
            return
        if name == 'star_throw':
            name = 'swing'
        if name == 'hit' and 'hit_light' in self.sounds and 'hit_heavy' in self.sounds:
            self.hit_sequence += 1
            name = 'hit_light' if self.hit_sequence % 3 == 0 else 'hit_heavy'
        if name in ('hit_light', 'hit_heavy') and name not in self.sounds:
            name = 'hit'
        sound = self.sounds.get(name)
        if sound:
            if name in ('kiai', 'defeat'):
                channel = pygame.mixer.Channel(1)
                if name == 'kiai' and channel.get_busy():
                    return
                if name == 'defeat':
                    pygame.mixer.Channel(2).fadeout(50)
            elif name == 'nunchaku_spin':
                channel = pygame.mixer.Channel(2)
            else:
                channel = pygame.mixer.find_channel()
            if channel:
                channel.play(sound)

    def close(self):
        if self.enabled:
            pygame.mixer.stop()
            pygame.mixer.quit()
