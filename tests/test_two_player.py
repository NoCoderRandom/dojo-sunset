"""Two local SDL Xbox pads; no Linux input devices or real player saves."""
import argparse
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame

from dojo.app import PLAY_ENTRIES, Application
from dojo.competition import ClassicMatch
from dojo.elite_input import ElitePad
from dojo.model import Command, Match, RollDirection
from dojo.storage import Storage
from tools.sdl_virtual import VirtualPad


class HeadlessRenderer:
    def __init__(self, settings):
        pygame.display.set_mode((64, 64))


class TwoPlayerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='dojo-versus-')
        args = argparse.Namespace(windowed=True, practice=False, demo=False,
                                  smoke=False, seconds=0, mute=True, data_dir=Path(self.temp.name))
        with patch('dojo.app.Renderer', HeadlessRenderer):
            self.app = Application(args)
        self.pads = [VirtualPad(), VirtualPad()]
        self.frame()

    def tearDown(self):
        self.app.controls.close()
        for pad in self.pads:
            pad.close()
        self.app.audio.close()
        pygame.quit()
        self.temp.cleanup()

    def frame(self, dt=1 / 60):
        self.app.handle_input(dt)
        if self.app.screen == 'game':
            self.app.tick_match(dt)

    def tap(self, player, button):
        self.pads[player].button(button, True)
        self.frame()
        self.pads[player].button(button, False)
        self.frame()

    def start(self, rules=1):
        self.app.open_versus(rules)
        self.tap(0, 0)
        self.assertEqual(self.app.screen, 'versus_ready')
        self.tap(1, 0)
        self.assertEqual(self.app.screen, 'game')
        self.app.match.phase = 'fight'

    def test_ready_and_independent_simultaneous_inputs(self):
        self.start()
        self.assertNotEqual(self.app.controls.instance, self.app.controls2.instance)
        self.assertEqual(self.app.match.player.attacks, 0)
        self.assertEqual(self.app.match.enemy.attacks, 0)
        self.pads[0].button(2, True)
        self.pads[1].button(10, True)
        with patch.object(self.app.match.brain, 'update', side_effect=AssertionError('CPU in versus')):
            self.frame()
        self.assertEqual(self.app.match.player.move_key, 'jab')
        self.assertEqual(self.app.match.enemy.move_key, 'spin_kick')

    def test_both_players_can_roll_backward_away_from_the_centre(self):
        self.start()
        self.pads[0].button(13, True)  # Player 1 outward: left.
        self.pads[0].button(1, True)
        self.pads[1].button(14, True)  # Player 2 outward: right.
        self.pads[1].button(1, True)
        self.frame()
        self.assertEqual(self.app.match.player.state, 'roll')
        self.assertEqual(self.app.match.enemy.state, 'roll')
        self.assertEqual(self.app.match.player.roll_direction, RollDirection.BACKWARD)
        self.assertEqual(self.app.match.enemy.roll_direction, RollDirection.BACKWARD)
        self.assertLess(self.app.match.player.roll_facing, 0)
        self.assertGreater(self.app.match.enemy.roll_facing, 0)

    def test_second_player_brief_press_is_buffered(self):
        self.start()
        self.app.accumulator = 0
        self.pads[1].button(10, True)
        self.frame(1 / 240)
        self.pads[1].button(10, False)
        self.frame(1 / 240)
        self.assertEqual(self.app.match.enemy.attacks, 1)
        self.assertEqual(self.app.match.player.attacks, 0)

    def test_second_player_pause_resume_and_disconnect_preserves_slots(self):
        self.start()
        self.tap(1, 6)
        self.assertEqual(self.app.screen, 'pause')
        self.tap(1, 0)
        self.assertEqual(self.app.screen, 'game')
        self.assertEqual(self.app.match.enemy.attacks, 0)
        second_id = self.app.controls2.instance
        self.pads[0].close()
        self.frame()
        self.assertEqual(self.app.screen, 'pause')
        self.assertEqual(self.app.controls2.instance, second_id)
        self.tap(1, 0)
        self.assertEqual(self.app.screen, 'pause')
        self.pads[0] = VirtualPad()
        self.frame()
        self.assertEqual(self.app.controls.instance, self.pads[0].instance_id)
        self.assertEqual(self.app.controls2.instance, second_id)
        self.tap(1, 0)
        self.assertEqual(self.app.screen, 'game')
        self.pads[1].close()
        self.frame()
        self.assertEqual(self.app.screen, 'pause')

    def test_keyboard_cannot_play_or_select_menus(self):
        for key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_j, pygame.K_u, pygame.K_RIGHT):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.frame()
        self.assertEqual(self.app.screen, 'title')
        self.start()
        for key in (pygame.K_u, pygame.K_j, pygame.K_RIGHT, pygame.K_ESCAPE):
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.frame()
        self.assertEqual(self.app.screen, 'game')
        self.assertEqual(self.app.match.player.attacks, 0)
        self.assertEqual(self.app.match.enemy.attacks, 0)
        self.assertEqual(self.app.controls.command().move, 0)

    def test_cpu_mode_ignores_second_pad(self):
        self.app.new_match()
        self.app.match.phase = 'fight'
        self.pads[1].button(6, True)
        with patch.object(self.app.match.brain, 'update', return_value=Command(attack='cross')) as brain:
            self.frame()
        self.assertTrue(brain.called)
        self.assertEqual(self.app.screen, 'game')
        self.assertEqual(self.app.match.enemy.move_key, 'cross')

    def test_ready_is_reset_after_controller_replacement(self):
        self.app.open_versus(0)
        self.tap(1, 0)
        self.assertTrue(self.app.ready[1])
        self.pads[1].close()
        self.frame()
        self.pads[1] = VirtualPad()
        self.frame()
        self.tap(0, 0)
        self.assertEqual(self.app.screen, 'versus_ready')
        self.tap(1, 0)
        self.assertIsInstance(self.app.match, ClassicMatch)

    def test_both_rules_allow_player_two_win_and_rematch_without_cpu_records(self):
        for rules, match_type in ((0, ClassicMatch), (1, Match)):
            self.start(rules)
            match = self.app.match
            self.assertIsInstance(match, match_type)
            with patch.object(match.brain, 'update', side_effect=AssertionError('CPU in versus')):
                for _ in range(2):
                    match.phase = 'fight'
                    match.hit_stop = 0
                    if rules == 0:
                        match.enemy_points = 4
                        match.player_points = 0
                    else:
                        match.player.health = 0
                    match.decide_round()
                    match.update(4, Command(), Command())
            self.assertIs(match.winner, match.enemy)
            self.frame()
            self.assertEqual(self.app.screen, 'result')
            self.assertEqual(self.app.storage.records, [])
            self.app.ui.begin(.016)
            self.app.ui.result(match, ['Spela igen', 'Träna karate', 'Till huvudmenyn'], 0, False)
            self.tap(1, 0)
            self.assertEqual(self.app.screen, 'versus_ready')
            self.assertEqual(self.app.versus_rules, rules)

    def test_new_screens_draw_and_non_xbox_is_ignored(self):
        for choice in range(len(PLAY_ENTRIES)):
            self.app.ui.begin(.016)
            self.app.ui.mode_select('VÄLJ DIN MATCH', PLAY_ENTRIES, choice, False)
        self.app.ui.versus_ready((self.app.controls, self.app.controls2), [False, True], 0)
        self.app.controls.close_pad()
        with patch('dojo.controls.controller.name_forindex', return_value='Other controller'):
            self.app.controls.scan()
        self.assertIsNone(self.app.controls.pad)

    def test_controller_preferences_assign_two_distinct_xbox_pads(self):
        self.app.storage.settings['controller_p1'] = 'xbox'
        self.app.storage.settings['controller_p2'] = 'xbox'
        self.assertTrue(self.app.apply_controller_preferences())
        self.assertIsNotNone(self.app.controls.pad)
        self.assertIsNotNone(self.app.controls2.pad)
        self.assertNotEqual(self.app.controls.instance, self.app.controls2.instance)
        restored = Storage(Path(self.temp.name))
        self.assertEqual(restored.settings['controller_p1'], 'xbox')
        self.assertEqual(restored.settings['controller_p2'], 'xbox')

    def test_unavailable_controller_choice_preserves_active_pads(self):
        instances = (self.app.controls.instance, self.app.controls2.instance)
        self.app.storage.settings['controller_p1'] = 'speedlink'
        self.assertFalse(self.app.apply_controller_preferences())
        self.assertEqual((self.app.controls.instance, self.app.controls2.instance), instances)

    def test_elite_fallback_can_ready_attack_and_disconnect_beside_sdl_xbox(self):
        elite = ElitePad.__new__(ElitePad)
        elite.instance = 'elite:test-device'
        elite.fd = None
        elite.keys = bytearray(96)
        elite.axes = {code: (0, -32768, 32767, 0, 0, 0) for code in (0, 1, 16, 17)}
        elite.axes.update({code: (0, 0, 1023, 0, 0, 0) for code in (9, 10)})
        self.pads[1].close()
        with (patch('dojo.controls.find_elite', return_value=elite),
              patch.object(ElitePad, 'attached', return_value=True),
              patch.object(ElitePad, 'poll', return_value=set())):
            self.frame()
            self.assertIs(self.app.controls2.pad, elite)
            self.app.open_versus(1)
            self.tap(0, 0)
            elite.keys[304 // 8] |= 1 << (304 % 8)  # A, as advertised by Linux.
            self.frame()
            self.assertEqual(self.app.screen, 'game')
            self.assertEqual(self.app.match.enemy.attacks, 0)
            elite.keys = bytearray(96)
            self.frame()
            self.app.match.phase = 'fight'
            elite.keys[307 // 8] |= 1 << (307 % 8)  # X.
            self.frame()
            self.assertEqual(self.app.match.enemy.move_key, 'jab')
            self.assertEqual(self.app.match.player.attacks, 0)
            elite.axes[10] = (1023, 0, 1023, 0, 0, 0)
            self.assertEqual(elite.get_axis(pygame.CONTROLLER_AXIS_TRIGGERLEFT), 32767)
            self.assertEqual(elite.get_axis(pygame.CONTROLLER_AXIS_TRIGGERRIGHT), 0)
            with patch.object(ElitePad, 'poll', side_effect=OSError('disconnected')):
                self.frame()
            self.assertEqual(self.app.screen, 'pause')
