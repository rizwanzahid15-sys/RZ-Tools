# Pull Box — test checklist

Tested on Revit version: ______  pyRevit version: ______

Setup: a junction box family with "box" in its name and **two conduit
connectors** (a through / 2-way box) loaded; a conduit run from a panel with
straight lengths and 90° elbows, total about 40 m with 3–4 bends.

| # | Do this | Expect |
|---|---|---|
| 1 | Click **Pull Box** with no box family loaded (empty test project) | "Load a junction box family first." |
| 2 | Click **Pull Box** | Dialog: 15 / 2 / riser unticked / box type list showing only box families |
| 3 | Type `abc` in distance, Start | Red message, dialog stays open |
| 4 | Start with 15 / 2, click the conduit near the panel | Boxes placed: one every 15 m, or 300 mm after the 2nd bend; message gives count, length, bends |
| 5 | Check a placed box | At conduit height, lined up with the conduit, conduit cut and connected on both sides |
| 6 | Ctrl+Z | All boxes gone, conduits whole again (one undo) |
| 7 | Run again but click the conduit near its **far** end | Counting starts from the clicked (far) end |
| 8 | Tick the riser option | First box comes one bend earlier |
| 9 | Run on a short run (< 15 m, 1 bend) | "No pull box needed: run is X m with 1 bend(s)." |
| 10 | Run on a run that has a tee | Boxes up to the tee, message "Run branches at …; stopped there." |
| 11 | Run on a run that already has a junction box in the middle | Count restarts after the existing box |
| 12 | Use a box family with no connectors | Boxes placed on the conduit without cutting; message says so |
| 13 | Run the tool again | Dialog shows the last values you used |
