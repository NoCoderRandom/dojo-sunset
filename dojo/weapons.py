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
    # The hand sits near the chain, not on the butt of the held stick.  This
    # keeps the weapon controllable and prevents the old upside-down grip.
    first_angle = math.pi / 2
    second_angle = -1.35
    if fighter.state == 'flourish':
        phase = fighter.elapsed * math.tau * 2.6
        first_angle = 1.15 + math.sin(phase) * .50
        second_angle = -.35 + math.sin(phase * 2) * 1.30
    elif fighter.attacking and fighter.move_key.startswith('nunchaku'):
        move = fighter.move
        if fighter.move_key == 'nunchaku_overhead':
            chamber = (1.02, -2.10)
            contact = (-.38, -.92)
        elif fighter.move_key == 'nunchaku_low':
            chamber = (2.35, 2.70)
            contact = (.10, -.30)
        else:
            chamber = (1.70, -2.30)
            contact = (.10, -.08)
        if fighter.elapsed < move.startup:
            amount = fighter.elapsed / move.startup
            first_angle = chamber[0] + (contact[0] - chamber[0]) * amount
            second_angle = chamber[1] + (contact[1] - chamber[1]) * amount
        elif fighter.elapsed < move.startup + move.active:
            first_angle, second_angle = contact
        else:
            amount = min(1, (fighter.elapsed - move.startup - move.active) / move.recovery)
            first_angle = contact[0] + (math.pi / 2 - contact[0]) * amount
            second_angle = contact[1] + (-1.35 - contact[1]) * amount
    direction = (math.cos(first_angle), math.sin(first_angle), 0)
    grip = (hand[0] - direction[0] * .30,
            hand[1] - direction[1] * .30, hand[2])
    tip = (hand[0] + direction[0] * .10,
           hand[1] + direction[1] * .10, hand[2])
    chain = (tip[0] + math.cos(second_angle) * .12,
             tip[1] + math.sin(second_angle) * .12, tip[2])
    end = (chain[0] + math.cos(second_angle) * .44,
           chain[1] + math.sin(second_angle) * .44, chain[2])
    return grip, tip, chain, end


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
