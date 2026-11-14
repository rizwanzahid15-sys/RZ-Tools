# ============================================================
# Shared Library
# ============================================================
# Module Name    : rztools_markup
# Purpose        : Shared logic for the Falcon markup pushbuttons
#                  (Redline Markup, Blue Markup, Clear) - apply or
#                  remove a projection-line color override on picked
#                  elements, in the active view only.
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7 (safe on every supported version)
# ============================================================
"""Shared helpers for the Falcon markup pushbuttons.

Kept in the extension lib/ so Redline Markup, Blue Markup, and Clear all
call the same tested logic instead of duplicating it per pushbutton.
"""

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException

RZTOOLS_SUITE_VERSION = "1.0.0"


def build_line_override(color):
    """Return an OverrideGraphicSettings for the given projection line color.

    color=None returns a blank OverrideGraphicSettings, which clears any
    existing override (used by the Clear tool).
    """
    ogs = DB.OverrideGraphicSettings()
    if color is not None:
        ogs.SetProjectionLineColor(color)
        ogs.SetProjectionLineWeight(6)
    return ogs


def expand_group_members(doc, eid, seen=None):
    """If eid is a Group, or a member of a Group, return every member id
    (recursively, for nested groups) so the whole group changes together
    instead of just the one member that got picked. Otherwise return [eid].
    """
    if seen is None:
        seen = set()
    if eid in seen:
        return []
    seen.add(eid)

    element = doc.GetElement(eid)
    if element is None:
        return [eid]

    group = None
    if isinstance(element, DB.Group):
        group = element
    else:
        group_id = getattr(element, "GroupId", None)
        if group_id is not None and group_id != DB.ElementId.InvalidElementId:
            group = doc.GetElement(group_id)

    if isinstance(group, DB.Group):
        member_ids = []
        for member_id in group.GetMemberIds():
            member_ids.extend(expand_group_members(doc, member_id, seen))
        return member_ids if member_ids else [eid]

    return [eid]


def apply_override(doc, view, element_ids, ogs):
    """Apply ogs to each element id in view, expanding any grouped element
    to its full group so the whole group changes color together. Skips
    elements that reject the override (e.g. unsupported category) instead
    of stopping the run."""
    expanded_ids = set()
    for eid in element_ids:
        for member_id in expand_group_members(doc, eid):
            expanded_ids.add(member_id)

    for eid in expanded_ids:
        try:
            view.SetElementOverrides(eid, ogs)
        except Exception:
            pass


def run_markup_tool(tool_title, color, transaction_name):
    """Entry point shared by Redline Markup, Blue Markup, and Clear.

    color: DB.Color to apply, or None to clear the override.
    Elements already selected before the tool was clicked are updated
    immediately; then the user can keep picking elements one at a time,
    each updated the instant it is picked, until Esc is pressed.

    Each pick commits in its own transaction (instead of one transaction
    for the whole run) so Revit repaints the color the moment the element
    is picked, instead of waiting until Esc. Ctrl+Z undoes one element at
    a time, not the whole run.
    """
    doc = revit.doc
    uidoc = revit.uidoc

    if doc is None:
        forms.alert("Please open a Revit project first.", title="Falcon")
        script.exit()

    view = doc.ActiveView
    ogs = build_line_override(color)

    preselected = list(uidoc.Selection.GetElementIds())
    if preselected:
        with revit.Transaction(transaction_name):
            apply_override(doc, view, preselected, ogs)

    prompt = "Select element for {} (Esc to finish)".format(tool_title)
    while True:
        try:
            ref = uidoc.Selection.PickObject(ObjectType.Element, prompt)
        except OperationCanceledException:
            break
        with revit.Transaction(transaction_name):
            apply_override(doc, view, [ref.ElementId], ogs)
