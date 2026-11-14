# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Convert Line
# Purpose        : Turn straight model/detail lines or lines inside a
#                  linked/imported CAD file into real conduits.
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
# Input          : Revit lines (selection) or CAD lines (picked); conduit
#                  type, diameter, middle elevation, fittings option.
# Output         : One conduit per straight line, on the active view's
#                  level; elbows/couplings where lines touch.
#
# Dependencies   :
#   - pyRevit, Revit API
#   - Falcon.extension/lib/rzgeom.py, rzconduit.py, rzsettings.py
#
# Features       :
#   - Arcs and other curves are skipped and counted
#   - Original lines are left in place
#   - Remembers last settings; one undo step
#
# Changelog
# ------------------------------------------------------------
# v1.0.0
# - Initial Release
#
# License        : Proprietary
# Copyright      : (c) Rizwan Zahid. All Rights Reserved
# ============================================================

import os
import traceback

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import OperationCanceledException

import rzgeom
import rzconduit
import rzsettings

TITLE = "Falcon - Convert Line"
SECTION = "rztools_convertline"
DEFAULTS = {"type_name": "", "diameter_mm": 20.0, "elevation_mm": 3000.0,
            "fittings": True}
JOINT_TOL_MM = 5.0
MIN_LENGTH_MM = 10.0

doc = revit.doc
uidoc = revit.uidoc


class CurveFilter(ISelectionFilter):
    def AllowElement(self, element):
        return isinstance(element, DB.CurveElement)

    def AllowReference(self, reference, position):
        return False


class ImportFilter(ISelectionFilter):
    def AllowElement(self, element):
        return isinstance(element, DB.ImportInstance)

    def AllowReference(self, reference, position):
        return True


class ConvertDialog(forms.WPFWindow):
    def __init__(self, settings, types):
        forms.WPFWindow.__init__(
            self, os.path.join(os.path.dirname(__file__), "ConvertLine.xaml"))
        self.types = types
        self.result = None
        names = [n for n, _t in types]
        for name in names:
            self.ctype.Items.Add(name)
        self.ctype.SelectedIndex = (names.index(settings["type_name"])
                                    if settings["type_name"] in names else 0)
        self.diameter.Text = str(settings["diameter_mm"])
        self.elevation.Text = str(settings["elevation_mm"])
        self.fittings.IsChecked = settings["fittings"]

    def ok_click(self, sender, args):
        try:
            diameter = float(self.diameter.Text.replace(",", "."))
            elevation = float(self.elevation.Text.replace(",", "."))
        except ValueError:
            self.error.Text = "Enter numbers for diameter and elevation."
            return
        if diameter <= 0:
            self.error.Text = "Diameter must be more than 0."
            return
        name, ctype = self.types[self.ctype.SelectedIndex]
        self.result = {"type_name": name, "type": ctype, "diameter_mm": diameter,
                       "elevation_mm": elevation,
                       "fittings": bool(self.fittings.IsChecked)}
        self.Close()

    def cancel_click(self, sender, args):
        self.Close()


def _segments_of(curve):
    """Straight (p0, p1) pieces of a Line or PolyLine; [] for anything else."""
    if isinstance(curve, DB.Line):
        return [(curve.GetEndPoint(0), curve.GetEndPoint(1))]
    if isinstance(curve, DB.PolyLine):
        pts = list(curve.GetCoordinates())
        return list(zip(pts, pts[1:]))
    return []


def revit_lines():
    elements = [doc.GetElement(i) for i in uidoc.Selection.GetElementIds()]
    elements = [e for e in elements if isinstance(e, DB.CurveElement)]
    if not elements:
        refs = uidoc.Selection.PickObjects(
            ObjectType.Element, CurveFilter(), "Select the lines to convert, then Finish")
        elements = [doc.GetElement(r.ElementId) for r in refs]
    segments, skipped = [], 0
    for el in elements:
        pieces = _segments_of(el.GeometryCurve)
        if pieces:
            segments.extend(pieces)
        else:
            skipped += 1
    return segments, skipped


def cad_lines():
    refs = uidoc.Selection.PickObjects(
        ObjectType.PointOnElement, ImportFilter(),
        "Pick the CAD lines to convert, then Finish")
    segments, skipped = [], 0
    for ref in refs:
        imp = doc.GetElement(ref.ElementId)
        geo = imp.GetGeometryObjectFromReference(ref)
        pieces = _segments_of(geo)
        if not pieces:
            skipped += 1
            continue
        # The geometry may come back in the CAD file's own coordinates;
        # if it does not pass near the picked point, move it into the model.
        hit = rzconduit.tup(ref.GlobalPoint)
        near = min(_plan_gap(p, hit) for p in pieces)
        if near > rzgeom.mm_to_ft(50):
            tf = imp.GetTotalTransform()
            pieces = [(tf.OfPoint(a), tf.OfPoint(b)) for a, b in pieces]
        segments.extend(pieces)
    return segments, skipped


def _plan_gap(piece, point):
    a, b = rzconduit.tup(piece[0]), rzconduit.tup(piece[1])
    flat_a, flat_b = (a[0], a[1], 0.0), (b[0], b[1], 0.0)
    flat_p = (point[0], point[1], 0.0)
    d = rzgeom.project_distance(flat_a, flat_b, flat_p)
    on = rzgeom.point_along(flat_a, flat_b, d)
    return rzgeom.vlen(rzgeom.vsub(on, flat_p))


def main():
    if doc is None:
        forms.alert("Please open a Revit project first.", title=TITLE)
        return
    level = getattr(doc.ActiveView, "GenLevel", None)
    if level is None:
        forms.alert("Open a plan view first - the conduits go on its level.", title=TITLE)
        return
    types = rzconduit.conduit_types(doc)
    if not types:
        forms.alert("This project has no conduit types.", title=TITLE)
        return

    source = forms.CommandSwitchWindow.show(
        ["Revit lines", "CAD lines"], message="Which lines do you want to convert?")
    if not source:
        return
    try:
        segments, skipped_curves = revit_lines() if source == "Revit lines" else cad_lines()
    except OperationCanceledException:
        return
    min_len = rzgeom.mm_to_ft(MIN_LENGTH_MM)
    flat = []
    for a, b in segments:
        p0 = (a.X, a.Y, 0.0)
        p1 = (b.X, b.Y, 0.0)
        if rzgeom.vlen(rzgeom.vsub(p1, p0)) >= min_len:
            flat.append((p0, p1))
        else:
            skipped_curves += 1
    # The same CAD polyline comes back once per picked segment - drop repeats.
    flat = rzgeom.dedupe_segments(flat, rzgeom.mm_to_ft(1.0))
    if not flat:
        forms.alert("No straight lines to convert.", title=TITLE)
        return

    dialog = ConvertDialog(rzsettings.load(SECTION, DEFAULTS), types)
    dialog.show_dialog()
    opts = dialog.result
    if opts is None:
        return
    rzsettings.save(SECTION, dict((k, opts[k]) for k in DEFAULTS))

    diameter = rzgeom.mm_to_ft(opts["diameter_mm"])
    offset = rzgeom.mm_to_ft(opts["elevation_mm"])
    joints = rzgeom.joint_pairs(flat, rzgeom.mm_to_ft(JOINT_TOL_MM))
    if opts["fittings"]:
        # Fittings need the two ends to meet exactly - close small CAD gaps.
        flat = rzgeom.snap_joints(flat, joints)
    conduits = []
    failed = []
    fittings = 0
    with revit.TransactionGroup("Falcon: Convert Line"):
        with revit.Transaction("Falcon: Convert Line"):
            for p0, p1 in flat:
                try:
                    c = rzconduit.new_conduit(doc, opts["type"].Id, level.Id,
                                              rzconduit.xyz(p0), rzconduit.xyz(p1), diameter)
                    rzconduit.set_middle_elevation(c, offset)
                    conduits.append(c)
                except Exception as ex:
                    conduits.append(None)
                    failed.append(u"line {}: {}".format(len(conduits), ex))
            doc.Regenerate()
            if opts["fittings"]:
                for i, _ei, j, _ej in joints:
                    a, b = conduits[i], conduits[j]
                    if a is None or b is None:
                        continue
                    da = rzgeom.vsub(flat[i][1], flat[i][0])
                    db = rzgeom.vsub(flat[j][1], flat[j][0])
                    if rzgeom.joint_kind(da, db) == "union":
                        made = rzconduit.connect_union(doc, a, b)
                    else:
                        made = rzconduit.connect_elbow(doc, a, b)
                    if made is None:
                        failed.append(u"joint between {} and {}: Revit could not add a "
                                      u"fitting".format(a.Id, b.Id))
                    else:
                        fittings += 1

    made_count = len([c for c in conduits if c is not None])
    lines = [u"Created {} conduit(s) and {} fitting(s).".format(made_count, fittings)]
    if skipped_curves:
        lines.append(u"Skipped {} arc / other / very short line(s).".format(skipped_curves))
    if failed:
        lines.append(u"Problems:\n" + u"\n".join(failed))
    forms.alert(u"\n".join(lines), title=TITLE)


try:
    main()
except Exception:
    output = script.get_output()
    output.print_md("**Falcon - Convert Line stopped. Nothing was changed.**")
    output.print_code(traceback.format_exc())
