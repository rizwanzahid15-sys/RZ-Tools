# Home Run — test checklist

Tested on Revit version: ______  pyRevit version: ______

Setup: a panel and devices circuited to it (e.g. LP-1 circuits 3 and 5); one
device not on any circuit.

| # | Do this | Expect |
|---|---|---|
| 1 | Run in a 3D view | "Open a plan view first." |
| 2 | In plan, click a circuited device, Esc | 600 mm arrow pointing toward the panel + note like `LP-1-3` |
| 3 | Click the uncircuited device | Listed "not on a circuit with a panel", nothing drawn, never "None" (Review Focus 5) |
| 4 | Shift+click, set 1000 | Next arrows are 1000 mm |
| 5 | Ctrl+Z after a run with several devices | All arrows and notes from that run removed |
| 6 | Test on Revit 2020 and on 2022+ | Works on both (different circuit API) |
| 7 | Click a device that is not on a circuit | Listed in the message; no red error window |
| 8 | Click a sub-panel | Arrow points to the panel that feeds it, not to a circuit it feeds |
