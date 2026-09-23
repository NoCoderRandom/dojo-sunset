"""Asset latency, clipping and preload checks without playing through speakers."""
import os

os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import json
import unittest
import wave

import numpy as np

from dojo.audio import Audio
from dojo.storage import ROOT


class AudioAssetTests(unittest.TestCase):
    def test_all_imported_transients_start_promptly(self):
        for name in ('block', 'hit_light', 'hit_heavy'):
            with self.subTest(name=name):
                with wave.open(str(ROOT / 'assets' / 'audio' / (name + '.wav')), 'rb') as handle:
                    rate = handle.getframerate()
                    samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype='<i2')
                    samples = samples.reshape(-1, handle.getnchannels())
                peak = np.max(np.abs(samples.astype(float)), axis=1)
                onset = np.flatnonzero(peak > peak.max() * .1)[0] / rate
                self.assertLess(onset, .003)
                self.assertLess(peak.max(), 32760)

    def test_files_are_short_uncompressed_stereo_pcm(self):
        for name in ('block', 'hit_light', 'hit_heavy'):
            with wave.open(str(ROOT / 'assets' / 'audio' / (name + '.wav')), 'rb') as handle:
                self.assertEqual(handle.getsampwidth(), 2)
                self.assertEqual(handle.getnchannels(), 2)
                self.assertEqual(handle.getframerate(), 44100)
                self.assertLess(handle.getnframes() / handle.getframerate(), .4)

    def test_original_audio_sources_are_documented(self):
        report = json.loads((ROOT / 'assets' / 'audio' / 'audio-review.json').read_text())
        self.assertEqual(len(report['sources']), 2)
        self.assertTrue(all(source['license'] == 'CC0 1.0' for source in report['sources']))
        self.assertEqual(len(report['edits']), 3)

    def test_audio_loads_every_sound_before_play(self):
        audio = Audio(volume=0)
        try:
            self.assertTrue(audio.enabled)
            self.assertEqual(set(audio.loaded_external), {
                'block', 'hit_light', 'hit_heavy', 'hit_chop', 'round_swing',
                'miss', 'nunchaku_spin', 'kiai', 'defeat'})
            for name in ('hit', 'block', 'swing', 'menu', 'accept', 'bell', 'point', 'win'):
                audio.play(name)
            self.assertTrue(all(sound.get_length() > 0 for sound in audio.sounds.values()))
        finally:
            audio.close()

    def test_muting_sets_all_sound_volumes(self):
        audio = Audio(volume=.5)
        try:
            audio.set_volume(0)
            self.assertTrue(all(sound.get_volume() == 0 for sound in audio.sounds.values()))
        finally:
            audio.close()


if __name__ == '__main__':
    unittest.main()
