# Falcon — pyRevit Extension

A pyRevit extension for electrical BIM work: quick visual markup, coloring,
and conduit automation (pull boxes, crossing offsets).

- **Markup** and **Graphics** tools only change how things *look* in views.
- **Electrical** tools change the model (they place boxes and cut conduits).
  Every Electrical run is one undo step — a single **Ctrl+Z** reverses it.

## Ribbon layout

The **Falcon** tab uses compact small buttons, stacked three high:

| Panel | Column 1 | Column 2 | Column 3 |
|---|---|---|---|
| **Electrical** | Connect Conduit, Convert Line, Multi Fillet | Junction Box, Pull Box, Conduit Cutter | Auto Dimension, Home Run, Line Cutter |
| **Graphics** | Coloring, **Markup ▾** (Redline Markup, Blue Markup, Clear) | | |

## Markup (Graphics panel → Markup ▾)

Every Markup tool changes only a **view-specific graphic override**
(`View.SetElementOverrides`). Nothing about the element itself — its material,
type, or appearance in any other view — is ever changed. Overrides are easy
to reverse: undo one at a time with Ctrl+Z, or run **Clear** to remove them.

### Tools

All three are in the **Markup ▾** dropdown on the **Graphics** panel.

### Redline Markup
Turns elements red in the active view.

### Blue Markup
Turns elements blue in the active view.

### Clear
Removes the color override from elements in the active view (whichever
color they were set to).

### How to use any of the three

- **Pre-select first:** select one or more elements in Revit, *then* click
  the tool — they update immediately.
- **Or run first, then pick:** click the tool with nothing selected, then
  click elements one at a time in the view. Each one updates the instant
  it's picked. Press **Esc** to stop picking.

Both approaches can be combined in the same run, and each click commits
immediately so the color change is visible right away (no waiting for Esc).

### Groups

If a picked element belongs to a Revit **Group**, the whole group is
recolored together — not just the one member you clicked.

## Graphics panel

### Coloring
Click it and choose:

- **Color Family** — a list of families and their types (search box, and
  "Only families that are used in the project"). Tick a family or some types,
  press **Choose color…** and pick a color in Revit's color dialog. The color
  is added as a view filter (named `FALCON_COLOR_…`) to every plan, section and
  elevation — on the view template where a view has one, so the color stays
  when templates are re-applied. 3D views are left alone unless you tick
  **Also apply in 3D views**. **Remove color from selected** and **Remove all
  Coloring colors** delete only the filters this tool made.
- **Color Element** — pick elements (or pre-select them); they are colored in
  the current view and in every 3D view. Esc to finish.

## Electrical panel

### Pull Box
Fill in the dialog — distance between pull boxes (default 15 m), bends before
a pull box (default 2), whether the panel riser bend counts as the first bend,
and which junction box type to use — press **Start**, then click the conduit
**at the panel end**. The tool follows the run through its elbows and places a
box every 15 m, or on the straight conduit 300 mm after every second 90° bend,
whichever comes first. An existing junction box on the run restarts the count;
a tee stops the walk. If the box family has two conduit connectors
(a "through / 2-way" box) the conduit is cut and connected to it. The dialog
remembers your last values.

### Conduit Cutter
Select the straight conduits that cross (or pick them and click **Finish**),
then choose **Up** (go over) or **Down** (go under). The smaller group is moved
around the bigger one: each of its conduits is cut and rebuilt with 30°
offsets so it clears the other group by 50 mm. Crossings close together share
one offset. Conduits that can't fit (crossing too close to the end, already
clear) are listed at the end and left untouched. Elbows come from the conduit
type's fitting settings.

**Shift+click** Conduit Cutter to change the clearance (mm) and elbow angle.

### Junction Box
Pick the box type (your last one is listed first), then click conduits. A
click mid-run places the box there — a 2-way box cuts the conduit and is
connected to both sides. A click within 300 mm of a conduit end puts the box
on the end and connects it. Esc to finish.

### Convert Line
Choose **Revit lines** (model/detail lines — pre-select or pick) or **CAD
lines** (pick lines inside a linked/imported DWG). Then pick the conduit
type, diameter and middle elevation above the current plan's level. Every
straight line becomes a conduit; where lines touch, an elbow (corner) or
coupling (straight on) is added. Arcs are skipped and counted. Your lines are
left in place.

### Connect Conduit
Click a conduit near the end you want to connect, then click the target:
- **another conduit in line** → joined with a coupling;
- **another conduit at an angle** (same height) → both trimmed/extended to
  the corner and joined with an elbow;
- **a device or box** → a conduit route into its free conduit connector
  (across then down for a top/bottom connector, down then across for a side
  connector).
Anything else is refused with a reason and nothing changes.

### Multi Fillet
Select the first group of parallel conduits (Finish), then the second group
(Finish). Each pair is trimmed/extended to its corner and joined with an
elbow — inner with inner, whatever order you picked them in. If the elbow
family has a writable **Bend Radius**, the bends are made concentric.

### Home Run (plan views)
Click circuited devices. For each one an arrow is drawn toward its panel with
a `Panel-Circuit` text note (e.g. `LP-1-3,5`). Devices with no circuit are
listed and skipped. **Shift+click** to set the arrow length (default 600 mm).

### Auto Dimension (plan views)
Dimensions the selected conduits — or every conduit in the view — to the
nearest parallel grid (or wall face if no grid is within 10 m). Side-by-side
conduits get one dimension string. **Shift+click** to set how far from the
conduit midpoint the dimension sits (default 500 mm).

### Line Cutter (plan views)
Where one conduit passes over another, a small white "Falcon Mask" region hides
the lower one so the crossing reads clearly. Only the view changes. Running it
again replaces the masks it made before in that view. **Shift+click** to set
the gap each side of the upper conduit (default 50 mm).

## Install

1. In Revit, open **pyRevit tab → Settings**.
2. Under **Custom Extension Directories**, add the folder that *contains*
   `Falcon.extension` (not the extension folder itself).
3. **Save Settings**, then fully close and reopen Revit (a plain
   **Reload** is not enough after adding a new extension directory for the
   first time).
4. The **Falcon** tab should appear with the **Electrical** and **Graphics**
   panels.

## Structure

```
Falcon.extension/
  Falcon.tab/
    Electrical.panel/
      A.stack/                      (column 1 - stack folders keep paths short)
        A_ConnectConduit.pushbutton/
        B_ConvertLine.pushbutton/
        C_MultiFillet.pushbutton/
      B.stack/
        A_JunctionBox.pushbutton/
        B_PullBox.pushbutton/
        C_ConduitCutter.pushbutton/ (config.py = Shift+click settings)
      C.stack/
        A_AutoDimension.pushbutton/ (config.py)
        B_HomeRun.pushbutton/       (config.py)
        C_LineCutter.pushbutton/    (config.py)
    Graphics.panel/
      A.stack/
        A_Coloring.pushbutton/
        B_Markup.pulldown/
          A_RedlineMarkup.pushbutton/
          B_BlueMarkup.pushbutton/
          C_Clear.pushbutton/
  lib/
    falcon_markup.py               (Markup tools)
    falcon_geom.py, falcon_naming.py          (pure maths/naming - tested offline)
    falcon_conduit.py, falcon_color.py        (Revit conduit and colour helpers)
    falcon_settings.py                   (remembered settings)
    falcon_view.py                       (plan-view / annotation helpers)
tests/                              (pytest: maths, naming, ribbon layout)
docs/testing/                       (manual test checklists for Revit)
```

The A_/B_/C_ prefixes set the order. Keep folder names short: Windows
can't open files whose full path is longer than 260 characters, and
`tests/test_ribbon_layout.py` checks for that.

## Offline tests

The maths behind Pull Box and Conduit Cutter runs without Revit:

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest tests -q
```

The Revit side is checked by hand with the lists in `docs/testing/`.

## Compatibility

IronPython 2.7-safe. The Markup tools only use APIs unchanged across Revit
2020–2027. The Graphics and Electrical tools are built and checked for
**Revit 2025** and handle the 2022 filter-rule and 2024 ElementId API
changes, so they are expected to work on 2020–2027.
