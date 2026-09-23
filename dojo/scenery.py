"""An original low-poly Japanese garden, constructed entirely from geometry."""
import math
import random

from OpenGL.GL import *

from .geometry import begin_2d, color, end_2d, triangle

PALETTES = [
    {'sky_top': (.12, .15, .28), 'sky_low': (.91, .47, .34),
     'sun': (1.0, .78, .48), 'mountain': (.25, .27, .35),
     'haze': (.47, .36, .43), 'grass': (.22, .31, .28),
     'leaves': (.90, .48, .55), 'name': 'SAKURA • SOLNEDGÅNG'},
    {'sky_top': (.025, .07, .16), 'sky_low': (.24, .31, .44),
     'sun': (.82, .90, .95), 'mountain': (.10, .18, .25),
     'haze': (.21, .29, .37), 'grass': (.12, .23, .23),
     'leaves': (.52, .55, .77), 'name': 'TSUKI • MÅNSKEN'},
]


class Scenery:
    def __init__(self, meshes, arena=0):
        self.meshes = meshes
        self.arena = arena
        self.palette = PALETTES[arena]
        self.random = random.Random(918)
        self.display_list = glGenLists(1)
        glNewList(self.display_list, GL_COMPILE)
        self.build()
        glEndList()
        self.petals = []
        for _index in range(42):
            self.petals.append((self.random.uniform(-8, 8),
                                self.random.uniform(.5, 5),
                                self.random.uniform(-3, 2),
                                self.random.uniform(.5, 1.4),
                                self.random.uniform(0, math.tau)))

    def sky(self, width, height):
        begin_2d(width, height)
        glBegin(GL_QUADS)
        color(self.palette['sky_top'])
        glVertex2f(0, 0)
        glVertex2f(width, 0)
        color(self.palette['sky_low'])
        glVertex2f(width, height)
        glVertex2f(0, height)
        glEnd()
        end_2d()

    def mountains(self):
        for depth, tint, base_height in [(-23, self.palette['haze'], 3),
                                         (-17, self.palette['mountain'], 1)]:
            for index in range(7):
                x = -22 + index * 7
                top = self.random.uniform(4, 9) + base_height
                width = self.random.uniform(5, 8)
                shade = tuple(channel * self.random.uniform(.9, 1.08) for channel in tint)
                color(shade)
                glBegin(GL_TRIANGLES)
                triangle((x - width, -2, depth), (x, top, depth - 2), (x + width, -2, depth))
                glEnd()
                if top > 8:
                    color((.76, .70, .70))
                    glBegin(GL_TRIANGLES)
                    triangle((x - width * .18, top - 1.9, depth - 1.7),
                             (x, top, depth - 1.98),
                             (x + width * .19, top - 2, depth - 1.7))
                    glEnd()

    def torii(self, x, z, scale=1):
        m = self.meshes
        red = (.48, .12, .12)
        dark = (.16, .15, .19)
        glPushMatrix()
        glTranslatef(x, 0, z)
        glScalef(scale, scale, scale)
        for side in (-1, 1):
            m.pillar((side * 1.6, 0, 0), .15, 3.6, red)
            m.pillar((side * 1.6, 0, 0), .20, .4, dark)
            m.box((side * 1.95, 3.70, 0), (.80, .17, .5), dark, side * -5)
        m.box((0, 3.50, 0), (4.5, .20, .45), red)
        m.box((0, 3.73, 0), (4.0, .18, .54), dark)
        m.box((0, 2.75, 0), (3.8, .16, .25), red)
        m.box((0, 3.14, 0), (.19, .65, .25), red)
        m.box((0, 3.12, .16), (.4, .50, .06), (.65, .48, .25))
        glPopMatrix()

    def pagoda(self, x, z):
        m = self.meshes
        wood = (.21, .15, .17)
        roof = (.15, .20, .23)
        for tier in range(3):
            y = tier * 1.1
            width = 1.5 - tier * .27
            m.box((x, y + .50, z), (width * 1.65, .95, width * 1.25), wood)
            for side in (-1, 1):
                m.box((x + side * width * .58, y + .52, z + width * .64),
                      (.22, .50, .04), (.95, .62, .30))
            m.roof(x, y + 1.0, z, width * 1.25, width, .65, roof)
            m.box((x, y + .98, z), (width * 2.6, .10, width * 2.0), roof)
        m.pillar((x, 3.6, z), .05, .65, (.52, .37, .2))

    def tree(self, x, z, scale=1):
        m = self.meshes
        bark = (.28, .19, .19)
        leaves = self.palette['leaves']
        glPushMatrix()
        glTranslatef(x, 0, z)
        glScalef(scale, scale, scale)
        m.limb((0, 0, 0), (.2, 2.4, 0), .18, bark)
        for index in range(7):
            angle = index * 2.4
            radius = self.random.uniform(.65, 1.35)
            endpoint = (math.cos(angle) * radius, self.random.uniform(2.5, 3.5), math.sin(angle) * radius * .6)
            m.limb((.1, 1.7, 0), endpoint, .085, bark)
            tint = tuple(channel * self.random.uniform(.87, 1.09) for channel in leaves)
            m.ball(endpoint, (.94, .56, .72), tint)
        glPopMatrix()

    def lantern(self, x, z):
        m = self.meshes
        stone = (.40, .43, .41)
        m.box((x, .10, z), (.52, .20, .52), stone)
        m.pillar((x, .20, z), .11, .6, stone)
        m.box((x, .81, z), (.44, .12, .44), stone)
        m.box((x, 1.02, z), (.30, .35, .30), (.91, .61, .28))
        for dx in (-.16, .16):
            for dz in (-.16, .16):
                m.box((x + dx, 1.01, z + dz), (.055, .36, .055), stone)
        m.roof(x, 1.2, z, .35, .35, .20, stone)
        m.ball((x, 1.42, z), (.09, .10, .09), stone)

    def fence(self):
        m = self.meshes
        wood = (.30, .22, .22)
        for x in range(-10, 11):
            m.pillar((x * .75, 0, -4), .055, 1.0, wood)
        for y in (.35, .78):
            m.box((0, y, -4), (16, .075, .08), wood)

    def build(self):
        m = self.meshes
        glDisable(GL_LIGHTING)
        self.mountains()
        m.ball((-7, 7, -24), (2.1, 2.1, .3), self.palette['sun'])
        glEnable(GL_LIGHTING)
        m.box((0, -.34, -4), (60, .25, 50), self.palette['grass'])
        m.box((0, -.10, 0), (11.2, .25, 4.8), (.22, .24, .25))
        m.box((0, .025, 0), (10.8, .06, 4.4), (.68, .61, .44))
        for ix in range(12):
            for iz in range(5):
                x = -4.95 + ix * .90
                z = -1.76 + iz * .88
                tint = (.49, .56, .44) if (ix + iz) % 2 else (.54, .60, .47)
                m.box((x, .064, z), (.885, .02, .865), tint)
        for x in (-5.35, 5.35):
            m.box((x, .08, 0), (.05, .03, 4.35), (.87, .69, .38))
        for z in (-2.16, 2.16):
            m.box((0, .08, z), (10.7, .03, .04), (.87, .69, .38))
        for x in (-1.5, 1.5):
            m.box((x, .083, 0), (.045, .025, .60), (.82, .78, .62))
        glPushMatrix()
        glTranslatef(0, -.20, 0)
        self.fence()
        self.torii(0, -6.5, 1.4)
        self.pagoda(7.4, -10)
        self.tree(-6.7, -3.5, 1.35)
        self.tree(6.6, -4.5, 1.1)
        self.tree(-9, -9, 1.25)
        for x in (-5.9, 5.9):
            self.lantern(x, -1.7)
            self.lantern(x, 2.1)
        glPopMatrix()
        for _index in range(30):
            x = self.random.uniform(-12, 12)
            z = self.random.uniform(-9, -4.5)
            m.ball((x, -.04, z), (self.random.uniform(.2, .5), .16, .3), (.36, .40, .36))

    def draw(self, elapsed, quality):
        glCallList(self.display_list)
        if not quality:
            return
        glDisable(GL_LIGHTING)
        color(self.palette['leaves'], .8)
        glBegin(GL_TRIANGLES)
        for x, y, z, speed, phase in self.petals:
            px = ((x + elapsed * speed * .45 + 9) % 18) - 9
            py = (y - elapsed * .25 * speed) % 5 + .2
            pz = z + math.sin(elapsed + phase) * .18
            sway = math.sin(elapsed * 3 + phase) * .06
            glVertex3f(px - .04, py, pz)
            glVertex3f(px + .04, py + sway, pz)
            glVertex3f(px, py + .06, pz + .025)
        glEnd()
        glEnable(GL_LIGHTING)

    def close(self):
        glDeleteLists(self.display_list, 1)
