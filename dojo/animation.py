"""Authored skeletal poses in metres, with eased keyframe interpolation."""
import math

from .model import clamp, lerp

BASE = {
    'hip': (0.0, 1.00, 0.0),
    'chest': (0.02, 1.48, 0.0),
    'neck': (0.03, 1.76, 0.0),
    'head': (0.04, 1.98, 0.0),
    'shoulder_front': (0.02, 1.62, .22),
    'elbow_front': (.28, 1.34, .26),
    'hand_front': (.52, 1.58, .23),
    'shoulder_back': (.02, 1.62, -.22),
    'elbow_back': (-.28, 1.32, -.20),
    'hand_back': (.06, 1.36, -.28),
    'hip_front': (-.10, 1.00, .13),
    'knee_front': (-.32, .55, .16),
    'foot_front': (-.49, .13, .18),
    'hip_back': (.10, 1.00, -.13),
    'knee_back': (.37, .55, -.14),
    'foot_back': (.53, .13, -.17),
}


def pose(**changes):
    result = dict(BASE)
    result.update(changes)
    return result


def blend(first, second, amount):
    amount = clamp(amount, 0, 1)
    amount = amount * amount * (3 - 2 * amount)
    return {name: tuple(lerp(first[name][i], second[name][i], amount)
                        for i in range(3)) for name in BASE}


JAB_WINDUP = pose(
    chest=(-.05, 1.47, -.02),
    elbow_front=(.08, 1.36, .30),
    hand_front=(.27, 1.56, .28),
    hand_back=(.17, 1.65, -.15),
)
JAB_CONTACT = pose(
    chest=(.13, 1.48, .03),
    neck=(.15, 1.76, .01),
    head=(.16, 1.98, 0),
    shoulder_front=(.23, 1.63, .17),
    elbow_front=(.66, 1.68, .15),
    hand_front=(1.12, 1.74, .12),
    shoulder_back=(-.02, 1.62, -.17),
    elbow_back=(-.22, 1.35, -.19),
    hand_back=(.03, 1.36, -.22),
    knee_back=(.47, .55, -.13),
)
CROSS_WINDUP = pose(
    chest=(-.09, 1.46, .03),
    shoulder_back=(-.12, 1.61, -.20),
    elbow_back=(-.43, 1.29, -.23),
    hand_back=(-.12, 1.27, -.28),
    hand_front=(.45, 1.75, .13),
    knee_front=(-.40, .51, .17),
)
CROSS_CONTACT = pose(
    hip=(.10, .98, 0),
    chest=(.23, 1.44, 0),
    neck=(.29, 1.73, 0),
    head=(.31, 1.95, 0),
    shoulder_back=(.38, 1.59, -.05),
    elbow_back=(.81, 1.48, -.02),
    hand_back=(1.27, 1.40, .04),
    shoulder_front=(.07, 1.58, .16),
    elbow_front=(-.13, 1.30, .23),
    hand_front=(.20, 1.29, .24),
    knee_front=(-.23, .50, .15),
    foot_front=(-.40, .13, .18),
)
KICK_CHAMBER = pose(
    hip=(-.10, 1.03, 0),
    chest=(-.16, 1.50, 0),
    neck=(-.17, 1.77, 0),
    head=(-.17, 1.99, 0),
    hip_back=(-.05, 1.02, -.13),
    knee_back=(.45, 1.12, -.12),
    foot_back=(.30, .72, -.12),
    hand_front=(.38, 1.74, .25),
    elbow_front=(.13, 1.40, .28),
    hand_back=(.05, 1.65, -.25),
)
FRONT_CONTACT = pose(
    hip=(-.16, 1.04, 0),
    chest=(-.32, 1.49, 0),
    neck=(-.36, 1.77, 0),
    head=(-.37, 1.99, 0),
    shoulder_front=(-.28, 1.62, .21),
    elbow_front=(-.14, 1.30, .27),
    hand_front=(.15, 1.49, .23),
    shoulder_back=(-.32, 1.62, -.22),
    elbow_back=(-.56, 1.27, -.25),
    hand_back=(-.28, 1.31, -.25),
    hip_back=(-.06, 1.06, -.12),
    knee_back=(.58, 1.23, -.11),
    foot_back=(1.43, 1.31, -.09),
    hip_front=(-.24, 1.03, .13),
    knee_front=(-.44, .57, .17),
    foot_front=(-.48, .13, .18),
)
HIGH_CHAMBER = pose(
    hip=(-.08, 1.04, 0),
    chest=(-.20, 1.51, 0),
    neck=(-.24, 1.78, 0),
    head=(-.25, 2.00, 0),
    knee_back=(.34, 1.43, -.15),
    foot_back=(.05, 1.10, -.19),
    hand_front=(.25, 1.73, .23),
    elbow_back=(-.43, 1.32, -.23),
)
HIGH_CONTACT = pose(
    hip=(-.15, 1.02, 0),
    chest=(-.46, 1.41, 0),
    neck=(-.60, 1.63, 0),
    head=(-.66, 1.83, 0),
    shoulder_front=(-.42, 1.56, .22),
    elbow_front=(-.17, 1.33, .29),
    hand_front=(.08, 1.55, .25),
    shoulder_back=(-.48, 1.54, -.22),
    elbow_back=(-.81, 1.25, -.23),
    hand_back=(-.58, 1.18, -.27),
    hip_back=(-.08, 1.04, -.12),
    knee_back=(.55, 1.45, -.11),
    foot_back=(1.39, 1.94, -.08),
    hip_front=(-.20, 1.02, .14),
    knee_front=(-.37, .57, .16),
    foot_front=(-.49, .13, .18),
)
LOW_CONTACT = pose(
    hip=(-.09, .89, 0),
    chest=(-.20, 1.34, 0),
    neck=(-.23, 1.62, 0),
    head=(-.24, 1.83, 0),
    shoulder_front=(-.16, 1.47, .22),
    elbow_front=(.10, 1.24, .27),
    hand_front=(.38, 1.49, .24),
    shoulder_back=(-.18, 1.47, -.22),
    elbow_back=(-.42, 1.22, -.22),
    hand_back=(-.10, 1.30, -.24),
    hip_back=(-.02, .89, -.12),
    knee_back=(.59, .63, -.11),
    foot_back=(1.30, .39, -.10),
    hip_front=(-.19, .88, .14),
    knee_front=(-.43, .43, .16),
    foot_front=(-.52, .13, .18),
)
CROUCH = pose(
    hip=(-.10, .61, 0),
    chest=(.05, 1.01, 0),
    neck=(.12, 1.26, 0),
    head=(.15, 1.48, 0),
    shoulder_front=(.08, 1.15, .22),
    elbow_front=(.28, .91, .26),
    hand_front=(.50, 1.19, .23),
    shoulder_back=(.08, 1.15, -.22),
    elbow_back=(-.20, .92, -.21),
    hand_back=(.06, 1.02, -.23),
    hip_front=(-.18, .61, .13),
    knee_front=(-.52, .34, .17),
    foot_front=(-.48, .13, .18),
    hip_back=(.00, .61, -.13),
    knee_back=(.45, .36, -.14),
    foot_back=(.57, .13, -.17),
)
LOW_GUARD = dict(CROUCH,
    elbow_front=(.23, .78, .27),
    hand_front=(.43, .55, .23),
    elbow_back=(-.10, .81, -.25),
    hand_back=(.27, .65, -.18),
)
SWEEP_CHAMBER = dict(CROUCH,
    hand_front=(.21, .61, .31),
    elbow_front=(.01, .84, .30),
    knee_back=(.24, .49, -.22),
    foot_back=(-.01, .21, -.32),
)
SWEEP_CONTACT = dict(CROUCH,
    hip=(-.16, .45, 0),
    hip_front=(-.26, .45, .14),
    hip_back=(-.06, .45, -.13),
    chest=(-.15, .89, .01),
    neck=(-.12, 1.16, .02),
    head=(-.10, 1.37, .03),
    shoulder_front=(-.12, 1.02, .24),
    elbow_front=(-.20, .59, .30),
    hand_front=(-.09, .20, .33),
    shoulder_back=(-.17, 1.02, -.18),
    elbow_back=(-.42, .81, -.20),
    hand_back=(-.18, .97, -.21),
    knee_back=(.68, .27, -.12),
    foot_back=(1.45, .18, -.10),
    knee_front=(-.56, .25, .19),
    foot_front=(-.80, .13, .20),
)
SPIN_CHAMBER = pose(
    chest=(-.17, 1.45, 0),
    shoulder_front=(-.14, 1.59, -.22),
    shoulder_back=(-.19, 1.59, .22),
    elbow_front=(-.43, 1.29, -.21),
    hand_front=(-.06, 1.31, -.25),
    elbow_back=(-.50, 1.35, .22),
    hand_back=(-.21, 1.61, .25),
    knee_back=(.03, 1.11, -.15),
    foot_back=(-.27, .76, -.18),
)
SPIN_CONTACT = dict(FRONT_CONTACT,
    chest=(-.53, 1.28, 0),
    neck=(-.73, 1.46, 0),
    head=(-.85, 1.64, 0),
    shoulder_front=(-.45, 1.43, .21),
    shoulder_back=(-.47, 1.42, -.21),
    elbow_front=(-.64, 1.12, .26),
    hand_front=(-.36, 1.02, .28),
    elbow_back=(-.90, 1.24, -.21),
    hand_back=(-.64, 1.47, -.24),
    knee_back=(.64, 1.28, -.10),
    foot_back=(1.56, 1.40, -.09),
)
JUMP_CHAMBER = dict(HIGH_CHAMBER,
    knee_front=(-.32, .80, .17),
    foot_front=(-.65, .66, .19),
    elbow_front=(.07, 1.64, .26),
    hand_front=(.19, 1.98, .25),
)
JUMP_CONTACT = dict(FRONT_CONTACT,
    knee_front=(-.28, .83, .17),
    foot_front=(-.66, .68, .18),
    knee_back=(.60, 1.36, -.11),
    foot_back=(1.42, 1.59, -.09),
    hand_front=(.03, 1.76, .23),
)
GUARD = pose(
    chest=(-.08, 1.47, 0),
    neck=(-.10, 1.74, 0),
    head=(-.12, 1.96, 0),
    elbow_front=(.25, 1.48, .29),
    hand_front=(.33, 1.95, .24),
    elbow_back=(.21, 1.40, -.25),
    hand_back=(.36, 1.83, -.13),
)
HURT = pose(
    hip=(-.08, .99, 0),
    chest=(-.31, 1.43, 0),
    neck=(-.42, 1.68, 0),
    head=(-.50, 1.89, 0),
    shoulder_front=(-.28, 1.58, .22),
    elbow_front=(-.15, 1.26, .28),
    hand_front=(.14, 1.45, .30),
    shoulder_back=(-.31, 1.58, -.22),
    elbow_back=(-.53, 1.25, -.24),
    hand_back=(-.23, 1.16, -.27),
)
FALLEN = pose(
    hip=(-.25, .26, 0),
    chest=(-.71, .28, 0),
    neck=(-.98, .25, 0),
    head=(-1.20, .21, 0),
    shoulder_front=(-.83, .29, .22),
    elbow_front=(-.54, .20, .42),
    hand_front=(-.24, .16, .55),
    shoulder_back=(-.83, .29, -.22),
    elbow_back=(-.56, .19, -.45),
    hand_back=(-.23, .16, -.55),
    hip_front=(-.23, .26, .13),
    knee_front=(.20, .25, .17),
    foot_front=(.67, .17, .18),
    hip_back=(-.23, .26, -.13),
    knee_back=(.13, .48, -.20),
    foot_back=(.57, .17, -.21),
)
VICTORY = pose(
    elbow_front=(-.20, 1.91, .27),
    hand_front=(.05, 2.28, .25),
    elbow_back=(-.20, 1.91, -.26),
    hand_back=(.05, 2.28, -.25),
    knee_front=(-.20, .56, .16),
    foot_front=(-.29, .13, .18),
    knee_back=(.25, .56, -.14),
    foot_back=(.34, .13, -.17),
)

ROUND_CHAMBER = dict(HIGH_CHAMBER,
    hip_back=(-.07, 1.03, -.12),
    knee_back=(.28, 1.28, -.49),
    foot_back=(-.23, 1.07, -.62),
    chest=(-.22, 1.45, .05),
    shoulder_front=(-.11, 1.61, .24),
    shoulder_back=(-.31, 1.56, -.14),
)
ROUND_CONTACT = dict(FRONT_CONTACT,
    hip=(-.10, 1.03, .03),
    hip_back=(-.03, 1.04, -.08),
    knee_back=(.66, 1.27, .10),
    foot_back=(1.46, 1.44, .25),
    chest=(-.34, 1.46, .05),
    shoulder_front=(-.20, 1.60, .17),
    shoulder_back=(-.42, 1.57, -.17),
    elbow_front=(-.03, 1.35, .23),
    hand_front=(.17, 1.66, .20),
    elbow_back=(-.73, 1.33, -.18),
    hand_back=(-.57, 1.12, -.21),
)
ROUND_FOLLOW = dict(ROUND_CONTACT,
    foot_back=(1.36, 1.42, .57),
    knee_back=(.59, 1.26, .26),
    chest=(-.31, 1.45, .10),
    shoulder_front=(-.18, 1.59, .10),
    shoulder_back=(-.40, 1.58, -.12),
    hand_front=(.12, 1.69, .14),
    hand_back=(-.62, 1.14, -.08),
)

NUNCHAKU_CHAMBER = pose(
    hand_front=(.13, 1.86, .26),
    elbow_front=(.02, 1.45, .28),
    hand_back=(.17, 1.70, -.19),
    chest=(-.09, 1.49, -.02),
)
NUNCHAKU_CONTACT = dict(JAB_CONTACT,
    hand_front=(1.02, 1.70, .17),
    elbow_front=(.59, 1.58, .18),
    hand_back=(.07, 1.65, -.19),
)
NUNCHAKU_OVERHEAD_CHAMBER = pose(
    hip=(-.08, 1.00, 0), chest=(-.16, 1.47, 0),
    shoulder_front=(-.10, 1.62, .22), elbow_front=(.04, 1.93, .25),
    hand_front=(.30, 2.13, .21), hand_back=(.26, 1.68, -.19),
)
NUNCHAKU_OVERHEAD_CONTACT = pose(
    hip=(.10, .98, 0), chest=(.19, 1.43, 0), head=(.24, 1.94, 0),
    shoulder_front=(.22, 1.59, .18), elbow_front=(.61, 1.73, .17),
    hand_front=(.92, 1.91, .14), hand_back=(.10, 1.54, -.22),
)
NUNCHAKU_LOW_CHAMBER = dict(CROUCH,
    hip=(-.06, .76, 0), chest=(-.14, 1.19, 0), neck=(-.15, 1.47, 0), head=(-.14, 1.69, 0),
    shoulder_front=(-.10, 1.34, .23), elbow_front=(-.20, 1.12, .28),
    hand_front=(.10, 1.07, .27), hand_back=(.26, 1.37, -.20),
)
NUNCHAKU_LOW_CONTACT = dict(CROUCH,
    hip=(.04, .72, 0), chest=(.18, 1.12, 0), neck=(.23, 1.39, 0), head=(.25, 1.61, 0),
    shoulder_front=(.20, 1.27, .20), elbow_front=(.59, 1.05, .19),
    hand_front=(.98, .83, .16), hand_back=(.09, 1.29, -.23),
)
NUNCHAKU_FLOURISH = pose(
    chest=(-.04, 1.48, 0), shoulder_front=(.02, 1.63, .22),
    elbow_front=(.31, 1.43, .27), hand_front=(.51, 1.60, .24),
    hand_back=(.24, 1.72, -.18),
)
STAR_CHAMBER = pose(
    hand_front=(-.04, 1.88, .29),
    elbow_front=(-.25, 1.54, .32),
    hand_back=(.14, 1.63, -.20),
    chest=(-.09, 1.45, -.03),
)
STAR_RELEASE = dict(JAB_CONTACT,
    hand_front=(.68, 1.65, .24),
    elbow_front=(.32, 1.55, .25),
    hand_back=(.16, 1.64, -.22),
)
SUMO_STANCE = pose(
    hip=(0, .80, 0), chest=(.06, 1.24, 0), neck=(.10, 1.53, 0), head=(.12, 1.76, 0),
    hip_front=(-.16, .80, .22), hip_back=(.16, .80, -.22),
    shoulder_front=(.03, 1.42, .30), shoulder_back=(.03, 1.42, -.30),
    elbow_front=(.31, 1.12, .34), elbow_back=(-.13, 1.10, -.32),
    hand_front=(.56, 1.40, .30), hand_back=(.30, 1.30, -.30),
    knee_front=(-.43, .41, .24), foot_front=(-.60, .13, .26),
    knee_back=(.43, .41, -.24), foot_back=(.61, .13, -.26),
)
SUMO_PALM_WINDUP = dict(SUMO_STANCE,
    hand_front=(.13, 1.12, .34), elbow_front=(-.15, 1.17, .34),
    hand_back=(.30, 1.54, -.22),
)
SUMO_PALM_CONTACT = dict(SUMO_STANCE,
    hand_front=(1.03, 1.31, .24), elbow_front=(.58, 1.22, .25),
    chest=(.13, 1.23, 0), head=(.23, 1.76, 0),
)
SUMO_STOMP_WINDUP = dict(SUMO_STANCE,
    knee_back=(.35, 1.17, -.30), foot_back=(.55, .84, -.34),
    hand_front=(.23, 1.64, .38), hand_back=(.09, 1.54, -.38),
)
SUMO_STOMP_CONTACT = dict(SUMO_STANCE,
    hip=(.03, .67, 0), chest=(.13, 1.10, 0), neck=(.20, 1.38, 0), head=(.23, 1.61, 0),
    knee_back=(.62, .39, -.22), foot_back=(1.03, .13, -.22),
    shoulder_front=(.16, 1.28, .30), shoulder_back=(.10, 1.28, -.30),
    hand_front=(.50, .98, .30), hand_back=(.28, .95, -.30),
)
SUMO_CHARGE_WINDUP = dict(SUMO_STANCE,
    chest=(.29, 1.13, 0), neck=(.46, 1.36, 0), head=(.59, 1.52, 0),
    hand_front=(.62, 1.27, .31), hand_back=(.56, 1.22, -.30),
)
SUMO_CHARGE_CONTACT = dict(SUMO_CHARGE_WINDUP,
    hand_front=(1.05, 1.22, .28), hand_back=(.95, 1.21, -.28),
    elbow_front=(.70, 1.09, .29), elbow_back=(.62, 1.03, -.29),
)

CROUCH_PUNCH_WINDUP = dict(CROUCH,
    elbow_front=(.03, .84, .30),
    hand_front=(.21, 1.05, .26),
    hand_back=(.29, 1.25, -.22),
)
CROUCH_PUNCH_CONTACT = dict(CROUCH,
    chest=(.13, 1.01, .03),
    neck=(.21, 1.27, .02),
    head=(.24, 1.48, .01),
    shoulder_front=(.19, 1.14, .18),
    elbow_front=(.61, 1.08, .16),
    hand_front=(1.04, 1.02, .14),
    hand_back=(.05, 1.00, -.25),
)

CLIPS = {
    'nunchaku': (NUNCHAKU_CHAMBER, NUNCHAKU_CONTACT),
    'nunchaku_overhead': (NUNCHAKU_OVERHEAD_CHAMBER, NUNCHAKU_OVERHEAD_CONTACT),
    'nunchaku_low': (NUNCHAKU_LOW_CHAMBER, NUNCHAKU_LOW_CONTACT),
    'shuriken': (STAR_CHAMBER, STAR_RELEASE),
    'sumo_palm': (SUMO_PALM_WINDUP, SUMO_PALM_CONTACT),
    'sumo_stomp': (SUMO_STOMP_WINDUP, SUMO_STOMP_CONTACT),
    'sumo_charge': (SUMO_CHARGE_WINDUP, SUMO_CHARGE_CONTACT),
    'crouch_punch': (CROUCH_PUNCH_WINDUP, CROUCH_PUNCH_CONTACT),
    'round_kick': (ROUND_CHAMBER, ROUND_CONTACT),
    'jab': (JAB_WINDUP, JAB_CONTACT),
    'cross': (CROSS_WINDUP, CROSS_CONTACT),
    'front_kick': (KICK_CHAMBER, FRONT_CONTACT),
    'high_kick': (HIGH_CHAMBER, HIGH_CONTACT),
    'low_kick': (KICK_CHAMBER, LOW_CONTACT),
    'sweep': (SWEEP_CHAMBER, SWEEP_CONTACT),
    'spin_kick': (SPIN_CHAMBER, SPIN_CONTACT),
    'jump_kick': (JUMP_CHAMBER, JUMP_CONTACT),
}


def circular_leg(pose_result, first, second, amount):
    """Rotate the bent leg around the hip instead of sliding it in a line."""
    amount = clamp(amount, 0, 1)
    amount = amount * amount * (3 - 2 * amount)
    result = dict(pose_result)
    pivot = result['hip_back']
    for joint in ('knee_back', 'foot_back'):
        start = tuple(first[joint][i] - first['hip_back'][i] for i in range(3))
        end = tuple(second[joint][i] - second['hip_back'][i] for i in range(3))
        angle_start = math.atan2(start[2], start[0])
        angle_end = math.atan2(end[2], end[0])
        difference = (angle_end - angle_start + math.pi) % math.tau - math.pi
        angle = angle_start + difference * amount
        radius_start = math.hypot(start[0], start[2])
        radius_end = math.hypot(end[0], end[2])
        radius = lerp(radius_start, radius_end, amount)
        result[joint] = (
            pivot[0] + math.cos(angle) * radius,
            pivot[1] + lerp(start[1], end[1], amount),
            pivot[2] + math.sin(angle) * radius,
        )
    return result


def sample(fighter, clock):
    stance = SUMO_STANCE if fighter.archetype == 'sumo' else BASE
    if fighter.attacking:
        windup, contact = CLIPS[fighter.move_key]
        move = fighter.move
        elapsed = fighter.elapsed
        rest = CROUCH if fighter.crouch else stance
        if elapsed < move.startup * .55:
            result = blend(rest, windup, elapsed / (move.startup * .55))
        elif elapsed < move.startup:
            swing = (elapsed - move.startup * .55) / (move.startup * .45)
            result = blend(windup, contact, swing)
            if fighter.move_key in ('round_kick', 'sweep'):
                result = circular_leg(result, windup, contact, swing)
        elif elapsed < move.startup + move.active:
            result = contact
            if fighter.move_key == 'round_kick':
                follow = (elapsed - move.startup) / move.active
                result = circular_leg(blend(contact, ROUND_FOLLOW, follow), contact, ROUND_FOLLOW, follow)
        else:
            recovery = (elapsed - move.startup - move.active) / move.recovery
            if fighter.move_key == 'round_kick':
                if recovery < .48:
                    amount = recovery / .48
                    result = circular_leg(blend(ROUND_FOLLOW, windup, amount), ROUND_FOLLOW, windup, amount)
                else:
                    result = blend(windup, rest, (recovery - .48) / .52)
            else:
                result = blend(contact, rest, recovery)
    elif fighter.state == 'flourish':
        # A showy figure-eight: the wrist leads while the body stays ready.
        wave = math.sin(fighter.elapsed * math.tau * 2.6)
        amount = min(1.0, fighter.elapsed / .18, (1.15 - fighter.elapsed) / .18)
        result = blend(BASE, NUNCHAKU_FLOURISH, amount)
        hand = result['hand_front']
        result['hand_front'] = (hand[0] + wave * .08, hand[1] + math.cos(fighter.elapsed * math.tau * 2.6) * .06, hand[2])
    elif fighter.state == 'roll':
        # A tucked forward somersault: rotate all joints together around the
        # body's centre so the head, hips and bent legs visibly turn over.
        tucked = dict(CROUCH,
            hip=(0, .62, 0), hip_front=(0, .62, .13), hip_back=(0, .62, -.13),
            chest=(.25, .75, 0), neck=(.36, .77, 0), head=(.38, .70, 0),
            shoulder_front=(.29, .80, .22), shoulder_back=(.29, .80, -.22),
            elbow_front=(.47, .49, .24), elbow_back=(.47, .49, -.24),
            hand_front=(.32, .28, .19), hand_back=(.32, .28, -.19),
            knee_front=(.25, .24, .16), knee_back=(.25, .24, -.16),
            foot_front=(-.20, .18, .18), foot_back=(-.20, .18, -.18))
        if fighter.elapsed < .12:
            result = blend(BASE, tucked, fighter.elapsed / .12)
        elif fighter.elapsed < .64:
            turn = (fighter.elapsed - .12) / .52 * math.tau * fighter.roll_direction
            cosine, sine = math.cos(turn), math.sin(turn)
            result = {name: (x * cosine + (y - .55) * sine,
                             .55 - x * sine + (y - .55) * cosine, z)
                      for name, (x, y, z) in tucked.items()}
        else:
            result = blend(tucked, BASE, (fighter.elapsed - .64) / .16)
    elif fighter.state == 'knockdown':
        result = blend(HURT, FALLEN, fighter.elapsed / .30)
        if fighter.health > 0 and fighter.elapsed > .65:
            result = blend(FALLEN, BASE, (fighter.elapsed - .65) / .35)
    elif fighter.state == 'hurt':
        result = blend(HURT, BASE, fighter.elapsed / .34)
    elif fighter.state == 'win':
        result = blend(BASE, VICTORY, fighter.elapsed / .4)
    elif fighter.state == 'crouch':
        result = CROUCH
    elif fighter.state == 'guard':
        result = LOW_GUARD if fighter.crouch else GUARD
    elif fighter.state == 'dodge':
        result = HURT
    elif fighter.state == 'jump':
        result = JUMP_CHAMBER
    else:
        result = dict(stance)
        breath = math.sin(clock * 3.2) * .014
        for joint in ('chest', 'neck', 'head', 'hand_front', 'hand_back'):
            x, y, z = result[joint]
            result[joint] = (x, y + breath, z)
        if fighter.state == 'walk':
            stride = math.sin(fighter.walk_phase) * .19
            for joint, sign in [('foot_front', 1), ('foot_back', -1),
                                ('knee_front', .5), ('knee_back', -.5)]:
                x, y, z = result[joint]
                result[joint] = (x + stride * sign, y + max(0, stride * sign) * .35, z)
    return result
