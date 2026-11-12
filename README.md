# RZ Tools — pyRevit Extension

A pyRevit extension for electrical BIM work: quick visual markup, coloring,
and conduit automation (pull boxes, crossing offsets).

- **Markup** and **Graphics** tools only change how things *look* in views.
- **Electrical** tools change the model (they place boxes and cut conduits).
  Every Electrical run is one undo step — a single **Ctrl+Z** reverses it.

## Markup panel

Every Markup tool changes only a **view-specific graphic override**
(`View.SetElementOverrides`). Nothing about the element itself — its material,
type, or appearance in any other view — is ever changed. Overrides are easy
to reverse: undo one at a time with Ctrl+Z, or run **Clear** to remove them.

### Tools

All three live on the **RZ Tools** ribbon tab, **Markup** panel.

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
  is added as a view filter (named `RZ_COLOR_…`) to every plan, section and
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

## Install

1. In Revit, open **pyRevit tab → Settings**.
2. Under **Custom Extension Directories**, add the folder that *contains*
   `RZTools.extension` (not the extension folder itself).
3. **Save Settings**, then fully close and reopen Revit (a plain
   **Reload** is not enough after adding a new extension directory for the
   first time).
4. The **RZ Tools** tab should appear with the **Markup**, **Electrical** and
   **Graphics** panels.

## Structure

```
RZTools.extension/
  RZTools.tab/
    Markup.panel/
      Clear.pushbutton/
      D_RedlineMarkup.pushbutton/   (D_ prefix forces ribbon order: Clear, Redline, Blue)
      E_BlueMarkup.pushbutton/
    Electrical.panel/
      E_ConduitCutter.pushbutton/   (config.py = Shift+click settings)
      I_PullBox.pushbutton/
    Graphics.panel/
      Coloring.pushbutton/
  lib/
    rztools_markup.py               (Markup tools)
    rzgeom.py, rznaming.py          (pure maths/naming - tested offline)
    rzconduit.py, rzcolor.py        (Revit conduit and colour helpers)
    rzsettings.py                   (remembered settings)
tests/                              (pytest tests for rzgeom / rznaming)
docs/testing/                       (manual test checklists for Revit)
```

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
