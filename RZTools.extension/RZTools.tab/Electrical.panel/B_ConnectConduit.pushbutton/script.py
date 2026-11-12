# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Connect Conduit
# Purpose        : Connect a conduit end to another conduit (coupling or
#                  elbow) or route it into a device / box connector.
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Created Date   : 2026-11-12
# Updated Date   : 2026-11-12
# Status         : Production
#
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7
#
# Category       : BIM Automation
# Discipline     : Electrical
# Tool Type      : pyRevit Tool
#
# Input          : Click a conduit near the end to connect, then click the
#                  target conduit or device.
# Output         : Conduits extended/trimmed and joined with a coupling or
#                  elbow, or new conduit legs into the device connector.
#
# Dependencies   :
#   - pyRevit, Revit API
#   - RZTools.extension/lib/rzgeom.py, rzconduit.py
#
# Features       :
#   - In-line conduits -> coupling; crossing directions -> elbow
#   - Device -> across then down (top/bottom connector) or down then
#     across (side connector)
#   - Nothing changes if the case is not supported; one undo step
#
# Changelog
# ------------------------------------------------------------
# v1.0.0
# - Initial Release
#
# License        : Proprietary
# Copyright      : (c) Rizwan Zahid. All Rights Reserved
# ============================================================

import traceback

from pyrevit import revit, forms, script
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException

import rzgeom
import rzconduit

TITLE = "RZ Tools - Connect Conduit"
TOL_MM = 5.0

doc = revit.doc
uidoc = revit.uidoc
tup = rzconduit.tup
xyz = rzconduit.xyz


def set_end(conduit, index, point):
    p0, p1 = rzconduit.ends(conduit)
    if index == 0:
        rzconduit.set_ends(conduit, point, p1)
    else:
        rzconduit.set_ends(conduit, p0, point)


def end_index(conduit, point):
    p0, p1 = rzconduit.ends(conduit)
    return 0 if p0.DistanceTo(point) <= p1.DistanceTo(point) else 1


def check_free(conduit, index):
    point = rzconduit.ends(conduit)[index]
    if rzconduit.end_connector(conduit, point).IsConnected:
        raise ValueError("conduit {} is already connected at that end".format(conduit.Id))


def connect_conduits(a, ia, b):
    tol = rzgeom.mm_to_ft(TOL_MM)
    a0, a1 = [tup(p) for p in rzconduit.ends(a)]
    b0, b1 = [tup(p) for p in rzconduit.ends(b)]
    a_end, a_other = (a0, a1) if ia == 0 else (a1, a0)
    ib = end_index(b, xyz(a_end))
    check_free(a, ia)
    check_free(b, ib)
    da, db = rzgeom.vsub(a1, a0), rzgeom.vsub(b1, b0)
    if rzgeom.is_vertical(da) or rzgeom.is_vertical(db):
        raise ValueError("vertical conduits are not supported")
    if abs(a0[2] - a1[2]) > tol or abs(b0[2] - b1[2]) > tol or abs(a_end[2] - b0[2]) > tol:
        raise ValueError("the conduits are not level at the same height")

    if rzgeom.joint_kind(da, db) == "union":
        b_near = (b0, b1)[ib]
        flat = lambda p: (p[0], p[1], 0.0)
        d = rzgeom.project_distance(flat(a_other), flat(a_end), flat(b_near))
        foot = rzgeom.point_along(flat(a_other), flat(a_end), d)
        if rzgeom.vlen(rzgeom.vsub(foot, flat(b_near))) > tol:
            raise ValueError("these conduits are parallel but not in line")
        set_end(a, ia, xyz(b_near))
        doc.Regenerate()
        if rzconduit.connect_union(doc, a, b) is None:
            raise ValueError("Revit could not add a coupling")
        return "coupling"

    corner = rzgeom.line_intersection_xy(a0, a1, b0, b1)
    corner = (corner[0], corner[1], a_end[2])
    if rzgeom.vdot(rzgeom.vsub(corner, a_other), rzgeom.vsub(a_end, a_other)) <= 0:
        raise ValueError("the conduits point away from each other")
    set_end(a, ia, xyz(corner))
    set_end(b, ib, xyz(corner))
    doc.Regenerate()
    if rzconduit.connect_elbow(doc, a, b) is None:
        raise ValueError("Revit could not add an elbow (check bend radius / lengths)")
    return "elbow"


def _dedupe(points):
    tol = rzgeom.mm_to_ft(1.0)
    out = [points[0]]
    for p in points[1:]:
        if rzgeom.vlen(rzgeom.vsub(p, out[-1])) > tol:
            out.append(p)
    return out


def connect_device(a, ia, target):
    check_free(a, ia)
    end = rzconduit.ends(a)[ia]
    other = rzconduit.ends(a)[1 - ia]
    conn = rzconduit.free_conduit_connector(target, end)
    if conn is None:
        raise ValueError("that element has no free conduit connector")
    points = _dedupe(rzgeom.route_points(
        tup(end), tup(conn.Origin), tup(conn.CoordinateSystem.BasisZ)))
    if len(points) < 2:
        raise ValueError("the conduit already ends at the connector")

    prev = a
    out_dir = rzgeom.vsub(tup(end), tup(other))
    first_leg = rzgeom.vsub(points[1], points[0])
    if rzgeom.angle_between_deg(out_dir, first_leg) < 1.0:
        set_end(a, ia, xyz(points[1]))      # just extend the conduit
        points = points[1:]
    for p, q in zip(points, points[1:]):
        leg = rzconduit.new_conduit_like(doc, a, xyz(p), xyz(q))
        doc.Regenerate()
        if rzconduit.connect_elbow(doc, prev, leg) is None:
            raise ValueError("Revit could not add an elbow on the route")
        prev = leg
    doc.Regenerate()
    rzconduit.end_connector(prev, conn.Origin).ConnectTo(conn)
    return "route"


def main():
    if doc is None:
        forms.alert("Please open a Revit project first.", title=TITLE)
        return
    try:
        ref_a = uidoc.Selection.PickObject(
            ObjectType.Element, rzconduit.ConduitFilter(),
            "Click the conduit near the end you want to connect")
        ref_b = uidoc.Selection.PickObject(
            ObjectType.Element, "Click the conduit or device to connect to")
    except OperationCanceledException:
        return
    a = doc.GetElement(ref_a.ElementId)
    target = doc.GetElement(ref_b.ElementId)
    if target.Id == a.Id:
        forms.alert("Pick a different element to connect to.", title=TITLE)
        return
    ia = end_index(a, ref_a.GlobalPoint)

    try:
        with revit.TransactionGroup("RZTools: Connect Conduit"):
            with revit.Transaction("RZTools: Connect Conduit"):
                if rzconduit.is_conduit(target):
                    result = rzconduit.all_or_nothing(
                        doc, lambda: connect_conduits(a, ia, target))
                else:
                    result = rzconduit.all_or_nothing(
                        doc, lambda: connect_device(a, ia, target))
    except ValueError as reason:
        forms.alert(u"Not connected: {}.\nNothing was changed.".format(reason), title=TITLE)
        return
    done = {"coupling": "Connected with a coupling.",
            "elbow": "Connected with an elbow.",
            "route": "Routed the conduit into the connector."}[result]
    forms.alert(done, title=TITLE)


try:
    main()
except Exception:
    output = script.get_output()
    output.print_md("**RZ Tools - Connect Conduit stopped. Nothing was changed.**")
    output.print_code(traceback.format_exc())
