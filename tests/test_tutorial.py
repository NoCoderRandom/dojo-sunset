"""Every lesson must be achievable through the same commands as normal play."""
import unittest

from dojo.model import Command
from dojo.tutorial import LESSONS, Tutorial


class TutorialTests(unittest.TestCase):
    def test_all_attack_lessons_can_be_completed(self):
        for index, lesson in enumerate(LESSONS):
            if lesson.goal != 'hit':
                continue
            with self.subTest(lesson=lesson.title):
                tutorial = Tutorial()
                tutorial.index = index
                tutorial.setup_lesson()
                for _step in range(120 * 20):
                    command = Command()
                    if tutorial.match.player.can_act:
                        command.attack = lesson.technique
                        command.crouch = lesson.technique == 'sweep'
                    tutorial.update(1 / 120, command)
                    if tutorial.lesson_done:
                        break
                self.assertTrue(tutorial.lesson_done, lesson.title)

    def test_wrong_move_does_not_complete_roundkick_lesson(self):
        tutorial = Tutorial()
        tutorial.index = 4
        tutorial.setup_lesson()
        for _step in range(120 * 5):
            tutorial.update(1 / 120, Command(attack='front_kick'))
        self.assertEqual(tutorial.progress, 0)

    def test_high_block_lesson_is_achievable(self):
        tutorial = Tutorial()
        tutorial.index = 7
        tutorial.setup_lesson()
        for _step in range(120 * 12):
            tutorial.update(1 / 120, Command(guard=True))
            if tutorial.lesson_done:
                break
        self.assertTrue(tutorial.lesson_done)

    def test_low_block_lesson_is_achievable(self):
        tutorial = Tutorial()
        tutorial.index = 8
        tutorial.setup_lesson()
        for _step in range(120 * 12):
            tutorial.update(1 / 120, Command(guard=True, crouch=True))
            if tutorial.lesson_done:
                break
        self.assertTrue(tutorial.lesson_done)

    def test_wrong_block_does_not_complete_sweep_defense(self):
        tutorial = Tutorial()
        tutorial.index = 8
        tutorial.setup_lesson()
        for _step in range(120 * 8):
            tutorial.update(1 / 120, Command(guard=True))
        self.assertEqual(tutorial.progress, 0)

    def test_movement_requires_both_directions(self):
        tutorial = Tutorial()
        for _step in range(60):
            tutorial.update(1 / 120, Command(move=-1))
        self.assertEqual(tutorial.progress, 1)
        for _step in range(90):
            tutorial.update(1 / 120, Command(move=1))
        self.assertTrue(tutorial.lesson_done)

    def test_dodge_lesson_is_achievable(self):
        tutorial = Tutorial()
        tutorial.index = 11
        tutorial.setup_lesson()
        for _step in range(120 * 5):
            tutorial.update(1 / 120, Command(dodge=True))
            if tutorial.lesson_done:
                break
        self.assertTrue(tutorial.lesson_done)

    def test_wrong_blocks_do_not_leave_the_student_out_of_range(self):
        for index in (7, 8):
            with self.subTest(lesson=index):
                tutorial = Tutorial()
                tutorial.index = index
                tutorial.setup_lesson()
                correct_crouch = index == 8
                for _ in range(120 * 8):
                    tutorial.update(1 / 120, Command(guard=True, crouch=not correct_crouch))
                self.assertEqual(tutorial.progress, 0)
                for _ in range(120 * 15):
                    tutorial.update(1 / 120, Command(guard=True, crouch=correct_crouch))
                    if tutorial.lesson_done:
                        break
                self.assertTrue(tutorial.lesson_done)

    def test_wrong_attacks_reset_distance_before_retrying_the_right_technique(self):
        tutorial = Tutorial()
        tutorial.index = 1
        tutorial.setup_lesson()
        for _ in range(120 * 5):
            tutorial.update(1 / 120, Command(attack='front_kick'))
        self.assertEqual(tutorial.progress, 0)
        for _ in range(120 * 15):
            tutorial.update(1 / 120, Command(attack='jab'))
            if tutorial.lesson_done:
                break
        self.assertTrue(tutorial.lesson_done)

    def test_skip_and_previous_are_bounded(self):
        tutorial = Tutorial()
        tutorial.previous_lesson()
        self.assertEqual(tutorial.index, 0)
        for _ in range(len(LESSONS) + 2):
            tutorial.skip_lesson()
        self.assertTrue(tutorial.completed)
        self.assertEqual(tutorial.index, len(LESSONS) - 1)

    def test_lesson_reset_preserves_statistics_consistency(self):
        tutorial = Tutorial()
        tutorial.index = 4
        tutorial.setup_lesson()
        tutorial.match.player.hits = 2
        tutorial.last_hits = 2
        tutorial.reset_positions()
        tutorial.update(.01, Command())
        self.assertEqual(tutorial.progress, 0)
        self.assertEqual(tutorial.match.player.hits, 2)


if __name__ == '__main__':
    unittest.main()
