"""Verify buffered action timing against real fighter recovery states."""
import unittest

from dojo.input_buffer import InputBuffer
from dojo.model import MOVES, Command, Fighter


class BufferedInputTests(unittest.TestCase):
    def fighter(self):
        return Fighter('Test', 0, 1, (1, 1, 1))

    def test_attack_pressed_near_recovery_is_not_lost(self):
        fighter = self.fighter()
        fighter.start_attack('jab')
        fighter.elapsed = MOVES['jab'].duration - .06
        buffer = InputBuffer()
        buffer.offer(Command(attack='round_kick'), 0)
        for step in range(12):
            command = buffer.take(fighter, Command(), step * .01)
            fighter.tick(.01, command)
        self.assertEqual(fighter.move_key, 'round_kick')

    def test_early_press_expires_instead_of_attacking_later(self):
        fighter = self.fighter()
        fighter.start_attack('spin_kick')
        buffer = InputBuffer()
        buffer.offer(Command(attack='jab'), 0)
        for step in range(150):
            command = buffer.take(fighter, Command(), step * .01)
            fighter.tick(.01, command)
        self.assertEqual(fighter.attacks, 1)

    def test_one_press_cannot_repeat(self):
        fighter = self.fighter()
        buffer = InputBuffer()
        buffer.offer(Command(attack='jab'), 0)
        for step in range(100):
            fighter.tick(.01, buffer.take(fighter, Command(), step * .01))
        self.assertEqual(fighter.attacks, 1)

    def test_sweep_modifier_is_preserved_until_execution(self):
        fighter = self.fighter()
        fighter.start_attack('jab')
        fighter.elapsed = MOVES['jab'].duration - .03
        buffer = InputBuffer()
        buffer.offer(Command(attack='round_kick', crouch=True), 0)
        for step in range(9):
            fighter.tick(.01, buffer.take(fighter, Command(), step * .01))
        self.assertEqual(fighter.move_key, 'sweep')

    def test_newer_button_press_replaces_older_intent(self):
        fighter = self.fighter()
        buffer = InputBuffer()
        buffer.offer(Command(attack='jab'), 0)
        buffer.offer(Command(attack='front_kick'), .02)
        fighter.tick(.01, buffer.take(fighter, Command(), .03))
        self.assertEqual(fighter.move_key, 'front_kick')

    def test_clear_prevents_menu_input_from_becoming_an_attack(self):
        fighter = self.fighter()
        buffer = InputBuffer()
        buffer.offer(Command(attack='front_kick'), 0)
        buffer.clear()
        fighter.tick(.01, buffer.take(fighter, Command(), .01))
        self.assertEqual(fighter.attacks, 0)

    def test_held_movement_and_block_are_not_delayed(self):
        fighter = self.fighter()
        buffer = InputBuffer()
        result = buffer.take(fighter, Command(move=-.7, guard=True), 10)
        self.assertEqual(result.move, -.7)
        self.assertTrue(result.guard)

    def test_buffer_accepts_highkick_chord_during_jump_anticipation(self):
        fighter = self.fighter()
        fighter.tick(.01, Command(jump=True))
        fighter.tick(.08, Command())
        buffer = InputBuffer()
        buffer.offer(Command(attack='high_kick'), .1)
        fighter.tick(.01, buffer.take(fighter, Command(), .1))
        self.assertEqual(fighter.move_key, 'high_kick')


if __name__ == '__main__':
    unittest.main()
