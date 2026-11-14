# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Home Run
# Purpose        : Draw the home-run arrow from a device toward its panel
#                  with a "<Panel>-<Circuit>" note, read from the device's
#                  electrical circuit.
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
# Input          : Plan view; click circuited devices (Esc to finish).
#                  Shift+click = arrow length.
# Output         : Detail-line arrow + text note in the active plan view.
#
# Dependencies   :
#   - pyRevit, Revit API
#   - Falcon.extension/lib/falcon_geom.py, falcon_view.py, falcon_settings.py
#
# Features       :
#   - Works on Revit 2020 (ElectricalSystems) and 2021+ (GetElectricalSystems)
#   - Devices with no circuit/panel are listed, nothing drawn
#   - One undo step for the whole run
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
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import OperationCanceledException

import falcon_geom
import falcon_conduit
import falcon_view
import falcon_settings

TITLE = "Falcon - Home Run"
SECTION = "falcon_homerun"
DEFAULT_LENGTH_MM = 600.0
HEAD_MM = 150.0
TEXT_GAP_MM = 100.0

doc = revit.doc
uidoc = revit.uidoc


class DeviceFilter(ISelectionFilter):
    def AllowElement(self, element):
        return isinstance(element, DB.FamilyInstance) and element.MEPModel is not None

    def AllowReference(self, reference, position):
        return False


def circuit_of(device):
    """(panel name, circuit number, panel element) or None."""
    mep = device.MEPModel
    getter = getattr(mep, "GetElectricalSystems", None)
    systems = getter() if getter is not None else getattr(mep, "ElectricalSystems", None)
    for system in (list(systems) if systems else []):
        panel = system.BaseEquipment
        # A sub-panel also "has" the circuits it feeds; skip those.
        if panel is not None and panel.Id != device.Id:
            return system.PanelName, system.CircuitNumber, panel
    return None


def draw(view, device, length):
    found = circuit_of(device)
    if found is None:
        raise ValueError("not on a circuit with a panel")
    panel_name, circuit, panel = found
    label = falcon_geom.home_run_label(panel_name, circuit)
    if label is None:
        raise ValueError("the circuit has no panel name")
    start_pt = getattr(device.Location, "Point", None)
    panel_pt = getattr(panel.Location, "Point", None)
    if start_pt is None or panel_pt is None:
        raise ValueError("device or panel has no insertion point")
    z = falcon_view.plan_z(view)
    start = (start_pt.X, start_pt.Y, z)
    toward = (panel_pt.X, panel_pt.Y, z)
    if falcon_geom.vlen(falcon_geom.vsub(toward, start)) < 1e-6:
        raise ValueError("device sits on the panel")
    end, left, right = falcon_geom.arrow_points(start, toward, length, falcon_geom.mm_to_ft(HEAD_MM))
    falcon_view.detail_line(doc, view, falcon_view.at_z(start, z), falcon_view.at_z(end, z))
    falcon_view.detail_line(doc, view, falcon_view.at_z(end, z), falcon_view.at_z(left, z))
    falcon_view.detail_line(doc, view, falcon_view.at_z(end, z), falcon_view.at_z(right, z))
    gap = falcon_geom.mm_to_ft(TEXT_GAP_MM)
    text_at = falcon_geom.point_along(start, end, length + gap)
    falcon_view.text_note(doc, view, falcon_view.at_z(text_at, z), label)
    return label


def main():
    if doc is None:
        forms.alert("Please open a Revit project first.", title=TITLE)
        return
    view = doc.ActiveView
    if not falcon_view.is_plan(view):
        forms.alert("Open a plan view first.", title=TITLE)
        return
    length = falcon_geom.mm_to_ft(
        falcon_settings.load(SECTION, {"length_mm": DEFAULT_LENGTH_MM})["length_mm"])

    drawn, skipped = [], []
    with revit.TransactionGroup("Falcon: Home Run"):
        while True:
            try:
                ref = uidoc.Selection.PickObject(
                    ObjectType.Element, DeviceFilter(),
                    "Click a device for its home run (Esc to finish)")
            except OperationCanceledException:
                break
            device = doc.GetElement(ref.ElementId)
            with revit.Transaction("Falcon: Home Run"):
                # Caught inside the transaction so a skipped device never
                # shows as an error, and never undoes earlier home runs.
                try:
                    drawn.append(falcon_conduit.all_or_nothing(
                        doc, lambda: draw(view, device, length)))
                except Exception as reason:
                    skipped.append(u"{}: {}".format(device.Id, reason))

    if drawn or skipped:
        lines = [u"Drew {} home run(s): {}".format(len(drawn), u", ".join(drawn))]
        if skipped:
            lines.append(u"Skipped:\n" + u"\n".join(skipped))
        forms.alert(u"\n".join(lines), title=TITLE)


try:
    main()
except Exception:
    output = script.get_output()
    output.print_md("**Falcon - Home Run stopped. Nothing was changed.**")
    output.print_code(traceback.format_exc())
