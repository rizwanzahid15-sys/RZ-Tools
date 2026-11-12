# Multi Fillet — test checklist

Tested on Revit version: ______  pyRevit version: ______

Setup: 3 parallel conduits running east (not reaching the corner) and 3
parallel conduits running north, same height, forming an L corner.

| # | Do this | Expect |
|---|---|---|
| 1 | Select 3, Finish, then 2, Finish | "Select the same number…" |
| 2 | Select group 1 outer-first, Finish; group 2 inner-first, Finish | 3 elbows, inner joined to inner (no crossing conduits) (Review Focus 2) |
| 3 | Look at the bends | Concentric if the elbow family has a writable Bend Radius; otherwise message says they may not be |
| 4 | Two groups running the same direction | "…they don't meet at a corner." |
| 5 | Ctrl+Z | All back as before |
