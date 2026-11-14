# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Redline Markup
# Purpose        : Turn selected elements red in the active view only,
#                  for quick visual markup/redlining during coordination.
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Created Date   : 2026-08-04
# Updated Date   : 2026-08-04
# Status         : Production
#
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7
#
# Category       : BIM Automation
# Discipline     : All Disciplines
# Tool Type      : pyRevit Tool
#
# Input          : Tool Scope: Selection or interactive pick, Active View.
#                  Pre-select elements before running, or pick them one at
#                  a time after running (Esc to finish).
# Output         : View-specific graphic override (red projection line) on
#                  the active view only. Element geometry/material/other
#                  views are never touched.
#
# Dependencies   :
#   - pyRevit
#   - Revit API
#   - Falcon.extension/lib/rztools_markup.py
#
# Features       :
#   - Redlines elements already selected before the tool is run
#   - Or lets the user click elements one at a time, each turning red
#     the instant it is picked, until Esc
#   - Single undo step for the whole run
#   - View-only override - never changes the real element
#
# Notes          :
#   - Designed for production BIM workflows.
#   - IronPython 2.7-safe by default so it runs on every supported Revit version.
#
# Changelog
# ------------------------------------------------------------
# v1.0.0
# - Initial Release
#
# License        : Proprietary
# Copyright      : (c) Rizwan Zahid. All Rights Reserved
# ============================================================

from pyrevit import DB
import rztools_markup as markup

RED = DB.Color(255, 0, 0)

markup.run_markup_tool("Redline Markup", RED, "Falcon: Redline Markup")
