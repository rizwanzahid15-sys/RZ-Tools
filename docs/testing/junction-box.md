# Junction Box — test checklist

Tested on Revit version: ______  pyRevit version: ______

Setup: a 2-way (two conduit connectors) junction box family and a 1-connector
end box family loaded; a few straight conduits.

| # | Do this | Expect |
|---|---|---|
| 1 | Run with no box family (empty project) | "Load a junction box family first." |
| 2 | Run, choose the 2-way box, click the middle of a conduit | Box at the click, lined up, conduit cut and connected both sides |
| 3 | Click within 300 mm of a free conduit end with the end box | Box on the end, its connector joined to the conduit |
| 4 | Click several conduits, then Esc | All placed; message counts placed / connected |
| 5 | Ctrl+Z once | Every box from the run removed, conduits whole again |
| 6 | Run again | Last box type is listed first |
| 7 | Use a box whose connectors run along Y in the family | Still lines up (turned by its connectors), or reported as "could not be connected" — never a diagonal stub |
