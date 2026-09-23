"""Classic point karate, inspired by the original International Karate rules.

A clean attack earns an ippon, a glancing attack a half point. Two full points
win a bout. Two bouts win the match. The rule implementation is original.
"""
from dataclasses import dataclass

from .model import MOVES, Command, Match, clamp


@dataclass(frozen=True)
class Belt:
    name: str
    color: tuple
    threshold: int
    motto: str


BELTS = (
    Belt('VITT', (.89, .88, .78), 0, 'Början är en del av vägen.'),
    Belt('GULT', (.91, .72, .21), 2500, 'Hitta avståndet före attacken.'),
    Belt('ORANGE', (.88, .40, .14), 6000, 'Låt din timing göra arbetet.'),
    Belt('GRÖNT', (.20, .55, .37), 11000, 'Balans är mer än att stå still.'),
    Belt('BLÅTT', (.16, .37, .65), 18000, 'En öppning räcker.'),
    Belt('BRUNT', (.39, .24, .15), 27000, 'Tålamod är också en teknik.'),
    Belt('SVART', (.06, .07, .09), 40000, 'Fortsätt lära.'),
)


CLASSIC_SCORES = {
    'jab': 800,
    'cross': 800,
    'crouch_punch': 800,
    'front_kick': 200,
    'low_kick': 200,
    'high_kick': 800,
    'round_kick': 1000,
    'sweep': 400,
    'spin_kick': 800,
    'jump_kick': 1000,
}


def belt_for(score):
    result = BELTS[0]
    for belt in BELTS:
        if score >= belt.threshold:
            result = belt
    return result


class ClassicMatch(Match):
    """Point scoring resets the fighters after every valid scoring exchange."""

    def __init__(self, difficulty=1, seed=None):
        super().__init__(difficulty=difficulty, practice=False, seed=seed)
        self.rules = 'classic'
        self.remaining = 30.0
        self.player_points = 0
        self.enemy_points = 0
        self.point_winner = None
        self.point_value = 0
        self.point_message = ''
        self.point_technique = ''
        self.point_timer = 0.0
        self.exchanges = 0
        self.clean_hits = 0
        self.bout_limit = 30.0
        self.distance_at_hit = 0.0

    def points_of(self, fighter):
        return self.player_points if fighter is self.player else self.enemy_points

    def clean_contact(self, attacker, defender):
        """The best reach band gives an ippon; close/range-edge hits give half."""
        move = attacker.move
        distance = abs(attacker.x - defender.x)
        ratio = distance / move.reach
        if move.key in ('jab', 'cross', 'crouch_punch'):
            return .55 <= ratio <= .91
        return .66 <= ratio <= .94

    def resolve(self, attacker, defender):
        if self.phase != 'fight':
            return
        before_hits = attacker.hits
        before_score = attacker.score
        key = attacker.move_key
        full = self.clean_contact(attacker, defender) if attacker.move else False
        distance = abs(attacker.x - defender.x)
        super().resolve(attacker, defender)
        if attacker.hits == before_hits:
            return
        self.distance_at_hit = distance
        self.point_winner = attacker
        self.point_value = 2 if full else 1
        self.point_message = 'IPPON • HEL POÄNG' if full else 'WAZA-ARI • HALV POÄNG'
        self.point_technique = MOVES[key].title
        earned = CLASSIC_SCORES[key] if full else CLASSIC_SCORES[key] // 2
        attacker.score = before_score + earned
        if self.impacts:
            self.impacts[-1].text = f'+{earned}'
        if attacker is self.player:
            self.player_points = min(4, self.player_points + self.point_value)
            if full:
                self.clean_hits += 1
        else:
            self.enemy_points = min(4, self.enemy_points + self.point_value)
        defender.state = 'knockdown'
        defender.elapsed = 0.0
        defender.guard = False
        defender.health = 100
        self.phase = 'point'
        self.point_timer = 1.65
        self.exchanges += 1
        self.emit('point')

    def decide_round(self):
        self.hit_stop = 0.0
        if self.player_points > self.enemy_points:
            self.round_winner = self.player
        elif self.enemy_points > self.player_points:
            self.round_winner = self.enemy
        else:
            self.round_winner = None
        if self.round_winner:
            self.round_winner.wins += 1
            self.round_winner.score += 500
            self.result = self.round_winner.name + ' VINNER RONDEN'
            self.round_winner.state = 'win'
            self.round_winner.elapsed = 0.0
        else:
            self.result = 'OAVGJORT — NY ROND'
        self.phase = 'round_over'
        self.phase_time = 3.2
        self.emit('bell')
        if self.round_winner is not None:
            self.emit('defeat')

    def reset_exchange(self):
        self.player.reset_round(-1.6, 1)
        self.enemy.reset_round(1.6, -1)
        self.phase = 'intro'
        self.phase_time = 1.1
        self.brain.wait = .3
        self.brain.intent = Command()
        self.hit_stop = 0.0
        self.last_technique = 'Två hela poäng vinner ronden.'

    def update(self, dt, command, opponent_command=None):
        if self.phase == 'point':
            self.events.clear()
            self.elapsed += dt
            self.point_timer -= dt
            self.shake = max(0, self.shake - dt)
            for fighter in (self.player, self.enemy):
                fighter.tick(dt, Command())
                fighter.x = clamp(fighter.x, -4.5, 4.5)
            for impact in self.impacts:
                impact.life -= dt
            self.impacts = [impact for impact in self.impacts if impact.life > 0]
            if self.point_timer <= 0:
                if max(self.player_points, self.enemy_points) >= 4 or self.remaining <= 0:
                    self.decide_round()
                else:
                    self.reset_exchange()
            return
        old_phase = self.phase
        old_round = self.round
        super().update(dt, command, opponent_command)
        if self.round != old_round:
            self.player_points = 0
            self.enemy_points = 0
            self.remaining = self.bout_limit
        if self.phase == 'finished' and old_phase != 'finished' and self.winner:
            self.winner.score += 2000


OPPONENTS = (
    ('AKIRA', (.73, .16, .19), 'balanced', 'karate'),
    ('REN', (.22, .39, .62), 'counter', 'karate'),
    ('KAGE', (.10, .14, .23), 'counter', 'ninja'),
    ('YORU', (.19, .10, .22), 'pressure', 'ninja'),
    ('DAICHI', (.27, .34, .26), 'balanced', 'sumo'),
    ('RAIDEN', (.33, .12, .12), 'pressure', 'sumo'),
)

ARCHETYPE_NAMES = {'karate': 'KARATE', 'ninja': 'NINJA', 'sumo': 'SUMO'}
OPPONENT_HINTS = {
    'karate': 'Två poäng vinner ronden. Hitta avståndet för en ren träff.',
    'ninja': 'Huka under höga vapen; hoppa eller blockera lågt vid svepet.',
    'sumo': 'Hoppa över stampen. Backa undan rusningen och kontra.',
}


def opponent_match(archetype, difficulty=1, practice=False, seed=None):
    """The unarmed player faces a readable specialist, with no global settings."""
    match = Match(difficulty, practice, seed)
    match.enemy.set_archetype(archetype)
    if archetype == 'ninja':
        match.enemy.name = 'KAGE'
        match.enemy.color = (.10, .14, .23)
    elif archetype == 'sumo':
        match.enemy.name = 'DAICHI'
        match.enemy.color = (.27, .34, .26)
    match.last_technique = OPPONENT_HINTS[archetype]
    return match


class Tournament:
    """A six-opponent arcade run; finished matches remain independently valid."""

    def __init__(self, difficulty=1):
        self.difficulty = difficulty
        self.stage = 0
        self.total_score = 0
        self.total_hits = 0
        self.total_attacks = 0
        self.total_blocks = 0
        self.best_combo = 0
        self.finished = False
        self.failed = False
        self.previous_belt = BELTS[0]
        self.current_match = None
        self.completed_match = None

    @property
    def opponent(self):
        return OPPONENTS[min(self.stage, len(OPPONENTS) - 1)]

    @property
    def belt(self):
        return belt_for(self.total_score)

    def start_stage(self):
        level = min(2, self.difficulty + self.stage // 3)
        name, color, style, archetype = self.opponent
        match = ClassicMatch(level) if archetype == 'karate' else opponent_match(archetype, level)
        match.enemy.name = name
        match.enemy.color = color
        match.brain.style = style
        match.player.score = self.total_score
        match.player.belt_color = self.belt.color
        match.chapter = ARCHETYPE_NAMES[archetype]
        match.stage_number = self.stage + 1
        self.current_match = match
        return match

    def complete_stage(self):
        match = self.current_match
        if not match or match.phase != 'finished' or match is self.completed_match:
            return False
        self.completed_match = match
        self.previous_belt = self.belt
        self.total_score = match.player.score
        self.total_hits += match.player.hits
        self.total_attacks += match.player.attacks
        self.total_blocks += match.player.blocks
        self.best_combo = max(self.best_combo, match.player.best_combo)
        if match.winner is not match.player:
            self.finished = True
            self.failed = True
        elif self.stage >= len(OPPONENTS) - 1:
            self.finished = True
        else:
            self.stage += 1
        return True
