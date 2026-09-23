"""Focused checks for the B roll, defense and its tutorial."""
import unittest

from dojo.animation import sample
from dojo.controls import Controls
from dojo.input_buffer import InputBuffer
from dojo.model import MOVES, Command, Fighter, Match
from dojo.tutorial import Tutorial


class RollTests(unittest.TestCase):
    def test_b_roll_and_existing_direction_modifiers(self):
        controls = Controls.__new__(Controls)
        controls.digital_x = 0
        controls.digital_direction_active = False
        controls.axis_x = 0
        controls.held = {'b'}
        controls.pressed = {'b'}
        self.assertTrue(controls.command().roll)
        self.assertEqual(controls.command().attack, '')
        controls.held.add('down')
        self.assertEqual(controls.command().attack, 'sweep')
        self.assertFalse(controls.command().roll)
        controls.held = {'b', 'up'}
        self.assertEqual(controls.command().attack, 'high_kick')

    def test_buffered_roll_moves_forward_both_directions_without_damage(self):
        for facing in (-1, 1):
            fighter = Fighter('TEST', 0, facing, (1, 1, 1))
            buffer = InputBuffer()
            buffer.offer(Command(roll=True), 0)
            fighter.tick(.01, buffer.take(fighter, Command(), .01))
            self.assertEqual(fighter.state, 'roll')
            self.assertEqual(fighter.stamina, 74)
            for step in range(90):
                fighter.tick(.01, buffer.take(fighter, Command(), (step + 2) * .01))
            self.assertAlmostEqual(fighter.x, facing * 1.485)
            self.assertTrue(fighter.can_act)
            self.assertEqual(fighter.attacks, 0)
            fighter.stamina = 10
            fighter.tick(.01, Command(roll=True))
            self.assertNotEqual(fighter.state, 'roll')

    def test_roll_ducks_high_hits_but_low_hits_can_interrupt(self):
        for move, safe in (('jab', True), ('sweep', False), ('front_kick', False)):
            match = Match(practice=True)
            match.phase = 'fight'
            defender, attacker = match.player, match.enemy
            defender.x, attacker.x = 0, .8
            defender.tick(.01, Command(roll=True))
            defender.tick(.25, Command())
            attacker.start_attack(move)
            attacker.elapsed = MOVES[move].startup + .01
            match.resolve(attacker, defender)
            self.assertEqual(defender.health == 100, safe)

    def test_tucked_pose_visibly_rotates_and_returns_to_standing(self):
        fighter = Fighter('TEST', 0, 1, (1, 1, 1), state='roll')
        fighter.elapsed = .38
        inverted = sample(fighter, 0)
        self.assertLess(inverted['head'][1], inverted['hip'][1])
        fighter.elapsed = .8
        standing = sample(fighter, 0)
        self.assertGreater(standing['head'][1], 1.9)

    def test_tutorial_and_arena_collision(self):
        tutorial = Tutorial()
        tutorial.index = 4
        tutorial.setup_lesson()
        for step in range(360):
            tutorial.update(1 / 120, Command(roll=step % 120 == 0))
        self.assertTrue(tutorial.lesson_done)
        match = Match(practice=True)
        match.phase = 'fight'
        match.player.x, match.enemy.x = 3.5, 4.5
        for step in range(120):
            match.update(1 / 120, Command(roll=step == 0))
        self.assertLessEqual(match.enemy.x, 4.5)
        self.assertLess(match.player.x, match.enemy.x)
