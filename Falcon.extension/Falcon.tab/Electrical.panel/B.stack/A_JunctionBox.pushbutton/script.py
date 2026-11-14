# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Junction Box
# Purpose        : Place junction boxes on conduits where you click -
#                  mid-run (conduit cut and connected for 2-way boxes)
#                  or on a conduit end (box connected to the end).
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
# Input          : Box type (remembered); clicks on conduits, Esc to finish.
# Output         : Junction box instances, lined up and connected.
#
# Dependencies   :
#   - pyRevit, Revit API
#   - Falcon.extension/lib/rzgeom.py, rzconduit.py, rzsettings.py
#
# Features       :
#   - Click within 300 mm of a conduit end -> box goes on the end
#   - Each box all-or-nothing; whole run is one undo step
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
import rzsettings

TITLE = "Falcon - Junction Box"
SECTION = "rztools_junctionbox"
END_SNAP_MM = 300.0
END_MARGIN_MM = 150.0

doc = revit.doc
uidoc = revit.uidoc


def choose_symbol():
    symbols = rzconduit.box_symbols(doc)
    if not symbols:
        forms.alert("Load a junction box family first.", title=TITLE)
        return None
    labels = [label for label, _sym in symbols]
    last = rzsettings.load(SECTION, {"box_label": ""})["box_label"]
    if last in labels:
        labels.remove(last)
        labels.insert(0, last)
    picked = forms.SelectFromList.show(labels, title="Junction box type",
                                       multiselect=False, button_name="Use this box")
    if not picked:
        return None
    rzsettings.save(SECTION, {"box_label": picked})
    return dict(symbols)[picked]


def place_one(symbol, conduit, pick_point):
    """Place one box for one click. Returns a short result word."""
    start, finish = rzconduit.ends(conduit)
    p0, p1 = rzconduit.tup(start), rzconduit.tup(finish)
    length = rzgeom.vlen(rzgeom.vsub(p1, p0))
    dist = rzgeom.project_distance(p0, p1, rzconduit.tup(pick_point))
    end = rzgeom.snap_end(length, dist, rzgeom.mm_to_ft(END_SNAP_MM))
    if end is not None and rzconduit.end_connector(
            conduit, (start, finish)[end]).IsConnected:
        end = None   # that end already has a fitting - place the box inline
    if end is not None:
        _inst, connected = rzconduit.place_box_at_end(
            doc, symbol, conduit, (start, finish)[end])
        return "connected" if connected else "placed"
    margin = rzgeom.mm_to_ft(END_MARGIN_MM)
    dist = min(max(dist, margin), length - margin)
    point = rzconduit.xyz(rzgeom.point_along(p0, p1, dist))
    _inst, new_piece, _note = rzconduit.place_box(doc, symbol, conduit, point)
    return "connected" if new_piece is not None else "placed"


def main():
    if doc is None:
        forms.alert("Please open a Revit project first.", title=TITLE)
        return
    symbol = choose_symbol()
    if symbol is None:
        return

    counts = {"connected": 0, "placed": 0}
    skipped = []
    with revit.TransactionGroup("Falcon: Junction Box"):
        while True:
            try:
                ref = uidoc.Selection.PickObject(
                    ObjectType.Element, rzconduit.ConduitFilter(),
                    "Click a conduit where the junction box goes (Esc to finish)")
            except OperationCanceledException:
                break
            conduit = doc.GetElement(ref.ElementId)
            with revit.Transaction("Falcon: Junction Box"):
                try:
                    result = rzconduit.all_or_nothing(
                        doc, lambda: place_one(symbol, conduit, ref.GlobalPoint))
                    counts[result] += 1
                except Exception as ex:
                    skipped.append(u"{}: {}".format(conduit.Id, ex))

    total = counts["connected"] + counts["placed"]
    if total or skipped:
        lines = [u"Placed {} junction box(es); {} connected to the conduit.".format(
            total, counts["connected"])]
        if counts["placed"]:
            lines.append(u"{} box(es) could not be connected (the family's conduit "
                         u"connectors do not line up with the conduit).".format(counts["placed"]))
        if skipped:
            lines.append(u"Skipped:\n" + u"\n".join(skipped))
        forms.alert(u"\n".join(lines), title=TITLE)


try:
    main()
except Exception:
    output = script.get_output()
    output.print_md("**Falcon - Junction Box stopped. Nothing was changed.**")
    output.print_code(traceback.format_exc())
