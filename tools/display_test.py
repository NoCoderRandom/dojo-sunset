"""Exercise real fullscreen/context recreation and capture the updated artwork."""
import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame
from OpenGL.GL import GL_NO_ERROR, glGetError, glIsTexture

from dojo.app import Application
from dojo.model import MOVES, Command
from dojo.storage import ROOT
from tools.benchmark import resident_mb


def frame(app, count=1):
    for _ in range(count):
        app.elapsed += 1 / 60
        app.handle_input(1 / 60)
        app.draw(1 / 60)


def capture(app, directory, name):
    app.screenshot_requested = True
    # Render directly to a known filename instead of relying on glob ordering.
    fighters = [app.match.player, app.match.enemy] if app.match else app.demo_fighters
    app.renderer.draw_world(fighters, app.elapsed, app.match)
    app.renderer.draw_hud(app.ui.surface)
    app.renderer.screenshot(directory / (name + '.png'))
    app.renderer.present()
    app.screenshot_requested = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cycles', type=int, default=4)
    options = parser.parse_args()
    if options.cycles < 1:
        parser.error('cycles must be positive')
    report = []
    directory = ROOT / 'userdata' / 'display-test'
    directory.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dojo-display-') as temporary:
        args = argparse.Namespace(windowed=True, practice=False, demo=False, smoke=False,
                                  seconds=0, mute=True, data_dir=Path(temporary))
        app = Application(args)
        try:
            frame(app, 5)
            capture(app, directory, 'title')
            for index in range(options.cycles):
                before = app.renderer.fullscreen
                texture_before = app.renderer.hud_texture
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))
                frame(app, 5)
                assert app.renderer.fullscreen != before
                assert app.renderer.hud_texture == texture_before
                assert glIsTexture(texture_before)
                if not app.renderer.fullscreen:
                    assert (app.renderer.width, app.renderer.height) == (1280, 720)
                assert glGetError() == GL_NO_ERROR
                report.append({'transition': index, 'fullscreen': app.renderer.fullscreen,
                               'size': [app.renderer.width, app.renderer.height],
                               'msaa_actual': app.renderer.samples_actual,
                               'open_fds': len(list(Path('/proc/self/fd').iterdir())),
                               'rss_mb': round(resident_mb(), 2)})
            app.storage.settings['rules'] = 0
            app.new_match(False)
            app.match.phase = 'fight'
            app.match.player.x = -.65
            app.match.enemy.x = .65
            app.match.player.start_attack('round_kick')
            app.match.player.elapsed = MOVES['round_kick'].startup + .01
            app.match.resolve(app.match.player, app.match.enemy)
            for _ in range(25):
                app.match.update(1 / 60, Command())
                frame(app)
            app.screen = 'game'
            app.draw(0)
            capture(app, directory, 'judge-ippon')
            for arena in (1, 0, 1, 0):
                app.storage.settings['arena'] = arena
                app.renderer.change_arena()
                frame(app, 5)
                assert glGetError() == GL_NO_ERROR
            app.storage.settings['arena'] = 1
            app.renderer.change_arena()
            app.screen = 'title'
            app.match = None
            app.draw(0)
            capture(app, directory, 'moonlight')
            app.open_screen('play_select', 'title')
            app.draw(0)
            capture(app, directory, 'mode-select')
            app.open_screen('train_select', 'title')
            app.draw(0)
            capture(app, directory, 'training-select')
            report.append({'arena_swaps': 5, 'gl_error': glGetError()})
        finally:
            app.controls.close()
            app.audio.close()
            app.renderer.close()
            pygame.quit()
    (directory / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
