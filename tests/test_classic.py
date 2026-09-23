"""Point-karate scoring and arcade progression regression tests."""
import unittest

from dojo.competition import BELTS, ClassicMatch, Tournament, belt_for
from dojo.model import MOVES, Brain, Command


class ClassicTests(unittest.TestCase):
    def hit(self, key='round_kick', ratio=.8):
        match = ClassicMatch(seed=2)
        match.phase = 'fight'
        match.player.x = 0
        match.enemy.x = MOVES[key].reach * ratio
        match.player.start_attack(key)
        match.player.elapsed = MOVES[key].startup + .02
        match.resolve(match.player, match.enemy)
        return match

    def test_clean_roundhouse_scores_ippon(self):
        match = self.hit()
        self.assertEqual(match.player_points, 2)
        self.assertEqual(match.player.score, 1000)
        self.assertEqual(match.phase, 'point')
        self.assertEqual(match.enemy.state, 'knockdown')

    def test_glancing_roundhouse_scores_half(self):
        match = self.hit(ratio=.98)
        self.assertEqual(match.player_points, 1)
        self.assertEqual(match.player.score, 500)

    def test_legsweep_scores_and_falls(self):
        match = self.hit('sweep')
        self.assertEqual(match.player_points, 2)
        self.assertEqual(match.player.score, 400)
        self.assertEqual(match.enemy.state, 'knockdown')

    def test_scoring_recoil_stays_inside_both_arena_edges(self):
        for facing in (-1, 1):
            with self.subTest(facing=facing):
                match = ClassicMatch(seed=2)
                match.phase = 'fight'
                match.player.x = 3 * facing
                match.player.facing = facing
                match.enemy.x = 4.4 * facing
                match.enemy.facing = -facing
                match.player.start_attack('round_kick')
                match.player.elapsed = MOVES['round_kick'].startup + .01
                match.resolve(match.player, match.enemy)
                self.assertEqual(match.phase, 'point')
                for _ in range(150):
                    match.update(1 / 120, Command())
                    self.assertLessEqual(abs(match.enemy.x), 4.5)
                    self.assertLessEqual(abs(match.player.x), 4.5)

    def test_point_pause_freezes_clock(self):
        match = self.hit()
        remaining = match.remaining
        for _ in range(100):
            match.update(.01, Command())
        self.assertEqual(match.remaining, remaining)

    def test_no_second_hit_during_judgement(self):
        match = self.hit()
        points = match.player_points
        match.player.landed = False
        match.enemy.invulnerable = 0
        match.resolve(match.player, match.enemy)
        self.assertEqual(match.player_points, points)

    def test_exchange_restarts_at_safe_distance(self):
        match = self.hit()
        for _ in range(170):
            match.update(.01, Command())
        self.assertEqual(match.phase, 'intro')
        self.assertEqual(match.player.x, -1.6)
        self.assertEqual(match.enemy.x, 1.6)
        self.assertEqual(match.player_points, 2)

    def test_two_ippons_win_bout(self):
        match = self.hit()
        match.player_points = 4
        for _ in range(170):
            match.update(.01, Command())
        self.assertEqual(match.phase, 'round_over')
        self.assertEqual(match.player.wins, 1)

    def test_new_bout_clears_points(self):
        match = self.hit()
        match.player_points = 4
        match.decide_round()
        match.update(3.3, Command())
        self.assertEqual(match.round, 2)
        self.assertEqual(match.player_points, 0)
        self.assertEqual(match.enemy_points, 0)
        self.assertEqual(match.remaining, 30)

    def test_time_decision_uses_points_not_health(self):
        match = ClassicMatch(seed=2)
        match.player_points = 1
        match.enemy_points = 2
        match.player.health = 100
        match.enemy.health = 40
        match.decide_round()
        self.assertIs(match.round_winner, match.enemy)

    def test_match_bonus_given_only_once(self):
        match = ClassicMatch(seed=2)
        match.player.wins = 1
        match.player_points = 4
        match.decide_round()
        match.update(3.3, Command())
        score = match.player.score
        match.update(.1, Command())
        self.assertEqual(match.player.score, score)
        self.assertEqual(match.phase, 'finished')
        self.assertEqual(score, 2500)

    def test_seeded_classic_matches_finish(self):
        for seed in range(30):
            match = ClassicMatch(seed % 3, seed=seed)
            brain = Brain((seed + 1) % 3, seed + 200)
            for _step in range(120 * 300):
                command = brain.update(1 / 120, match.player, match.enemy)
                match.update(1 / 120, command)
                self.assertLessEqual(match.player_points, 4)
                self.assertLessEqual(match.enemy_points, 4)
                if match.phase == 'finished':
                    break
            self.assertEqual(match.phase, 'finished', seed)

    def test_belt_thresholds(self):
        self.assertEqual(belt_for(0), BELTS[0])
        for belt in BELTS:
            self.assertEqual(belt_for(belt.threshold), belt)
        self.assertEqual(belt_for(999999), BELTS[-1])

    def test_tournament_advances_and_keeps_score(self):
        tournament = Tournament()
        match = tournament.start_stage()
        match.phase = 'finished'
        match.winner = match.player
        match.player.score = 3500
        self.assertTrue(tournament.complete_stage())
        self.assertEqual(tournament.stage, 1)
        next_match = tournament.start_stage()
        self.assertEqual(next_match.player.score, 3500)
        self.assertEqual(next_match.enemy.name, 'REN')

    def test_stage_completion_is_idempotent(self):
        tournament = Tournament()
        match = tournament.start_stage()
        match.phase = 'finished'
        match.winner = match.player
        self.assertTrue(tournament.complete_stage())
        self.assertFalse(tournament.complete_stage())
        self.assertEqual(tournament.stage, 1)

    def test_tournament_loss_ends_run(self):
        tournament = Tournament()
        match = tournament.start_stage()
        match.phase = 'finished'
        match.winner = match.enemy
        tournament.complete_stage()
        self.assertTrue(tournament.finished)
        self.assertTrue(tournament.failed)

    def test_six_tournament_wins_complete_run(self):
        tournament = Tournament()
        for _stage in range(6):
            match = tournament.start_stage()
            match.phase = 'finished'
            match.winner = match.player
            match.player.score += 3000
            tournament.complete_stage()
        self.assertTrue(tournament.finished)
        self.assertFalse(tournament.failed)
        self.assertEqual(tournament.total_score, 18000)


if __name__ == '__main__':
    unittest.main()
