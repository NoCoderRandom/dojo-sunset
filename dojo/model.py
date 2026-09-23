"""Deterministic karate rules. This module has no display or input side effects."""
import math
import random
from dataclasses import dataclass
from enum import IntEnum


def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, t):
    return a + (b - a) * t


@dataclass(frozen=True)
class Move:
    key: str
    title: str
    startup: float
    active: float
    recovery: float
    reach: float
    damage: float
    cost: float
    level: str
    push: float
    points: int
    advance: float = 0.0
    airborne: bool = False
    projectile: bool = False

    @property
    def duration(self):
        return self.startup + self.active + self.recovery

    def phase(self, elapsed):
        if elapsed < self.startup:
            return 'startup'
        if elapsed < self.startup + self.active:
            return 'active'
        return 'recovery'


MOVES = {
    'jab': Move('jab', 'KIZAMI ZUKI', .12, .10, .23, 1.18, 9, 9, 'high', .16, 100),
    'crouch_punch': Move('crouch_punch', 'HUKSLAG', .15, .10, .25, 1.12, 11, 11, 'mid', .14, 150),
    'cross': Move('cross', 'GYAKU ZUKI', .21, .12, .28, 1.35, 14, 14, 'mid', .23, 150, .14),
    'front_kick': Move('front_kick', 'MAE GERI', .23, .14, .34, 1.65, 17, 18, 'mid', .32, 200),
    'round_kick': Move('round_kick', 'MAWASHI GERI', .28, .14, .36, 1.76, 20, 22, 'mid', .34, 250),
    'high_kick': Move('high_kick', 'JODAN GERI', .32, .15, .40, 1.82, 22, 24, 'high', .38, 250),
    'low_kick': Move('low_kick', 'GEDAN GERI', .20, .13, .30, 1.48, 12, 14, 'low', .20, 150),
    'sweep': Move('sweep', 'ASHI BARAI', .30, .14, .45, 1.70, 18, 23, 'low', .42, 250),
    'spin_kick': Move('spin_kick', 'ROTERANDE RUNDSPARK', .43, .15, .43, 1.92, 27, 32, 'mid', .50, 350, .20),
    'jump_kick': Move('jump_kick', 'TOBI GERI', .36, .17, .44, 1.80, 24, 29, 'high', .45, 300, .46, True),
    'nunchaku': Move('nunchaku', 'NUNCHAKU • SIDOSLAG', .38, .16, .42, 2.02, 19, 24, 'high', .30, 250),
    'nunchaku_overhead': Move('nunchaku_overhead', 'NUNCHAKU • ÖVERHUVUDSSLAG',
                               .48, .17, .46, 1.94, 22, 28, 'high', .36, 300),
    'nunchaku_low': Move('nunchaku_low', 'NUNCHAKU • LÅG SVEPNING',
                          .35, .17, .43, 1.88, 17, 23, 'low', .27, 250),
    'shuriken': Move('shuriken', 'KASTSTJÄRNA', .48, .04, .49, 6.8, 12, 20, 'high', .12, 150,
                     projectile=True),
    'sumo_palm': Move('sumo_palm', 'SUMO • HANDFLATA', .34, .16, .43, 1.52, 24, 24, 'mid', .55, 250),
    'sumo_stomp': Move('sumo_stomp', 'SUMO • STAMP', .61, .18, .52, 1.48, 20, 29, 'low', .35, 250),
    'sumo_charge': Move('sumo_charge', 'SUMO • RUSNING', .70, .20, .63, 1.48, 27, 34, 'mid', .70, 300, .94),
}


class RollDirection(IntEnum):
    BACKWARD = -1
    NONE = 0
    FORWARD = 1


@dataclass
class Command:
    move: float = 0.0
    crouch: bool = False
    guard: bool = False
    attack: str = ''
    jump: bool = False
    dodge: bool = False
    roll: RollDirection = RollDirection.NONE
    flourish: bool = False


@dataclass
class Fighter:
    name: str
    x: float
    facing: int
    color: tuple
    health: float = 100.0
    stamina: float = 100.0
    state: str = 'idle'
    elapsed: float = 0.0
    move_key: str = ''
    landed: bool = False
    guard: bool = False
    crouch: bool = False
    invulnerable: float = 0.0
    score: int = 0
    wins: int = 0
    combo: int = 0
    last_hit: float = -100.0
    velocity: float = 0.0
    walk_phase: float = 0.0
    hit_flash: float = 0.0
    attacks: int = 0
    hits: int = 0
    blocks: int = 0
    damage_done: float = 0.0
    belt_color: tuple = (.075, .085, .10)
    best_combo: int = 0
    archetype: str = 'karate'
    stars: int = 0
    star_cooldown: float = 0.0
    roll_facing: int = 1
    roll_direction: RollDirection = RollDirection.FORWARD

    @property
    def walk_speed(self):
        return {'karate': 2.0, 'ninja': 2.25, 'sumo': 1.30}[self.archetype]

    @property
    def body_radius(self):
        return {'karate': .325, 'ninja': .30, 'sumo': .50}[self.archetype]

    @property
    def mass(self):
        return 1.7 if self.archetype == 'sumo' else 1.0

    def set_archetype(self, archetype):
        if archetype not in ('karate', 'ninja', 'sumo'):
            raise ValueError('Unknown fighter archetype')
        self.archetype = archetype
        self.stars = 4 if archetype == 'ninja' else 0
        self.star_cooldown = 0

    @property
    def move(self):
        return MOVES.get(self.move_key)

    @property
    def attacking(self):
        return self.state == 'attack'

    @property
    def grounded(self):
        return self.height < .12

    @property
    def can_act(self):
        return self.state in ('idle', 'walk', 'crouch', 'guard')

    @property
    def height(self):
        if self.state == 'jump':
            return math.sin(clamp((self.elapsed - .12) / .58, 0, 1) * math.pi) * .72
        if self.attacking and self.move and self.move.airborne:
            return math.sin(clamp(self.elapsed / self.move.duration, 0, 1) * math.pi) * .60
        return 0.0

    def start_attack(self, key):
        move = MOVES.get(key)
        if not move or not self.can_act or self.stamina < move.cost:
            return False
        if (key.startswith('nunchaku') or key == 'shuriken') and self.archetype != 'ninja':
            return False
        if key.startswith('sumo_') and self.archetype != 'sumo':
            return False
        if key == 'shuriken' and (self.stars <= 0 or self.star_cooldown > 0):
            return False
        self.state = 'attack'
        self.move_key = key
        self.elapsed = 0.0
        self.landed = False
        self.guard = False
        self.crouch = key in ('crouch_punch', 'sweep')
        self.stamina -= move.cost
        self.attacks += 1
        return True

    def reset_round(self, x, facing):
        self.x = x
        self.facing = facing
        self.health = 100.0
        self.stamina = 100.0
        self.state = 'idle'
        self.elapsed = 0.0
        self.move_key = ''
        self.landed = False
        self.guard = False
        self.crouch = False
        self.invulnerable = 0.0
        self.velocity = 0.0
        self.combo = 0
        self.hit_flash = 0.0
        self.stars = 4 if self.archetype == 'ninja' else 0
        self.star_cooldown = 0.0

    def tick(self, dt, command):
        self.elapsed += dt
        self.star_cooldown = max(0.0, self.star_cooldown - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.x += self.velocity * dt
        self.velocity *= math.exp(-9 * dt)
        regen = 13 if self.can_act and not self.guard else 5
        self.stamina = min(100.0, self.stamina + regen * dt)
        if self.state == 'attack':
            move = self.move
            if self.elapsed < move.startup:
                self.x += self.facing * move.advance * dt / move.startup
            if self.elapsed >= move.duration:
                self.state = 'idle'
                self.move_key = ''
                self.elapsed = 0.0
        elif self.state in ('hurt', 'knockdown', 'dodge', 'jump', 'roll', 'flourish'):
            durations = {'hurt': .34, 'knockdown': 1.0, 'dodge': .34, 'jump': .70,
                         'roll': .80, 'flourish': 1.15}
            if self.state == 'roll':
                previous = max(0, self.elapsed - dt)
                travel = max(0, min(self.elapsed, .65) - max(previous, .10))
                self.x += self.roll_facing * 2.7 * travel
                self.crouch = .12 <= self.elapsed < .64
            if self.elapsed >= durations[self.state] and self.health > 0:
                self.state = 'idle'
                self.elapsed = 0.0
        if self.state == 'jump' and self.elapsed < .18 and command.attack == 'high_kick':
            self.state = 'idle'
        if not self.can_act:
            return
        self.crouch = command.crouch
        self.guard = command.guard
        if command.roll and self.stamina >= 26:
            self.state = 'roll'
            self.roll_direction = RollDirection(command.roll)
            self.roll_facing = self.facing * self.roll_direction
            self.elapsed = 0.0
            self.stamina -= 26
            self.guard = False
            self.velocity = 0.0
            return
        if command.attack:
            key = command.attack
            if self.crouch and key in ('jab', 'cross'):
                key = 'crouch_punch'
            elif self.crouch and key == 'front_kick':
                key = 'low_kick'
            elif self.crouch and key in ('high_kick', 'round_kick'):
                key = 'sweep'
            if self.start_attack(key):
                return
        if command.flourish and self.archetype == 'ninja':
            self.state = 'flourish'
            self.elapsed = 0.0
            self.guard = False
            return
        if command.jump and self.stamina >= 12:
            self.state = 'jump'
            self.elapsed = 0.0
            self.stamina -= 12
            return
        if command.dodge and self.stamina >= 18:
            self.state = 'dodge'
            self.elapsed = 0.0
            self.invulnerable = .25
            self.velocity = -self.facing * 4.2
            self.stamina -= 18
            return
        if self.guard:
            self.state = 'guard'
        elif self.crouch:
            self.state = 'crouch'
        elif abs(command.move) > .05:
            self.state = 'walk'
            self.x += command.move * self.walk_speed * dt
            self.walk_phase += dt * abs(command.move) * 16
        else:
            self.state = 'idle'


@dataclass
class Impact:
    x: float
    y: float
    kind: str
    text: str
    life: float = .65
    seed: int = 0


@dataclass
class Projectile:
    owner: Fighter
    x: float
    y: float
    velocity: float
    life: float = 1.25
    rotation: float = 0.0


class Brain:
    """Reactive opponent with a real reaction delay and finite stamina."""

    def __init__(self, difficulty=1, seed=None):
        self.random = random.Random(seed)
        self.difficulty = difficulty
        self.wait = .5
        self.intent = Command()
        self.style = self.random.choice(('counter', 'pressure', 'balanced'))
        self.player_last_x = None
        self.player_passive_time = 0.0
        self.player_approach_grace = 0.0

    def observe_player(self, dt, fighter, player):
        """Track passivity from player motion, independent of the ninja's motion."""
        if self.player_last_x is None:
            approaching = False
        else:
            player_delta = player.x - self.player_last_x
            approaching = player_delta * -fighter.facing > dt * .12
        self.player_last_x = player.x
        if approaching:
            self.player_approach_grace = .55
        else:
            self.player_approach_grace = max(0.0, self.player_approach_grace - dt)
        passive_state = player.state in ('idle', 'crouch', 'guard')
        if passive_state and self.player_approach_grace <= 0:
            self.player_passive_time += dt
        else:
            self.player_passive_time = 0.0

    def update(self, dt, fighter, enemy):
        self.observe_player(dt, fighter, enemy)
        self.wait -= dt
        if self.wait > 0:
            return Command(move=self.intent.move, guard=self.intent.guard,
                           crouch=self.intent.crouch)
        reaction = (.42, .25, .14)[self.difficulty]
        self.wait = reaction + self.random.uniform(.02, .16)
        distance = abs(enemy.x - fighter.x)
        command = Command()
        toward = fighter.facing
        threatening = enemy.attacking and enemy.move.phase(enemy.elapsed) != 'recovery'
        if enemy.state == 'knockdown' and enemy.elapsed < .8:
            command.move = -toward * .4 if distance < 1.2 else 0
        elif fighter.stamina < 24:
            command.move = -toward * .65
            command.guard = distance < 1.7
        elif threatening and distance < 2.0 and self.random.random() < (.35, .62, .83)[self.difficulty]:
            command.guard = True
            command.crouch = enemy.move.level == 'low'
            if self.random.random() < .15:
                command.dodge = True
        elif fighter.archetype == 'sumo':
            if distance > 1.5:
                command.move = toward * .85
                if 1.8 < distance < 2.65 and self.random.random() < .45:
                    command.attack = 'sumo_charge'
            elif self.random.random() < (.50, .70, .85)[self.difficulty]:
                command.attack = 'sumo_palm' if self.random.random() < .65 else 'sumo_stomp'
            else:
                command.guard = True
        elif (fighter.archetype == 'ninja' and 2.25 < distance < 6.0
              and fighter.stars > 0 and fighter.star_cooldown <= 0
              and self.player_passive_time >= (1.05, .80, .60)[self.difficulty]
              and self.random.random() < .55):
            command.attack = 'shuriken'
            self.player_passive_time = 0.0
        elif fighter.archetype == 'ninja' and 1.15 < distance < 2.02 and self.random.random() < .52:
            choices = ['nunchaku', 'nunchaku_overhead']
            if distance < MOVES['nunchaku_low'].reach:
                choices.append('nunchaku_low')
            command.attack = self.random.choice(choices)
        elif fighter.archetype == 'ninja' and distance > 2.5 and self.random.random() < .13:
            command.flourish = True
        elif distance > 1.65:
            command.move = toward * self.random.uniform(.55, 1.0)
            if distance < 2.15 and self.random.random() < .18:
                command.attack = 'jump_kick'
        elif distance < .8:
            command.move = -toward * .7
            if self.random.random() < .45:
                command.attack = 'jab'
        elif self.random.random() < (.48, .70, .85)[self.difficulty]:
            options = ['jab', 'cross', 'front_kick', 'round_kick', 'high_kick', 'low_kick']
            if self.difficulty > 0:
                options += ['spin_kick', 'sweep']
            if enemy.guard:
                options = ['high_kick', 'cross'] if enemy.crouch else ['low_kick', 'sweep']
            if self.difficulty == 2:
                options = [key for key in options
                           if MOVES[key].reach + MOVES[key].advance >= distance]
            command.attack = self.random.choice(options) if options else ''
        elif self.style == 'counter':
            command.guard = True
        else:
            command.move = self.random.choice((-1, 0, 1)) * .4
        self.intent = command
        return command


class Match:
    """Best of three rounds, or an endless safe practice session."""

    def __init__(self, difficulty=1, practice=False, seed=None):
        self.player = Fighter('BRUCE PI', -1.6, 1, (.91, .93, .87))
        self.enemy = Fighter('AKIRA', 1.6, -1, (.73, .16, .19))
        self.brain = Brain(difficulty, seed)
        self.practice = practice
        self.practice_ai = False
        self.two_player = False
        self.phase = 'intro'
        self.phase_time = 2.3
        self.round = 1
        self.remaining = 60.0
        self.elapsed = 0.0
        self.impacts = []
        self.projectiles = []
        self.events = []
        self.result = ''
        self.winner = None
        self.round_winner = None
        self.hit_stop = 0.0
        self.shake = 0.0
        self.last_impact_damage = 0.0
        self.last_impact_move = ''
        self.last_kiai = -10.0
        self.last_technique = 'Håll avstånd. Vänta på din öppning.'
        self.seed = random.Random(seed)

    def emit(self, event):
        self.events.append(event)

    def resolve(self, attacker, defender):
        if not attacker.attacking or attacker.landed:
            return
        move = attacker.move
        if move.projectile:
            return
        if move.phase(attacker.elapsed) != 'active':
            return
        distance = abs(attacker.x - defender.x)
        extra_reach = max(0.0, defender.body_radius - .325)
        if distance > move.reach + extra_reach or defender.invulnerable > 0 or defender.health <= 0:
            return
        if (defender.x - attacker.x) * attacker.facing < 0:
            return
        if defender.state == 'knockdown':
            return
        if move.level == 'low' and not defender.grounded:
            return
        if move.level == 'high' and defender.crouch and defender.grounded:
            return
        attacker.landed = True
        self.contact(attacker, defender, move)

    def contact(self, attacker, defender, move, direction=None):
        """One collision produces one block or hit, shared by melee and stars."""
        direction = attacker.facing if direction is None else direction
        y = {'high': 1.75, 'mid': 1.2, 'low': .42}[move.level]
        guarded = defender.guard and defender.can_act
        guarded = guarded and (defender.crouch == (move.level == 'low'))
        if guarded and defender.stamina >= move.damage * .8:
            defender.stamina -= move.damage * .8
            defender.velocity = direction * move.push * 2 / defender.mass
            defender.blocks += 1
            self.impacts.append(Impact(defender.x, y, 'block', 'BLOCK', seed=self.seed.randrange(9999)))
            self.hit_stop = .035
            self.emit('block')
            return
        damage = move.damage * (.80 if defender.archetype == 'sumo' else 1.0)
        defender.health = max(0.0, defender.health - damage)
        if defender.move_key.startswith('nunchaku') or defender.state == 'flourish':
            self.emit('nunchaku_stop')
        defender.guard = False
        defender.crouch = False
        defender.state = 'knockdown' if move.key in ('sweep', 'sumo_stomp') or defender.health <= 0 else 'hurt'
        defender.elapsed = 0.0
        defender.move_key = ''
        defender.velocity = direction * move.push * 4 / defender.mass
        defender.hit_flash = .18
        defender.invulnerable = .22
        attacker.combo = attacker.combo + 1 if self.elapsed - attacker.last_hit < 1.4 else 1
        attacker.last_hit = self.elapsed
        attacker.best_combo = max(attacker.best_combo, attacker.combo)
        earned = move.points + max(0, attacker.combo - 1) * 50
        attacker.score += earned
        attacker.hits += 1
        attacker.damage_done += damage
        self.last_technique = move.title
        self.impacts.append(Impact(defender.x, y, 'hit', f'+{earned}', seed=self.seed.randrange(9999)))
        self.hit_stop = .055
        self.shake = .12
        self.last_impact_damage = damage
        self.last_impact_move = move.key
        self.emit('hit')
        if move.key.startswith('nunchaku') or move.key == 'sumo_palm':
            self.emit('hit_chop')
        else:
            self.emit('hit_heavy' if damage >= 18 else 'hit_light')
        if (attacker is self.player and move.key in ('round_kick', 'high_kick', 'jump_kick', 'spin_kick')
                and self.elapsed - self.last_kiai >= 2.5):
            self.last_kiai = self.elapsed
            self.emit('kiai')
        if self.practice and defender.health <= 0:
            defender.health = 100
            defender.stamina = 100

    def update_projectiles(self, dt):
        remaining = []
        for star in self.projectiles:
            if star.life <= 0:
                continue
            previous_x = star.x
            star.x += star.velocity * min(dt, max(0, star.life))
            star.life -= dt
            star.rotation += dt * 1200
            defender = self.enemy if star.owner is self.player else self.player
            near = min(previous_x, star.x) - defender.body_radius - .08 <= defender.x
            near = near and defender.x <= max(previous_x, star.x) + defender.body_radius + .08
            top = (1.48 if defender.crouch and defender.grounded else 2.18) + defender.height
            bottom = .15 + defender.height
            vulnerable = (defender.health > 0 and defender.invulnerable <= 0
                          and defender.state != 'knockdown')
            if near and vulnerable and bottom < star.y < top:
                self.contact(star.owner, defender, MOVES['shuriken'], 1 if star.velocity > 0 else -1)
                continue
            if star.life > 0 and abs(star.x) < 6.5:
                remaining.append(star)
        self.projectiles = remaining

    def decide_round(self):
        self.projectiles.clear()
        a, b = self.player, self.enemy
        if a.health > b.health:
            self.round_winner = a
        elif b.health > a.health:
            self.round_winner = b
        else:
            self.round_winner = None
        if self.round_winner:
            self.round_winner.wins += 1
            self.round_winner.score += 500 + int(self.remaining) * 5
            self.result = self.round_winner.name + ' VINNER RONDEN'
            if self.round_winner.health > 0:
                self.round_winner.state = 'win'
                self.round_winner.elapsed = 0
        else:
            self.result = 'OAVGJORT — NY ROND'
        self.phase = 'round_over'
        self.phase_time = 3.2
        self.emit('bell')
        if self.round_winner is not None:
            self.emit('defeat')

    def update(self, dt, command, opponent_command=None):
        self.events.clear()
        self.elapsed += dt
        self.shake = max(0.0, self.shake - dt)
        for impact in self.impacts:
            impact.life -= dt
        self.impacts = [impact for impact in self.impacts if impact.life > 0]
        if self.hit_stop > 0:
            self.hit_stop -= dt
            return
        if self.phase == 'intro':
            self.phase_time -= dt
            if self.phase_time <= 0:
                self.phase = 'fight'
                self.emit('bell')
            return
        if self.phase == 'round_over':
            for fighter in (self.player, self.enemy):
                fighter.elapsed += dt
            self.phase_time -= dt
            if self.phase_time <= 0:
                if max(self.player.wins, self.enemy.wins) >= 2:
                    self.winner = self.player if self.player.wins >= 2 else self.enemy
                    self.phase = 'finished'
                else:
                    self.round += 1
                    self.player.reset_round(-1.6, 1)
                    self.enemy.reset_round(1.6, -1)
                    self.remaining = 60
                    self.phase = 'intro'
                    self.phase_time = 2.3
            return
        if self.phase != 'fight':
            return
        if not self.practice:
            self.remaining = max(0.0, self.remaining - dt)
        self.player.facing = 1 if self.enemy.x >= self.player.x else -1
        self.enemy.facing = -self.player.facing
        enemy_command = Command()
        if self.two_player:
            enemy_command = opponent_command if opponent_command is not None else Command()
        elif not self.practice or self.practice_ai:
            enemy_command = self.brain.update(dt, self.enemy, self.player)
        old_states = (self.player.state, self.enemy.state)
        old_elapsed = (self.player.elapsed, self.enemy.elapsed)
        self.player.tick(dt, command)
        self.enemy.tick(dt, enemy_command)
        # Endless ninja training must continue teaching projectile defense.
        # Real matches still have exactly four stars per round.
        if (self.practice and self.enemy.archetype == 'ninja'
                and self.enemy.stars == 0 and self.enemy.star_cooldown <= 0
                and not self.projectiles):
            self.enemy.stars = 4
        for fighter, old, previous_time in zip((self.player, self.enemy), old_states, old_elapsed, strict=True):
            if fighter.attacking and old == 'attack':
                swing_start = fighter.move.startup * .55
                if fighter.move_key.startswith('nunchaku'):
                    swing_start = .06
                if previous_time < swing_start <= fighter.elapsed:
                    if fighter.move_key.startswith('nunchaku'):
                        self.emit('nunchaku_spin')
                    elif 'kick' in fighter.move_key or fighter.move_key == 'sweep':
                        self.emit('round_swing')
                    elif not fighter.move.projectile:
                        self.emit('swing')
                if fighter.move.projectile and not fighter.landed and fighter.elapsed >= fighter.move.startup:
                    fighter.landed = True
                    fighter.stars -= 1
                    fighter.star_cooldown = 2.4
                    self.projectiles.append(Projectile(fighter, fighter.x + fighter.facing * .65,
                                                       1.65, fighter.facing * 6.0,
                                                       life=(fighter.move.reach - .65) / 6.0))
                    self.emit('star_throw')
                active_end = fighter.move.startup + fighter.move.active
                if (previous_time < active_end <= fighter.elapsed and not fighter.landed
                        and not fighter.move.projectile):
                    self.emit('miss')
            if fighter.state == 'flourish' and old != 'flourish':
                self.emit('nunchaku_spin')
            elif old == 'flourish' and fighter.state != 'flourish':
                self.emit('nunchaku_stop')
            fighter.x = clamp(fighter.x, -4.5, 4.5)
        gap = self.enemy.x - self.player.x
        min_gap = self.player.body_radius + self.enemy.body_radius
        if abs(gap) < min_gap:
            correction = (min_gap - abs(gap)) * .5
            sign = 1 if gap >= 0 else -1
            self.player.x = clamp(self.player.x - correction * sign, -4.5, 4.5)
            self.enemy.x = clamp(self.enemy.x + correction * sign, -4.5, 4.5)
        self.resolve(self.player, self.enemy)
        self.resolve(self.enemy, self.player)
        self.update_projectiles(dt)
        if self.practice:
            self.player.health = max(self.player.health, 35)
        elif min(self.player.health, self.enemy.health) <= 0 or self.remaining <= 0:
            self.decide_round()
