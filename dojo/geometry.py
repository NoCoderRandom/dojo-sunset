"""Small fixed-function OpenGL mesh library for the Pi's V3D GPU."""
import math

from OpenGL.GL import *
from OpenGL.GLU import gluLookAt, gluPerspective


def color(rgb, alpha=1.0):
    glColor4f(rgb[0], rgb[1], rgb[2], alpha)


def normalize(vector):
    length = math.sqrt(sum(value * value for value in vector))
    if length < 1e-8:
        return (0.0, 1.0, 0.0)
    return tuple(value / length for value in vector)


def normal(a, b, c):
    u = tuple(b[i] - a[i] for i in range(3))
    v = tuple(c[i] - a[i] for i in range(3))
    return normalize((u[1] * v[2] - u[2] * v[1],
                      u[2] * v[0] - u[0] * v[2],
                      u[0] * v[1] - u[1] * v[0]))


def triangle(a, b, c):
    glNormal3f(*normal(a, b, c))
    glVertex3f(*a)
    glVertex3f(*b)
    glVertex3f(*c)


class Meshes:
    def __init__(self):
        self.lists = []
        self.cube = self.compile(self.build_cube)
        self.sphere = self.compile(self.build_sphere)
        self.cylinder = self.compile(self.build_cylinder)
        self.cone = self.compile(self.build_cone)
        self.disk = self.compile(self.build_disk)

    def compile(self, function):
        identity = glGenLists(1)
        glNewList(identity, GL_COMPILE)
        function()
        glEndList()
        self.lists.append(identity)
        return identity

    def build_cube(self):
        faces = [
            ((0, 0, 1), ((-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5))),
            ((0, 0, -1), ((.5, -.5, -.5), (-.5, -.5, -.5), (-.5, .5, -.5), (.5, .5, -.5))),
            ((1, 0, 0), ((.5, -.5, .5), (.5, -.5, -.5), (.5, .5, -.5), (.5, .5, .5))),
            ((-1, 0, 0), ((-.5, -.5, -.5), (-.5, -.5, .5), (-.5, .5, .5), (-.5, .5, -.5))),
            ((0, 1, 0), ((-.5, .5, .5), (.5, .5, .5), (.5, .5, -.5), (-.5, .5, -.5))),
            ((0, -1, 0), ((-.5, -.5, -.5), (.5, -.5, -.5), (.5, -.5, .5), (-.5, -.5, .5))),
        ]
        glBegin(GL_QUADS)
        for direction, vertices in faces:
            glNormal3f(*direction)
            for vertex in vertices:
                glVertex3f(*vertex)
        glEnd()

    def build_sphere(self):
        latitudes = 8
        longitudes = 12
        for row in range(latitudes):
            lower = -math.pi / 2 + row * math.pi / latitudes
            upper = -math.pi / 2 + (row + 1) * math.pi / latitudes
            glBegin(GL_QUAD_STRIP)
            for col in range(longitudes + 1):
                angle = col * math.tau / longitudes
                for latitude in (lower, upper):
                    vertex = (math.cos(latitude) * math.cos(angle),
                              math.sin(latitude),
                              math.cos(latitude) * math.sin(angle))
                    glNormal3f(*vertex)
                    glVertex3f(*vertex)
            glEnd()

    def build_cylinder(self):
        sides = 10
        glBegin(GL_QUAD_STRIP)
        for step in range(sides + 1):
            angle = step * math.tau / sides
            x, z = math.cos(angle), math.sin(angle)
            glNormal3f(x, 0, z)
            glVertex3f(x, 0, z)
            glVertex3f(x * .88, 1, z * .88)
        glEnd()
        for y, sign, radius in ((0, -1, 1), (1, 1, .88)):
            glBegin(GL_TRIANGLE_FAN)
            glNormal3f(0, sign, 0)
            glVertex3f(0, y, 0)
            for step in range(sides + 1):
                angle = step * math.tau / sides * sign
                glVertex3f(math.cos(angle) * radius, y, math.sin(angle) * radius)
            glEnd()

    def build_cone(self):
        glBegin(GL_TRIANGLES)
        for step in range(10):
            a = step * math.tau / 10
            b = (step + 1) * math.tau / 10
            triangle((math.cos(a), 0, math.sin(a)), (0, 1, 0),
                     (math.cos(b), 0, math.sin(b)))
        glEnd()

    def build_disk(self):
        glBegin(GL_TRIANGLE_FAN)
        glNormal3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        for step in range(33):
            angle = step * math.tau / 32
            glVertex3f(math.cos(angle), 0, math.sin(angle))
        glEnd()

    def object(self, mesh, position, scale, rgb, rotation=0):
        glPushMatrix()
        glTranslatef(*position)
        if rotation:
            glRotatef(rotation, 0, 1, 0)
        glScalef(*scale)
        color(rgb)
        glCallList(mesh)
        glPopMatrix()

    def box(self, position, scale, rgb, rotation=0):
        self.object(self.cube, position, scale, rgb, rotation)

    def ball(self, position, scale, rgb):
        self.object(self.sphere, position, scale, rgb)

    def pillar(self, position, radius, height, rgb):
        self.object(self.cylinder, position, (radius, height, radius), rgb)

    def limb(self, start, end, radius, rgb):
        delta = tuple(end[i] - start[i] for i in range(3))
        length = math.sqrt(sum(value * value for value in delta))
        if length < .001:
            return
        direction = tuple(value / length for value in delta)
        angle = math.degrees(math.acos(max(-1, min(1, direction[1]))))
        axis = (direction[2], 0, -direction[0])
        glPushMatrix()
        glTranslatef(*start)
        if abs(angle) > .001:
            if abs(axis[0]) + abs(axis[2]) < .001:
                glRotatef(180, 1, 0, 0)
            else:
                glRotatef(angle, *axis)
        glScalef(radius, length, radius)
        color(rgb)
        glCallList(self.cylinder)
        glPopMatrix()

    def roof(self, x, y, z, width, depth, height, rgb):
        a = (x - width, y, z - depth)
        b = (x + width, y, z - depth)
        c = (x + width, y, z + depth)
        d = (x - width, y, z + depth)
        left = (x - width * .55, y + height, z)
        right = (x + width * .55, y + height, z)
        color(rgb)
        glBegin(GL_TRIANGLES)
        triangle(a, left, right)
        triangle(a, right, b)
        triangle(d, c, right)
        triangle(d, right, left)
        triangle(a, d, left)
        triangle(b, right, c)
        glEnd()

    def close(self):
        for identity in self.lists:
            glDeleteLists(identity, 1)
        self.lists.clear()


def setup_gl():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (.98, .81, .60, 1))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (.18, .18, .23, 1))
    glLightfv(GL_LIGHT1, GL_DIFFUSE, (.24, .36, .48, 1))
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, (.25, .25, .30, 1))
    glShadeModel(GL_SMOOTH)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glDisable(GL_CULL_FACE)


def camera(width, height, target_x=0, shake=0, distance=12.4):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(38, width / max(1, height), .1, 90)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(target_x + shake, 1.15 + distance * .177, distance,
              target_x, 1.15, 0, 0, 1, 0)
    glLightfv(GL_LIGHT0, GL_POSITION, (-5, 8, -3, 0))
    glLightfv(GL_LIGHT1, GL_POSITION, (4, 3, 6, 0))


def begin_2d(width, height):
    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, width, height, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()


def end_2d():
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
