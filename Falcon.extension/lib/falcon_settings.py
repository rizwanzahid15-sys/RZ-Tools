# ============================================================
# Shared Library
# ============================================================
# Module Name    : falcon_settings
# Purpose        : Remember per-tool settings (last dialog values,
#                  Shift+click options) in the pyRevit user config.
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Created Date   : 2026-11-12
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7
# ============================================================
"""Load/save small settings dictionaries per tool section."""

from pyrevit import script


def _coerce(value, default):
    """Return value converted to the type of default (config stores text)."""
    if value is None:
        return default
    try:
        if isinstance(default, bool):
            return str(value).strip().lower() in ("true", "1", "yes")
        if isinstance(default, int):
            return int(float(value))
        if isinstance(default, float):
            return float(value)
        return str(value)
    except (TypeError, ValueError):
        return default


def load(section, defaults):
    """Saved values for section, falling back to defaults key by key."""
    cfg = script.get_config(section)
    values = {}
    for key, default in defaults.items():
        values[key] = _coerce(cfg.get_option(key, default), default)
    return values


def save(section, values):
    cfg = script.get_config(section)
    for key, value in values.items():
        setattr(cfg, key, value)
    script.save_config()
