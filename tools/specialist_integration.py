"""Real SDL input, mixer and OpenGL checks for the karate/ninja/sumo journey.

Uses isolated saves and process-local controllers. Finished matches and stars
are injected to exercise rare transitions deterministically, not claimed wins.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pygame
from OpenGL.GL import GL_NO_ERROR, glGetError

from dojo.model import Projectile
from dojo.storage import ROOT
from tools.integration_test import IntegrationRun


class SpecialistRun(IntegrationRun):
    def __init__(self):
        super().__init__()
        self.out = ROOT / 'userdata' / 'specialist-integration'
        self.out.mkdir(exist_ok=True)
        self.sounds = Counter()
        original_play = self.app.audio.play

        def record_play(name):
            self.sounds[name] += 1
            original_play(name)

        self.app.audio.play = record_play

    def leave_match(self):
        self.tap(6)
        for _ in range(3):
            self.tap(12)
        self.tap(0)
        self.check(self.app.screen == 'title', 'Pause returns to title')

    def train(self, index, kind):
        self.tap(12)
        self.tap(0)
        for _ in range(index):
            self.tap(12)
        self.tap(0)
        self.check(self.app.screen == 'game' and self.app.match.practice,
                   f'Controller opens {kind} practice')
        self.check(self.app.match.enemy.archetype == kind, f'Correct {kind} opponent')
        self.check(self.app.match.player.archetype == 'karate', 'Player stays unarmed')
        self.check(self.app.match.player.attacks == 0, 'Menu A does not leak into new match')
        self.check(self.app.match.practice_ai, 'Specialist practice starts with active opponent')
        self.tap(4)
        self.check(not self.app.match.practice_ai, 'Back disables training AI')
        self.frame(145)

    def run(self):
        self.frame(3)
        self.train(3, 'ninja')
        match = self.app.match
        match.player.x = -.8
        match.enemy.x = .8
        self.tap(10)
        self.frame(14)
        self.check(match.player.move_key == 'spin_kick', 'Xbox RB produces the spinning roundkick')
        self.check(self.sounds['round_swing'] > 0, 'Roundkick dispatches supplied swing audio')
        self.frame(60)
        self.pad.button(12, True)
        self.tap(1)
        self.check(match.player.move_key == 'sweep', 'Down+B remains legsweep against ninja')
        self.pad.button(12, False)
        self.frame(100)
        match.player.x = -1.8
        match.enemy.x = 1.8
        match.enemy.start_attack('shuriken')
        self.frame(31)
        self.check(bool(match.projectiles), 'Ninja star is rendered in flight')
        self.screenshot('star-flight')
        self.tap(6)
        self.check(self.app.screen == 'pause', 'Start pauses during star flight')
        frozen = [(p.x, p.life) for p in match.projectiles]
        self.frame(40)
        self.check([(p.x, p.life) for p in match.projectiles] == frozen,
                   'Paused stars do not advance or expire')
        self.tap(1)
        self.frame(5)
        self.check([(p.x, p.life) for p in match.projectiles] != frozen,
                   'Star resumes with simulation')
        self.frame(100)
        self.tap(4)
        self.check(match.practice_ai, 'Back restores training AI')
        self.leave_match()
        self.train(4, 'sumo')
        self.check(not self.app.match.projectiles, 'New sumo match has no old ninja stars')
        self.screenshot('sumo-practice')
        self.leave_match()

        self.tap(12)
        self.tap(12)
        self.tap(0)
        self.check(self.app.screen == 'help', 'Help accessible by controller')
        self.tap(14)
        self.tap(14)
        self.check(self.app.help_page == 2, 'Opponent help page reachable')
        self.screenshot('opponent-help')
        self.tap(14)
        self.check(self.app.help_page == 0, 'Three help pages wrap forward')
        self.tap(13)
        self.check(self.app.help_page == 2, 'Three help pages wrap backward')
        self.tap(1)
        self.tap(4)
        self.check(self.app.screen == 'controller', 'Back opens sound and controller test')
        for button, sound in ((0, 'round_swing'), (1, 'nunchaku_spin'), (11, 'kiai'),
                              (12, 'defeat'), (13, 'miss'), (14, 'hit_chop')):
            before = self.sounds[sound]
            self.tap(button)
            self.check(self.sounds[sound] == before + 1, f'Controller auditions {sound}')
            self.check(self.app.screen == 'controller', f'{sound} button stays in diagnostic')
        self.check(pygame.mixer.get_init() == (44100, -16, 2), 'Mixer retains stereo PCM format')
        self.tap(6)

        self.tap(0)
        self.tap(0)
        self.check(self.app.tournament is not None, 'First play choice starts journey')
        for index, kind in enumerate(('karate', 'karate', 'ninja', 'ninja', 'sumo', 'sumo')):
            match = self.app.match
            self.check(match.enemy.archetype == kind, f'Stage {index + 1} is {kind}')
            self.check(match.player.stars == 0, f'Player has no weapons at stage {index + 1}')
            self.check(match.player.attacks == 0, f'Continue A is not an attack at stage {index + 1}')
            # Deterministic result setup: test the actual result/save/continue path.
            match.phase = 'finished'
            match.winner = match.player
            match.player.score += 1500
            self.frame(1)
            self.check(self.app.screen == 'result', f'Stage {index + 1} reaches result menu')
            self.check(len(self.app.storage.records) == int(index == 5),
                       f'Stage {index + 1} saves only completed journey')
            self.screenshot(f'stage-{index + 1}-result')
            self.tap(0)
        self.check(self.app.tournament.stage == 0, 'Replay starts a fresh journey')
        self.check(self.app.match.player.score == 0, 'New journey resets session score')
        self.check(self.app.storage.records[0]['score'] == 9000, 'Completed journey score persists')
        self.check(self.app.storage.records[0]['name'] == 'BRUCE PI', 'Record belongs to player')
        # A new game cannot inherit a projectile even after an interrupted practice.
        self.app.match.projectiles.append(Projectile(self.app.match.enemy, 0, 1.65, -6))
        self.app.new_match(True, 'ninja')
        self.check(not self.app.match.projectiles, 'Fresh practice discards previous projectile state')
        self.check(glGetError() == GL_NO_ERROR, 'All specialist controller scenes render without GL error')
        self.leave_match()
        self.tap(6)
        self.tap(12)
        self.tap(0)
        self.check(not self.app.running, 'Controller exits after specialist tests')


def main():
    run = SpecialistRun()
    try:
        run.run()
    finally:
        run.close()


if __name__ == '__main__':
    main()
