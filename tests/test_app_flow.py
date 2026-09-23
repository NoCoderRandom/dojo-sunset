"""Real SDL input through application states, fixed stepping and isolated saves.

Only the OpenGL renderer is replaced, so these checks can run headlessly while
another process performs the real GPU endurance test.
"""
import os

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from dojo.app import Application
from dojo.storage import Storage
from dojo.tutorial import LESSONS
from tools.sdl_virtual import VirtualPad


class HeadlessRenderer:
    def __init__(self, settings):
        pygame.display.set_mode((64, 64))
        self.settings = settings

    def change_arena(self):
        pass


class ApplicationFlowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='dojo-flow-')
        args = argparse.Namespace(windowed=True, practice=False, demo=False,
                                  smoke=False, seconds=0, mute=True,
                                  data_dir=Path(self.temporary.name))
        with patch('dojo.app.Renderer', HeadlessRenderer):
            self.app = Application(args)
        self.pad = VirtualPad()
        self.app.controls.preferred_instance = self.pad.instance_id
        self.app.controls.scan()
        self.frame()

    def tearDown(self):
        self.app.controls.close()
        self.pad.close()
        self.app.audio.close()
        pygame.quit()
        self.temporary.cleanup()

    def frame(self, count=1, dt=1 / 60):
        for _ in range(count):
            self.app.elapsed += dt
            self.app.handle_input(dt)
            if self.app.screen == 'game':
                self.app.tick_match(dt)

    def tap(self, button):
        self.pad.button(button, True)
        self.frame()
        self.pad.button(button, False)
        self.frame()

    def neutral(self):
        for button in range(15):
            self.pad.button(button, False)
        for axis in range(4):
            self.pad.axis(axis, 0)
        self.pad.axis(4, -1)
        self.pad.axis(5, -1)

    def test_all_lessons_completed_with_real_controller_commands(self):
        self.app.start_tutorial()
        techniques = {'jab': 2, 'cross': 3, 'front_kick': 0, 'round_kick': 1,
                      'sweep': 1, 'high_kick': 1, 'spin_kick': 10}
        completed = []
        for index in range(len(LESSONS)):
            tutorial = self.app.tutorial
            self.assertEqual(tutorial.index, index)
            lesson = tutorial.lesson
            for frame in range(60 * 30):
                self.neutral()
                if lesson.goal == 'movement':
                    self.pad.axis(0, -1 if frame < 45 else 1)
                elif lesson.goal.startswith('block_'):
                    self.pad.button(9, True)
                    self.pad.button(12, lesson.goal == 'block_low')
                elif frame % 90 == 0:
                    if lesson.goal == 'roll':
                        self.pad.button(1, True)
                    elif lesson.goal == 'back_roll':
                        self.pad.button(13, True)
                        self.pad.button(1, True)
                    elif lesson.goal == 'dodge':
                        self.pad.axis(4, 1)
                    elif lesson.technique == 'jump_kick':
                        self.pad.axis(5, 1)
                    else:
                        self.pad.button(techniques[lesson.technique], True)
                        self.pad.button(12, lesson.technique == 'sweep')
                        self.pad.button(11, lesson.technique == 'high_kick')
                self.frame()
                if tutorial.lesson_done:
                    completed.append(lesson.title)
                    break
            self.assertTrue(tutorial.lesson_done, lesson.title)
            self.neutral()
            self.frame(30)
            self.tap(0)
        self.assertEqual(len(completed), len(LESSONS))
        self.assertEqual(self.app.screen, 'title')
        self.assertIsNone(self.app.tutorial)
        self.assertEqual(self.app.storage.records, [])

    def test_skip_final_lesson_returns_to_title(self):
        self.app.start_tutorial()
        for _ in range(len(LESSONS)):
            self.tap(4)
        self.assertEqual(self.app.screen, 'title')
        self.assertIsNone(self.app.match)

    def test_quick_press_is_retained_until_next_simulation_step(self):
        self.app.new_match(True)
        self.app.match.phase = 'fight'
        self.pad.button(10, True)
        self.frame(dt=1 / 240)
        self.pad.button(10, False)
        self.frame(dt=1 / 240)
        self.assertEqual(self.app.match.player.move_key, 'spin_kick')
        self.assertEqual(self.app.match.player.attacks, 1)

    def test_pause_and_resume_do_not_execute_menu_a_as_attack(self):
        self.app.new_match(True)
        self.app.match.phase = 'fight'
        self.tap(6)
        self.assertEqual(self.app.screen, 'pause')
        elapsed = self.app.match.elapsed
        self.frame(120)
        self.assertEqual(self.app.match.elapsed, elapsed)
        self.tap(0)
        self.frame(30)
        self.assertEqual(self.app.screen, 'game')
        self.assertEqual(self.app.match.player.attacks, 0)

    def test_background_input_cannot_resume_game_or_change_other_menus(self):
        self.app.arguments.mute = False  # SDL dummy audio: no physical playback.
        self.app.storage.settings['volume'] = .4
        self.app.audio.set_volume(.4)
        self.app.new_match(True)
        self.app.match.phase = 'fight'
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.frame()
        self.assertEqual(self.app.screen, 'pause')
        self.assertEqual(self.app.audio.volume, 0)
        self.tap(0)
        self.tap(6)
        self.assertEqual(self.app.screen, 'pause')
        self.pad.button(0, True)
        self.frame()
        pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.frame()
        self.assertEqual(self.app.screen, 'pause')
        self.assertEqual(self.app.audio.volume, .4)
        self.pad.button(0, False)
        self.frame()
        self.tap(0)
        self.assertEqual(self.app.screen, 'game')
        self.assertEqual(self.app.match.player.attacks, 0)

    def test_tournament_records_only_once_after_final_result(self):
        self.app.start_tournament()
        for stage in range(6):
            match = self.app.match
            self.assertEqual(self.app.tournament.stage, stage)
            match.player.score += 4200
            match.phase = 'finished'
            match.winner = match.player
            self.frame()
            self.assertEqual(self.app.screen, 'result')
            if stage < 5:
                self.assertEqual(self.app.storage.records, [])
                self.tap(0)
                self.assertEqual(self.app.screen, 'game')
            else:
                self.assertEqual(len(self.app.storage.records), 1)
                self.assertEqual(self.app.storage.records[0]['score'], 25200)
        self.frame(120)
        stored = Storage(Path(self.temporary.name))
        self.assertEqual(len(stored.records), 1)
        self.assertEqual(stored.best_score, 25200)

    def test_failed_tournament_saves_earned_score_and_restarts(self):
        self.app.start_tournament()
        self.app.match.player.score = 1800
        self.app.match.phase = 'finished'
        self.app.match.winner = self.app.match.enemy
        self.frame()
        self.assertTrue(self.app.tournament.failed)
        self.assertEqual(self.app.storage.best_score, 1800)
        self.tap(0)
        self.assertEqual(self.app.tournament.stage, 0)
        self.assertEqual(self.app.match.player.score, 0)
        self.assertEqual(self.app.screen, 'game')


if __name__ == '__main__':
    unittest.main()
