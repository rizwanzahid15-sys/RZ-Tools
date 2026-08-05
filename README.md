# RZ Tools — pyRevit Extension

A small pyRevit extension for quick visual markup during coordination — color
elements in the active view without touching the real model.

## What it does

Every tool here changes only a **view-specific graphic override**
(`View.SetElementOverrides`). Nothing about the element itself — its material,
type, or appearance in any other view — is ever changed. Overrides are easy
to reverse: undo one at a time with Ctrl+Z, or run **Clear** to remove them.

## Tools

All three live on the **RZ Tools** ribbon tab, **Markup** panel.

### Redline Markup
Turns elements red in the active view.

### Blue Markup
Turns elements blue in the active view.

### Clear
Removes the color override from elements in the active view (whichever
color they were set to).

## How to use any of the three

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

## Install

1. In Revit, open **pyRevit tab → Settings**.
2. Under **Custom Extension Directories**, add the folder that *contains*
   `RZTools.extension` (not the extension folder itself).
3. **Save Settings**, then fully close and reopen Revit (a plain
   **Reload** is not enough after adding a new extension directory for the
   first time).
4. The **RZ Tools** tab should appear with **Clear**, **Redline Markup**,
   and **Blue Markup** in that order.

## Structure

```
RZTools.extension/
  RZTools.tab/
    Markup.panel/
      Clear.pushbutton/
      D_RedlineMarkup.pushbutton/   (D_ prefix forces ribbon order: Clear, Redline, Blue)
      E_BlueMarkup.pushbutton/
  lib/
    rztools_markup.py               (shared logic used by all three tools)
```

## Compatibility

IronPython 2.7-safe. Only uses `OverrideGraphicSettings`, `Transaction`,
`PickObject`, and `Group` — none of which changed across Revit 2020–2027 —
so one script source runs on any Revit version pyRevit itself supports.
