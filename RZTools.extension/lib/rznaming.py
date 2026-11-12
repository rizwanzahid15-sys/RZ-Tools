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
with "_". Whenever that replacement happens (or a name itself contains
"__"), a short hash of the real family/type name is appended so two
different families can never end up sharing one filter.
"""

PREFIX = "RZ_COLOR_"
TYPE_SEP = "__"
FORBIDDEN = "\\:{}[]|;<>?`~"


def _clean(text):
    return "".join("_" if ch in FORBIDDEN else ch for ch in text)


def _short_hash(text):
    """8-hex-digit FNV-1a hash (stable across Python versions)."""
    h = 0x811c9dc5
    for byte in bytearray(text.encode("utf-8")):
        h ^= byte
        h = (h * 0x01000193) & 0xffffffff
    return "%08x" % h


def _ambiguous(text):
    return _clean(text) != text or TYPE_SEP in text


def filter_name(family, type_name=None):
    name = PREFIX + _clean(family)
    raw = family
    if type_name is not None:
        name += TYPE_SEP + _clean(type_name)
        raw = family + u"\n" + type_name
    if _ambiguous(family) or (type_name is not None and _ambiguous(type_name)):
        name += "_" + _short_hash(raw)
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
