"""Controller-to-pixels integration test using a process-local SDL gamepad."""
import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame

from dojo.app import Application
from dojo.storage import ROOT
from tools.sdl_virtual import VirtualPad


class IntegrationRun:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='dojo-integration-')
        arguments = argparse.Namespace(windowed=True, practice=False, demo=False,
                                       smoke=False, seconds=0, mute=True,
                                       data_dir=Path(self.temporary.name))
        self.app = Application(arguments)
        self.pad = VirtualPad()
        self.app.controls.preferred_instance = self.pad.instance_id
        self.app.controls.scan()
        self.checks = []
        self.frames = 0
        self.started = time.monotonic()
        self.out = ROOT / 'userdata' / 'integration'
        self.out.mkdir(exist_ok=True)

    def frame(self, count=1):
        for _ in range(count):
            dt = 1 / 60
            self.app.elapsed += dt
            self.app.handle_input(dt)
            if self.app.screen == 'game':
                self.app.tick_match(dt)
            else:
                self.app.tick_demo_background(dt)
            self.app.draw(dt)
            self.frames += 1

    def tap(self, button):
        self.pad.button(button, True)
        self.frame(2)
        self.pad.button(button, False)
        self.frame(2)

    def check(self, condition, message):
        self.checks.append({'name': message, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(message)
        print('PASS', message, flush=True)

    def screenshot(self, name):
        self.app.draw(0)
        self.app.renderer.draw_world(
            [self.app.match.player, self.app.match.enemy] if self.app.match else self.app.demo_fighters,
            self.app.elapsed, self.app.match)
        self.app.renderer.draw_hud(self.app.ui.surface)
        self.app.renderer.screenshot(self.out / (name + '.png'))
        self.app.renderer.present()

    def run(self):
        self.frame(3)
        self.check(self.app.screen == 'title', 'Starts at title')
        controller_id = self.app.controls.pad.id
        mixer_format = pygame.mixer.get_init()
        for fullscreen in (True, False):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))
            self.frame(3)
            self.check(self.app.renderer.fullscreen == fullscreen,
                       f'F11 changes fullscreen to {fullscreen}')
            self.check(self.app.controls.pad.id == controller_id,
                       f'Controller survives fullscreen={fullscreen}')
            self.check(pygame.mixer.get_init() == mixer_format,
                       f'Audio mixer survives fullscreen={fullscreen}')
        self.tap(0)
        self.check(self.app.screen == 'play_select', 'Xbox A opens play modes')
        self.tap(0)
        self.check(self.app.screen == 'game', 'Xbox A starts classic match')
        self.frame(150)
        self.check(self.app.match.phase == 'fight', 'Intro reaches live combat')
        self.app.match.player.x = -.45
        self.app.match.enemy.x = .45
        self.app.match.brain.wait = 2
        self.tap(2)
        self.frame(16)
        self.check(self.app.match.player_points > 0, 'Xbox X produces a scored hit')
        self.screenshot('classic-point')
        self.tap(6)
        self.check(self.app.screen == 'pause', 'Start pauses combat')
        frozen = self.app.match.elapsed
        self.frame(35)
        self.check(self.app.match.elapsed == frozen, 'Paused simulation stays frozen')
        self.tap(12)
        self.tap(12)
        self.tap(0)
        self.check(self.app.screen == 'controller', 'Pause menu opens control test')
        self.tap(1)
        self.check(self.app.screen == 'controller', 'B can be tested without closing diagnostics')
        self.pad.axis(0, .5)
        self.frame(3)
        self.check(self.app.controls.axis_x > 0, 'Analog stick reaches live diagnostic')
        self.pad.axis(0, 0)
        self.screenshot('controller')
        self.tap(6)
        self.check(self.app.screen == 'pause', 'Start returns from diagnostic')
        self.tap(1)
        self.check(self.app.screen == 'game', 'B resumes paused match')
        self.pad.close()
        self.frame(3)
        self.check(self.app.screen == 'pause', 'Unplugging controller automatically pauses')
        self.pad = VirtualPad()
        self.app.controls.preferred_instance = self.pad.instance_id
        self.frame(3)
        self.check(bool(self.app.controls.pad), 'Hotplug reconnect is detected')
        self.tap(12)
        self.tap(12)
        self.tap(12)
        self.tap(0)
        self.check(self.app.screen == 'title', 'Controller returns to title')
        self.tap(12)
        self.tap(0)
        self.check(self.app.screen == 'train_select', 'Training selection opens')
        self.tap(12)
        self.tap(0)
        self.check(self.app.tutorial is not None, 'Technique school starts')
        self.check(self.app.match.player.attacks == 0, 'Menu A does not leak into an attack')
        self.pad.axis(0, -1)
        self.frame(50)
        self.pad.axis(0, 1)
        self.frame(95)
        self.pad.axis(0, 0)
        self.frame(35)
        self.check(self.app.tutorial.lesson_done, 'Real stick movement completes first lesson')
        self.screenshot('tutorial-success')
        self.tap(0)
        self.check(self.app.tutorial.index == 1, 'A advances to second lesson')
        self.tap(6)
        self.tap(12)
        self.tap(12)
        self.tap(12)
        self.tap(0)
        self.check(self.app.screen == 'title', 'Training can be left from pause')
        self.tap(12)
        self.tap(12)
        self.tap(12)
        self.tap(0)
        self.check(self.app.screen == 'options', 'Settings reachable by controller')
        before = self.app.storage.settings['difficulty']
        self.tap(14)
        self.check(self.app.storage.settings['difficulty'] != before, 'D-pad changes selected setting')
        self.check((Path(self.temporary.name) / 'settings.json').exists(), 'Settings persist in isolated test directory')
        self.screenshot('settings')
        self.tap(1)
        self.check(self.app.screen == 'title', 'B returns from settings')
        self.tap(6)
        self.check(self.app.screen == 'quit', 'Start opens exit confirmation')
        self.tap(12)
        self.tap(0)
        self.check(not self.app.running, 'Exit works with controller only')

    def close(self):
        self.app.controls.close()
        self.pad.close()
        self.app.audio.close()
        self.app.renderer.close()
        pygame.quit()
        self.temporary.cleanup()
        report = {'checks': self.checks, 'frames': self.frames,
                  'seconds': round(time.monotonic() - self.started, 2)}
        (self.out / 'report.json').write_text(json.dumps(report, indent=2))


def main():
    run = IntegrationRun()
    try:
        run.run()
    finally:
        run.close()


if __name__ == '__main__':
    main()
