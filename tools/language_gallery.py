"""Render Swedish and English UI screens with real OpenGL for visual review."""
import argparse
import json
import sys
import tempfile
from pathlib import Path

import pygame
from OpenGL.GL import GL_NO_ERROR, glGetError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dojo.app import Application
from dojo.storage import ROOT


def capture(app, directory, name):
    app.draw(0)
    app.renderer.screenshot(directory / f'{name}.png')
    app.renderer.present()
    pygame.event.pump()
    if glGetError() != GL_NO_ERROR:
        raise RuntimeError(f'OpenGL error while rendering {name}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', choices=('sv', 'en'), default='en')
    options = parser.parse_args()
    directory = ROOT / 'userdata' / 'language-gallery' / options.language
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dojo-language-') as temporary:
        arguments = argparse.Namespace(windowed=True, practice=False, demo=False, smoke=False,
                                       seconds=0, mute=True, data_dir=Path(temporary))
        app = Application(arguments)
        try:
            app.storage.settings['language'] = options.language
            app.ui.set_language(options.language)
            capture(app, directory, 'title')
            app.screen = 'play_select'
            app.selected = 0
            capture(app, directory, 'match-select')
            app.screen = 'train_select'
            capture(app, directory, 'training-select')
            app.screen = 'options'
            app.selected = 8
            capture(app, directory, 'settings-language')
            app.screen = 'controller_select'
            app.selected = 0
            capture(app, directory, 'controller-select')
            app.screen = 'help'
            for page in range(3):
                app.help_page = page
                capture(app, directory, f'help-{page + 1}')
            app.screen = 'records'
            capture(app, directory, 'records')
            app.new_match(True, 'ninja')
            app.match.phase = 'fight'
            capture(app, directory, 'ninja-training')
            app.screen = 'pause'
            capture(app, directory, 'pause')
            app.match.winner = app.match.player
            app.match.player.wins = 2
            app.screen = 'result'
            capture(app, directory, 'result')
            app.screen = 'controller'
            capture(app, directory, 'controller-test')
            app.screen = 'quit'
            capture(app, directory, 'quit')
        finally:
            app.controls.close()
            app.controls2.close()
            app.audio.close()
            app.renderer.close()
            pygame.quit()
    report = {'language': options.language, 'screens': 14, 'gl_error': 0}
    (directory / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(directory)


if __name__ == '__main__':
    main()
