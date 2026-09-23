"""Real-time render soak with AI matches, memory, temperature and frame metrics."""
import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import argparse
import json
import statistics
import sys
import time
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame

from dojo.competition import ClassicMatch
from dojo.model import Brain, Match
from dojo.renderer import Renderer
from dojo.storage import DEFAULTS, ROOT
from dojo.ui import UI


def resident_mb():
    try:
        pages = int(Path('/proc/self/statm').read_text().split()[1])
        return pages * os.sysconf('SC_PAGE_SIZE') / 1048576
    except (OSError, ValueError, IndexError):
        return None


def temperature():
    try:
        return int(Path('/sys/class/thermal/thermal_zone0/temp').read_text()) / 1000
    except (OSError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--samples', type=int, default=2)
    parser.add_argument('--fullscreen', action='store_true')
    parser.add_argument('--label', default='benchmark')
    args = parser.parse_args()
    pygame.display.init()
    renderer = Renderer(dict(DEFAULTS, fullscreen=args.fullscreen, msaa=args.samples))
    ui = UI()
    match = ClassicMatch(seed=17)
    brain = Brain(difficulty=1, seed=45)
    clock = pygame.time.Clock()
    start = time.monotonic()
    previous = start
    segment_start = start
    frames = 0
    segment_frames = 0
    completed_matches = 0
    frame_times = deque(maxlen=3600)
    draw_times = deque(maxlen=3600)
    samples = []
    quit_requested = False
    output = ROOT / 'userdata' / (args.label + '.json')
    try:
        while time.monotonic() - start < args.seconds and not quit_requested:
            clock.tick(60)
            now = time.monotonic()
            dt = min(.1, now - previous)
            previous = now
            elapsed = now - start
            for event in pygame.event.get():
                if event.type == pygame.QUIT or event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    quit_requested = True
            command = brain.update(dt, match.player, match.enemy)
            match.update(dt, command)
            if match.phase == 'finished':
                completed_matches += 1
                if completed_matches % 2:
                    match = Match(seed=completed_matches)
                else:
                    match = ClassicMatch(seed=completed_matches)
                brain = Brain(completed_matches % 3, seed=completed_matches + 45)
                if completed_matches % 4 == 0:
                    renderer.settings['arena'] = 1 - renderer.settings['arena']
                    renderer.change_arena()
            drawing = time.monotonic()
            renderer.draw_world([match.player, match.enemy], elapsed, match)
            ui.begin(dt)
            ui.hud(match, None)
            renderer.draw_hud(ui.finish())
            draw_times.append(time.monotonic() - drawing)
            renderer.present()
            frames += 1
            segment_frames += 1
            frame_times.append(dt)
            if now - segment_start >= 10:
                sample = {
                    'seconds': round(elapsed, 1),
                    'fps': round(segment_frames / (now - segment_start), 2),
                    'rss_mb': round(resident_mb(), 2),
                    'temperature_c': temperature(),
                    'matches': completed_matches,
                    'phase': match.phase,
                }
                samples.append(sample)
                print(json.dumps(sample), flush=True)
                segment_frames = 0
                segment_start = now
        renderer.draw_world([match.player, match.enemy], time.monotonic() - start, match)
        renderer.draw_hud(ui.surface)
        renderer.screenshot(ROOT / 'userdata' / (args.label + '.png'))
        renderer.present()
    finally:
        total = time.monotonic() - start
        report = {
            'seconds': round(total, 2),
            'frames': frames,
            'average_fps': round(frames / max(.001, total), 2),
            'frame_ms_p50': round(statistics.median(frame_times) * 1000, 2) if frame_times else 0,
            'frame_ms_p95': round(sorted(frame_times)[int(len(frame_times) * .95)] * 1000, 2) if frame_times else 0,
            'draw_ms_median': round(statistics.median(draw_times) * 1000, 2) if draw_times else 0,
            'completed_matches': completed_matches,
            'msaa': renderer.samples,
            'gpu': renderer.gpu,
            'samples': samples,
            'quit_requested': quit_requested,
        }
        output.write_text(json.dumps(report, indent=2))
        print(json.dumps(report), flush=True)
        renderer.close()
        pygame.quit()


if __name__ == '__main__':
    main()
