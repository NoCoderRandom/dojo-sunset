"""Original geometric nunchaku and four-point throwing star models."""
import math

from OpenGL.GL import (
    GL_QUADS,
    GL_TRIANGLES,
    glBegin,
    glColor3f,
    glEnd,
    glNormal3f,
    glPopMatrix,
    glPushMatrix,
    glRotatef,
    glTranslatef,
    glVertex3f,
)


def nunchaku_points(fighter, hand):
    first_angle = -math.pi / 2
    second_angle = -math.pi / 2
    if fighter.attacking and fighter.move_key == 'nunchaku':
        move = fighter.move
        if fighter.elapsed < move.startup:
            amount = fighter.elapsed / move.startup
            first_angle *= 1 - amount
            second_angle = (1 - amount) * math.tau * 2
        elif fighter.elapsed < move.startup + move.active:
            first_angle = -.08
            second_angle = -.04
        else:
            amount = min(1, (fighter.elapsed - move.startup - move.active) / move.recovery)
            first_angle *= amount
            second_angle *= amount
    tip = (hand[0] + math.cos(first_angle) * .40,
           hand[1] + math.sin(first_angle) * .40, hand[2])
    chain = (tip[0] + math.cos(second_angle) * .12,
             tip[1] + math.sin(second_angle) * .12, tip[2])
    end = (chain[0] + math.cos(second_angle) * .44,
           chain[1] + math.sin(second_angle) * .44, chain[2])
    return hand, tip, chain, end


def draw_nunchaku(meshes, fighter, hand):
    grip, tip, chain, end = nunchaku_points(fighter, hand)
    wood = (.53, .26, .09)
    brass = (.82, .63, .24)
    metal = (.70, .76, .80)
    meshes.limb(grip, tip, .034, wood)
    meshes.limb(tip, chain, .012, metal)
    meshes.limb(chain, end, .034, wood)
    for point in (grip, tip, chain, end):
        meshes.ball(point, (.037, .037, .037), brass)
    for step in range(1, 5):
        point = tuple(tip[i] + (chain[i] - tip[i]) * step / 5 for i in range(3))
        meshes.ball(point, (.018, .018, .018), metal)


def draw_star(position, rotation=0, radius=.17):
    glPushMatrix()
    glTranslatef(*position)
    glRotatef(rotation, 0, 0, 1)
    points = [(math.cos(i * math.pi / 4) * radius * (1 if i % 2 == 0 else .32),
               math.sin(i * math.pi / 4) * radius * (1 if i % 2 == 0 else .32))
              for i in range(8)]
    for depth, normal in ((.015, 1), (-.015, -1)):
        glColor3f(.75, .83, .91)
        glNormal3f(0, 0, normal)
        glBegin(GL_TRIANGLES)
        for index, point in enumerate(points):
            following = points[(index + 1) % len(points)]
            glVertex3f(0, 0, depth)
            glVertex3f(*point, depth)
            glVertex3f(*following, depth)
        glEnd()
    glColor3f(.32, .41, .48)
    glBegin(GL_QUADS)
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        glNormal3f(point[0], point[1], 0)
        glVertex3f(*point, -.015)
        glVertex3f(*following, -.015)
        glVertex3f(*following, .015)
        glVertex3f(*point, .015)
    glEnd()
    glPopMatrix()
