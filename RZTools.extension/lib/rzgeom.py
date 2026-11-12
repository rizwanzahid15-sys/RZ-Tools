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


# ----------------------------------------------------------------- plan

def _plan_dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def nearest_end(p0, p1, pick):
    """0 if p0 is nearer the picked point in plan, else 1."""
    return 0 if _plan_dist(p0, pick) <= _plan_dist(p1, pick) else 1


def _plan_unit(d):
    length = math.hypot(d[0], d[1])
    if length < 1e-12:
        raise ValueError("direction has no plan component")
    return (d[0] / length, d[1] / length)


def group_by_direction(dirs, tol_deg=5.0):
    """Group directions that are parallel in plan (d and -d are the same).

    Returns lists of indices, ordered by each group's first index.
    """
    groups = []   # each: [reference unit, [indices]]
    limit = math.cos(math.radians(tol_deg))
    for i, d in enumerate(dirs):
        u = _plan_unit(d)
        for ref, members in groups:
            if abs(ref[0] * u[0] + ref[1] * u[1]) >= limit:
                members.append(i)
                break
        else:
            groups.append([u, [i]])
    return [members for _ref, members in groups]


def plan_intersection(a0, a1, b0, b1):
    """Where segments a and b cross in plan, as (t, u) params 0-1.

    None if they are parallel or do not cross inside both segments.
    """
    rx, ry = a1[0] - a0[0], a1[1] - a0[1]
    sx, sy = b1[0] - b0[0], b1[1] - b0[1]
    denom = rx * sy - ry * sx
    if abs(denom) < 1e-12:
        return None
    qx, qy = b0[0] - a0[0], b0[1] - a0[1]
    t = (qx * sy - qy * sx) / denom
    u = (qx * ry - qy * rx) / denom
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return (t, u)
    return None


def crossing_sin(da, db):
    """|sin| of the plan angle between two directions."""
    ua, ub = _plan_unit(da), _plan_unit(db)
    return abs(ua[0] * ub[1] - ua[1] * ub[0])


# ------------------------------------------------------------ pull boxes

def plan_pull_boxes(run, max_dist, max_bends, after_bend, start_bends=0,
                    end_margin=0.0):
    """Decide where pull boxes go along a traced conduit run.

    run: list of {"kind": "straight"|"bend"|"fitting"|"box"|"branch",
                  "length": float, "vertical": bool}
    Returns [(segment_index, distance_along_segment)] - boxes only ever
    land on horizontal straight segments.

    Rules: a box is owed when the distance since the last box reaches
    max_dist, or when the bend count reaches max_bends. A box owed by
    bends (or owed while on a vertical riser) is placed after_bend into
    the next horizontal straight (mid-length if that straight is shorter
    than 2 * after_bend). An existing box resets both counters. A branch
    ends the walk.

    Every box is kept at least end_margin from both ends of its straight
    (so it never lands on a joint or off the conduit); a straight shorter
    than 2 * end_margin gets its box at mid-length. A run that ends exactly
    on a spacing mark gets no box at its very end.
    """
    def fit(at, length):
        if length < 2 * end_margin:
            return length / 2.0
        return min(max(at, end_margin), length - end_margin)

    boxes = []
    dist = 0.0
    bends = start_bends
    pending = False
    for i, seg in enumerate(run):
        kind = seg["kind"]
        length = float(seg.get("length", 0.0))
        if kind == "branch":
            break
        if kind == "box":
            dist, bends, pending = 0.0, 0, False
            continue
        if kind == "bend":
            dist += length
            bends += 1
            if bends >= max_bends:
                pending = True
            continue
        if kind != "straight":
            dist += length
            continue
        if seg.get("vertical"):
            dist += length
            if dist >= max_dist:
                pending = True
            continue
        pos = 0.0
        if pending:
            at = after_bend if length >= 2 * after_bend else length / 2.0
            at = fit(at, length)
            boxes.append((i, at))
            pos, dist, bends, pending = at, 0.0, 0, False
        while dist + (length - pos) > max_dist:
            at = fit(pos + (max_dist - dist), length)
            if at <= pos and boxes and boxes[-1][0] == i:
                break
            boxes.append((i, at))
            pos, dist, bends = at, 0.0, 0
        dist += length - pos
    return boxes


# ------------------------------------------------------ crossing offsets

def required_rise(mover_z, mover_r, others, clearance, up):
    """Vertical move that puts the mover clearance clear of every other.

    others: [(centre_z, outer_radius)]. Positive = up, negative = down.
    0.0 when the mover is already clear in the chosen direction.
    """
    if up:
        top = max(z + r for z, r in others)
        rise = top + clearance + mover_r - mover_z
        return rise if rise > 0 else 0.0
    bottom = min(z - r for z, r in others)
    rise = bottom - clearance - mover_r - mover_z
    return rise if rise < 0 else 0.0


def slope_run(rise, angle_deg):
    """Horizontal length of one slope that climbs |rise| at angle_deg."""
    return abs(rise) / math.tan(math.radians(angle_deg))


def offset_spans(length, crossings, run, end_clear):
    """Spans along the mover that must be offset, merged where they overlap.

    crossings: [(distance_along_mover, half_width_along_mover)].
    Each span (s0, e0) covers slope + flat part + slope. Raises
    ValueError when a span would come closer than end_clear to either end.
    """
    raw = sorted((c - hw - run, c + hw + run) for c, hw in crossings)
    merged = []
    for s0, e0 in raw:
        if merged and s0 <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e0))
        else:
            merged.append((s0, e0))
    for s0, e0 in merged:
        if s0 < end_clear or e0 > length - end_clear:
            raise ValueError("too close to end")
    return merged


def dogleg_polyline(p0, p1, spans, rise, run):
    """Centreline points of the offset conduit: p0, A, B, C, D, ..., p1."""
    pts = [p0]
    up = (0.0, 0.0, rise)
    for s0, e0 in spans:
        pts.append(point_along(p0, p1, s0))
        pts.append(vadd(point_along(p0, p1, s0 + run), up))
        pts.append(vadd(point_along(p0, p1, e0 - run), up))
        pts.append(point_along(p0, p1, e0))
    pts.append(p1)
    return pts


# ------------------------------------------- junction box / connect / convert

def project_distance(p0, p1, point):
    """Distance from p0 along p0->p1 of point's projection, clamped."""
    d = vsub(p1, p0)
    length = vlen(d)
    along = vdot(vsub(point, p0), vnorm(d))
    return max(0.0, min(length, along))


def snap_end(length, dist, snap):
    """0 / 1 when dist is within snap of the start / end, else None."""
    if dist <= snap:
        return 0
    if dist >= length - snap:
        return 1
    return None


def joint_pairs(segments, tol):
    """Ends of different segments that touch (within tol).

    segments: [(p0, p1)]. Returns [(i, end_i, j, end_j)] with i < j;
    each end joins at most one other end.
    """
    used = set()
    pairs = []
    for i in range(len(segments)):
        for ei in (0, 1):
            if (i, ei) in used:
                continue
            for j in range(i + 1, len(segments)):
                match = None
                for ej in (0, 1):
                    if (j, ej) in used:
                        continue
                    if vlen(vsub(segments[i][ei], segments[j][ej])) <= tol:
                        match = ej
                        break
                if match is not None:
                    used.add((i, ei))
                    used.add((j, match))
                    pairs.append((i, ei, j, match))
                    break
    return pairs


def joint_kind(dir_a, dir_b, tol_deg=1.0):
    """"union" for a straight continuation, else "elbow"."""
    ua, ub = _plan_unit(dir_a), _plan_unit(dir_b)
    if abs(ua[0] * ub[0] + ua[1] * ub[1]) >= math.cos(math.radians(tol_deg)):
        return "union"
    return "elbow"


def line_intersection_xy(a0, a1, b0, b1):
    """Plan intersection of the two infinite lines (z from a0); None if parallel."""
    rx, ry = a1[0] - a0[0], a1[1] - a0[1]
    sx, sy = b1[0] - b0[0], b1[1] - b0[1]
    denom = rx * sy - ry * sx
    if abs(denom) < 1e-12:
        return None
    qx, qy = b0[0] - a0[0], b0[1] - a0[1]
    t = (qx * sy - qy * sx) / denom
    return (a0[0] + t * rx, a0[1] + t * ry, a0[2])


def route_points(end, target, target_facing):
    """Conduit path from a conduit end to a device connector.

    Same height -> straight. Connector facing up/down -> across first,
    then drop/rise into it. Connector facing sideways -> rise/drop first,
    then across into it.
    """
    if abs(target[2] - end[2]) < 1e-3:
        return [end, target]
    if abs(vnorm(target_facing)[2]) > 0.7:
        return [end, (target[0], target[1], end[2]), target]
    return [end, (end[0], end[1], target[2]), target]
