# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Conduit Cutter - Settings (Shift+click)
# Purpose        : Change the clearance and elbow angle used by
#                  Conduit Cutter.
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Created Date   : 2026-11-12
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7
# ============================================================

from pyrevit import forms

import rzsettings

TITLE = "Falcon - Conduit Cutter Settings"
SECTION = "rztools_cutter"
DEFAULTS = {"clearance_mm": 50.0, "angle_deg": 30.0}


def ask_number(prompt, default, low, high):
    text = forms.ask_for_string(default=str(default), prompt=prompt, title=TITLE)
    if text is None:
        return None
    try:
        value = float(text.replace(",", "."))
    except ValueError:
        value = None
    if value is None or not (low <= value <= high):
        forms.alert(u"Enter a number from {:g} to {:g}.".format(low, high), title=TITLE)
        return None
    return value


settings = rzsettings.load(SECTION, DEFAULTS)
clearance = ask_number("Clear gap between the two conduit groups (mm)",
                       settings["clearance_mm"], 0, 1000)
if clearance is not None:
    angle = ask_number("Offset elbow angle (degrees)", settings["angle_deg"], 15, 60)
    if angle is not None:
        rzsettings.save(SECTION, {"clearance_mm": clearance, "angle_deg": angle})
        forms.alert(u"Saved: {:g} mm clearance, {:g}-degree elbows.".format(clearance, angle),
                    title=TITLE)
