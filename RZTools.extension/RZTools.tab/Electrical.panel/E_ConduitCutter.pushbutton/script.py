# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Conduit Cutter
# Purpose        : Resolve conduit crossings - the smaller group of
#                  crossing conduits is offset over/under the bigger group
#                  with 30-degree elbows, keeping a set clearance.
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
# Input          : Crossing straight conduits (pre-select or pick, then
#                  Finish); Up or Down. Shift+click = clearance / angle.
# Output         : The moving conduits are cut and rebuilt as offsets
#                  joined with elbows from the conduit type's settings.
#
# Dependencies   :
#   - pyRevit
#   - Revit API
#   - RZTools.extension/lib/rzgeom.py, rzconduit.py, rzsettings.py
#
# Features       :
#   - Crossings close together share one offset
#   - Conduits that cannot fit the offset are skipped and listed
#   - Single undo step for the whole run
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
import rzsettings

TITLE = "RZ Tools - Conduit Cutter"
SECTION = "rztools_cutter"
DEFAULTS = {"clearance_mm": 50.0, "angle_deg": 30.0}
END_MARGIN_MM = 100.0

doc = revit.doc
uidoc = revit.uidoc


def selected_conduits():
    picked = [doc.GetElement(i) for i in uidoc.Selection.GetElementIds()]
    picked = [e for e in picked if rzconduit.is_conduit(e)]
    if picked:
        return picked
    refs = uidoc.Selection.PickObjects(
        ObjectType.Element, rzconduit.ConduitFilter(),
        "Select the crossing straight conduits, then click Finish")
    return [doc.GetElement(r.ElementId) for r in refs]


class Run(object):
    """A straight conduit with its geometry as plain tuples."""

    def __init__(self, conduit):
        self.conduit = conduit
        p0, p1 = rzconduit.ends(conduit)
        self.p0, self.p1 = rzconduit.tup(p0), rzconduit.tup(p1)
        self.dir = rzgeom.vsub(self.p1, self.p0)
        self.length = rzgeom.vlen(self.dir)
        self.radius = rzconduit.outer_radius(conduit)
        self.z = (self.p0[2] + self.p1[2]) / 2.0

    def z_at(self, t):
        return self.p0[2] + t * (self.p1[2] - self.p0[2])


def plan_offset(mover, others, clearance, angle, up):
    """Return (points, offset count, crossing count) for one moving conduit.

    Raises ValueError with a plain reason when it must be skipped."""
    crossings = []
    stack = []
    for other in others:
        hit = rzgeom.plan_intersection(mover.p0, mover.p1, other.p0, other.p1)
        if hit is None:
            continue
        t, u = hit
        sin = rzgeom.crossing_sin(mover.dir, other.dir)
        half = (other.radius + clearance + mover.radius) / sin
        crossings.append((t * mover.length, half))
        stack.append((other.z_at(u), other.radius))
    if not crossings:
        raise ValueError("does not cross the other group")
    rise = rzgeom.required_rise(mover.z, mover.radius, stack, clearance, up)
    if rise == 0.0:
        raise ValueError("already clear of the other group")
    run = rzgeom.slope_run(rise, angle)
    end_clear = 2 * mover.radius + rzgeom.mm_to_ft(END_MARGIN_MM)
    try:
        spans = rzgeom.offset_spans(mover.length, crossings, run, end_clear)
    except ValueError:
        raise ValueError("crossing too close to the conduit end")
    points = rzgeom.dogleg_polyline(mover.p0, mover.p1, spans, rise, run)
    return points, len(spans), len(crossings)


def build_offset(conduit, points):
    """Rebuild conduit along points; returns list of joints that failed."""
    xyz = rzconduit.xyz
    far = rzconduit.end_connector(conduit, xyz(points[-1]))
    far_links = rzconduit.connected_others(far)
    for link in far_links:
        far.DisconnectFrom(link)

    rzconduit.set_ends(conduit, xyz(points[0]), xyz(points[1]))
    pieces = [conduit]
    for a, b in zip(points[1:-1], points[2:]):
        pieces.append(rzconduit.new_conduit_like(doc, conduit, xyz(a), xyz(b)))

    last_end = rzconduit.end_connector(pieces[-1], xyz(points[-1]))
    for link in far_links:
        try:
            last_end.ConnectTo(link)
        except Exception:
            pass

    doc.Regenerate()
    failed = []
    for a, b in zip(pieces, pieces[1:]):
        if rzconduit.connect_elbow(doc, a, b) is None:
            failed.append(u"{}: no elbow between {} and {}".format(conduit.Id, a.Id, b.Id))
    return failed


def choose_movers(groups, runs):
    a = [runs[i] for i in groups[0]]
    b = [runs[i] for i in groups[1]]
    if len(a) < len(b):
        return a, b
    if len(b) < len(a):
        return b, a
    first = u"Group with conduit {} ({} conduits)".format(a[0].conduit.Id, len(a))
    second = u"Group with conduit {} ({} conduits)".format(b[0].conduit.Id, len(b))
    pick = forms.alert(u"Both groups have {} conduits. Which group should move?".format(len(a)),
                       title=TITLE, options=[first, second])
    if pick is None:
        return None, None
    return (a, b) if pick == first else (b, a)


def main():
    if doc is None:
        forms.alert("Please open a Revit project first.", title=TITLE)
        return
    settings = rzsettings.load(SECTION, DEFAULTS)
    clearance = rzgeom.mm_to_ft(settings["clearance_mm"])
    angle = settings["angle_deg"]

    try:
        conduits = selected_conduits()
    except OperationCanceledException:
        return

    runs, skipped = [], []
    for c in conduits:
        if not isinstance(c.Location.Curve, DB.Line):
            skipped.append(u"{}: not straight".format(c.Id))
            continue
        run = Run(c)
        if rzgeom.is_vertical(run.dir):
            skipped.append(u"{}: vertical".format(c.Id))
            continue
        runs.append(run)

    groups = rzgeom.group_by_direction([r.dir for r in runs]) if runs else []
    if len(groups) != 2:
        forms.alert("Select two sets of conduits that cross each other.", title=TITLE)
        return
    movers, others = choose_movers(groups, runs)
    if movers is None:
        return

    down = u"Down - go under the other conduits"
    up = u"Up - go over the other conduits"
    way = forms.alert(
        "Which way should the smaller group of conduits go?",
        sub_msg="The group with fewer conduits is moved around the bigger group, "
                "so fewer conduits get offsets.",
        title=TITLE, options=[down, up])
    if way is None:
        return
    going_up = way == up

    offsets = crossings = 0
    with revit.TransactionGroup("RZTools: Conduit Cutter"):
        with revit.Transaction("RZTools: Conduit Cutter"):
            for mover in movers:
                try:
                    points, n_spans, n_cross = plan_offset(
                        mover, others, clearance, angle, going_up)
                except ValueError as reason:
                    skipped.append(u"{}: {}".format(mover.conduit.Id, reason))
                    continue
                try:
                    skipped.extend(build_offset(mover.conduit, points))
                except Exception as ex:
                    skipped.append(u"{}: {}".format(mover.conduit.Id, ex))
                    continue
                offsets += n_spans
                crossings += n_cross

    lines = [
        u"Finished.",
        u"Created {} {} offset(s) covering {} crossing(s) with {:g}-degree elbows.".format(
            offsets, "upward" if going_up else "downward", crossings, angle),
        u"Revit's conduit settings choose the fittings and minimum bend settings.",
    ]
    if skipped:
        lines.append(u"Skipped:\n" + u"\n".join(skipped))
    forms.alert(u"\n".join(lines), title=TITLE)


try:
    main()
except Exception:
    output = script.get_output()
    output.print_md("**RZ Tools - Conduit Cutter stopped. Nothing was changed.**")
    output.print_code(traceback.format_exc())
