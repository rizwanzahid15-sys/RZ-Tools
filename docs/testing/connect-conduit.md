# Connect Conduit — test checklist

Tested on Revit version: ______  pyRevit version: ______

Setup: two conduits in line with a gap; two conduits at 90° not touching
(same height); a device/box with a free conduit connector on top, another with
a side connector, both lower than a conduit.

| # | Do this | Expect |
|---|---|---|
| 1 | Click the in-line pair (near the gap ends) | Joined with a coupling |
| 2 | Click the 90° pair | Both trimmed/extended to the corner, elbow added |
| 3 | Conduit → device with top connector | Conduit goes across above the device, then down into it, elbows at the turns |
| 4 | Conduit → device with side connector, lower | Goes down first, then across into the side (Review Focus 3) |
| 5 | Two parallel conduits side by side (not in line) | "Not connected: these conduits are parallel but not in line. Nothing was changed." |
| 6 | Click an end that is already connected | Refused with reason, nothing changed |
| 7 | Ctrl+Z after a success | Back to how it was |
