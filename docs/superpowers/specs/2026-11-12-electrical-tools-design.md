# Falcon — Electrical & Graphics Tools — Design Spec

Date: 2026-11-12
Status: Draft — awaiting review
Source: LinkedIn demo video (Pull Box, Conduit Cutter, Coloring shown working)
plus a ribbon screenshot naming 7 more tools whose behaviour was agreed in chat
from their names (marked *agreed from name*).

## 1. Goal

Add ten conduit-focused tools to the existing **Falcon** pyRevit extension so
that electrical BIM modellers stop doing repetitive conduit work by hand:
pull boxes, crossings, coloring, conversion from CAD, connecting, filleting,
home runs, dimensions and plan line breaks.

Success = each tool runs from the Falcon tab in Revit 2025 on a real
electrical model, does the job in one click-flow, and is fully undoable with a
single Ctrl+Z.

## 2. Constraints & conventions (from the existing extension)

- pyRevit, **IronPython 2.7**-safe code (same as current Markup tools), target
  Revit 2020–2027, tested primarily on **Revit 2025**.
- Same file header block as existing scripts (Tool Metadata comment block).
- Shared logic lives in `Falcon.extension/lib/` modules; pushbutton
  `script.py` files stay thin.
- Never change elements the user did not ask about. View-only changes
  (overrides/filters) are preferred where the tool is graphical.
- Each run = one `TransactionGroup` (assimilated) → one Ctrl+Z.
  Exception: Color Element follows the existing Markup behaviour (commit per pick).
- `ElementId` integer access via a helper that uses `.Value` (2024+) or
  `.IntegerValue` (older).
- Lengths shown to the user in **mm / m**; internal Revit units are feet,
  converted with `DB.UnitUtils`.

## 3. Ribbon layout

```
Falcon.tab/
  Markup.panel/          (existing — unchanged)
  Electrical.panel/
    A_AutoDimension.pushbutton
    B_ConnectConduit.pushbutton
    C_ConvertLine.pushbutton
    D_JunctionBox.pushbutton
    E_ConduitCutter.pushbutton
    F_LineCutter.pushbutton
    G_HomeRun.pushbutton
    H_MultiFillet.pushbutton
    I_PullBox.pushbutton
  Graphics.panel/
    Coloring.pushbutton
```

Each pushbutton has `script.py`, `bundle.yaml`, `icon.png`; tools with saved
settings also have `config.py` (pyRevit runs it on **Shift+click**).

## 4. Shared library modules

| Module | Purpose | Revit-free? |
|---|---|---|
| `falcon_geom.py` | Pure maths: points/vectors as tuples, walk distance along a polyline, offset (dogleg) geometry, angle between directions, segment–segment intersection in plan, grouping by direction | **Yes** — unit-tested with CPython/pytest |
| `falcon_conduit.py` | Revit conduit helpers: get/set ends, diameter, type, level; copy a conduit; split a conduit at a point (create second piece + reconnect far end); trace a run through fittings; elbow/fitting angle; connect two conduits with an elbow | No |
| `falcon_settings.py` | Read/write per-tool saved settings via `pyrevit.script.get_config()` with defaults | No |
| `falcon_markup.py` | Existing — reused by Color Element | No |
| `falcon_color.py` | Filter create/find/remove, apply to views & templates, element override builder (line + solid surface fill) | No |

Splitting a conduit (no `BreakCurve` API exists for conduits): shorten the
original to the split point, create a new conduit of the same type/diameter/
level from the split point to the old end, move any connection at the old end
to the new piece, copy key instance parameters (comments, mark-free ones,
service type, workset).

## 5. Tools

### 5.1 Coloring (Graphics panel) — *seen in video*

Start window: **Color Family** / **Color Element**.

**Color Element**
- Pre-selected elements + pick loop (Esc to finish), like Markup tools.
- Revit `ColorSelectionDialog` once at start.
- Override = projection line color + surface foreground solid fill color.
- Applied to the active view **and** all non-template 3D views.
- Status: "Colored N element(s) in view X and in M 3D view(s)".

**Color Family** (WPF window)
- Search box, "Only families that are used in the project" (default on),
  tree: Family [Category] → Types, each node with checkbox + color swatch if
  already colored.
- "Also apply in 3D views" (default off).
- **Choose color…** → `ColorSelectionDialog` → for each ticked family/type:
  create/update a `ParameterFilterElement` named `FALCON_COLOR_<Family>` or
  `FALCON_COLOR_<Family>__<Type>`; category = the family's category; rule = family
  name equals / type name equals (`ALL_MODEL_FAMILY_NAME`,
  `ALL_MODEL_TYPE_NAME`).
- Filter added (with override) to every graphical view that supports filters.
  If a view has a template, the filter goes on the template instead (each
  template once). 3D views skipped unless ticked.
- **Remove color from selected** → remove those Falcon filters from all views and
  delete them. **Remove all Coloring colors** → delete all `FALCON_COLOR_*` filters.
- Status line: "Colored type X in N view(s). 3D views were left out."

### 5.2 Pull Box (Electrical) — *seen in video*

Dialog: Distance between pull boxes (m) [15], Bends before a pull box [2],
☐ "Panel riser bend is hidden in plan, so it counts as the first bend",
Junction box (family : type list of Electrical Fixtures / Conduit Fittings /
Electrical Equipment families with "box" or "junction" in name, else all
those). Last values remembered.

Flow: click a conduit near its **panel end** → nearest end = start. Trace the
run through connectors (conduit → fitting → conduit …).
- Distance counter adds conduit lengths and fitting path lengths.
- A fitting is a **bend** if its connector directions differ by 80°–100°.
- Place a box when distance reaches the limit (box at that exact point) or
  when the bend count reaches the limit (box on the next straight conduit,
  300 mm past the elbow, or mid-length if the conduit is shorter than 600 mm).
  Counters reset at every box and at any existing junction box on the run.
- Tee/cross fitting → stop and report "Run branches at <id>; stopped".
- Vertical conduits (>45° from horizontal): never place there; skip forward.

Placement: level-based instance at conduit centre elevation, rotated to the
conduit direction. If the family has exactly 2 conduit connectors, split the
conduit at the box and connect both sides; otherwise place only.

Report: "Placed N pull box(es) along X m of conduit with Y bends."

### 5.3 Conduit Cutter (Electrical) — *seen in video*

Select crossing straight conduits (pick loop with Finish/Cancel, pre-selection
accepted) → split into two direction groups (directions within 5°). Not
exactly two groups → explain and stop. Smaller group moves (tie → ask which).

Dialog: "Which way should the smaller group of conduits go?" **Down** (under)
/ **Up** (over).

Geometry per moving conduit: rise Δ so its outside is `clearance` clear of the
other group's outside (top or bottom); horizontal length of each slope =
Δ / tan(angle). Crossings closer than 2 × slope length are merged into one
offset. Pieces: original → slope → raised run → slope → new piece of the
original. Joints joined with `NewElbowFitting` (routing preferences choose the
elbow). Not enough straight length → skip that conduit and list it.

Settings (Shift+click): clearance [50 mm], angle [30°].
Report: "Created N upward/downward offset(s) covering M crossing(s) with 30°
elbows. Skipped: …"

### 5.4 Junction Box (Electrical) — *agreed from name*

Choose box type (same list as Pull Box, remembered) → click points on
conduits; each click places a box at that point on the conduit, aligned and
at conduit elevation, splitting + connecting if 2-way (same placement code as
Pull Box). Clicking near a conduit **end** places the box at the end and
connects it if the family has a connector. Esc to finish.

### 5.5 Convert Line (Electrical) — *agreed from name*

Select model lines, detail lines, or lines inside a linked/imported CAD
(pick by sub-element for CAD). Dialog: conduit type, diameter, middle
elevation (mm, from the active view's level), ☑ add elbows at connected
corners. Creates a conduit for every straight line (arcs: converted as
straight segments chord-wise is **out of scope** — arcs are skipped and
counted). Touching ends within 5 mm get an elbow. Original lines are left
in place.

### 5.6 Connect Conduit (Electrical) — *agreed from name*

Pick a conduit end, then a target: another conduit or any element with an
unused electrical/conduit connector (device, box, panel).
- Conduit → conduit, collinear: join with a union/coupling.
- Conduit → conduit, at an angle in plan with intersecting lines: extend/trim
  both to the intersection and add an elbow.
- Conduit → device/box: route from the conduit end horizontally to above/
  below the connector, then vertically down/up into it, with elbows.
If no route fits these three patterns, say so and change nothing.

### 5.7 Line Cutter (Electrical) — *agreed from name*

Plan readability: in the active plan view, where conduits cross, hide a short
piece of the **lower** conduit's lines so the upper one reads on top. Done
with detail-level masking: place a masking region (white/no-line filled
region of type "Falcon Mask", created if missing) sized
`upper diameter + 2 × gap` across the lower conduit at each crossing.
Gap setting [50 mm]. Scope: selection or whole view. Re-running removes
previous Falcon masks in that view first. No model change.

### 5.8 Home Run (Electrical) — *agreed from name*

Pick the last device of a circuit (or a conduit end) → tool reads the device's
electrical system (panel + circuit number) → draws a home-run arrow toward
the panel (detail line with arrowhead from a detail component "Falcon Home Run
Arrow" if loaded, else a detail line + filled triangle) with a saved length
setting [600 mm, model length] and places a text note
"<Panel>-<Circuit>" beside it. Direction: from the device toward the panel's
location in plan. Device with no circuit → message, nothing drawn.

### 5.9 Multi Fillet (Electrical) — *agreed from name*

Select two bundles of parallel conduits that meet at a corner (pairs matched
by order across the bundle, each pair ends must meet/intersect in plan).
Each pair is trimmed/extended to its intersection and joined with an elbow;
the bend radius of each elbow grows outward so bends are concentric
(inner = fitting default, each next one + spacing). Spacing taken from the
existing conduit spacing. Counts must match, else stop with a message.

### 5.10 Auto Dimension (Electrical) — *agreed from name*

Select conduits (or all in view) in a plan → for each straight conduit (and
each parallel bundle), create one dimension string across it to the nearest
grid line (or wall face if no grid within 10 m) perpendicular to the run,
placed at the conduit's midpoint offset by a setting [500 mm]. Bundles get
one chain dimension through all conduits. Uses conduit centreline references.

## 6. Error handling

- No document / wrong view type (e.g. Home Run in 3D) → alert and exit.
- Every per-element failure is caught, skipped, and listed in the final report
  (element id + reason), never a crash mid-run.
- Any unexpected exception rolls back the whole TransactionGroup and shows the
  error in the pyRevit output window.

## 7. Testing

- `lib/falcon_geom.py` is Revit-free and covered by **pytest** tests in `tests/`
  (walk along polyline, dogleg geometry, bend classification, direction
  grouping, plan intersection, merge of close crossings).
- Each tool gets a manual test checklist in `docs/testing/<tool>.md` for the
  user to run in Revit 2025 on a sample model.

## 8. Delivery order

1. **Batch 1:** `falcon_geom`, `falcon_conduit`, `falcon_settings`, `falcon_color`; Coloring,
   Pull Box, Conduit Cutter.
2. **Batch 2:** Junction Box, Convert Line, Connect Conduit.
3. **Batch 3:** Multi Fillet, Home Run, Auto Dimension, Line Cutter.

Each batch ends with tests passing, a commit, and README updated.

## 9. Out of scope

Arcs in Convert Line, cable trays, auto-routing around obstacles, panel
schedules, recreating the video author's exact UI look or branding.
