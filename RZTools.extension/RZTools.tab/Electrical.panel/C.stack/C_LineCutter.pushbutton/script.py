# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Line Cutter
# Purpose        : Make conduit crossings read clearly in plan - a small
#                  white masking region hides the LOWER conduit where an
#                  upper one passes over it.
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
# Category       : Documentation
# Discipline     : Electrical
# Tool Type      : pyRevit Tool
#
# Input          : Plan view; selected conduits, or all conduits in view.
#                  Shift+click = gap each side of the upper conduit.
# Output         : "RZ Mask" filled regions in the active view only. The
#                  model is never changed.
#
# Dependencies   :
#   - pyRevit, Revit API
#   - RZTools.extension/lib/rzgeom.py, rzconduit.py, rzview.py, rzsettings.py
#
# Features       :
#   - Re-running replaces the masks it made before in this view
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

from System.Collections.Generic import List

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.DB.Electrical import Conduit

import rzgeom
import rzconduit
import rzcolor
import rzview
import rzsettings

TITLE = "RZ Tools - Line Cutter"
SECTION = "rztools_linecutter"
MARK = "RZ_LINE_CUTTER"
MASK_TYPE = "RZ Mask"
EDGE_STYLE = "RZ Line Cutter"
SIDE_EXTRA_MM = 20.0
MIN_SIN = math.sin(math.radians(10.0))

doc = revit.doc
uidoc = revit.uidoc
tup = rzconduit.tup


class Run(object):
    def __init__(self, conduit):
        self.conduit = conduit
        p0, p1 = rzconduit.ends(conduit)
        self.p0, self.p1 = tup(p0), tup(p1)
        self.dir = rzgeom.vsub(self.p1, self.p0)
        self.r = rzconduit.outer_radius(conduit)

    def top_at(self, t):
        return self.p0[2] + t * (self.p1[2] - self.p0[2]) + self.r


def runs_in_scope(view):
    picked = [doc.GetElement(i) for i in uidoc.Selection.GetElementIds()]
    picked = [e for e in picked if rzconduit.is_conduit(e)]
    if not picked:
        picked = list(DB.FilteredElementCollector(doc, view.Id).OfClass(Conduit))
    runs = []
    for c in picked:
        if isinstance(c.Location.Curve, DB.Line):
            run = Run(c)
            if not rzgeom.is_vertical(run.dir):
                runs.append(run)
    return runs


def _solid_fill_id():
    for fpe in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement):
        pattern = fpe.GetFillPattern()
        if pattern is not None and pattern.IsSolidFill:
            return fpe.Id
    return None


def mask_type():
    types = list(DB.FilteredElementCollector(doc).OfClass(DB.FilledRegionType))
    for t in types:
        if rzconduit.element_name(t) == MASK_TYPE:
            return t
    if not types:
        raise ValueError("this project has no filled region types to copy")
    new = types[0].Duplicate(MASK_TYPE)
    solid = _solid_fill_id()
    if solid is not None:
        new.ForegroundPatternId = solid
    new.ForegroundPatternColor = DB.Color(255, 255, 255)
    try:
        new.BackgroundPatternId = DB.ElementId.InvalidElementId
    except Exception:
        pass
    try:
        new.IsMasking = True
    except Exception:
        pass
    return new


def invisible_line_style():
    """<Invisible lines> style, found by its built-in id (any language)."""
    lines_cat = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Lines)
    invisible_id = int(DB.BuiltInCategory.OST_InvisibleLines)
    for sub in lines_cat.SubCategories:
        if rzcolor.eid_int(sub.Id) == invisible_id or sub.Name == "<Invisible lines>":
            return sub.GetGraphicsStyle(DB.GraphicsStyleType.Projection)
    return None


def edge_line_style():
    """Thin black "RZ Line Cutter" line style used to redraw the upper
    conduit over the mask (created the first time)."""
    lines_cat = doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Lines)
    for sub in lines_cat.SubCategories:
        if sub.Name == EDGE_STYLE:
            return sub.GetGraphicsStyle(DB.GraphicsStyleType.Projection)
    sub = doc.Settings.Categories.NewSubcategory(lines_cat, EDGE_STYLE)
    sub.LineColor = DB.Color(0, 0, 0)
    sub.SetLineWeight(1, DB.GraphicsStyleType.Projection)
    doc.Regenerate()
    return sub.GetGraphicsStyle(DB.GraphicsStyleType.Projection)


def remove_old_masks(view):
    """Delete this tool's masks and redrawn edges in view; returns mask count."""
    old = []
    for region in DB.FilteredElementCollector(doc, view.Id).OfClass(DB.FilledRegion):
        param = region.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if param is not None and param.AsString() == MARK:
            old.append(region.Id)
    edges = []
    for curve in DB.FilteredElementCollector(doc, view.Id).OfClass(DB.CurveElement):
        style = getattr(curve, "LineStyle", None)
        if style is not None and style.Name == EDGE_STYLE:
            edges.append(curve.Id)
    for eid in old + edges:
        doc.Delete(eid)
    return len(old)


def crossings(runs, gap):
    """[(center, lower run, along, across)] for every pair that crosses."""
    found = []
    for i in range(len(runs)):
        for j in range(i + 1, len(runs)):
            a, b = runs[i], runs[j]
            hit = rzgeom.plan_intersection(a.p0, a.p1, b.p0, b.p1)
            if hit is None:
                continue
            t, u = hit
            top_a, top_b = a.top_at(t), b.top_at(u)
            if abs(top_a - top_b) < rzgeom.mm_to_ft(1):
                continue
            lower, upper = (a, b) if top_a < top_b else (b, a)
            center = rzgeom.point_along(a.p0, a.p1, t * rzgeom.vlen(a.dir))
            sin = rzgeom.crossing_sin(lower.dir, upper.dir)
            if sin < MIN_SIN:
                continue   # nearly parallel - a mask would be huge
            along = (2 * upper.r + 2 * gap) / sin
            across = 2 * lower.r + rzgeom.mm_to_ft(SIDE_EXTRA_MM)
            found.append((center, lower, upper, along, across))
    return found


def make_mask(view, type_id, style, edge_style, center, lower, upper, along, across):
    z = rzview.plan_z(view)
    pts = [rzview.at_z(p, z) for p in rzgeom.mask_rect(center, lower.dir, along, across)]
    loop = DB.CurveLoop()
    for a, b in zip(pts, pts[1:] + pts[:1]):
        loop.Append(DB.Line.CreateBound(a, b))
    loops = List[DB.CurveLoop]()
    loops.Add(loop)
    region = DB.FilledRegion.Create(doc, type_id, view.Id, loops)
    if style is not None:
        try:
            region.SetLineStyleId(style.Id)
        except Exception:
            pass
    region.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(MARK)
    # The mask covers everything under it, including the upper conduit,
    # so redraw the upper conduit's two edges on top of the mask.
    reach = math.hypot(along, across) + 2 * upper.r
    for a, b in rzgeom.upper_edges(center, upper.dir, upper.r, reach):
        line = rzview.detail_line(doc, view, rzview.at_z(a, z), rzview.at_z(b, z))
        line.LineStyle = edge_style
    return region


def main():
    if doc is None:
        forms.alert("Please open a Revit project first.", title=TITLE)
        return
    view = doc.ActiveView
    if not rzview.is_plan(view):
        forms.alert("Open a plan view first.", title=TITLE)
        return
    gap = rzgeom.mm_to_ft(rzsettings.load(SECTION, {"gap_mm": 50.0})["gap_mm"])
    runs = runs_in_scope(view)
    found = crossings(runs, gap)

    made, skipped = 0, []
    with revit.TransactionGroup("RZTools: Line Cutter"):
        with revit.Transaction("RZTools: Line Cutter"):
            removed = remove_old_masks(view)
            if found:
                type_id = mask_type().Id
                style = invisible_line_style()
                edges = edge_line_style()
                for center, lower, upper, along, across in found:
                    try:
                        rzconduit.all_or_nothing(doc, lambda: make_mask(
                            view, type_id, style, edges, center, lower, upper,
                            along, across))
                        made += 1
                    except Exception as ex:
                        skipped.append(u"crossing on {}: {}".format(lower.conduit.Id, ex))

    lines = [u"Masked {} crossing(s) in this view.".format(made)]
    if removed:
        lines.append(u"Replaced {} mask(s) from the last run.".format(removed))
    if not found:
        lines.append(u"No crossings at different heights were found.")
    if skipped:
        lines.append(u"Skipped:\n" + u"\n".join(skipped))
    forms.alert(u"\n".join(lines), title=TITLE)


try:
    main()
except Exception:
    output = script.get_output()
    output.print_md("**RZ Tools - Line Cutter stopped. Nothing was changed.**")
    output.print_code(traceback.format_exc())
