"""The eight prepared effects: format, preload, transients and routing."""
import os

os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import unittest
import wave
from unittest.mock import patch

import numpy as np
import pygame

from dojo.audio import Audio
from dojo.storage import ROOT


class PreparedAudioTests(unittest.TestCase):
    EFFECTS = ('hit_chop.wav', 'hit_light.wav', 'hit_heavy.wav', 'round_swing.wav',
               'miss.wav', 'nunchaku_spin.wav', 'kiai.wav', 'defeat.wav')

    def test_all_eight_prepared_effects_are_in_the_public_game(self):
        for name in self.EFFECTS:
            self.assertTrue((ROOT / 'assets/audio' / name).is_file())

    def test_prepared_files_are_pcm_with_prompt_onsets_and_no_clipping(self):
        for name in self.EFFECTS:
            with self.subTest(file=name):
                path = ROOT / 'assets/audio' / name
                with wave.open(str(path), 'rb') as handle:
                    self.assertEqual(handle.getframerate(), 44100)
                    self.assertEqual(handle.getnchannels(), 2)
                    self.assertEqual(handle.getsampwidth(), 2)
                    data = np.frombuffer(handle.readframes(handle.getnframes()), dtype='<i2')
                envelope = np.max(np.abs(data.reshape(-1, 2).astype(float)), axis=1)
                onset = np.flatnonzero(envelope >= envelope.max() * .1)[0] / 44100
                self.assertLess(onset, .003)
                self.assertLess(envelope.max(), 32760)
                self.assertLess(len(envelope) / 44100, 1.65)

    def test_motion_and_impact_have_separate_channels(self):
        audio = Audio(0)
        try:
            audio.play('nunchaku_spin')
            self.assertIs(pygame.mixer.Channel(2).get_sound(), audio.sounds['nunchaku_spin'])
            audio.play('hit_chop')
            self.assertIs(pygame.mixer.Channel(2).get_sound(), audio.sounds['nunchaku_spin'])
            self.assertIs(pygame.mixer.Channel(0).get_sound(), audio.sounds['ambience'])
        finally:
            audio.close()

    def test_chop_and_roundkick_contain_one_source_action(self):
        for name in ('hit_chop.wav', 'round_swing.wav'):
            with wave.open(str(ROOT / 'assets/audio' / name), 'rb') as handle:
                frames = handle.readframes(handle.getnframes())
                rate = handle.getframerate()
            envelope = np.max(np.abs(np.frombuffer(frames, dtype='<i2').reshape(-1, 2)), axis=1)
            self.assertLess(len(envelope) / rate, 0.121)
            self.assertLess(int(np.argmax(envelope)) / rate, 0.060)

    def test_defeat_takes_priority_over_voice_and_stops_weapon_sound(self):
        audio = Audio(0)
        try:
            audio.play('kiai')
            audio.play('nunchaku_spin')
            audio.play('defeat')
            self.assertIs(pygame.mixer.Channel(1).get_sound(), audio.sounds['defeat'])
            pygame.time.wait(65)
            self.assertFalse(pygame.mixer.Channel(2).get_busy())
        finally:
            audio.close()

    def test_playback_never_loads_a_file_during_combat(self):
        audio = Audio(0)
        try:
            with patch('pygame.mixer.Sound', side_effect=AssertionError('late load')):
                for sound in ('hit_chop', 'round_swing', 'miss', 'nunchaku_spin',
                              'star_throw', 'kiai', 'defeat'):
                    audio.play(sound)
        finally:
            audio.close()


if __name__ == '__main__':
    unittest.main()
