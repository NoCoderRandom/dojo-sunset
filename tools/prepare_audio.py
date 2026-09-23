"""Reproducible transient editing for two CC0 Freesound karate recordings.

These files are the originals behind entries suggested in the Pixabay search.
The preview recordings are openly served on Freesound's own CDN. No account,
private API or browser session is used by this preparation tool.
"""
import hashlib
import json
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / 'assets' / 'audio'


def read_wave(path):
    with wave.open(str(path), 'rb') as handle:
        if handle.getsampwidth() != 2:
            raise ValueError('Expected PCM16 source')
        rate = handle.getframerate()
        channels = handle.getnchannels()
        data = np.frombuffer(handle.readframes(handle.getnframes()), dtype='<i2')
    return data.reshape(-1, channels).astype(np.float64) / 32768.0, rate


def write_wave(path, samples, rate):
    pcm = np.clip(samples * 32767, -32767, 32767).astype('<i2')
    with wave.open(str(path), 'wb') as handle:
        handle.setnchannels(samples.shape[1])
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())


def analyse(samples, rate):
    envelope = np.max(np.abs(samples), axis=1)
    maximum = float(envelope.max())
    threshold = max(.005, maximum * .1)
    active = np.flatnonzero(envelope >= threshold)
    return {
        'duration_ms': round(len(samples) / rate * 1000, 2),
        'peak': round(maximum, 4),
        'first_10_percent_peak_ms': round(float(active[0]) / rate * 1000, 2) if len(active) else None,
        'peak_at_ms': round(float(envelope.argmax()) / rate * 1000, 2),
        'rms': round(float(np.sqrt(np.mean(samples * samples))), 4),
        'clipped_samples': int(np.count_nonzero(envelope >= .999)),
    }


def edit(source, name, start, end, level):
    samples, rate = read_wave(AUDIO / 'source' / (source + '.wav'))
    result = samples[int(start * rate):int(end * rate)].copy()
    result -= np.mean(result, axis=0)
    maximum = np.max(np.abs(result))
    if maximum > 0:
        result *= level / maximum
    # A short fade removes edit clicks without blurring the impact transient.
    fade_in = max(1, int(rate * .0015))
    fade_out = max(1, int(rate * .020))
    result[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    result[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    path = AUDIO / (name + '.wav')
    write_wave(path, result, rate)
    return {
        'file': path.name,
        'source': source + '.wav',
        'source_range_seconds': [start, end],
        'analysis': analyse(result, rate),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main():
    reports = [
        edit('block', 'block', .099, .29, .72),
        edit('chop', 'hit_light', .047, .145, .70),
        edit('chop', 'hit_heavy', .205, .505, .79),
    ]
    report = {
        'sources': [
            {'name': 'Blocking Arm With Hand', 'author': 'mmasonghi',
             'url': 'https://freesound.org/people/mmasonghi/sounds/321810/', 'license': 'CC0 1.0'},
            {'name': 'Karate Chop.m4a', 'author': 'ccolbert70Eagles23',
             'url': 'https://freesound.org/people/ccolbert70Eagles23/sounds/423526/', 'license': 'CC0 1.0'},
        ],
        'edits': reports,
        'auditory_review': 'Unavailable: agent audio-input capability does not support listening. Waveforms, transients, durations and clipping inspected; do not describe as personally auditioned.',
        'timing': 'Files loaded before play; block/hit playback triggered in the same simulation update as collision.',
    }
    (AUDIO / 'audio-review.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(reports, indent=2))


if __name__ == '__main__':
    main()
