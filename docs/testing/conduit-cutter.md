# Conduit Cutter — test checklist

Tested on Revit version: ______  pyRevit version: ______

Setup: 4 parallel conduits running east–west at one height, crossed by 2
conduits running north–south at the same height (a clash). Conduit type has
an elbow family that supports any angle.

| # | Do this | Expect |
|---|---|---|
| 1 | Select one conduit only, run | "Select two sets of conduits that cross each other." |
| 2 | Select all 6, run, choose **Up** | The 2 north–south conduits rise over the 4 with 30° elbows; message "Created 2 upward offset(s) covering 8 crossing(s)…" |
| 3 | Measure gap in a section | 50 mm clear between the bottom of the raised conduits and the top of the 4 |
| 4 | Check both ends of a moved conduit | Still connected to whatever they were connected to before |
| 5 | Ctrl+Z | Everything back as it was (one undo) |
| 6 | Run again, choose **Down** | They go under instead |
| 7 | Draw a conduit in the other bundle **backwards** (start/end swapped) and run | Still grouped with its bundle (the 4), not treated as a third group |
| 8 | Move a crossing to 100 mm from a conduit end and run | That conduit listed under "Skipped: … crossing too close to the conduit end"; others still done |
| 9 | Select 2 and 2 (equal groups) | Asked which group should move |
| 10 | Shift+click, set 100 mm and 45° | Saved message; next run uses 100 mm and 45° elbows |
| 11 | Shift+click, enter 90 for the angle | "Enter a number from 15 to 60." and nothing saved |
