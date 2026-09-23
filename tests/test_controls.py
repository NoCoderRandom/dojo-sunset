"""Exercise real SDL event polling with process-local virtual Xbox inputs."""
import os

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import unittest

import pygame

from dojo.controls import Controls, SpeedlinkPad
from dojo.storage import DEFAULTS
from tools.sdl_virtual import VirtualPad


class ControllerTests(unittest.TestCase):
    def setUp(self):
        pygame.display.init()
        pygame.display.set_mode((64, 64))
        pygame.joystick.init()
        self.virtual = VirtualPad()
        self.controls = Controls(dict(DEFAULTS), preferred_instance=self.virtual.instance_id)
        self.controls.poll(.016)
        self.controls.poll(.016)

    def tearDown(self):
        self.controls.close()
        self.virtual.close()
        pygame.quit()

    def press(self, index):
        self.virtual.button(index, True)
        self.controls.poll(.016)

    def test_virtual_pad_selected(self):
        self.assertIsNotNone(self.controls.pad)
        self.assertIn('virtual', self.controls.name.lower())

    def test_face_buttons_map_to_moves(self):
        for index, expected in [(0, 'front_kick'), (2, 'jab'), (3, 'cross')]:
            with self.subTest(index=index):
                self.press(index)
                self.assertEqual(self.controls.command().attack, expected)
                self.virtual.button(index, False)
                self.controls.poll(.016)

    def test_down_b_maps_to_sweep(self):
        self.virtual.button(12, True)
        self.press(1)
        command = self.controls.command()
        self.assertTrue(command.crouch)
        self.assertEqual(command.attack, 'sweep')

    def test_up_b_maps_to_highkick(self):
        self.virtual.button(11, True)
        self.press(1)
        self.assertEqual(self.controls.command().attack, 'high_kick')

    def test_dpad_moves_player(self):
        self.press(13)
        self.assertEqual(self.controls.command().move, -1)
        self.virtual.button(13, False)
        self.press(14)
        self.assertEqual(self.controls.command().move, 1)

    def test_left_shoulder_guards(self):
        self.press(9)
        self.assertTrue(self.controls.command().guard)
        self.controls.poll(.016)
        self.assertTrue(self.controls.command().guard)

    def test_right_shoulder_spins(self):
        self.press(10)
        self.assertEqual(self.controls.command().attack, 'spin_kick')

    def test_right_trigger_jumpkick(self):
        self.virtual.axis(5, 1)
        self.controls.poll(.016)
        self.assertEqual(self.controls.command().attack, 'jump_kick')

    def test_left_trigger_dodges(self):
        self.virtual.axis(4, 1)
        self.controls.poll(.016)
        self.assertTrue(self.controls.command().dodge)

    def test_start_pause_edge(self):
        self.press(6)
        self.assertTrue(self.controls.hit('start'))
        self.controls.poll(.016)
        self.assertFalse(self.controls.hit('start'))

    def test_held_attack_does_not_repeat(self):
        self.press(2)
        self.assertEqual(self.controls.command().attack, 'jab')
        self.controls.poll(.016)
        self.assertEqual(self.controls.command().attack, '')

    def test_deadzone_prevents_drift(self):
        self.virtual.axis(0, .10)
        self.controls.poll(.016)
        self.assertEqual(self.controls.command().move, 0)

    def test_analog_movement_is_proportional(self):
        self.virtual.axis(0, .40)
        self.controls.poll(.016)
        value = self.controls.command().move
        self.assertGreater(value, 0)
        self.assertLess(value, .5)

    def test_analog_speed_does_not_snap_to_full_at_menu_threshold(self):
        values = []
        for axis in (.4, .6, .7, .8, .9, 1.0):
            self.virtual.axis(0, axis)
            self.controls.poll(.016)
            values.append(self.controls.command().move)
        self.assertTrue(all(a < b for a, b in zip(values, values[1:], strict=False)))
        self.assertLess(values[3], .85)
        self.assertEqual(values[-1], 1)

    def test_opposed_dpad_directions_are_neutral(self):
        self.virtual.button(13, True)
        self.virtual.button(14, True)
        self.controls.poll(.016)
        self.assertEqual(self.controls.command().move, 0)

    def test_opening_menu_requires_old_vertical_input_to_be_released(self):
        self.press(12)
        self.controls.reset_menu_navigation()
        self.assertEqual(self.controls.menu_step(), 0)
        self.controls.poll(.6)
        self.assertEqual(self.controls.menu_step(), 0)
        self.virtual.button(12, False)
        self.controls.poll(.016)
        self.controls.menu_step()
        self.press(12)
        self.assertEqual(self.controls.menu_step(), 1)

    def test_disconnect_is_reported(self):
        self.virtual.close()
        self.controls.poll(.016)
        self.assertTrue(self.controls.disconnect)
        self.assertIsNone(self.controls.pad)

    def test_virtual_device_removal_tracks_instance_not_stale_index(self):
        other = VirtualPad()
        other_id = other.instance_id
        self.controls.close_pad()
        self.virtual.close()
        other.close()
        remaining = [pygame.joystick.Joystick(i).get_instance_id()
                     for i in range(pygame.joystick.get_count())]
        self.assertNotIn(other_id, remaining)

    def test_hotplug_reconnects(self):
        self.virtual.close()
        self.controls.poll(.016)
        self.virtual = VirtualPad()
        self.controls.preferred_instance = self.virtual.instance_id
        self.controls.poll(.016)
        self.assertIsNotNone(self.controls.pad)


class FakeCompetitionPro:
    def __init__(self):
        self.buttons = [False] * 5
        self.axes = [0.0, 0.0]
        self.closed = False

    def get_button(self, index):
        return self.buttons[index]

    def get_axis(self, index):
        return self.axes[index]

    def get_init(self):
        return not self.closed

    def quit(self):
        self.closed = True


class SpeedlinkPadTests(unittest.TestCase):
    def setUp(self):
        self.raw = FakeCompetitionPro()
        self.pad = SpeedlinkPad.__new__(SpeedlinkPad)
        self.pad.joystick = self.raw

    def test_four_physical_buttons_map_to_four_actions(self):
        mapped = [(0, pygame.CONTROLLER_BUTTON_B), (1, pygame.CONTROLLER_BUTTON_Y),
                  (3, pygame.CONTROLLER_BUTTON_A), (4, pygame.CONTROLLER_BUTTON_X)]
        for raw_index, button in mapped:
            with self.subTest(raw_index=raw_index):
                self.raw.buttons = [False] * 5
                self.raw.buttons[raw_index] = True
                self.assertTrue(self.pad.get_button(button))

    def test_digital_stick_maps_to_left_axes(self):
        self.raw.axes = [-1.0, 1.0]
        self.assertEqual(self.pad.get_axis(pygame.CONTROLLER_AXIS_LEFTX), -32767)
        self.assertEqual(self.pad.get_axis(pygame.CONTROLLER_AXIS_LEFTY), 32767)

    def test_all_four_buttons_is_pause_gesture(self):
        self.raw.buttons = [True] * 5
        self.assertTrue(self.pad.get_button(pygame.CONTROLLER_BUTTON_START))
        self.raw.buttons[3] = False
        self.assertFalse(self.pad.get_button(pygame.CONTROLLER_BUTTON_START))


if __name__ == '__main__':
    unittest.main()
