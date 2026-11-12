# Auto Dimension — test checklist

Tested on Revit version: ______  pyRevit version: ______

Setup: plan with grids; a bundle of 3 parallel conduits near a grid; another
bundle 8 m away; one conduit far from any grid but near a wall.

| # | Do this | Expect |
|---|---|---|
| 1 | Run with nothing selected | One dimension string per bundle (not one spanning both) (Review Focus 4), from the nearest parallel grid through each conduit |
| 2 | Check the far conduit | Dimensioned to the wall face |
| 3 | Conduit with no grid/wall within 10 m | Listed "no parallel grid or wall within 10 m" |
| 4 | Select only one bundle and run | Only that bundle dimensioned |
| 5 | Shift+click, set 1500 | Dimension line sits 1500 mm along the run from the midpoint |
| 6 | Ctrl+Z | All dimensions from the run removed |
| 7 | **Important:** check the dimension really snaps to the conduit centreline | Witness line on each conduit centre. If Revit refuses conduit references, every bundle is listed as skipped - report this |
| 8 | A grid hidden in this view near the conduits | Not used; the next visible grid or a wall is used |
