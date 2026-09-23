"""Render every technique at contact for visual inspection, without playing."""
import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame

from dojo.model import MOVES, Match
from dojo.renderer import Renderer
from dojo.storage import DEFAULTS, ROOT
from dojo.ui import UI


def main():
    pygame.display.init()
    settings = dict(DEFAULTS, fullscreen=False)
    renderer = Renderer(settings)
    ui = UI()
    directory = ROOT / 'userdata' / 'gallery'
    directory.mkdir(exist_ok=True)
    try:
        for number, (key, move) in enumerate(MOVES.items()):
            match = Match(practice=True, seed=1)
            match.phase = 'fight'
            match.player.x = -.8
            match.enemy.x = .8
            match.player.start_attack(key)
            match.player.elapsed = move.startup + move.active * .45
            match.last_technique = move.title
            renderer.camera_distance = 9.5
            renderer.camera_target = 0
            renderer.draw_world([match.player, match.enemy], 1 + number * .05, match)
            ui.begin(.016)
            ui.hud(match, None)
            renderer.draw_hud(ui.finish())
            renderer.screenshot(directory / (key + '.png'))
            renderer.present()
            pygame.event.pump()
    finally:
        renderer.close()
        pygame.quit()
    print(directory)


if __name__ == '__main__':
    main()
