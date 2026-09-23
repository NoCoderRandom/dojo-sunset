"""Process-local controller input, with stable player slots and hotplugging."""
from contextlib import suppress

import pygame
from pygame._sdl2 import controller

from .elite_input import ElitePad, find_elite
from .model import Command

BUTTONS = {
    'a': pygame.CONTROLLER_BUTTON_A,
    'b': pygame.CONTROLLER_BUTTON_B,
    'x': pygame.CONTROLLER_BUTTON_X,
    'y': pygame.CONTROLLER_BUTTON_Y,
    'lb': pygame.CONTROLLER_BUTTON_LEFTSHOULDER,
    'rb': pygame.CONTROLLER_BUTTON_RIGHTSHOULDER,
    'back': pygame.CONTROLLER_BUTTON_BACK,
    'start': pygame.CONTROLLER_BUTTON_START,
    'up': pygame.CONTROLLER_BUTTON_DPAD_UP,
    'down': pygame.CONTROLLER_BUTTON_DPAD_DOWN,
    'left': pygame.CONTROLLER_BUTTON_DPAD_LEFT,
    'right': pygame.CONTROLLER_BUTTON_DPAD_RIGHT,
}


def controller_kind(index, joystick=None):
    """Return the controller family used by Dojo Sunset, without modifying it."""
    joy = joystick or pygame.joystick.Joystick(index)
    name = joy.get_name()
    if 'speedlink' in name.lower() and joy.get_numbuttons() >= 4:
        return 'speedlink'
    if controller.is_controller(index):
        mapped_name = controller.name_forindex(index) or ''
        if 'xbox' in (name + ' ' + mapped_name).lower():
            return 'xbox'
    return None


class SpeedlinkPad:
    """Expose a four-button Competition Pro without changing system mappings.

    The controller's DragonRise USB interface advertises many controls that do
    not physically exist.  Reading the joystick directly keeps its real four
    buttons available instead of trusting that misleading SDL gamepad map.
    """

    BUTTON_MAP = {
        pygame.CONTROLLER_BUTTON_X: 0,  # SPEEDLINK button 1 / X
        pygame.CONTROLLER_BUTTON_A: 1,  # SPEEDLINK button 2 / A
        pygame.CONTROLLER_BUTTON_Y: 2,  # SPEEDLINK button 3 / Y
        pygame.CONTROLLER_BUTTON_B: 3,  # SPEEDLINK button 4 / B
    }

    def __init__(self, index):
        self.joystick = pygame.joystick.Joystick(index)

    def attached(self):
        return self.joystick.get_init()

    def get_button(self, button):
        raw_button = self.BUTTON_MAP.get(button)
        if raw_button is not None:
            return self.joystick.get_button(raw_button)
        # There is no Start button.  All four fire buttons is a deliberate,
        # hard-to-trigger pause gesture that does not affect system settings.
        if button == pygame.CONTROLLER_BUTTON_START:
            return all(self.joystick.get_button(index) for index in range(4))
        return False

    def get_axis(self, axis):
        if axis == pygame.CONTROLLER_AXIS_LEFTX:
            return int(self.joystick.get_axis(0) * 32767)
        if axis == pygame.CONTROLLER_AXIS_LEFTY:
            return int(self.joystick.get_axis(1) * 32767)
        return 0

    def rumble(self, low_frequency, high_frequency, duration):
        return False

    def stop_rumble(self):
        pass

    def quit(self):
        self.joystick.quit()



class Controls:
    def __init__(self, settings, preferred_instance=None, excluded_instances=None,
                 preferred_kind='auto'):
        pygame.joystick.init()
        controller.init()
        self.settings = settings
        self.preferred_instance = preferred_instance
        self.preferred_kind = preferred_kind
        self.excluded_instances = excluded_instances or (lambda: set())
        self.secondary = None
        self.scan_wait = 0.0
        self.pad = None
        self.joystick = None
        self.name = 'Spelkontroll saknas'
        self.held = set()
        self.previous = set()
        self.pressed = set()
        self.digital_x = 0
        self.digital_direction_active = False
        self.axis_x = 0.0
        self.axis_y = 0.0
        self.left_trigger = 0.0
        self.right_trigger = 0.0
        self.disconnect = False
        self.quit_requested = False
        self.fullscreen_requested = False
        self.screenshot_requested = False
        self.focus_lost = False
        self.has_focus = True
        self.menu_wait = 0.0
        self.menu_direction = 0
        self.menu_blocked_until_release = False
        self.instance = None
        self.scan()

    def scan(self):
        # Keep player slots stable when another controller is plugged in.
        if self.pad and self.pad.attached() and (
                self.preferred_instance is None or self.preferred_instance == self.instance):
            return
        candidates = []
        sdl_has_elite = False
        for index in range(pygame.joystick.get_count()):
            try:
                joy = pygame.joystick.Joystick(index)
                guid = joy.get_guid()
                if guid[8:12] == '5e04' and guid[16:20] == '220b':
                    sdl_has_elite = True
                if joy.get_instance_id() in self.excluded_instances():
                    continue
                if self.preferred_instance is not None and joy.get_instance_id() != self.preferred_instance:
                    continue
                kind = controller_kind(index, joy)
                if kind == 'speedlink' and self.preferred_kind in ('auto', 'speedlink'):
                    candidates.append((1, index, 'speedlink'))
                elif kind == 'xbox' and self.preferred_kind in ('auto', 'xbox'):
                    candidates.append((0, index, 'xbox'))
            except pygame.error:
                continue
        if not candidates:
            if (not sdl_has_elite and self.preferred_instance is None
                    and self.preferred_kind in ('auto', 'xbox')):
                fallback = find_elite(self.excluded_instances())
                if fallback:
                    self.close_pad()
                    self.pad = fallback
                    self.instance = fallback.instance
                    self.name = fallback.name
            return
        candidates.sort()
        try:
            _, index, pad_type = candidates[0]
            candidate = pygame.joystick.Joystick(index)
            if candidate.get_instance_id() == self.instance:
                return
            self.close_pad()
            if pad_type == 'speedlink':
                self.pad = SpeedlinkPad(index)
                self.joystick = self.pad.joystick
            else:
                self.pad = controller.Controller(index)
                self.joystick = self.pad.as_joystick()
            self.instance = self.joystick.get_instance_id()
            self.name = self.joystick.get_name()
        except (pygame.error, OSError):
            self.pad = None
            self.joystick = None
            self.name = 'Spelkontroll saknas'

    def close_pad(self):
        if self.pad:
            try:
                self.pad.stop_rumble()
                self.pad.quit()
            except pygame.error:
                pass
        self.pad = None
        self.joystick = None
        self.instance = None
        self.name = 'Spelkontroll saknas'

    def axis(self, axis_id):
        if not self.pad:
            return 0.0
        return max(-1.0, min(1.0, self.pad.get_axis(axis_id) / 32767.0))

    def deadzone(self, value):
        zone = self.settings['deadzone']
        if abs(value) <= zone:
            return 0.0
        magnitude = (abs(value) - zone) / (1.0 - zone)
        return magnitude if value > 0 else -magnitude

    def poll(self, dt, events=None):
        self.disconnect = False
        self.quit_requested = False
        self.fullscreen_requested = False
        self.screenshot_requested = False
        self.focus_lost = False
        self.scan_wait -= dt
        if not self.pad and self.scan_wait <= 0:
            self.scan_wait = 1.0
            self.scan()
        event_presses = set()
        for event in pygame.event.get() if events is None else events:
            if event.type == pygame.QUIT:
                self.quit_requested = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.fullscreen_requested = True
                if event.key == pygame.K_F10:
                    self.screenshot_requested = True
            elif event.type == pygame.CONTROLLERBUTTONDOWN:
                if getattr(event, 'instance_id', None) == self.instance:
                    for name, button in BUTTONS.items():
                        if event.button == button:
                            event_presses.add(name)
            elif event.type == pygame.JOYDEVICEADDED:
                self.scan()
            elif event.type == pygame.JOYDEVICEREMOVED:
                if event.instance_id == self.instance:
                    self.close_pad()
                    self.disconnect = True
                    self.scan()
            elif event.type == pygame.WINDOWFOCUSLOST:
                self.focus_lost = True
                self.has_focus = False
            elif event.type == pygame.WINDOWFOCUSGAINED:
                self.has_focus = True
        self.previous = self.held
        self.held = set()
        self.axis_x = 0.0
        self.axis_y = 0.0
        self.left_trigger = 0.0
        self.right_trigger = 0.0
        if self.pad:
            try:
                if isinstance(self.pad, ElitePad):
                    raw_presses = self.pad.poll()
                    event_presses.update(name for name, button in BUTTONS.items() if button in raw_presses)
                for name, button in BUTTONS.items():
                    if self.pad.get_button(button):
                        self.held.add(name)
                self.axis_x = self.deadzone(self.axis(pygame.CONTROLLER_AXIS_LEFTX))
                self.axis_y = self.deadzone(self.axis(pygame.CONTROLLER_AXIS_LEFTY))
                self.left_trigger = self.axis(pygame.CONTROLLER_AXIS_TRIGGERLEFT)
                self.right_trigger = self.axis(pygame.CONTROLLER_AXIS_TRIGGERRIGHT)
            except (pygame.error, OSError):
                self.close_pad()
                self.disconnect = True
        self.digital_x = int('right' in self.held) - int('left' in self.held)
        self.digital_direction_active = 'left' in self.held or 'right' in self.held
        if self.axis_x > .55:
            self.held.add('right')
        elif self.axis_x < -.55:
            self.held.add('left')
        if self.axis_y > .55:
            self.held.add('down')
        elif self.axis_y < -.55:
            self.held.add('up')
        if self.left_trigger > .5:
            self.held.add('dodge')
        if self.right_trigger > .5:
            self.held.add('power')
        self.pressed = (self.held - self.previous) | event_presses
        self.menu_wait = max(0.0, self.menu_wait - dt)

    def hit(self, name):
        return name in self.pressed

    def down(self, name):
        return name in self.held

    def accept(self):
        return self.hit('a') or self.hit('confirm')

    def cancel(self):
        return self.hit('b') or self.hit('start')

    def reset_menu_navigation(self):
        self.menu_direction = 0
        self.menu_wait = 0.0
        self.menu_blocked_until_release = self.down('up') or self.down('down')

    def menu_step(self):
        direction = int(self.down('down')) - int(self.down('up'))
        if self.menu_blocked_until_release:
            if not direction:
                self.menu_blocked_until_release = False
            return 0
        if not direction:
            self.menu_direction = 0
            return 0
        if direction != self.menu_direction:
            self.menu_direction = direction
            self.menu_wait = .35
            return direction
        if self.menu_wait <= 0:
            self.menu_wait = .14
            return direction
        return 0

    def command(self):
        result = Command()
        result.move = self.digital_x if self.digital_direction_active else self.axis_x
        result.crouch = self.down('down')
        result.guard = self.down('lb')
        result.dodge = self.hit('dodge')
        result.jump = self.hit('up') or self.hit('jump')
        if self.hit('x'):
            result.attack = 'jab'
        elif self.hit('y'):
            result.attack = 'cross'
        elif self.hit('a'):
            result.attack = 'jump_kick' if self.down('up') else 'front_kick'
        elif self.hit('b'):
            if self.down('up'):
                result.attack = 'high_kick'
            elif result.crouch:
                result.attack = 'sweep'
            else:
                result.roll = True
        elif self.hit('rb'):
            result.attack = 'sweep' if result.crouch else 'spin_kick'
        elif self.hit('power'):
            result.attack = 'jump_kick'
        return result

    def rumble(self, strength=.35, duration=90):
        if not self.pad or not self.settings['rumble']:
            return
        with suppress(pygame.error):
            self.pad.rumble(strength, strength * .6, duration)

    def diagnostics(self):
        return {
            'name': self.name,
            'connected': bool(self.pad),
            'instance': self.instance,
            'left_x': round(self.axis_x, 2),
            'left_y': round(self.axis_y, 2),
            'lt': round(self.left_trigger, 2),
            'rt': round(self.right_trigger, 2),
            'buttons': sorted(self.held),
        }

    def close(self):
        if self.secondary:
            self.secondary.close_pad()
            self.secondary.excluded_instances = lambda: set()
            self.secondary = None
        self.excluded_instances = lambda: set()
        self.close_pad()
        controller.quit()
