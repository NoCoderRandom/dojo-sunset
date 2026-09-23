"""Original seated judge, with animated white/red scoring flags."""
import math

from OpenGL.GL import *

from .geometry import color


class Referee:
    def __init__(self, meshes):
        self.meshes = meshes
        self.lift = {-1: 0.0, 1: 0.0}
        self.last_time = 0.0
        self.skin = (.72, .51, .35)
        self.robe = (.20, .28, .33)
        self.list = glGenLists(1)
        glNewList(self.list, GL_COMPILE)
        self.build_body()
        glEndList()

    def build_body(self):
        m = self.meshes
        wood = (.27, .18, .14)
        hair = (.37, .37, .35)
        m.box((0, .43, -.02), (.66, .12, .54), wood)
        for x in (-.24, .24):
            for z in (-.19, .19):
                m.box((x, .22, z), (.075, .42, .075), wood)
        m.ball((0, .87, 0), (.27, .36, .20), self.robe)
        m.box((0, .64, .03), (.49, .07, .38), (.11, .15, .18))
        m.limb((-.15, 1.15, .16), (.08, .74, .18), .018, (.51, .55, .51))
        m.limb((.15, 1.15, .16), (-.02, .92, .22), .018, (.51, .55, .51))
        for side in (-1, 1):
            m.ball((side * .24, 1.05, .00), (.12, .13, .12), self.robe)
            m.limb((side * .14, .64, .02), (side * .24, .38, .31), .135, self.robe)
            m.limb((side * .24, .38, .31), (side * .25, .10, .38), .10, self.robe)
            m.ball((side * .25, .09, .44), (.09, .07, .15), (.11, .13, .14))
        m.pillar((0, 1.16, 0), .07, .15, self.skin)
        m.ball((0, 1.40, 0), (.17, .21, .16), self.skin)
        m.ball((0, 1.52, -.025), (.174, .115, .155), hair)
        for side in (-1, 1):
            m.ball((side * .168, 1.4, 0), (.033, .055, .045), self.skin)
            m.ball((side * .075, 1.445, .143), (.023, .013, .013), (.08, .09, .09))
            m.limb((side * .045, 1.485, .143), (side * .113, 1.48, .129), .017, hair)
        m.ball((0, 1.398, .166), (.04, .055, .05), self.skin)
        m.ball((0, 1.284, .091), (.115, .10, .104), (.55, .55, .51))

    def arm_and_flag(self, side, raised, elapsed):
        m = self.meshes
        shoulder = (side * .24, 1.05, 0)
        elbow = (side * (.34 + raised * .07), .88 + raised * .34, .09)
        hand = (side * (.40 + raised * .12), .72 + raised * .79, .19)
        m.limb(shoulder, elbow, .095, self.robe)
        m.limb(elbow, hand, .074, self.robe)
        m.ball(hand, (.062, .071, .06), self.skin)
        top = (hand[0] + side * .03, hand[1] + .47, hand[2])
        m.limb(hand, top, .013, (.56, .40, .23))
        flag = (.91, .88, .77) if side < 0 else (.72, .13, .15)
        flutter = math.sin(elapsed * 5 + side) * .025
        color(flag)
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1)
        glVertex3f(top[0], top[1], top[2])
        glVertex3f(top[0] + side * .28, top[1] - .03, top[2] + flutter)
        glVertex3f(top[0] + side * .27, top[1] - .23, top[2] + flutter)
        glVertex3f(top[0], top[1] - .20, top[2])
        glEnd()

    def draw(self, elapsed, match=None):
        dt = max(0, min(.1, elapsed - self.last_time))
        self.last_time = elapsed
        winner = None
        amount = 1.0
        if match:
            if match.phase == 'point':
                winner = match.point_winner
                amount = 1.0 if match.point_value == 2 else .68
            elif match.phase in ('round_over', 'finished'):
                winner = match.round_winner
        for side in (-1, 1):
            target = 0.0
            if match and winner:
                winning_side = -1 if winner is match.player else 1
                if side == winning_side:
                    target = amount
            self.lift[side] += (target - self.lift[side]) * (1 - math.exp(-9 * dt))
        glPushMatrix()
        glTranslatef(0, -.20, -3.0)
        glScalef(.9, .9, .9)
        glCallList(self.list)
        for side in (-1, 1):
            self.arm_and_flag(side, self.lift[side], elapsed)
        glPopMatrix()

    def close(self):
        glDeleteLists(self.list, 1)
