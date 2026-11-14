# ============================================================
# Shared Library
# ============================================================
# Module Name    : falcon_view
# Purpose        : View / annotation helpers for Home Run, Auto
#                  Dimension and Line Cutter (plan views only).
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Created Date   : 2026-11-12
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7
# ============================================================
"""Plan-view helpers: plane height, detail lines, text, number prompts."""

from pyrevit import DB, forms

import falcon_settings


def is_plan(view):
    return isinstance(view, DB.ViewPlan) and not view.IsTemplate


def plan_z(view):
    """Height of the plan view's sketch plane (where 2D items must sit)."""
    sketch = getattr(view, "SketchPlane", None)
    if sketch is not None:
        return sketch.GetPlane().Origin.Z
    level = getattr(view, "GenLevel", None)
    if level is not None:
        return level.ProjectElevation
    return 0.0


def at_z(point_tuple, z):
    return DB.XYZ(point_tuple[0], point_tuple[1], z)


def detail_line(doc, view, a, b):
    return doc.Create.NewDetailCurve(view, DB.Line.CreateBound(a, b))


def text_note(doc, view, point, text):
    type_id = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.TextNoteType)
    return DB.TextNote.Create(doc, view.Id, point, text, type_id)


def ask_setting(title, section, key, default, prompt, low, high):
    """Shift+click helper: ask for one number and save it."""
    current = falcon_settings.load(section, {key: default})[key]
    text = forms.ask_for_string(default=str(current), prompt=prompt, title=title)
    if text is None:
        return None
    try:
        value = float(text.replace(",", "."))
    except ValueError:
        value = None
    if value is None or not (low <= value <= high):
        forms.alert(u"Enter a number from {:g} to {:g}.".format(low, high), title=title)
        return None
    falcon_settings.save(section, {key: value})
    forms.alert(u"Saved: {:g}.".format(value), title=title)
    return value
