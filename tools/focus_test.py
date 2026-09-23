"""Exercise real desktop focus loss using a second, temporary SDL process."""
import os

os.environ['SDL_AUDIODRIVER'] = 'dummy'  # Volume assertions must stay inaudible.
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame

from dojo.app import Application
from dojo.storage import ROOT
from tools.sdl_virtual import VirtualPad

CHILD = '''
import time
import pygame
from pygame._sdl2.video import Window
pygame.display.init()
pygame.display.set_mode((320, 100))
pygame.display.set_caption('Dojo Sunset — tillfälligt fokusprov')
window = Window.from_display_module()
window.focus()
start = time.monotonic()
while time.monotonic() - start < 3:
    pygame.event.pump()
    pygame.display.flip()
    pygame.time.wait(20)
pygame.quit()
'''


def main():
    checks = []
    directory = ROOT / 'userdata' / 'focus-test'
    directory.mkdir(exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix='dojo-focus-')
    args = argparse.Namespace(windowed=True, practice=False, demo=False, smoke=False,
                              seconds=0, mute=False, data_dir=Path(temporary.name))
    app = Application(args)
    pad = VirtualPad()
    app.controls.preferred_instance = pad.instance_id
    app.controls.scan()
    app.new_match(True)
    app.match.phase = 'fight'
    child = None
    clock = pygame.time.Clock()

    def frame(count=1):
        for _ in range(count):
            dt = min(.1, clock.tick(60) / 1000)
            app.elapsed += dt
            app.handle_input(dt)
            if app.screen == 'game':
                app.tick_match(dt)
            app.draw(dt)

    def check(condition, label):
        checks.append({'name': label, 'passed': bool(condition)})
        print(label, bool(condition), flush=True)
        if not condition:
            raise AssertionError(label)

    try:
        frame(10)
        window = app.renderer.window
        child = subprocess.Popen([sys.executable, '-c', CHILD], cwd=ROOT,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 2
        while app.controls.has_focus and time.monotonic() < deadline:
            frame()
        check(not app.controls.has_focus, 'Real second window takes focus')
        check(app.screen == 'pause', 'Real focus loss pauses the match')
        check(app.audio.volume == 0, 'Only the game audio becomes silent')
        frozen = app.match.elapsed
        pad.button(0, True)
        frame(20)
        check(app.screen == 'pause', 'Background A cannot resume gameplay')
        check(app.match.elapsed == frozen, 'Background simulation stays frozen')
        while child.poll() is None:
            frame()
        check(child.returncode == 0, 'Temporary focus window exits cleanly')
        window.focus()
        deadline = time.monotonic() + 2
        while not app.controls.has_focus and time.monotonic() < deadline:
            frame()
        frame(12)
        check(app.controls.has_focus, 'Game regains real desktop focus')
        check(app.screen == 'pause', 'Held A cannot resume on focus regain')
        check(app.audio.volume == app.storage.settings['volume'], 'Game volume restores correctly')
        pad.button(0, False)
        frame(3)
        pad.button(0, True)
        frame(2)
        pad.button(0, False)
        frame(2)
        check(app.screen == 'game', 'A fresh A press resumes normally')
        check(app.match.player.attacks == 0, 'Resume does not generate a stray attack')
    finally:
        if child and child.poll() is None:
            child.terminate()
            child.wait(timeout=5)
        if child and child.stderr:
            errors = child.stderr.read().decode(errors='replace')
            if errors:
                (directory / 'helper-stderr.log').write_text(errors)
            child.stderr.close()
        app.controls.close()
        pad.close()
        app.audio.close()
        app.renderer.close()
        pygame.quit()
        temporary.cleanup()
        (directory / 'report.json').write_text(json.dumps(checks, indent=2))


if __name__ == '__main__':
    main()
