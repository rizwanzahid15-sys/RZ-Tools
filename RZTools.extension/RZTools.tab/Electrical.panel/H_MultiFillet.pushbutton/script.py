# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Multi Fillet
# Purpose        : Join two groups of parallel conduits that meet at a
#                  corner with elbows in one go, inner with inner, with
#                  bend radii growing outward so the bends are concentric.
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
# Input          : First group of parallel conduits (Finish), then the
#                  second group (Finish). Same number in each.
# Output         : Conduits trimmed/extended to their corners and joined
#                  with elbows.
#
# Dependencies   :
#   - pyRevit, Revit API
#   - RZTools.extension/lib/rzgeom.py, rzconduit.py
#
# Features       :
#   - Pairs inner-with-inner whatever order you picked them in
#   - Sets "Bend Radius" when the elbow family allows it
#   - Each pair all-or-nothing; one undo step
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

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException

import rzgeom
import rzconduit

TITLE = "RZ Tools - Multi Fillet"
RADIUS_PARAM = "Bend Radius"

doc = revit.doc
uidoc = revit.uidoc
tup = rzconduit.tup
xyz = rzconduit.xyz


def pick_group(prompt):
    refs = uidoc.Selection.PickObjects(ObjectType.Element, rzconduit.ConduitFilter(), prompt)
    conduits = [doc.GetElement(r.ElementId) for r in refs]
    return [c for c in conduits if isinstance(c.Location.Curve, DB.Line)]


def as_lines(conduits):
    return [tuple(tup(p) for p in rzconduit.ends(c)) for c in conduits]


def fillet_pair(a, b):
    """Trim/extend a and b to their plan corner and join with an elbow."""
    la, lb = as_lines([a])[0], as_lines([b])[0]
    corner = rzgeom.line_intersection_xy(la[0], la[1], lb[0], lb[1])
    tol = rzgeom.mm_to_ft(5)
    for line, c in ((la, a), (lb, b)):
        if rzgeom.is_vertical(rzgeom.vsub(line[1], line[0])) or abs(line[0][2] - line[1][2]) > tol:
            raise ValueError("conduit {} is not level".format(c.Id))
    if abs(la[0][2] - lb[0][2]) > tol:
        raise ValueError("conduits {} and {} are at different heights".format(a.Id, b.Id))
    corner = (corner[0], corner[1], la[0][2])
    for line, c in ((la, a), (lb, b)):
        p0, p1 = line
        near_is_0 = rzgeom.vlen(rzgeom.vsub(p0, corner)) <= rzgeom.vlen(rzgeom.vsub(p1, corner))
        if rzconduit.end_connector(c, xyz(p0 if near_is_0 else p1)).IsConnected:
            raise ValueError("conduit {} is already connected at the corner end".format(c.Id))
        if near_is_0:
            rzconduit.set_ends(c, xyz(corner), xyz(p1))
        else:
            rzconduit.set_ends(c, xyz(p0), xyz(corner))
    doc.Regenerate()
    elbow = rzconduit.connect_elbow(doc, a, b)
    if elbow is None:
        raise ValueError("Revit could not add an elbow between {} and {}".format(a.Id, b.Id))
    return elbow


def set_radius(elbow, radius):
    param = elbow.LookupParameter(RADIUS_PARAM)
    if param is None or param.IsReadOnly:
        return False
    param.Set(radius)
    return True


def main():
    if doc is None:
        forms.alert("Please open a Revit project first.", title=TITLE)
        return
    try:
        group_a = pick_group("Select the FIRST group of parallel conduits, then Finish")
        group_b = pick_group("Select the SECOND group of parallel conduits, then Finish")
    except OperationCanceledException:
        return
    if not group_a or len(group_a) != len(group_b):
        forms.alert("Select the same number of straight conduits in each group "
                    "({} and {} selected).".format(len(group_a), len(group_b)), title=TITLE)
        return
    lines_a, lines_b = as_lines(group_a), as_lines(group_b)
    if (len(rzgeom.group_by_direction([rzgeom.vsub(l[1], l[0]) for l in lines_a])) != 1
            or len(rzgeom.group_by_direction([rzgeom.vsub(l[1], l[0]) for l in lines_b])) != 1):
        forms.alert("Each group must be conduits running in the same direction.", title=TITLE)
        return
    try:
        pairs = rzgeom.pair_bundles(lines_a, lines_b)
    except ValueError:
        forms.alert("The two groups run in the same direction - they don't meet at a corner.",
                    title=TITLE)
        return
    spacing = rzgeom.bundle_spacing(lines_a)

    made, skipped = 0, []
    radius_note = False
    inner_radius = None
    with revit.TransactionGroup("RZTools: Multi Fillet"):
        with revit.Transaction("RZTools: Multi Fillet"):
            for k, (ia, ib) in enumerate(pairs):
                a, b = group_a[ia], group_b[ib]
                try:
                    elbow = rzconduit.all_or_nothing(doc, lambda: fillet_pair(a, b))
                except Exception as ex:
                    skipped.append(u"{} / {}: {}".format(a.Id, b.Id, ex))
                    continue
                made += 1
                param = elbow.LookupParameter(RADIUS_PARAM)
                if inner_radius is None and param is not None:
                    inner_radius = param.AsDouble()
                if inner_radius is not None and k > 0:
                    try:
                        if not rzconduit.all_or_nothing(
                                doc, lambda: set_radius(elbow, inner_radius + k * spacing)):
                            radius_note = True
                    except Exception:
                        radius_note = True

    lines = [u"Joined {} pair(s) of conduits with elbows.".format(made)]
    if radius_note:
        lines.append(u"The bend radius is set by the elbow family, so the bends may "
                     u"not be perfectly concentric.")
    if skipped:
        lines.append(u"Skipped:\n" + u"\n".join(skipped))
    forms.alert(u"\n".join(lines), title=TITLE)


try:
    main()
except Exception:
    output = script.get_output()
    output.print_md("**RZ Tools - Multi Fillet stopped. Nothing was changed.**")
    output.print_code(traceback.format_exc())
