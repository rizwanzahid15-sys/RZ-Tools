# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Clear
# Purpose        : Remove the markup override (red or blue) from elements,
#                  in the active view only.
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
# Output         : Removes the view-specific graphic override on the active
#                  view only. Element geometry/material/other views are
#                  never touched.
#
# Dependencies   :
#   - pyRevit
#   - Revit API
#   - RZTools.extension/lib/rztools_markup.py
#
# Features       :
#   - Clears markup on elements already selected before the tool is run
#   - Or lets the user click elements one at a time, each cleared the
#     instant it is picked, until Esc
#   - Single undo step for the whole run
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

import rztools_markup as markup

markup.run_markup_tool("Clear", None, "RZTools: Clear Markup")
