"""Process-local SDL virtual controller for tests; never creates Linux devices.

The virtual device exists only inside the testing process's SDL instance. It
cannot reorder RetroArch's devices, add udev rules, or send input to the desktop.
"""
import ctypes
import ctypes.util

import pygame


class VirtualPad:
    def __init__(self):
        library = ctypes.util.find_library('SDL2-2.0')
        self.sdl = ctypes.CDLL(library)
        self.sdl.SDL_JoystickAttachVirtual.argtypes = [ctypes.c_int] * 4
        self.sdl.SDL_JoystickAttachVirtual.restype = ctypes.c_int
        self.sdl.SDL_JoystickDetachVirtual.argtypes = [ctypes.c_int]
        self.sdl.SDL_JoystickDetachVirtual.restype = ctypes.c_int
        self.sdl.SDL_JoystickOpen.argtypes = [ctypes.c_int]
        self.sdl.SDL_JoystickOpen.restype = ctypes.c_void_p
        self.sdl.SDL_JoystickGetDeviceInstanceID.argtypes = [ctypes.c_int]
        self.sdl.SDL_JoystickGetDeviceInstanceID.restype = ctypes.c_int32
        self.sdl.SDL_JoystickClose.argtypes = [ctypes.c_void_p]
        self.sdl.SDL_JoystickSetVirtualButton.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_uint8]
        self.sdl.SDL_JoystickSetVirtualAxis.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int16]
        self.sdl.SDL_GameControllerAddMapping.argtypes = [ctypes.c_char_p]
        self.sdl.SDL_GameControllerAddMapping.restype = ctypes.c_int
        self.index = self.sdl.SDL_JoystickAttachVirtual(1, 6, 15, 0)
        if self.index < 0:
            raise RuntimeError('SDL could not attach a process-local virtual gamepad')
        self.handle = self.sdl.SDL_JoystickOpen(self.index)
        joy = pygame.joystick.Joystick(self.index)
        self.instance_id = joy.get_instance_id()
        guid = joy.get_guid()
        mapping = (f'{guid},Xbox process-local test controller,'
                   'a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,'
                   'leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,'
                   'dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,'
                   'leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,')
        self.sdl.SDL_GameControllerAddMapping(mapping.encode())
        self.axis(4, -1)
        self.axis(5, -1)
        pygame.event.pump()

    def button(self, index, value):
        result = self.sdl.SDL_JoystickSetVirtualButton(self.handle, index, int(bool(value)))
        if result < 0:
            raise RuntimeError('SDL virtual button failed')
        self.sdl.SDL_JoystickUpdate()

    def axis(self, index, value):
        raw = int(max(-1, min(1, value)) * 32767)
        result = self.sdl.SDL_JoystickSetVirtualAxis(self.handle, index, raw)
        if result < 0:
            raise RuntimeError('SDL virtual axis failed')
        self.sdl.SDL_JoystickUpdate()

    def close(self):
        if self.handle:
            self.sdl.SDL_JoystickClose(self.handle)
            self.handle = None
        if self.index >= 0:
            for index in range(pygame.joystick.get_count()):
                if self.sdl.SDL_JoystickGetDeviceInstanceID(index) == self.instance_id:
                    self.sdl.SDL_JoystickDetachVirtual(index)
                    break
            self.index = -1
        pygame.event.pump()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
