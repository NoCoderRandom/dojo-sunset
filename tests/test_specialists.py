"""Playable counters, projectile ownership, progression and sound timing."""
import math
import unittest

from dojo.animation import BASE, ROUND_CHAMBER, sample
from dojo.competition import ClassicMatch, Tournament, opponent_match
from dojo.model import MOVES, Brain, Command, Fighter, Projectile
from dojo.weapons import nunchaku_points


class SpecialistTests(unittest.TestCase):
    def encounter(self, kind='ninja'):
        match = opponent_match(kind, practice=True, seed=7)
        match.phase = 'fight'
        match.player.x = -1.5
        match.enemy.x = 1.5
        return match

    def step(self, match, seconds, command=None):
        events = []
        for _ in range(round(seconds * 120)):
            match.update(1 / 120, command or Command())
            events.extend(match.events)
        return events

    def incoming(self, match, x=-.5):
        match.player.x = 0
        match.enemy.x = -3
        star = Projectile(match.enemy, x, 1.65, 6)
        match.projectiles.append(star)
        return star

    def test_player_cannot_use_ninja_or_sumo_attacks(self):
        fighter = Fighter('BRUCE PI', 0, 1, (1, 1, 1))
        for key in ('nunchaku', 'nunchaku_overhead', 'nunchaku_low', 'shuriken',
                    'sumo_palm', 'sumo_stomp', 'sumo_charge'):
            self.assertFalse(fighter.start_attack(key), key)
        self.assertEqual(fighter.stamina, 100)
        self.assertEqual(fighter.attacks, 0)

    def test_campaign_has_two_karate_then_two_ninja_then_two_sumo(self):
        tournament = Tournament()
        kinds = []
        for stage in range(6):
            match = tournament.start_stage()
            kinds.append(match.enemy.archetype)
            self.assertEqual(match.player.archetype, 'karate')
            self.assertEqual(match.player.stars, 0)
            self.assertEqual(isinstance(match, ClassicMatch), stage < 2)
            match.phase = 'finished'
            match.winner = match.player
            match.player.score += 1000
            self.assertTrue(tournament.complete_stage())
        self.assertEqual(kinds, ['karate', 'karate', 'ninja', 'ninja', 'sumo', 'sumo'])
        self.assertTrue(tournament.finished)
        self.assertEqual(tournament.total_score, 6000)

    def test_star_release_uses_one_ammo_and_has_real_travel_time(self):
        match = self.encounter()
        self.assertTrue(match.enemy.start_attack('shuriken'))
        events = self.step(match, .45)
        self.assertFalse(match.projectiles)
        self.assertNotIn('star_throw', events)
        events += self.step(match, .06)
        self.assertEqual(len(match.projectiles), 1)
        self.assertEqual(match.enemy.stars, 3)
        self.assertEqual(match.player.health, 100)
        self.assertEqual(events.count('star_throw'), 1)
        events += self.step(match, .8)
        self.assertEqual(events.count('star_throw'), 1)
        self.assertLess(match.player.health, 100)
        self.assertFalse(match.projectiles)

    def test_interrupted_throw_does_not_spawn_or_spend_ammo(self):
        match = self.encounter()
        match.player.x = .4
        match.enemy.x = 1.5
        match.enemy.start_attack('shuriken')
        match.enemy.elapsed = .2
        match.player.start_attack('cross')
        match.player.elapsed = MOVES['cross'].startup + .01
        match.resolve(match.player, match.enemy)
        self.step(match, .8)
        self.assertFalse(match.projectiles)
        self.assertEqual(match.enemy.stars, 4)

    def test_empty_ammo_and_cooldown_prevent_star_spam(self):
        ninja = self.encounter().enemy
        ninja.stars = 0
        self.assertFalse(ninja.start_attack('shuriken'))
        ninja.stars = 2
        ninja.star_cooldown = .5
        self.assertFalse(ninja.start_attack('shuriken'))
        ninja.tick(.51, Command())
        self.assertTrue(ninja.start_attack('shuriken'))

    def test_stars_replenish_only_at_round_reset(self):
        ninja = self.encounter().enemy
        ninja.stars = 0
        ninja.reset_round(1.6, -1)
        self.assertEqual(ninja.stars, 4)

    def test_standing_guard_blocks_star_once(self):
        match = self.encounter()
        self.incoming(match)
        match.player.guard = True
        match.player.state = 'guard'
        match.update_projectiles(.1)
        match.update_projectiles(.1)
        self.assertEqual(match.player.health, 100)
        self.assertEqual(match.player.blocks, 1)
        self.assertEqual(match.events.count('block'), 1)
        self.assertFalse(match.projectiles)

    def test_crouch_evades_star_but_low_guard_cannot_catch_a_standing_hit(self):
        match = self.encounter()
        self.incoming(match)
        match.player.crouch = True
        self.step(match, .5, Command(crouch=True))
        self.assertEqual(match.player.health, 100)
        self.assertEqual(match.enemy.hits, 0)

    def test_star_dodge_does_not_catch_after_invulnerability_expires(self):
        match = self.encounter()
        self.incoming(match)
        match.player.invulnerable = .3
        self.step(match, .7)
        self.assertEqual(match.player.health, 100)

    def test_swept_collision_catches_fast_star(self):
        match = self.encounter()
        self.incoming(match, -1)
        match.update_projectiles(.4)
        self.assertEqual(match.player.health, 88)
        self.assertFalse(match.projectiles)

    def test_projectile_push_uses_its_direction_not_owners_new_facing(self):
        match = self.encounter()
        self.incoming(match)
        match.enemy.facing = -1
        match.update_projectiles(.1)
        self.assertGreater(match.player.velocity, 0)

    def test_round_end_clears_inflight_stars(self):
        match = self.encounter()
        self.incoming(match)
        match.player.health = 20
        match.decide_round()
        self.assertFalse(match.projectiles)
        self.assertEqual(match.events.count('defeat'), 1)

    def test_expired_stars_leave_no_persistent_objects(self):
        match = self.encounter()
        match.projectiles.append(Projectile(match.enemy, 3, 1.65, 6))
        for _ in range(200):
            match.update_projectiles(1 / 60)
        self.assertFalse(match.projectiles)

    def test_already_expired_star_cannot_damage_overlapping_player(self):
        match = self.encounter()
        star = self.incoming(match, 0)
        star.life = 0
        match.update_projectiles(.1)
        self.assertEqual(match.player.health, 100)
        self.assertFalse(match.projectiles)

    def test_star_cannot_travel_beyond_remaining_lifetime(self):
        match = self.encounter()
        star = self.incoming(match, -3)
        star.life = .1
        match.update_projectiles(1)
        self.assertEqual(match.player.health, 100)
        self.assertAlmostEqual(star.x, -2.4)
        self.assertFalse(match.projectiles)

    def test_ninja_training_refills_ammo_after_cooldown_only(self):
        match = self.encounter()
        match.enemy.stars = 0
        match.enemy.star_cooldown = .3
        self.step(match, .2)
        self.assertEqual(match.enemy.stars, 0)
        self.step(match, .2)
        self.assertEqual(match.enemy.stars, 4)
        match.practice = False
        match.brain.wait = 10
        match.enemy.stars = 0
        self.step(match, .2)
        self.assertEqual(match.enemy.stars, 0)

    def test_nunchaku_is_high_and_can_be_ducked(self):
        match = self.encounter()
        match.player.x = 0
        match.enemy.x = 1.7
        match.player.crouch = True
        match.enemy.start_attack('nunchaku')
        match.enemy.elapsed = MOVES['nunchaku'].startup + .01
        match.resolve(match.enemy, match.player)
        self.assertEqual(match.player.health, 100)
        match.player.crouch = False
        match.resolve(match.enemy, match.player)
        self.assertEqual(match.player.health, 81)
        self.assertIn('hit_chop', match.events)
        self.assertNotIn('nunchaku_spin', match.events)

    def test_low_nunchaku_needs_a_low_guard(self):
        standing = self.encounter()
        standing.player.x = 0
        standing.enemy.x = 1.7
        standing.player.guard = True
        standing.player.state = 'guard'
        standing.enemy.start_attack('nunchaku_low')
        standing.enemy.elapsed = MOVES['nunchaku_low'].startup + .01
        standing.resolve(standing.enemy, standing.player)
        self.assertLess(standing.player.health, 100)

        low = self.encounter()
        low.player.x = 0
        low.enemy.x = 1.7
        low.player.guard = True
        low.player.crouch = True
        low.player.state = 'guard'
        low.enemy.start_attack('nunchaku_low')
        low.enemy.elapsed = MOVES['nunchaku_low'].startup + .01
        low.resolve(low.enemy, low.player)
        self.assertEqual(low.player.health, 100)

    def test_nunchaku_sound_starts_with_motion_and_stops_on_interrupt(self):
        match = self.encounter()
        match.enemy.start_attack('nunchaku')
        events = self.step(match, .12)
        self.assertEqual(events.count('nunchaku_spin'), 1)
        self.assertNotIn('hit', events)
        match.player.x = .4
        match.enemy.x = 1.5
        match.player.start_attack('cross')
        match.player.elapsed = MOVES['cross'].startup + .01
        match.resolve(match.player, match.enemy)
        self.assertIn('nunchaku_stop', match.events)

    def test_miss_sound_only_after_missed_active_window(self):
        match = self.encounter('karate')
        match.player.start_attack('round_kick')
        events = self.step(match, .85)
        self.assertEqual(events.count('round_swing'), 1)
        self.assertEqual(events.count('miss'), 1)
        self.assertNotIn('hit', events)
        match = self.encounter('karate')
        match.player.x = 0
        match.enemy.x = 1.4
        match.player.start_attack('round_kick')
        events = self.step(match, .85)
        self.assertEqual(events.count('hit'), 1)
        self.assertEqual(events.count('kiai'), 1)
        self.assertNotIn('miss', events)

    def test_sumo_is_slower_heavier_and_resists_damage(self):
        regular = self.encounter('karate')
        sumo = self.encounter('sumo')
        self.assertLess(sumo.enemy.walk_speed, regular.enemy.walk_speed)
        self.assertGreater(sumo.enemy.body_radius, regular.enemy.body_radius)
        for match in (regular, sumo):
            match.player.x = 0
            match.enemy.x = 1.2
            match.player.start_attack('cross')
            match.player.elapsed = MOVES['cross'].startup + .01
            match.resolve(match.player, match.enemy)
        self.assertGreater(sumo.enemy.health, regular.enemy.health)
        self.assertLess(abs(sumo.enemy.velocity), abs(regular.enemy.velocity))

    def test_sumo_stomp_can_be_jumped(self):
        match = self.encounter('sumo')
        match.player.x = .2
        match.player.state = 'jump'
        match.player.elapsed = .35
        match.enemy.start_attack('sumo_stomp')
        match.enemy.elapsed = MOVES['sumo_stomp'].startup + .01
        match.resolve(match.enemy, match.player)
        self.assertEqual(match.player.health, 100)

    def test_all_new_poses_and_weapon_segments_are_finite(self):
        for kind, moves in [('ninja', ('nunchaku', 'nunchaku_overhead', 'nunchaku_low', 'shuriken')),
                            ('sumo', ('sumo_palm', 'sumo_stomp', 'sumo_charge'))]:
            for key in moves:
                fighter = self.encounter(kind).enemy
                self.assertTrue(fighter.start_attack(key))
                for index in range(101):
                    fighter.elapsed = MOVES[key].duration * index / 100
                    pose = sample(fighter, 0)
                    self.assertEqual(set(pose), set(BASE))
                    self.assertTrue(all(math.isfinite(x) for point in pose.values() for x in point))
                    if kind == 'ninja':
                        points = nunchaku_points(fighter, pose['hand_front'])
                        for a, b, length in zip(points[:-1], points[1:], (.40, .12, .44), strict=True):
                            self.assertAlmostEqual(math.dist(a, b), length)

    def test_roundkick_returns_through_a_bent_chamber(self):
        fighter = self.encounter().player
        fighter.start_attack('round_kick')
        move = fighter.move
        fighter.elapsed = move.startup + move.active + move.recovery * .48
        pose = sample(fighter, 0)
        self.assertLess(math.dist(pose['foot_back'], ROUND_CHAMBER['foot_back']), .01)

    def test_specialist_ai_can_select_its_signature_attacks(self):
        for kind, distance, expected in [('ninja', 3, 'shuriken'), ('ninja', 1.8, 'nunchaku'),
                                         ('sumo', 1.3, 'sumo_palm'), ('sumo', 2.3, 'sumo_charge')]:
            match = self.encounter(kind)
            match.player.x = 0
            match.enemy.x = distance
            brain = Brain(1, 9)
            chosen = set()
            for _ in range(100):
                brain.wait = 0
                chosen.add(brain.update(.01, match.enemy, match.player).attack)
            self.assertIn(expected, chosen)

    def test_ninja_ai_uses_all_three_nunchaku_attacks(self):
        match = self.encounter('ninja')
        match.player.x = 0
        match.enemy.x = 1.7
        brain = Brain(1, 37)
        chosen = set()
        for _ in range(250):
            brain.wait = 0
            attack = brain.update(.01, match.enemy, match.player).attack
            if attack.startswith('nunchaku'):
                chosen.add(attack)
        self.assertEqual(chosen, {'nunchaku', 'nunchaku_overhead', 'nunchaku_low'})

    def test_ninja_throws_stars_only_after_player_stays_passive(self):
        match = self.encounter('ninja')
        match.player.x = 0
        match.enemy.x = 3
        brain = Brain(1, 9)
        brain.random.random = lambda: 0.0
        for _ in range(79):
            brain.wait = 0
            self.assertNotEqual(brain.update(.01, match.enemy, match.player).attack, 'shuriken')
        brain.wait = 0
        self.assertEqual(brain.update(.01, match.enemy, match.player).attack, 'shuriken')

    def test_approaching_player_cancels_ninja_star_setup(self):
        match = self.encounter('ninja')
        match.player.x = 0
        match.enemy.x = 3
        brain = Brain(1, 9)
        brain.random.random = lambda: 0.0
        for _ in range(100):
            match.player.x += .004
            brain.wait = 0
            self.assertNotEqual(brain.update(.01, match.enemy, match.player).attack, 'shuriken')
        self.assertEqual(brain.player_passive_time, 0)

    def test_active_player_cannot_trigger_ninja_star(self):
        match = self.encounter('ninja')
        match.player.x = 0
        match.enemy.x = 3
        match.player.state = 'attack'
        match.player.move_key = 'jab'
        brain = Brain(1, 9)
        brain.random.random = lambda: 0.0
        for _ in range(120):
            brain.wait = 0
            self.assertNotEqual(brain.update(.01, match.enemy, match.player).attack, 'shuriken')

    def test_distant_ninja_can_flourish_without_attacking(self):
        match = self.encounter('ninja')
        match.player.x = 0
        match.enemy.x = 3
        brain = Brain(1, 9)
        brain.random.random = lambda: 0.0
        brain.wait = 0
        command = brain.update(.01, match.enemy, match.player)
        self.assertTrue(command.flourish)
        self.assertFalse(command.attack)
        match.enemy.tick(.01, command)
        self.assertEqual(match.enemy.state, 'flourish')

    def test_flourish_is_harmless_and_stops_its_sound(self):
        match = self.encounter('ninja')
        match.enemy.state = 'flourish'
        match.enemy.elapsed = 1.14
        health = match.player.health
        match.update(.02, Command())
        self.assertEqual(match.player.health, health)
        self.assertEqual(match.enemy.state, 'idle')
        self.assertIn('nunchaku_stop', match.events)


if __name__ == '__main__':
    unittest.main()
