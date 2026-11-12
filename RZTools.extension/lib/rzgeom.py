# ============================================================
# Shared Library
# ============================================================
# Module Name    : rzgeom
# Purpose        : Revit-free geometry and planning maths for the RZ Tools
#                  electrical tools (pull boxes, conduit crossings).
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Created Date   : 2026-11-12
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7 / CPython 3 (no Revit imports)
# ============================================================
"""Pure maths helpers. Points and vectors are (x, y, z) tuples.

Nothing here imports Revit, so every function is unit-tested offline
with pytest (see tests/). Units are whatever the caller passes in;
the Revit tools pass feet.
"""

import math

MM_PER_FT = 304.8


# ---------------------------------------------------------------- units

def mm_to_ft(mm):
    return mm / MM_PER_FT


def ft_to_mm(ft):
    return ft * MM_PER_FT


def m_to_ft(m):
    return m * 1000.0 / MM_PER_FT


# -------------------------------------------------------------- vectors

def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vscale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vlen(a):
    return math.sqrt(vdot(a, a))


def vnorm(a):
    length = vlen(a)
    if length < 1e-12:
        raise ValueError("zero-length vector")
    return vscale(a, 1.0 / length)


def angle_between_deg(d1, d2):
    """Angle between two directions, 0-180 degrees."""
    c = vdot(vnorm(d1), vnorm(d2))
    c = max(-1.0, min(1.0, c))
    return math.degrees(math.acos(c))


def bend_angle_deg(out_a, out_b):
    """Bend made by a fitting, from its two outward connector directions.

    A straight coupling has opposite outward directions -> 0.
    A 90 degree elbow has perpendicular outward directions -> 90.
    """
    return 180.0 - angle_between_deg(out_a, out_b)


def is_bend(angle_deg, lo=80.0, hi=100.0):
    return lo <= angle_deg <= hi


def is_vertical(direction, max_deg=45.0):
    """True when the direction is more than max_deg away from horizontal."""
    d = vnorm(direction)
    from_horizontal = math.degrees(math.asin(min(1.0, abs(d[2]))))
    return from_horizontal > max_deg


def point_along(p0, p1, dist):
    """Point at dist from p0, toward p1."""
    return vadd(p0, vscale(vnorm(vsub(p1, p0)), dist))
