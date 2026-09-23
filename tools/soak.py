"""Full-application endurance test in real time, with process-local Xbox input.

The test uses temporary save data. It repeatedly finishes complete fights,
visits menus, swaps arenas and reconnects its private SDL controller. No Linux
input devices, system settings or emulator files are created or changed.
"""
import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import argparse
import faulthandler
import hashlib
import json
import signal
import sys
import tempfile
import time
import weakref
from collections import Counter, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame
from OpenGL.GL import GL_NO_ERROR, glGetError

from dojo.app import Application
from dojo.model import Brain
from dojo.storage import ROOT
from tools.benchmark import resident_mb, temperature
from tools.sdl_virtual import VirtualPad
from tools.specialist_balance import player_command


class Soak:
    def __init__(self, seconds, label, fullscreen, specialists=False):
        self.seconds = seconds
        self.label = label
        self.specialists = specialists
        self.temp = tempfile.TemporaryDirectory(prefix='dojo-soak-')
        args = argparse.Namespace(windowed=not fullscreen, practice=False, demo=False,
                                  smoke=False, seconds=0, mute=True, data_dir=Path(self.temp.name))
        self.app = Application(args)
        pygame.display.set_caption('Dojo Sunset — automatiskt långtest (Esc avslutar)')
        self.pad = VirtualPad()
        self.app.controls.preferred_instance = self.pad.instance_id
        self.app.controls.scan()
        self.app.new_match(False, 'ninja' if specialists else 'karate')
        self.brain = Brain(1, 600)
        self.start = time.monotonic()
        self.last_report = self.start
        self.last_screenshot = self.start
        self.matches = 0
        self.frames = 0
        self.segment_frames = 0
        self.disconnects = 0
        self.arena_switches = 0
        self.frame_times = deque(maxlen=3600)
        self.stop_requested = False
        self.stop_reason = 'duration'
        self.max_frame_ms = 0.0
        self.stalls = 0
        self.samples = []
        self.failures = []
        self.finished_at = None
        self.menu_cycle = 0
        self.reset_pad_pending = False
        self.attack_release = False
        self.last_phase = ''
        self.opponent_counts = Counter()
        self.sound_events = Counter()
        self.max_projectiles = 0
        self.seen_attacks = Counter()
        self.previous_attacks = 0
        original_play = weakref.WeakMethod(self.app.audio.play)
        sound_events = self.sound_events

        def observe_audio(name):
            sound_events[name] += 1
            play = original_play()
            if play is not None:
                play(name)

        self.app.audio.play = observe_audio
        self.out = ROOT / 'userdata' / label
        self.out.mkdir(exist_ok=True)
        hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for folder in ('dojo', 'tools')
                  for path in (ROOT / folder).glob('*.py')}
        hashes.update({str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in (ROOT / 'assets' / 'audio').glob('*.wav')})
        (self.out / 'source-hashes.json').write_text(json.dumps(hashes, indent=2))

    def drive_pad(self, dt):
        if self.app.screen != 'game':
            return
        match = self.app.match
        command = player_command(self.brain, match, dt, aware=self.specialists)
        self.pad.axis(0, command.move)
        self.pad.button(12, command.crouch)
        self.pad.button(9, command.guard)
        for button in (0, 1, 2, 3, 10, 11):
            self.pad.button(button, False)
        self.pad.axis(4, -1)
        self.pad.axis(5, -1)
        mapping = {'jab': 2, 'cross': 3, 'front_kick': 0, 'round_kick': 1,
                   'high_kick': 1, 'low_kick': 0, 'sweep': 1, 'spin_kick': 10}
        if command.attack in mapping:
            self.pad.button(mapping[command.attack], True)
        if command.attack in ('low_kick', 'sweep'):
            self.pad.button(12, True)
        if command.attack == 'high_kick':
            self.pad.button(11, True)
        if command.attack == 'jump_kick':
            self.pad.axis(5, 1)
        if command.dodge:
            self.pad.axis(4, 1)
        if command.jump:
            self.pad.button(11, True)

    def assert_invariants(self):
        match = self.app.match
        if not match:
            return
        for fighter in (match.player, match.enemy):
            if not -4.501 <= fighter.x <= 4.501:
                raise AssertionError('Fighter left arena')
            if not 0 <= fighter.health <= 100:
                raise AssertionError('Health outside range')
            if not 0 <= fighter.stamina <= 100.001:
                raise AssertionError('Stamina outside range')
        if match.phase not in ('intro', 'fight', 'point', 'round_over', 'finished'):
            raise AssertionError('Unknown combat phase')
        if match.player.archetype != 'karate' or match.player.stars != 0:
            raise AssertionError('Player must remain unarmed')
        if not 0 <= match.enemy.stars <= 4 or len(match.projectiles) > 4:
            raise AssertionError('Unbounded ninja ammunition or projectiles')
        if match.phase != 'fight' and match.projectiles:
            raise AssertionError('Projectile survived round boundary')
        if match.enemy.attacks != self.previous_attacks:
            self.seen_attacks[match.enemy.move_key or 'interrupted'] += 1
            self.previous_attacks = match.enemy.attacks
        self.max_projectiles = max(self.max_projectiles, len(match.projectiles))

    def next_match(self):
        self.opponent_counts[self.app.match.enemy.archetype] += 1
        self.matches += 1
        settings = self.app.storage.settings
        settings['rules'] = self.matches % 2
        settings['difficulty'] = self.matches % 3
        if self.matches % 3 == 0:
            settings['arena'] = 1 - settings['arena']
            self.app.renderer.change_arena()
            self.arena_switches += 1
        if self.matches % 5 == 0:
            self.app.controls.close_pad()
            self.pad.close()
            self.pad = VirtualPad()
            self.app.controls.preferred_instance = self.pad.instance_id
            self.app.controls.scan()
            self.disconnects += 1
        kind = ('ninja', 'sumo', 'karate')[self.matches % 3] if self.specialists else 'karate'
        self.app.new_match(False, kind)
        self.brain = Brain((self.matches + 1) % 3, self.matches + 600)
        self.finished_at = None
        self.previous_attacks = 0

    def report(self, now):
        segment = max(.001, now - self.last_report)
        ordered = sorted(self.frame_times)
        gl_error = int(glGetError())
        if gl_error != GL_NO_ERROR:
            raise AssertionError(f'OpenGL error during endurance run: {gl_error}')
        sample = {
            'elapsed_seconds': round(now - self.start, 1),
            'fps': round(self.segment_frames / segment, 2),
            'gl_error': gl_error,
            'p95_ms': round(ordered[int(len(ordered) * .95)] * 1000, 2) if ordered else 0,
            'rss_mb': round(resident_mb(), 2),
            'open_fds': len(list(Path('/proc/self/fd').iterdir())),
            'text_cache_entries': len(self.app.ui.cache),
            'max_frame_ms': round(self.max_frame_ms, 2),
            'frames_above_50ms': self.stalls,
            'temperature_c': temperature(),
            'matches': self.matches,
            'controller_reconnects': self.disconnects,
            'arena_switches': self.arena_switches,
            'screen': self.app.screen,
            'phase': self.app.match.phase if self.app.match else None,
            'save_records': len(self.app.storage.records),
            'opponent': self.app.match.enemy.archetype if self.app.match else None,
            'completed_opponents': dict(self.opponent_counts),
            'max_projectiles': self.max_projectiles,
        }
        self.samples.append(sample)
        (self.out / 'latest.json').write_text(json.dumps(sample, indent=2))
        print(json.dumps(sample), flush=True)
        self.segment_frames = 0
        self.last_report = now

    def run(self):
        clock = pygame.time.Clock()
        while (time.monotonic() - self.start < self.seconds
               and self.app.running and not self.stop_requested):
            measured = clock.tick(60) / 1000
            self.max_frame_ms = max(self.max_frame_ms, measured * 1000)
            self.stalls += measured > .05
            dt = min(.1, measured)
            self.app.elapsed += dt
            self.drive_pad(dt)
            self.app.handle_input(dt)
            if not self.app.controls.has_focus:
                self.stop_reason = 'desktop_focus_lost'
                self.app.running = False
                break
            if self.app.controls.hit('start') or self.app.controls.quit_requested:
                self.stop_reason = 'requested_exit'
                self.app.running = False
                break
            if self.app.screen == 'game':
                self.app.tick_match(dt)
            elif self.app.screen == 'result':
                if self.finished_at is None:
                    self.finished_at = time.monotonic()
                elif time.monotonic() - self.finished_at > 1.5:
                    self.next_match()
            # A test-controller reconnect may pause the match. Real desktop
            # focus loss exits above, freeing the machine for its owner.
            elif self.app.screen == 'pause':
                self.app.screen = 'game'
                self.app.accumulator = 0
            self.assert_invariants()
            self.app.draw(dt)
            self.frames += 1
            self.segment_frames += 1
            self.frame_times.append(measured)
            now = time.monotonic()
            if now - self.last_report >= 30:
                self.report(now)
            if now - self.last_screenshot >= 600:
                self.app.screenshot_requested = True
                self.last_screenshot = now
        self.report(time.monotonic())

    def close(self):
        report = {
            'seconds': round(time.monotonic() - self.start, 2),
            'requested_seconds': self.seconds,
            'stop_reason': self.stop_reason,
            'interrupted': self.stop_requested or not self.app.running,
            'frames': self.frames,
            'matches': self.matches,
            'failures': self.failures,
            'samples': self.samples,
            'gpu': self.app.renderer.gpu,
            'msaa_actual': self.app.renderer.samples_actual,
            'specialists': self.specialists,
            'completed_opponents': dict(self.opponent_counts),
            'sound_events': dict(self.sound_events),
            'enemy_attacks': dict(self.seen_attacks),
            'max_projectiles': self.max_projectiles,
        }
        (self.out / 'report.json').write_text(json.dumps(report, indent=2))
        # Remove the observer before closing native resources. It must not keep
        # the application/audio alive until interpreter-finalization GC.
        del self.app.audio.play
        steps = [
            ('controls', self.app.controls.close),
            ('virtual_pad', self.pad.close),
            ('audio', self.app.audio.close),
            ('renderer', self.app.renderer.close),
            ('pygame', pygame.quit),
            ('temporary_data', self.temp.cleanup),
        ]
        shutdown = {'complete': False, 'completed_steps': []}
        for name, operation in steps:
            shutdown['current_step'] = name
            (self.out / 'shutdown.json').write_text(json.dumps(shutdown, indent=2))
            operation()
            shutdown['completed_steps'].append(name)
        shutdown.update(complete=True, current_step=None)
        (self.out / 'shutdown.json').write_text(json.dumps(shutdown, indent=2))


def main():
    faulthandler.enable()
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=1800)
    parser.add_argument('--label', default='soak')
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--specialists', action='store_true')
    args = parser.parse_args()
    soak = Soak(args.seconds, args.label, not args.windowed, args.specialists)
    def stop(signum, frame):
        soak.stop_requested = True
        soak.stop_reason = signal.Signals(signum).name

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        soak.run()
    except BaseException as exc:
        soak.failures.append(repr(exc))
        raise
    finally:
        soak.close()


if __name__ == '__main__':
    main()
