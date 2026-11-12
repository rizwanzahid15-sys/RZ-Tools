# ============================================================
# Shared Library
# ============================================================
# Module Name    : rznaming
# Purpose        : Revit-free naming rules for the view filters created
#                  by the Coloring tool.
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Created Date   : 2026-11-12
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7 / CPython 3 (no Revit imports)
# ============================================================
"""Filter names: RZ_COLOR_<Family> or RZ_COLOR_<Family>__<Type>.

Revit rejects some characters in filter names, so they are replaced
with "_".
"""

PREFIX = "RZ_COLOR_"
TYPE_SEP = "__"
FORBIDDEN = "\\:{}[]|;<>?`~"


def _clean(text):
    return "".join("_" if ch in FORBIDDEN else ch for ch in text)


def filter_name(family, type_name=None):
    name = PREFIX + _clean(family)
    if type_name is not None:
        name += TYPE_SEP + _clean(type_name)
    return name


def parse_filter_name(name):
    """(family, type_or_None) for an RZ filter name, else None.

    Splits on the first "__", so it is best-effort for names that
    themselves contain "__"; used only for display.
    """
    if not name.startswith(PREFIX):
        return None
    rest = name[len(PREFIX):]
    if TYPE_SEP in rest:
        family, type_name = rest.split(TYPE_SEP, 1)
        return (family, type_name)
    return (rest, None)
