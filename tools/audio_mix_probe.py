"""Capture the real SDL mixer into a private PCM file, without speakers.

Checks numerical output and clipping, not perceptual quality or hardware
latency. SDL disk-driver pacing differs from a real sound device.
"""
import os

os.environ['SDL_AUDIODRIVER'] = 'disk'
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import argparse
import hashlib
import json
import sys
import time
import wave
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pygame

from dojo.audio import Audio
from dojo.competition import opponent_match
from dojo.model import Brain
from dojo.storage import ROOT
from tools.specialist_balance import player_command


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds-per-kind', type=float, default=100)
    parser.add_argument('--label', default='audio-mix-probe')
    args = parser.parse_args()
    if Path(args.label).name != args.label or args.seconds_per_kind <= 0:
        parser.error('plain label and positive duration required')
    directory = ROOT / 'userdata' / args.label
    directory.mkdir(exist_ok=True)
    raw_path = directory / 'mixer-output.raw'
    os.environ['SDL_DISKAUDIOFILE'] = str(raw_path)
    files = [ROOT / 'dojo/audio.py', ROOT / 'dojo/model.py', Path(__file__),
             *(ROOT / 'assets/audio').glob('*.wav')]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in files}
    audio = Audio(1.0)
    if not audio.enabled:
        raise RuntimeError('SDL disk mixer unavailable')
    counts = Counter()
    start = time.monotonic()
    clock = pygame.time.Clock()

    def play(name):
        if name != 'hit':
            counts[name] += 1
            audio.play(name)

    try:
        for kind in ('ninja', 'sumo'):
            match = opponent_match(kind, difficulty=2, practice=True, seed=17)
            match.practice_ai = True
            brain = Brain(2, 47)
            elapsed = 0.0
            while elapsed < args.seconds_per_kind:
                clock.tick(120)
                dt = 1 / 120
                command = player_command(brain, match, dt)
                match.update(dt, command)
                for event in match.events:
                    play(event)
                elapsed += dt
            print(f'Captured {kind} combat at maximum game volume', flush=True)
        # Deliberately dense effects, including simultaneous hit/voice/bell.
        groups = (
            ('round_swing', 'hit_heavy', 'kiai'),
            ('nunchaku_spin', 'hit_chop', 'block'),
            ('hit_light', 'hit_heavy', 'round_swing', 'kiai'),
            ('hit_heavy', 'defeat', 'bell'),
            ('miss', 'round_swing', 'star_throw'),
        )
        for _ in range(4):
            for group in groups:
                for event in group:
                    play(event)
                pygame.time.wait(1750)
        pygame.time.wait(1800)
    finally:
        audio.close()
    samples = np.fromfile(raw_path, dtype='<i2').reshape(-1, 2)
    magnitude = np.abs(samples.astype(np.int32))
    peak = int(magnitude.max())
    clipped = int(np.count_nonzero(magnitude >= 32767))
    with wave.open(str(directory / 'mixer-output.wav'), 'wb') as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(Audio.RATE)
        handle.writeframes(samples.tobytes())
    raw_path.unlink()
    report = {
        'wall_seconds': round(time.monotonic() - start, 2),
        'captured_pcm_seconds': round(len(samples) / Audio.RATE, 2),
        'master_volume': 1.0, 'sample_rate': Audio.RATE,
        'peak_pcm16': peak, 'peak_dbfs': round(20 * np.log10(max(1, peak) / 32768), 3),
        'clipped_channel_samples': clipped,
        'rms': round(float(np.sqrt(np.mean((samples.astype(float) / 32768) ** 2))), 6),
        'sound_events': dict(counts), 'source_hashes': hashes,
        'note': 'Actual SDL disk-mixer output; technical check only, not listening or hardware latency.',
    }
    (directory / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)
    if clipped:
        raise SystemExit('Clipped mixed output requires review')


if __name__ == '__main__':
    main()
