"""Behavior tests for combat, rounds and deterministic long-running matches."""
import unittest

from dojo.animation import BASE, CLIPS, sample
from dojo.model import MOVES, Brain, Command, Fighter, Match


class CombatTests(unittest.TestCase):
    def allow_specialist(self, fighter, key):
        if key.startswith('nunchaku') or key == 'shuriken':
            fighter.set_archetype('ninja')
        elif key.startswith('sumo_'):
            fighter.set_archetype('sumo')

    def match(self):
        match = Match(practice=True, seed=42)
        match.phase = 'fight'
        match.player.x = -.7
        match.enemy.x = .7
        return match

    def strike(self, key, guard=False, crouch=False, distance=1.0):
        match = self.match()
        match.player.x = -distance / 2
        match.enemy.x = distance / 2
        match.enemy.guard = guard
        match.enemy.crouch = crouch
        match.enemy.state = 'guard' if guard else 'crouch' if crouch else 'idle'
        self.allow_specialist(match.player, key)
        self.assertTrue(match.player.start_attack(key))
        match.player.elapsed = MOVES[key].startup + .01
        match.resolve(match.player, match.enemy)
        return match

    def test_swing_and_hit_events_align_with_attack_animation(self):
        for key, move in MOVES.items():
            if move.projectile:
                continue  # Travel and release timing are tested in test_specialists.
            with self.subTest(key=key):
                match = self.match()
                match.player.x = -.4
                match.enemy.x = .4
                self.allow_specialist(match.player, key)
                self.assertTrue(match.player.start_attack(key))
                events = []
                for _ in range(180):
                    match.update(1 / 120, Command())
                    events.extend((event, match.elapsed) for event in match.events)
                swings = [time for event, time in events if event in ('swing', 'round_swing', 'nunchaku_spin')]
                hits = [time for event, time in events if event == 'hit']
                self.assertEqual(len(swings), 1)
                self.assertEqual(len(hits), 1)
                swing_time = .06 if key.startswith('nunchaku') else move.startup * .55
                self.assertAlmostEqual(swings[0], swing_time, delta=.009)
                self.assertAlmostEqual(hits[0], move.startup, delta=.009)
                self.assertLess(swings[0], hits[0])

    def test_all_moves_have_animation(self):
        self.assertEqual(set(MOVES), set(CLIPS))

    def test_roundhouse_hits_mid_level(self):
        match = self.strike('round_kick')
        self.assertEqual(match.enemy.health, 80)
        self.assertEqual(match.player.score, 250)
        self.assertEqual(match.enemy.state, 'hurt')

    def test_legsweep_knocks_down(self):
        match = self.strike('sweep')
        self.assertEqual(match.enemy.state, 'knockdown')
        self.assertLess(match.enemy.health, 100)

    def test_attack_hits_only_once(self):
        match = self.strike('jab')
        health = match.enemy.health
        match.enemy.invulnerable = 0
        match.resolve(match.player, match.enemy)
        self.assertEqual(match.enemy.health, health)

    def test_out_of_range_does_not_hit(self):
        for key in MOVES:
            if MOVES[key].projectile:
                continue
            with self.subTest(key=key):
                match = self.strike(key, distance=MOVES[key].reach + .2)
                self.assertEqual(match.enemy.health, 100)
                self.assertEqual(match.player.score, 0)

    def test_startup_cannot_hit(self):
        match = self.match()
        match.player.start_attack('round_kick')
        match.resolve(match.player, match.enemy)
        self.assertEqual(match.enemy.health, 100)

    def test_recovery_cannot_hit(self):
        match = self.match()
        match.player.start_attack('round_kick')
        match.player.elapsed = MOVES['round_kick'].duration - .02
        match.resolve(match.player, match.enemy)
        self.assertEqual(match.enemy.health, 100)

    def test_standing_block_stops_mid_and_high(self):
        for key in ('jab', 'cross', 'round_kick', 'high_kick'):
            with self.subTest(key=key):
                match = self.strike(key, guard=True)
                self.assertEqual(match.enemy.health, 100)
                self.assertLess(match.enemy.stamina, 100)
                self.assertEqual(match.enemy.blocks, 1)

    def test_standing_block_does_not_stop_sweep(self):
        match = self.strike('sweep', guard=True)
        self.assertLess(match.enemy.health, 100)

    def test_low_block_stops_sweep(self):
        match = self.strike('sweep', guard=True, crouch=True)
        self.assertEqual(match.enemy.health, 100)

    def test_crouch_evades_high_kick(self):
        match = self.strike('high_kick', crouch=True)
        self.assertEqual(match.enemy.health, 100)

    def test_low_guard_does_not_stop_mid_attack(self):
        match = self.strike('cross', guard=True, crouch=True)
        self.assertLess(match.enemy.health, 100)

    def test_downed_opponent_cannot_be_hit_on_the_floor(self):
        match = self.match()
        match.player.x = -.4
        match.enemy.x = .4
        match.enemy.state = 'knockdown'
        match.enemy.elapsed = .6
        match.enemy.invulnerable = 0
        match.player.start_attack('jab')
        match.player.elapsed = .13
        match.resolve(match.player, match.enemy)
        self.assertEqual(match.enemy.health, 100)
        match.enemy.tick(.5, Command())
        match.resolve(match.player, match.enemy)
        self.assertLess(match.enemy.health, 100)

    def test_depleted_guard_breaks(self):
        match = self.match()
        match.enemy.stamina = 0
        match.enemy.guard = True
        match.enemy.state = 'guard'
        match.player.start_attack('front_kick')
        match.player.elapsed = .24
        match.resolve(match.player, match.enemy)
        self.assertLess(match.enemy.health, 100)

    def test_cannot_attack_without_stamina(self):
        fighter = self.match().player
        fighter.stamina = 0
        self.assertFalse(fighter.start_attack('round_kick'))
        self.assertEqual(fighter.state, 'idle')

    def test_no_interrupting_attacks(self):
        fighter = self.match().player
        fighter.start_attack('round_kick')
        stamina = fighter.stamina
        self.assertFalse(fighter.start_attack('jab'))
        self.assertEqual(fighter.stamina, stamina)
        self.assertEqual(fighter.move_key, 'round_kick')

    def test_crouch_roundkick_becomes_legsweep(self):
        fighter = self.match().player
        fighter.tick(.01, Command(crouch=True, attack='round_kick'))
        self.assertEqual(fighter.move_key, 'sweep')

    def test_crouch_frontkick_becomes_lowkick(self):
        fighter = self.match().player
        fighter.tick(.01, Command(crouch=True, attack='front_kick'))
        self.assertEqual(fighter.move_key, 'low_kick')

    def test_high_kick_accepts_slightly_staggered_up_b_chord(self):
        fighter = self.match().player
        fighter.tick(.01, Command(jump=True))
        for _ in range(6):
            fighter.tick(.01, Command())
        fighter.tick(.01, Command(attack='high_kick'))
        self.assertEqual(fighter.move_key, 'high_kick')

    def test_jump_anticipation_is_still_grounded(self):
        fighter = self.match().player
        fighter.tick(.01, Command(jump=True))
        self.assertTrue(fighter.grounded)
        fighter.elapsed = .30
        self.assertFalse(fighter.grounded)

    def test_crouched_punch_has_a_matching_low_pose(self):
        fighter = self.match().player
        fighter.tick(.01, Command(attack='jab', crouch=True))
        self.assertEqual(fighter.move_key, 'crouch_punch')
        fighter.elapsed = MOVES['crouch_punch'].startup
        self.assertLess(sample(fighter, 0)['head'][1], 1.6)
        self.assertTrue(fighter.crouch)

    def test_lowkick_does_not_gain_invisible_high_attack_evasion(self):
        match = self.match()
        match.player.x = -.5
        match.enemy.x = .5
        match.enemy.start_attack('low_kick')
        match.enemy.elapsed = MOVES['low_kick'].startup
        self.assertGreater(sample(match.enemy, 0)['head'][1], 1.7)
        match.player.start_attack('jab')
        match.player.elapsed = MOVES['jab'].startup + .01
        match.resolve(match.player, match.enemy)
        self.assertLess(match.enemy.health, 100)

    def test_ducking_attacks_stay_visibly_low_in_every_phase(self):
        for key in ('crouch_punch', 'sweep'):
            fighter = self.match().player
            fighter.start_attack(key)
            for step in range(101):
                fighter.elapsed = MOVES[key].duration * step / 100
                with self.subTest(move=key, phase=step):
                    self.assertTrue(fighter.crouch)
                    self.assertLess(sample(fighter, 0)['head'][1], 1.6)

    def test_low_guard_keeps_the_head_visibly_crouched(self):
        fighter = self.match().player
        fighter.tick(.01, Command(crouch=True, guard=True))
        self.assertEqual(fighter.state, 'guard')
        self.assertLess(sample(fighter, 0)['head'][1], 1.6)

    def test_standing_attack_cannot_keep_a_phantom_crouch(self):
        fighter = self.match().player
        fighter.crouch = True
        fighter.start_attack('spin_kick')
        self.assertFalse(fighter.crouch)

    def test_jump_evades_sweep(self):
        match = self.match()
        match.enemy.state = 'jump'
        match.enemy.elapsed = .25
        match.player.start_attack('sweep')
        match.player.elapsed = .31
        match.resolve(match.player, match.enemy)
        self.assertEqual(match.enemy.health, 100)

    def test_dodge_has_short_invulnerability(self):
        match = self.match()
        match.enemy.tick(.01, Command(dodge=True))
        match.player.start_attack('round_kick')
        match.player.elapsed = .29
        match.resolve(match.player, match.enemy)
        self.assertEqual(match.enemy.health, 100)
        for _ in range(50):
            match.enemy.tick(.01, Command())
        self.assertEqual(match.enemy.invulnerable, 0)
        self.assertEqual(match.enemy.state, 'idle')

    def test_practice_has_no_time_limit(self):
        match = self.match()
        for _ in range(10000):
            match.update(.01, Command())
        self.assertEqual(match.phase, 'fight')
        self.assertEqual(match.remaining, 60)

    def test_time_limit_awards_health_lead(self):
        match = Match(seed=4)
        match.phase = 'fight'
        match.remaining = .01
        match.enemy.health = 40
        match.update(.02, Command())
        self.assertEqual(match.phase, 'round_over')
        self.assertIs(match.round_winner, match.player)
        self.assertEqual(match.player.wins, 1)

    def test_tied_round_awards_no_win(self):
        match = Match(seed=4)
        match.decide_round()
        self.assertIsNone(match.round_winner)
        self.assertEqual(match.player.wins, 0)
        self.assertEqual(match.enemy.wins, 0)

    def test_two_rounds_end_match(self):
        match = Match(seed=4)
        for _ in range(2):
            match.enemy.health = 0
            match.decide_round()
            match.update(3.3, Command())
        self.assertEqual(match.phase, 'finished')
        self.assertIs(match.winner, match.player)

    def test_pose_coordinates_are_finite(self):
        import math
        for key, move in MOVES.items():
            fighter = Fighter('Test', 0, 1, (1, 1, 1))
            self.allow_specialist(fighter, key)
            self.assertTrue(fighter.start_attack(key))
            for frame in range(50):
                fighter.elapsed = move.duration * frame / 49
                joints = sample(fighter, 0)
                self.assertEqual(set(joints), set(BASE))
                self.assertTrue(all(math.isfinite(value) for point in joints.values() for value in point))

    def test_hard_ai_selects_attacks_that_can_reach(self):
        match = self.match()
        match.player.x = 0
        match.enemy.x = 1.6
        brain = Brain(difficulty=2, seed=87)
        attacks = 0
        for _ in range(300):
            brain.wait = 0
            command = brain.update(.01, match.player, match.enemy)
            if command.attack:
                attacks += 1
                move = MOVES[command.attack]
                self.assertGreaterEqual(move.reach + move.advance, 1.6)
        self.assertGreater(attacks, 100)

    def test_ai_can_punish_recovery_instead_of_treating_it_as_an_active_attack(self):
        match = self.match()
        match.player.x = 0
        match.enemy.x = 1.4
        match.enemy.start_attack('front_kick')
        move = MOVES['front_kick']
        match.enemy.elapsed = move.startup + move.active + .01
        brain = Brain(difficulty=2, seed=93)
        brain.style = 'pressure'
        attacks = 0
        for _ in range(100):
            brain.wait = 0
            command = brain.update(.01, match.player, match.enemy)
            self.assertFalse(command.guard)
            attacks += bool(command.attack)
        self.assertGreater(attacks, 50)

    def test_seeded_ai_tournament_terminates(self):
        for seed in range(20):
            match = Match(difficulty=seed % 3, seed=seed)
            player_ai = Brain(difficulty=(seed + 1) % 3, seed=seed + 100)
            for _step in range(120 * 250):
                command = player_ai.update(1 / 120, match.player, match.enemy)
                match.update(1 / 120, command)
                self.assertTrue(-4.5 <= match.player.x <= 4.5)
                self.assertTrue(-4.5 <= match.enemy.x <= 4.5)
                self.assertTrue(0 <= match.player.health <= 100)
                self.assertTrue(0 <= match.enemy.health <= 100)
                self.assertTrue(0 <= match.player.stamina <= 100)
                if match.phase == 'finished':
                    break
            self.assertEqual(match.phase, 'finished', f'Match {seed} failed to finish')
            self.assertIn(match.winner, (match.player, match.enemy))


if __name__ == '__main__':
    unittest.main()
