# Line Cutter — test checklist

Tested on Revit version: ______  pyRevit version: ______

Setup: plan view; conduit A at 3000 mm crossing conduit B at 2700 mm; two
conduits crossing at the same height.

| # | Do this | Expect |
|---|---|---|
| 1 | Run | B (lower) is hidden under a small white mask where A passes; A stays continuous (its edges are redrawn in thin black "Falcon Line Cutter" lines); no mask on the same-height pair |
| 2 | Look for mask outline | No visible border (invisible lines) |
| 3 | Run again | Message "Replaced N mask(s) from the last run"; no duplicates |
| 4 | Shift+click, set 100 | Masks are wider next run |
| 5 | Check another view | Unchanged (view-only) |
| 6 | Ctrl+Z | Masks from that run removed |
| 7 | Two conduits crossing at a very shallow angle (under 10°) | No mask (skipped on purpose) |
| 8 | Revit in another language | Mask border still invisible |
