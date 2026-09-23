"""Guided karate lessons with observable goals and safe reset positions."""
from dataclasses import dataclass

from .model import Match


@dataclass(frozen=True)
class Lesson:
    title: str
    instruction: str
    hint: str
    goal: str
    technique: str = ''
    required: int = 1
    distance: float = 1.4


LESSONS = (
    Lesson('01 • FÖTTERNA FÖRST',
           'Gå åt båda hållen med vänster spak eller styrkorset.',
           'Balans och avstånd är grunden för varje teknik.',
           'movement', required=2, distance=3.2),
    Lesson('02 • DET SNABBA SLAGET',
           'Gå nära och träffa motståndaren med X.',
           'X är snabbt, men har kortare räckvidd än en spark.',
           'hit', 'jab', required=2, distance=1.0),
    Lesson('03 • RAKT SLAG',
           'Träffa med Y för ett gyaku zuki.',
           'Slaget är starkare, men tar längre tid att förbereda.',
           'hit', 'cross', required=2, distance=1.1),
    Lesson('04 • FRONTSPARK',
           'Träffa två gånger med A.',
           'Vänta tills foten är tillbaka innan du sparkar igen.',
           'hit', 'front_kick', required=2, distance=1.4),
    Lesson('05 • KULLERBYTTA',
           'Tryck B tre gånger för att rulla framåt.',
           'Du duckar under höga attacker mitt i rullningen. Låga sparkar träffar.',
           'roll', required=3, distance=3.0),
    Lesson('06 • LEGSWEEP',
           'Håll ner och tryck B eller RB för att svepa undan benen.',
           'Svepet går under ett stående block.',
           'hit', 'sweep', required=3, distance=1.4),
    Lesson('07 • HÖG SPARK',
           'Håll upp och tryck B för en hög spark.',
           'Tryck riktning och spark tillsammans, innan hoppet börjar.',
           'hit', 'high_kick', required=2, distance=1.5),
    Lesson('08 • SKYDDA ÖVERKROPPEN',
           'Håll LB och blockera motståndarens frontsparkar.',
           'Stående block skyddar huvudet och kroppen.',
           'block_high', required=3, distance=1.25),
    Lesson('09 • SKYDDA BENEN',
           'Håll ner + LB och blockera legsweep.',
           'Lågt block skyddar benen. Vanligt block gör det inte.',
           'block_low', required=3, distance=1.3),
    Lesson('10 • HOPPSPARK',
           'Tryck RT och träffa med tobi geri.',
           'En kraftig teknik som kostar mycket uthållighet.',
           'hit', 'jump_kick', required=2, distance=1.5),
    Lesson('11 • ROTERANDE RUNDSPARK',
           'Träffa med RB utan att hålla ner.',
           'Lång räckvidd, men lång förberedelse och återhämtning.',
           'hit', 'spin_kick', required=2, distance=1.65),
    Lesson('12 • UNDAN OCH TILLBAKA',
           'Använd LT tre gånger för att glida bakåt.',
           'Undanmanövern har ett kort fönster där du inte kan träffas.',
           'dodge', required=3, distance=2.0),
)


class Tutorial:
    """Uses the same combat simulation as normal play; no simulated successes."""

    def __init__(self):
        self.index = 0
        self.progress = 0
        self.completed = False
        self.lesson_done = False
        self.success_time = 0.0
        self.elapsed = 0.0
        self.moved_left = False
        self.moved_right = False
        self.last_x = 0.0
        self.left_distance = 0.0
        self.right_distance = 0.0
        self.last_hits = 0
        self.last_contacts = (0, 0)
        self.last_blocks = 0
        self.last_state = ''
        self.attack_wait = 1.2
        self.enemy_attack = ''
        self.reset_time = 0.0
        self.match = Match(difficulty=0, practice=True)
        self.setup_lesson()

    @property
    def lesson(self):
        return LESSONS[self.index]

    @property
    def fraction(self):
        return min(1.0, self.progress / self.lesson.required)

    def setup_lesson(self):
        self.match = Match(difficulty=0, practice=True)
        self.match.phase = 'fight'
        distance = self.lesson.distance
        self.match.player.reset_round(-distance / 2, 1)
        self.match.enemy.reset_round(distance / 2, -1)
        self.match.enemy.name = 'SENSEI'
        self.match.enemy.color = (.27, .38, .46)
        self.progress = 0
        self.lesson_done = False
        self.completed = False
        self.success_time = 0.0
        self.last_hits = 0
        self.last_contacts = (0, 0)
        self.last_blocks = 0
        self.last_state = 'idle'
        self.last_x = self.match.player.x
        self.left_distance = 0
        self.right_distance = 0
        self.moved_left = False
        self.moved_right = False
        self.attack_wait = 1.6
        self.reset_time = 0.0
        self.match.last_technique = self.lesson.hint

    def next_lesson(self):
        if self.index >= len(LESSONS) - 1:
            self.completed = True
            return False
        self.index += 1
        self.setup_lesson()
        return True

    def previous_lesson(self):
        self.index = max(0, self.index - 1)
        self.setup_lesson()

    def skip_lesson(self):
        return self.next_lesson()

    def reset_positions(self):
        distance = self.lesson.distance
        self.match.player.reset_round(-distance / 2, 1)
        self.match.enemy.reset_round(distance / 2, -1)
        self.last_x = self.match.player.x
        self.reset_time = 0.0

    def prepare_opponent(self, dt):
        goal = self.lesson.goal
        if goal not in ('block_high', 'block_low'):
            return
        self.attack_wait -= dt
        if self.attack_wait > 0:
            return
        if not self.match.enemy.can_act:
            return
        self.attack_wait = 1.5
        technique = 'sweep' if goal == 'block_low' else 'front_kick'
        self.match.enemy.stamina = 100
        self.match.enemy.start_attack(technique)
        self.enemy_attack = technique

    def observe_movement(self, fighter):
        delta = fighter.x - self.last_x
        self.last_x = fighter.x
        if delta > 0:
            self.right_distance += delta
        else:
            self.left_distance -= delta
        self.moved_left = self.left_distance >= .6
        self.moved_right = self.right_distance >= .6
        self.progress = int(self.moved_left) + int(self.moved_right)

    def observe_hits(self, fighter):
        gained = fighter.hits - self.last_hits
        if gained > 0 and fighter.move_key == self.lesson.technique:
            self.progress += gained
        self.last_hits = fighter.hits

    def observe_blocks(self, fighter):
        gained = fighter.blocks - self.last_blocks
        if gained > 0:
            self.progress += gained
            self.reset_time = 1.05
        self.last_blocks = fighter.blocks

    def observe_dodge(self, fighter):
        if fighter.state == 'dodge' and self.last_state != 'dodge':
            self.progress += 1
        self.last_state = fighter.state

    def update(self, dt, command):
        self.elapsed += dt
        if self.lesson_done:
            self.success_time += dt
            self.match.events.clear()
            return
        self.prepare_opponent(dt)
        self.match.update(dt, command)
        fighter = self.match.player
        goal = self.lesson.goal
        contacts = (fighter.hits, self.match.enemy.hits)
        if contacts != self.last_contacts and goal in ('hit', 'block_high', 'block_low'):
            # A mistaken technique or defense must still leave a fair retry.
            # Recoil must not strand either participant outside attack range.
            self.reset_time = .95 if goal == 'hit' else 1.05
        self.last_contacts = contacts
        if goal == 'movement':
            self.observe_movement(fighter)
        elif goal == 'hit':
            self.observe_hits(fighter)
        elif goal in ('block_high', 'block_low'):
            self.observe_blocks(fighter)
        elif goal == 'roll':
            if fighter.state == 'roll' and self.last_state != 'roll':
                self.progress += 1
            self.last_state = fighter.state
        elif goal == 'dodge':
            self.observe_dodge(fighter)
        fighter.health = 100
        self.match.enemy.health = 100
        if fighter.stamina < 35:
            fighter.stamina += dt * 35
        if self.reset_time > 0:
            self.reset_time -= dt
            if self.reset_time <= 0:
                self.reset_positions()
        if self.progress >= self.lesson.required:
            self.progress = self.lesson.required
            self.lesson_done = True
            self.success_time = 0.0
            self.match.emit('win')
