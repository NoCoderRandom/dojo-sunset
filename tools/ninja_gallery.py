"""Real OpenGL snapshots of the new opponents, animations and player menus."""
import os

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame
from OpenGL.GL import glGetError

from dojo.competition import Tournament, opponent_match
from dojo.model import MOVES, Projectile
from dojo.renderer import Renderer
from dojo.storage import DEFAULTS, ROOT
from dojo.ui import UI


def main():
    pygame.display.init()
    renderer = Renderer(dict(DEFAULTS, fullscreen=False))
    ui = UI()
    controls = SimpleNamespace(is_speedlink=False)
    out = ROOT / 'userdata' / 'ninja-gallery'
    out.mkdir(exist_ok=True)
    frames = []
    scenes = [
        ('roundkick-chamber', 'karate', 'round_kick', .45),
        ('roundkick-contact', 'karate', 'round_kick', 1.05),
        ('roundkick-follow', 'karate', 'round_kick', 1.35),
        ('ninja-ready', 'ninja', '', 0),
        ('nunchaku-windup', 'ninja', 'nunchaku', .45),
        ('nunchaku-contact', 'ninja', 'nunchaku', 1.08),
        ('nunchaku-overhead', 'ninja', 'nunchaku_overhead', 1.08),
        ('nunchaku-low', 'ninja', 'nunchaku_low', 1.08),
        ('nunchaku-flourish', 'ninja', 'flourish', 0),
        ('star-windup', 'ninja', 'shuriken', .75),
        ('star-flight', 'ninja', '', 0),
        ('sumo-ready', 'sumo', '', 0),
        ('sumo-palm', 'sumo', 'sumo_palm', 1.10),
        ('sumo-stomp-windup', 'sumo', 'sumo_stomp', .70),
        ('sumo-stomp', 'sumo', 'sumo_stomp', 1.1),
        ('sumo-charge', 'sumo', 'sumo_charge', 1.1),
    ]
    try:
        for index, (name, kind, move, phase) in enumerate(scenes):
            match = opponent_match(kind, practice=True, seed=1)
            match.phase = 'fight'
            match.player.x = -.90
            match.enemy.x = .90
            if move == 'flourish':
                match.enemy.state = 'flourish'
                match.enemy.elapsed = .48
                match.last_technique = 'NUNCHAKU • UPPVISNING'
            elif move:
                actor = match.player if kind == 'karate' else match.enemy
                assert actor.start_attack(move)
                actor.elapsed = MOVES[move].startup * phase
                match.last_technique = actor.move.title
            if name == 'star-flight':
                match.player.x = -1.5
                match.enemy.x = 2.0
                match.projectiles.append(Projectile(match.enemy, .1, 1.65, -6, rotation=23))
                match.last_technique = 'Huka under stjärnan, eller blockera med LB.'
            renderer.camera_distance = 9.5
            renderer.camera_target = 0
            renderer.draw_world([match.player, match.enemy], 1 + index * .02, match)
            ui.begin(.016)
            ui.hud(match, controls)
            renderer.draw_hud(ui.finish())
            renderer.screenshot(out / (name + '.png'))
            renderer.present()
            pygame.event.pump()
            error = int(glGetError())
            frames.append({'scene': name, 'gl_error': error})
            assert error == 0
        for stage in range(6):
            tournament = Tournament()
            tournament.stage = stage
            match = tournament.start_stage()
            renderer.draw_world([match.player, match.enemy], 2 + stage * .1, match)
            ui.begin(.016)
            ui.hud(match, controls)
            ui.tournament_badge(tournament)
            renderer.draw_hud(ui.finish())
            renderer.screenshot(out / f'chapter-{stage + 1}.png')
            renderer.present()
            pygame.event.pump()
        ui.begin(.016)
        ui.help(2, controls)
        renderer.draw_world([match.player, match.enemy], 3, match)
        renderer.draw_hud(ui.finish())
        renderer.screenshot(out / 'opponent-help.png')
        (out / 'report.json').write_text(json.dumps(frames, indent=2))
    finally:
        renderer.close()
        pygame.quit()
    print(out)


if __name__ == '__main__':
    main()
