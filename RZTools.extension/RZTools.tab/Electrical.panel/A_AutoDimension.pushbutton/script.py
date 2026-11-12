# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Auto Dimension
# Purpose        : Dimension conduits in a plan to the nearest parallel
#                  grid (or wall face) - one chain per bundle of parallel
#                  conduits.
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
# Input          : Plan view; selected conduits, or all conduits in view.
#                  Shift+click = how far along the run the dimension sits.
# Output         : Linear dimensions in the active plan view.
#
# Dependencies   :
#   - pyRevit, Revit API
#   - RZTools.extension/lib/rzgeom.py, rzconduit.py, rzview.py, rzsettings.py
#
# Features       :
#   - Grids first, wall faces if no parallel grid within 10 m
#   - Bundles of side-by-side conduits share one dimension string
#   - One undo step
#
# Changelog
# ------------------------------------------------------------
# v1.0.0
# - Initial Release
#
# License        : Proprietary
# Copyright      : (c) Rizwan Zahid. All Rights Reserved
# ============================================================

import math
import traceback

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB.Electrical import Conduit

import rzgeom
import rzconduit
import rzview
import rzsettings

TITLE = "RZ Tools - Auto Dimension"
SECTION = "rztools_autodim"
SEARCH_M = 10.0
BUNDLE_GAP_MM = 1000.0
EXTRA_MM = 300.0
PARALLEL = math.cos(math.radians(1.0))

doc = revit.doc
uidoc = revit.uidoc
tup = rzconduit.tup


def _plan_unit(v):
    length = math.hypot(v[0], v[1])
    return (v[0] / length, v[1] / length)


def _dot2(a, b):
    return a[0] * b[0] + a[1] * b[1]


def conduits_in_scope(view):
    picked = [doc.GetElement(i) for i in uidoc.Selection.GetElementIds()]
    picked = [e for e in picked if rzconduit.is_conduit(e)]
    if not picked:
        picked = list(DB.FilteredElementCollector(doc, view.Id).OfClass(Conduit))
    keep = []
    for c in picked:
        if not isinstance(c.Location.Curve, DB.Line):
            continue
        p0, p1 = [tup(p) for p in rzconduit.ends(c)]
        if rzgeom.is_vertical(rzgeom.vsub(p1, p0)):
            continue
        keep.append(c)
    return keep


def grid_candidates(view):
    """Grids visible in this view only (hidden / out-of-scope grids can't
    be dimensioned)."""
    out = []
    for grid in DB.FilteredElementCollector(doc, view.Id).OfClass(DB.Grid):
        curve = grid.Curve
        if isinstance(curve, DB.Line):
            out.append((DB.Reference(grid), tup(curve.GetEndPoint(0)),
                        tup(curve.GetEndPoint(1))))
    return out


def wall_face_candidates(view):
    out = []
    for wall in DB.FilteredElementCollector(doc, view.Id).OfClass(DB.Wall):
        loc = getattr(wall.Location, "Curve", None)
        if not isinstance(loc, DB.Line):
            continue
        for side in (DB.ShellLayerType.Exterior, DB.ShellLayerType.Interior):
            try:
                for ref in DB.HostObjectUtils.GetSideFaces(wall, side):
                    face = wall.GetGeometryObjectFromReference(ref)
                    if isinstance(face, DB.PlanarFace):
                        origin = tup(face.Origin)
                        along = tup(loc.Direction)
                        out.append((ref, origin, rzgeom.vadd(origin, along)))
            except Exception:
                continue
    return out


def nearest_parallel(candidates, mid, u, n, limit):
    """(reference, signed position across) of the closest parallel item."""
    best = None
    for ref, a, b in candidates:
        d = _plan_unit(rzgeom.vsub(b, a))
        if abs(_dot2(d, u)) < PARALLEL:
            continue
        across = _dot2(rzgeom.vsub(a, mid), n)
        if abs(across) <= limit and (best is None or abs(across) < abs(best[1])):
            best = (ref, across)
    return best


def dimension_bundle(view, members, along_offset, grids, walls):
    """Dimension one bundle to the nearest grid; if Revit refuses that
    grid, try the nearest wall face instead."""
    lines = [tuple(tup(p) for p in rzconduit.ends(c)) for c in members]
    first = lines[0]
    u = _plan_unit(rzgeom.vsub(first[1], first[0]))
    n = (-u[1], u[0])
    mid = rzgeom.vscale(rzgeom.vadd(first[0], first[1]), 0.5)
    limit = rzgeom.m_to_ft(SEARCH_M)
    targets = [t for t in (nearest_parallel(grids, mid, u, n, limit),
                           nearest_parallel(walls, mid, u, n, limit)) if t is not None]
    if not targets:
        raise ValueError("no parallel grid or wall within {:g} m".format(SEARCH_M))
    problem = None
    for ref, ref_across in targets:
        try:
            return rzconduit.all_or_nothing(doc, lambda: _make_dimension(
                view, members, lines, mid, u, n, ref, ref_across, along_offset))
        except Exception as ex:
            problem = ex
    raise ValueError("Revit could not dimension to the grid or wall ({})".format(problem))


def _make_dimension(view, members, lines, mid, u, n, ref, ref_across, along_offset):
    positions = [ref_across]
    refs = DB.ReferenceArray()
    refs.Append(ref)
    for c, line in zip(members, lines):
        m = rzgeom.vscale(rzgeom.vadd(line[0], line[1]), 0.5)
        positions.append(_dot2(rzgeom.vsub(m, mid), n))
        refs.Append(DB.Reference(c))

    extra = rzgeom.mm_to_ft(EXTRA_MM)
    z = rzview.plan_z(view)
    base = (mid[0] + u[0] * along_offset, mid[1] + u[1] * along_offset)
    lo, hi = min(positions) - extra, max(positions) + extra
    p_lo = DB.XYZ(base[0] + n[0] * lo, base[1] + n[1] * lo, z)
    p_hi = DB.XYZ(base[0] + n[0] * hi, base[1] + n[1] * hi, z)
    dim = doc.Create.NewDimension(view, DB.Line.CreateBound(p_lo, p_hi), refs)
    if dim is None:
        raise ValueError("Revit could not create the dimension")
    return dim


def main():
    if doc is None:
        forms.alert("Please open a Revit project first.", title=TITLE)
        return
    view = doc.ActiveView
    if not rzview.is_plan(view):
        forms.alert("Open a plan view first.", title=TITLE)
        return
    conduits = conduits_in_scope(view)
    if not conduits:
        forms.alert("No straight horizontal conduits to dimension.", title=TITLE)
        return
    along = rzgeom.mm_to_ft(rzsettings.load(SECTION, {"offset_mm": 500.0})["offset_mm"])
    lines = [tuple(tup(p) for p in rzconduit.ends(c)) for c in conduits]
    groups = rzgeom.bundles(lines, rzgeom.mm_to_ft(BUNDLE_GAP_MM))
    grids = grid_candidates(view)
    walls = wall_face_candidates(view)

    made, skipped = 0, []
    with revit.TransactionGroup("RZTools: Auto Dimension"):
        with revit.Transaction("RZTools: Auto Dimension"):
            for group in groups:
                members = [conduits[i] for i in group]
                try:
                    rzconduit.all_or_nothing(
                        doc, lambda: dimension_bundle(view, members, along, grids, walls))
                    made += 1
                except Exception as ex:
                    skipped.append(u"conduit {}{}: {}".format(
                        members[0].Id, u" (+{} more)".format(len(members) - 1)
                        if len(members) > 1 else u"", ex))

    lines_out = [u"Created {} dimension string(s) for {} conduit(s).".format(made, len(conduits))]
    if skipped:
        lines_out.append(u"Skipped:\n" + u"\n".join(skipped))
    forms.alert(u"\n".join(lines_out), title=TITLE)


try:
    main()
except Exception:
    output = script.get_output()
    output.print_md("**RZ Tools - Auto Dimension stopped. Nothing was changed.**")
    output.print_code(traceback.format_exc())
