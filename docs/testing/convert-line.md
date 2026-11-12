# Convert Line — test checklist

Tested on Revit version: ______  pyRevit version: ______

Setup: plan view; an L of model lines, two lines end-to-end in a straight
line, one arc; a linked DWG with lines.

| # | Do this | Expect |
|---|---|---|
| 1 | Run from a 3D view | "Open a plan view first…" |
| 2 | Revit lines → select the L + straight pair + arc → type/20 mm/3000 mm/fittings on | 4 conduits at 3000 mm above the level; elbow at the L corner; **coupling** (not elbow) between the straight pair (Review Focus 1); "Skipped 1 arc…" |
| 3 | Check Middle Elevation of a new conduit | 3000 mm |
| 4 | CAD lines → pick DWG lines | Conduits lie exactly on the DWG lines (not offset) |
| 5 | Ctrl+Z | All new conduits gone; original lines still there |
| 6 | Run again | Dialog shows last values |
| 7 | Pick two segments of the same DWG polyline | One conduit per segment (no doubles) |
| 8 | DWG lines with a 1-5 mm gap at a corner | Elbow still added |
| 9 | Type a diameter that is not a catalogue size (e.g. 23) | Note what Revit does (rounds to a size or keeps 23) |
