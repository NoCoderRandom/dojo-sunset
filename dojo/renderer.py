"""GPU renderer for articulated fighters, scenery and a composited HUD."""
import math
import random
from dataclasses import replace

import numpy as np
import pygame
from OpenGL.GL import *
from pygame._sdl2.video import Window

from .animation import sample
from .geometry import Meshes, begin_2d, camera, color, end_2d, setup_gl
from .referee import Referee
from .scenery import Scenery
from .weapons import draw_nunchaku, draw_star


class Renderer:
    def __init__(self, settings):
        self.settings = settings
        self.window_size = (1280, 720)
        self.width, self.height = self.window_size
        self.fullscreen = settings['fullscreen']
        self.meshes = None
        self.scenery = None
        self.referee = None
        self.hud_texture = None
        self.gpu = ''
        self.camera_distance = 12.4
        self.camera_target = 0.0
        self.last_time = 0.0
        self.create_window()

    def create_window(self):
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 2)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 1)
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
        flags = pygame.OPENGL | pygame.DOUBLEBUF
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
        last_error = None
        created = False
        requested_samples = self.settings.get('msaa', 2)
        for samples in dict.fromkeys((requested_samples, 0)):
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, int(samples > 0))
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, samples)
            try:
                pygame.display.set_mode(
                    (0, 0) if self.fullscreen else self.window_size, flags, vsync=1)
                self.samples = samples
                created = True
                break
            except pygame.error as exc:
                last_error = exc
        if not created:
            raise RuntimeError('Kunde inte skapa ett OpenGL-fönster: ' + str(last_error))
        pygame.display.set_caption('Dojo Sunset — Original 3D-karate')
        pygame.mouse.set_visible(not self.fullscreen)
        self.width, self.height = pygame.display.get_window_size()
        # SDL window events refer to this wrapper; retain it for the window's lifetime.
        self.window = Window.from_display_module()
        setup_gl()
        if self.samples:
            glEnable(GL_MULTISAMPLE)
        self.samples_actual = int(glGetIntegerv(GL_SAMPLES))
        self.gpu = glGetString(GL_RENDERER).decode('utf-8', errors='replace')
        self.meshes = Meshes()
        self.scenery = Scenery(self.meshes, self.settings['arena'])
        self.referee = Referee(self.meshes)
        self.hud_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.hud_texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1280, 720, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glBindTexture(GL_TEXTURE_2D, 0)

    def release_resources(self):
        if self.referee:
            self.referee.close()
            self.referee = None
        if self.scenery:
            self.scenery.close()
            self.scenery = None
        if self.meshes:
            self.meshes.close()
            self.meshes = None
        if self.hud_texture:
            glDeleteTextures([self.hud_texture])
            self.hud_texture = None

    def toggle_fullscreen(self):
        # Keep the GL context and its resources alive. Reinitializing Pygame's
        # display subsystem retains a framebuffer-sized allocation on this Pi.
        window = self.window
        if self.fullscreen:
            window.set_windowed()
            window.size = self.window_size
        else:
            window.set_fullscreen(desktop=True)
        self.fullscreen = not self.fullscreen
        self.settings['fullscreen'] = self.fullscreen
        pygame.event.pump()
        self.width, self.height = pygame.display.get_window_size()
        glViewport(0, 0, self.width, self.height)
        pygame.mouse.set_visible(not self.fullscreen)

    def change_arena(self):
        if self.scenery:
            self.scenery.close()
        self.scenery = Scenery(self.meshes, self.settings['arena'])

    def shadow(self, fighter):
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glPushMatrix()
        glTranslatef(fighter.x - fighter.height * .18, .080, .04)
        size = 1.38 if fighter.archetype == 'sumo' else 1.0
        glScalef((.70 + fighter.height * .22) * size, 1, (.28 + fighter.height * .1) * size)
        glColor4f(.045, .055, .07, .30 - fighter.height * .08)
        glCallList(self.meshes.disk)
        glPopMatrix()
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)

    def fighter(self, fighter, clock):
        m = self.meshes
        joints = sample(fighter, clock)
        gi = fighter.color
        if fighter.hit_flash > 0:
            gi = tuple(min(1, c + .25) for c in gi)
        trim = tuple(c * .78 for c in gi)
        skin = (.74, .49, .32)
        hair = (.075, .064, .068)
        belt = fighter.belt_color
        sumo = fighter.archetype == 'sumo'
        ninja = fighter.archetype == 'ninja'
        limb_color = skin if sumo else gi
        glPushMatrix()
        glTranslatef(fighter.x, .058 + fighter.height, 0)
        glScalef(fighter.facing, 1, 1)
        if fighter.move_key == 'spin_kick' and fighter.attacking:
            turn = min(1.0, fighter.elapsed / fighter.move.startup)
            turn = turn * turn * (3 - 2 * turn)
            glRotatef(turn * 360, 0, 1, 0)
        hip = joints['hip']
        chest = joints['chest']
        torso_center = tuple((hip[i] + chest[i]) * .5 for i in range(3))
        torso_angle = math.degrees(math.atan2(chest[0] - hip[0], chest[1] - hip[1]))
        glPushMatrix()
        glTranslatef(*torso_center)
        glRotatef(-torso_angle, 0, 0, 1)
        if sumo:
            m.ball((0, .03, 0), (.39, .40, .31), skin)
            m.ball((.09, -.10, .01), (.35, .30, .30), skin)
            m.box((.01, -.23, .01), (.64, .15, .59), gi)
            m.box((.05, -.35, .29), (.23, .23, .055), gi)
            for index in range(5):
                x = -.18 + index * .09
                m.limb((x, -.28, .32), (x + .02, -.48, .33), .011, trim)
        else:
            m.ball((0, .06, 0), (.245, .37, .225), gi)
            m.box((0, -.19, .01), (.47, .065, .44), belt)
            m.box((.04, -.23, .245), (.085, .13, .055), belt)
            m.limb((.02, -.26, .24), (-.06, -.48, .27), .028, belt)
            m.limb((.07, -.26, .24), (.16, -.44, .27), .028, belt)
            m.limb((-.14, .29, .19), (.08, -.14, .22), .025, trim)
            m.limb((.13, .27, .18), (-.02, .07, .24), .025, trim)
        glPopMatrix()
        for side in ('back', 'front'):
            shoulder = joints['shoulder_' + side]
            elbow = joints['elbow_' + side]
            hand = joints['hand_' + side]
            pelvis = joints['hip_' + side]
            knee = joints['knee_' + side]
            foot = joints['foot_' + side]
            arm_size = 1.38 if sumo else 1.0
            m.ball(shoulder, (.14 * arm_size, .16 * arm_size, .14 * arm_size), limb_color)
            m.limb(shoulder, elbow, .13 * arm_size, limb_color)
            m.ball(elbow, (.11 * arm_size, .11 * arm_size, .11 * arm_size), limb_color)
            sleeve_end = tuple(elbow[i] + (hand[i] - elbow[i]) * .74 for i in range(3))
            m.limb(elbow, sleeve_end, .11 * arm_size, limb_color)
            m.limb(sleeve_end, hand, .072 * arm_size, gi if ninja else skin)
            m.ball(hand, (.11 * arm_size, .092 * arm_size, .085 * arm_size), gi if ninja else skin)
            m.limb(pelvis, knee, .165 * arm_size, limb_color)
            m.ball(knee, (.135 * arm_size, .13 * arm_size, .135 * arm_size), limb_color)
            cuff = tuple(knee[i] + (foot[i] - knee[i]) * .85 for i in range(3))
            m.limb(knee, cuff, .13 * arm_size, limb_color)
            m.limb(cuff, foot, .07 * arm_size, gi if ninja else skin)
            m.ball((foot[0] + .07, foot[1] - .03, foot[2]),
                   (.17 * arm_size, .078, .105 * arm_size), gi if ninja else skin)
        neck = joints['neck']
        head = joints['head']
        m.limb(neck, head, .08, skin)
        glPushMatrix()
        glTranslatef(*head)
        head_tilt = math.degrees(math.atan2(head[0] - neck[0], head[1] - neck[1]))
        glRotatef(-head_tilt, 0, 0, 1)
        head = (0.0, 0.0, 0.0)
        if ninja:
            m.ball(head, (.18, .235, .168), gi)
            m.box((.075, .050, .161), (.20, .068, .022), skin)
            m.box((.075, .050, -.161), (.20, .068, .022), skin)
            m.ball((.14, .048, .177), (.021, .014, .014), hair)
            m.ball((.14, .048, -.177), (.021, .014, .014), hair)
            m.ball((.035, -.055, 0), (.177, .13, .17), trim)
        else:
            m.ball(head, (.17, .225, .155), skin)
            m.ball((head[0] - .025, head[1] + .13, head[2]), (.171, .12, .158), hair)
            m.ball((head[0] + .165, head[1] - .008, head[2]), (.055, .052, .05), skin)
            m.ball((head[0] -.025, head[1] - .015, head[2] + .151), (.043, .068, .028), skin)
            m.ball((head[0] + .121, head[1] + .046, head[2] + .104), (.022, .018, .024), hair)
            m.ball((head[0] + .121, head[1] + .046, head[2] - .104), (.022, .018, .024), hair)
        if sumo:
            m.ball((-.05, .25, 0), (.075, .085, .065), hair)
        band = (.69, .17, .18) if fighter.color[0] > .8 else (.90, .87, .76)
        if not sumo:
            m.box((head[0] -.012, head[1] + .092, head[2] + .147), (.27, .045, .024), band)
            m.limb((head[0] -.15, head[1] + .09, head[2]),
                   (head[0] -.34, head[1] -.02 + math.sin(clock * 6) * .035, head[2] + .04), .018, band)
        glPopMatrix()
        if ninja:
            if fighter.move_key == 'shuriken' and fighter.attacking and not fighter.landed:
                draw_star(joints['hand_front'], clock * 240, .12)
                draw_nunchaku(m, fighter, joints['hand_back'])
            else:
                draw_nunchaku(m, fighter, joints['hand_front'])
        glPopMatrix()

    def kick_trail(self, fighter, clock):
        if not fighter.attacking or fighter.move_key != 'round_kick':
            return
        move = fighter.move
        if not move.startup * .55 < fighter.elapsed < move.startup + move.active + .12:
            return
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        glLineWidth(3)
        glBegin(GL_LINE_STRIP)
        for index in range(8):
            previous = max(0, fighter.elapsed - (7 - index) * .012)
            foot = sample(replace(fighter, elapsed=previous), clock)['foot_back']
            glColor4f(.96, .81, .49, .035 + index * .028)
            glVertex3f(fighter.x + foot[0] * fighter.facing,
                       foot[1] + fighter.height + .058, foot[2] + .07)
        glEnd()
        glLineWidth(1)
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)

    def impacts(self, match):
        glDisable(GL_LIGHTING)
        glLineWidth(2)
        for impact in match.impacts:
            rng = random.Random(impact.seed)
            age = .65 - impact.life
            radius = .08 + age * 1.5
            alpha = max(0, 1 - age / .40)
            rgb = (.45, .82, 1.0) if impact.kind == 'block' else (1.0, .83, .40)
            color(rgb, alpha)
            glBegin(GL_LINES)
            for index in range(12):
                angle = index * math.tau / 12 + rng.random() * .2
                dx = math.cos(angle)
                dy = math.sin(angle)
                glVertex3f(impact.x + dx * radius * .55, impact.y + dy * radius * .55, .35)
                glVertex3f(impact.x + dx * radius, impact.y + dy * radius, .35)
            glEnd()
        glLineWidth(1)
        glEnable(GL_LIGHTING)

    def project(self, x, y, z):
        distance = self.camera_distance
        angle = math.atan(.177)
        dy = y - 1.15 - distance * .177
        dz = z - distance
        view_y = dy * math.cos(angle) - dz * math.sin(angle)
        depth = max(.01, -dy * math.sin(angle) - dz * math.cos(angle))
        tangent = math.tan(math.radians(19))
        aspect = self.width / max(1, self.height)
        screen_x = 640 * (1 + (x - self.camera_target) / (depth * tangent * aspect))
        screen_y = 360 * (1 - view_y / (depth * tangent))
        return screen_x, screen_y

    def draw_world(self, fighters, elapsed, match=None):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.scenery.sky(self.width, self.height)
        target = sum(f.x for f in fighters) / max(1, len(fighters))
        shake = math.sin(elapsed * 150) * match.shake * .13 if match else 0
        dt = max(0, min(.1, elapsed - self.last_time))
        self.last_time = elapsed
        desired_distance = 12.4
        desired_target = target * .20
        if match:
            separation = abs(fighters[0].x - fighters[1].x)
            desired_distance = max(9.5, min(13.8, separation * 1.1 + 7.3))
            desired_target = target * .8
        smoothing = 1 - math.exp(-3.0 * dt)
        self.camera_distance += (desired_distance - self.camera_distance) * smoothing
        self.camera_target += (desired_target - self.camera_target) * smoothing
        camera(self.width, self.height, self.camera_target, shake, self.camera_distance)
        glEnable(GL_FOG)
        glFogi(GL_FOG_MODE, GL_LINEAR)
        glFogf(GL_FOG_START, self.camera_distance + 7)
        glFogf(GL_FOG_END, self.camera_distance + 40)
        glFogfv(GL_FOG_COLOR, (*self.scenery.palette['haze'], 1))
        self.scenery.draw(elapsed, self.settings['quality'])
        if not match or getattr(match, 'rules', '') == 'classic':
            self.referee.draw(elapsed, match)
        for fighter in fighters:
            self.shadow(fighter)
        for fighter in fighters:
            self.fighter(fighter, elapsed)
            if self.settings['quality']:
                self.kick_trail(fighter, elapsed)
        if match:
            for star in match.projectiles:
                draw_star((star.x, star.y, .20), star.rotation)
            self.impacts(match)
        glDisable(GL_FOG)

    def draw_hud(self, surface):
        # Pygame's native 32-bit surface is BGRA on this little-endian Pi.
        # Upload its existing buffer instead of converting 3.7 MB every frame.
        if surface.get_masks() == (0xFF0000, 0xFF00, 0xFF, 0xFF000000):
            pixels = np.frombuffer(surface.get_buffer(), dtype=np.uint8)
            pixel_format = GL_BGRA
        else:
            pixels = pygame.image.tobytes(surface, 'RGBA', False)
            pixel_format = GL_RGBA
        glBindTexture(GL_TEXTURE_2D, self.hud_texture)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 1280, 720, pixel_format, GL_UNSIGNED_BYTE, pixels)
        begin_2d(1280, 720)
        glEnable(GL_TEXTURE_2D)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(0, 0)
        glTexCoord2f(1, 0)
        glVertex2f(1280, 0)
        glTexCoord2f(1, 1)
        glVertex2f(1280, 720)
        glTexCoord2f(0, 1)
        glVertex2f(0, 720)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        end_2d()

    def screenshot(self, path):
        glReadBuffer(GL_BACK)
        raw = glReadPixels(0, 0, self.width, self.height, GL_RGB, GL_UNSIGNED_BYTE)
        surface = pygame.image.frombytes(raw, (self.width, self.height), 'RGB')
        pygame.image.save(pygame.transform.flip(surface, False, True), str(path))

    def present(self):
        pygame.display.flip()

    def close(self):
        self.release_resources()
