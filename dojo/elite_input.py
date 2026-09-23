"""Read-only fallback for Bluetooth Elite 2 devices missing from SDL.

Some Elite firmware advertises a keyboard, losing the udev joystick tag.
Open only Microsoft 045e:0b22 Bluetooth input nodes. No grabs, writes, uinput,
udev changes, pairing changes or system mappings are used.
"""
import fcntl
import os
import struct
from pathlib import Path

import pygame

EVENT = struct.Struct('@llHHi')
KEY_BUTTONS = {
    304: pygame.CONTROLLER_BUTTON_A, 305: pygame.CONTROLLER_BUTTON_B,
    307: pygame.CONTROLLER_BUTTON_X, 308: pygame.CONTROLLER_BUTTON_Y,
    310: pygame.CONTROLLER_BUTTON_LEFTSHOULDER,
    311: pygame.CONTROLLER_BUTTON_RIGHTSHOULDER,
    314: pygame.CONTROLLER_BUTTON_BACK, 315: pygame.CONTROLLER_BUTTON_START,
}
AXES = {pygame.CONTROLLER_AXIS_LEFTX: 0, pygame.CONTROLLER_AXIS_LEFTY: 1,
        pygame.CONTROLLER_AXIS_TRIGGERLEFT: 10, pygame.CONTROLLER_AXIS_TRIGGERRIGHT: 9}
HATS = {pygame.CONTROLLER_BUTTON_DPAD_LEFT: (16, -1),
        pygame.CONTROLLER_BUTTON_DPAD_RIGHT: (16, 1),
        pygame.CONTROLLER_BUTTON_DPAD_UP: (17, -1),
        pygame.CONTROLLER_BUTTON_DPAD_DOWN: (17, 1)}


def read_ioctl(fd, number, size):
    data = bytearray(size)
    fcntl.ioctl(fd, 0x80000000 | (size << 16) | (ord('E') << 8) | number, data)
    return data


class ElitePad:
    name = 'Xbox Elite Series 2 (Bluetooth)'

    def __init__(self, path, instance):
        self.path = path
        self.instance = instance
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            # Recheck identity after opening in case input nodes were reused.
            bus, vendor, product, _ = struct.unpack('HHHH', read_ioctl(self.fd, 2, 8))
            if (bus, vendor, product) != (5, 0x045e, 0x0b22):
                raise OSError('Not a Bluetooth Xbox Elite 2')
            self.identity = (path.stat().st_ino, path.stat().st_rdev)
            self.refresh()
        except Exception:
            self.quit()
            raise

    def refresh(self):
        self.keys = read_ioctl(self.fd, 0x18, 96)
        self.axes = {code: struct.unpack('iiiiii', read_ioctl(self.fd, 0x40 + code, 24))
                     for code in (0, 1, 9, 10, 16, 17)}

    def poll(self):
        pressed = set()
        dropped = False
        while True:
            try:
                data = os.read(self.fd, EVENT.size * 64)
            except BlockingIOError:
                break
            if not data:
                raise OSError('Elite disconnected')
            for _, _, kind, code, value in EVENT.iter_unpack(data):
                if kind == 0 and code == 3:  # SYN_DROPPED: rely on fresh snapshots.
                    dropped = True
                elif kind == 1 and value == 1 and code in KEY_BUTTONS:
                    pressed.add(KEY_BUTTONS[code])
                elif kind == 3:
                    pressed.update(button for button, pair in HATS.items() if pair == (code, value))
        self.refresh()
        return set() if dropped else pressed

    def attached(self):
        try:
            stat = self.path.stat()
            return self.fd is not None and self.identity == (stat.st_ino, stat.st_rdev)
        except OSError:
            return False

    def get_button(self, button):
        if button in HATS:
            code, value = HATS[button]
            return self.axes[code][0] == value
        return any(self.keys[code // 8] & (1 << (code % 8))
                   for code, mapped in KEY_BUTTONS.items() if mapped == button)

    def get_axis(self, axis):
        if axis not in AXES:
            return 0
        value, low, high, *_ = self.axes[AXES[axis]]
        fraction = max(0.0, min(1.0, (value - low) / max(1, high - low)))
        if axis in (pygame.CONTROLLER_AXIS_TRIGGERLEFT, pygame.CONTROLLER_AXIS_TRIGGERRIGHT):
            return round(fraction * 32767)
        return round((fraction * 2 - 1) * 32767)

    def rumble(self, *args):
        pass  # Read-only fallback: no force-feedback writes.

    def stop_rumble(self):
        pass

    def quit(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def find_elite(excluded):
    for node in sorted(Path('/sys/class/input').glob('event*')):
        try:
            ids = node / 'device' / 'id'
            identity = tuple(int((ids / key).read_text().strip(), 16)
                             for key in ('bustype', 'vendor', 'product'))
            if identity != (5, 0x045e, 0x0b22):
                continue
            instance = 'elite:' + str(node.resolve())
            if instance not in excluded:
                return ElitePad(Path('/dev/input') / node.name, instance)
        except (OSError, ValueError):
            continue
    return None
