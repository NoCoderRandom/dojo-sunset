"""A short action buffer makes near-recovery button presses responsive."""
from .model import Command


class InputBuffer:
    def __init__(self, window=.12):
        self.window = window
        self.clear()

    def clear(self):
        self.attack = ''
        self.attack_crouch = False
        self.jump = False
        self.dodge = False
        self.roll = False
        self.expiry = -1.0

    def offer(self, command, now):
        if command.attack:
            self.clear()
            self.attack = command.attack
            self.attack_crouch = command.crouch
            self.expiry = now + self.window
        elif command.roll:
            self.clear()
            self.roll = True
            self.expiry = now + self.window
        elif command.dodge:
            self.clear()
            self.dodge = True
            self.expiry = now + self.window
        elif command.jump:
            self.clear()
            self.jump = True
            self.expiry = now + self.window

    def take(self, fighter, held, now):
        result = Command(move=held.move, crouch=held.crouch, guard=held.guard)
        if now > self.expiry:
            self.clear()
            return result
        early_high_kick = (fighter.state == 'jump' and fighter.elapsed < .18
                           and self.attack == 'high_kick')
        if not fighter.can_act and not early_high_kick:
            return result
        result.attack = self.attack
        result.jump = self.jump
        result.dodge = self.dodge
        result.roll = self.roll
        if self.attack:
            result.crouch = self.attack_crouch
        self.clear()
        return result
