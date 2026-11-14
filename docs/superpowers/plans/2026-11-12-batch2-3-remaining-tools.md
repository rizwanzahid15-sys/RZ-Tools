# Batches 2 & 3 — Remaining Seven Tools — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Junction Box, Convert Line, Connect Conduit, Multi Fillet, Home Run, Auto Dimension and Line Cutter to the Falcon Electrical panel.

**Architecture:** Same as batch 1 — every geometric decision is a Revit-free function in `falcon_geom.py` (pytest-covered); Revit work goes through `falcon_conduit.py` helpers and runs all-or-nothing per element (`falcon_conduit.all_or_nothing`) inside one `TransactionGroup` per run.

**Tech Stack:** pyRevit, IronPython 2.7, Revit API 2020–2027; CPython 3.12 + pytest + pyflakes offline.

**Spec:** `docs/superpowers/specs/2026-11-12-electrical-tools-design.md` (sections 5.4–5.10, 6, 7)

## Global Constraints

- Everything in the batch 1 plan's Global Constraints applies (IronPython 2.7 syntax, header blocks, feet internally / mm for users, one undo per run, per-element skip with reason, rollback + traceback on unexpected error).
- Must run on **Revit 2020–2027**: any API that changed between versions goes through a `getattr`/`try` fallback (e.g. `MEPModel.GetElectricalSystems()` 2021+ vs `MEPModel.ElectricalSystems` 2020).
- Conduit height for new conduits is set through `RBS_OFFSET_PARAM` (Middle Elevation, relative to the conduit's reference level), never by guessing level elevations.
- Annotation tools (Home Run, Auto Dimension, Line Cutter) only work in plan views (`ViewPlan`); other views → alert and exit.
- Tool markers: Line Cutter masks carry Comments = `FALCON_LINE_CUTTER`; Home Run text carries nothing special (plain text note).

## Review Focus

1. Convert Line on lines that touch at a straight continuation (collinear) must get a union, not an elbow or an error — test `test_joint_kind_collinear_is_union` (Task 1).
2. Multi Fillet bundles picked in opposite order (outer-first in one bundle, inner-first in the other) must still pair inner-with-inner — test `test_pair_bundles_inner_with_inner_any_order` (Task 2).
3. Connect Conduit to a device whose connector faces sideways at a different height must go vertical first, then horizontal — test `test_route_side_connector_vertical_first` (Task 1).
4. Auto Dimension with two bundles of parallel conduits far apart must make two dimension strings, not one spanning both — test `test_bundles_split_by_gap` (Task 2).
5. Home Run on a device with no circuit (no panel) → message, nothing drawn; label never prints "None" — test `test_home_run_label_missing_parts` (Task 2).

---

### Task 1: Geometry for Junction Box, Convert Line, Connect Conduit

**Files:** Modify `Falcon.extension/lib/falcon_geom.py`; Create `tests/test_falcon_geom_batch2.py`

**Interfaces (Produces):**
- `project_distance(p0, p1, point) -> float` — distance from p0 along p0→p1 of point's projection, clamped to [0, length].
- `snap_end(length, dist, snap) -> 0 | 1 | None` — 0 if `dist <= snap`, 1 if `dist >= length - snap`, else None.
- `joint_pairs(segments, tol) -> list[(i, end_i, j, end_j)]` — segments = list of `(p0, p1)`; every pair of ends (end index 0/1) closer than tol in 3D, i < j, each end used at most once.
- `joint_kind(dir_a, dir_b, tol_deg=1.0) -> "union" | "elbow"` — union when the plan directions are parallel (either sense) within tol_deg.
- `line_intersection_xy(a0, a1, b0, b1) -> point or None` — intersection of the two *infinite* lines in plan (z taken from a0), None when parallel.
- `route_points(end, target, target_facing) -> list[point]` — `[end, target]` if |dz| < 1e-3; else if `target_facing` is vertical (|z| > 0.7) → `[end, (target.x, target.y, end.z), target]`; else → `[end, (end.x, end.y, target.z), target]`.

- [ ] **Step 1: Failing tests**
  ```python
  def test_project_distance(): assert project_distance((0,0,0),(10,0,0),(4,3,0)) == 4; assert project_distance((0,0,0),(10,0,0),(-2,0,0)) == 0
  def test_snap_end(): assert snap_end(10,0.2,0.3) == 0 and snap_end(10,9.8,0.3) == 1 and snap_end(10,5,0.3) is None
  def test_joint_pairs():
      segs=[((0,0,0),(5,0,0)),((5,0,0),(5,5,0)),((9,9,0),(10,9,0))]
      assert joint_pairs(segs,0.01) == [(0,1,1,0)]
  def test_joint_kind_collinear_is_union():  # Review Focus 1
      assert joint_kind((1,0,0),(-1,0,0)) == "union"; assert joint_kind((1,0,0),(0,1,0)) == "elbow"
  def test_line_intersection_xy():
      assert line_intersection_xy((0,0,1),(2,0,1),(5,-3,0),(5,-1,0)) == pytest.approx((5,0,1))
      assert line_intersection_xy((0,0,0),(1,0,0),(0,1,0),(1,1,0)) is None
  def test_route_same_height(): assert route_points((0,0,1),(5,5,1),(1,0,0)) == [(0,0,1),(5,5,1)]
  def test_route_down_into_top_connector(): assert route_points((0,0,3),(5,5,1),(0,0,1)) == [(0,0,3),(5,5,3),(5,5,1)]
  def test_route_side_connector_vertical_first():  # Review Focus 3
      assert route_points((0,0,3),(5,5,1),(-1,0,0)) == [(0,0,3),(0,0,1),(5,5,1)]
  ```
- [ ] **Step 2:** run → FAIL. **Step 3:** implement. **Step 4:** run → PASS (whole suite).
- [ ] **Step 5: Commit** `feat: add geometry for junction box, convert line, connect conduit`

### Task 2: Geometry for Multi Fillet, Home Run, Auto Dimension, Line Cutter

**Files:** Modify `Falcon.extension/lib/falcon_geom.py`; Create `tests/test_falcon_geom_batch3.py`

**Interfaces (Produces):**
- `pair_bundles(lines_a, lines_b) -> list[(ia, ib)]` — lines = list of `(p0, p1)`. Corner P = `line_intersection_xy` of `lines_a[0]` and `lines_b[0]`. `dA` = unit plan direction of bundle A pointing away from P (toward the end of `lines_a[0]` farther from P); same for `dB`. Inside offset of an A line = dot(its midpoint − P, dB); of a B line = dot(midpoint − P, dA). Sort each bundle by inside offset descending and pair index by index. Raises `ValueError("bundles have different counts")` if lengths differ, `ValueError("bundles are parallel")` if no corner.
- `bundle_spacing(lines) -> float` — mean perpendicular distance between neighbours after sorting by perpendicular offset (0.0 for one line).
- `bundles(lines, gap) -> list[list[int]]` — group lines parallel (5°) whose perpendicular offset from the previous line in the sorted order is ≤ gap and whose projected extents overlap; order inside a bundle by perpendicular offset.
- `home_run_label(panel, circuit) -> str or None` — `"<panel>-<circuit>"`; None if panel empty/None; just panel if circuit empty/None.
- `arrow_points(start, toward, length, head) -> (shaft_end, left, right)` — in plan (z of start); arrow goes from start toward `toward` for `length`; head wings at ±30° back from shaft_end with length `head`.
- `mask_rect(center, lower_dir, along, across) -> list of 4 points` — rectangle centred on center, `along` measured on the lower conduit's plan direction, `across` perpendicular; z of center; counter-clockwise.

- [ ] **Step 1: Failing tests**
  ```python
  def test_pair_bundles_inner_with_inner_any_order():  # Review Focus 2
      A=[((0,2,0),(10,2,0)),((0,1,0),(10,1,0))]   # running in x, outer (y=2) listed first
      B=[((11,-10,0),(11,0,0)),((12,-10,0),(12,0,0))]  # running in y, inner (x=11) listed first
      # corner near (11..12, 1..2); inside = toward -y for A? bundle A goes away from corner toward -x, B toward -y
      assert sorted(pair_bundles(A,B)) == [(0,1),(1,0)]
  def test_pair_bundles_count_mismatch(): pytest.raises(ValueError, pair_bundles, [((0,0,0),(1,0,0))], [])
  def test_bundle_spacing(): assert bundle_spacing([((0,0,0),(5,0,0)),((0,0.3,0),(5,0.3,0)),((0,0.6,0),(5,0.6,0))]) == pytest.approx(0.3)
  def test_bundles_split_by_gap():  # Review Focus 4
      L=[((0,0,0),(5,0,0)),((0,0.2,0),(5,0.2,0)),((0,8,0),(5,8,0)),((0,8.2,0),(5,8.2,0))]
      assert bundles(L,1.0) == [[0,1],[2,3]]
  def test_bundles_no_overlap_split(): assert bundles([((0,0,0),(5,0,0)),((10,0.2,0),(15,0.2,0))],1.0) == [[0],[1]]
  def test_home_run_label_missing_parts():  # Review Focus 5
      assert home_run_label("LP-1","3,5") == "LP-1-3,5"; assert home_run_label("LP-1",None) == "LP-1"
      assert home_run_label(None,"3") is None; assert home_run_label("","3") is None
  def test_arrow_points():
      end,l,r = arrow_points((0,0,0),(10,0,0),2,0.5)
      assert end == pytest.approx((2,0,0)); assert l[0] < 2 and r[0] < 2 and l[1] == pytest.approx(-r[1])
  def test_mask_rect():
      pts = mask_rect((5,5,1),(1,0,0),2,0.4)
      assert sorted(pts) == sorted([pytest.approx(p) for p in [(4,4.8,1),(6,4.8,1),(6,5.2,1),(4,5.2,1)]])
  ```
  (The pair test's expected pairing must be confirmed by hand when implementing; the rule in Interfaces is binding — adjust the expected list only if the hand check shows the comment's geometry was mis-stated, and ledger it.)
- [ ] **Step 2–4:** FAIL → implement → PASS (whole suite).
- [ ] **Step 5: Commit** `feat: add geometry for fillet, home run, dimensions, line cutter`

### Task 3: falcon_conduit additions

**Files:** Modify `Falcon.extension/lib/falcon_conduit.py`

**Interfaces (Produces):**
- `place_box_at_end(doc, symbol, conduit, end_point) -> (inst, connected)` — place box, if it has ≥1 free conduit connector: rotate so that connector's BasisZ points from the end back along the conduit (toward the conduit body), move so the connector origin is on end_point, `ConnectTo` the conduit's end connector (raise on failure); else just align with the conduit (connected False).
- `connect_union(doc, c1, c2) -> FamilyInstance or None` — `doc.Create.NewUnionFitting` on the nearest connector pair.
- `set_middle_elevation(conduit, offset_ft)` — `RBS_OFFSET_PARAM`.
- `free_conduit_connector(element, near_point) -> Connector or None` — unconnected conduit-domain connector nearest point.
- `conduit_types(doc) -> list[(name, ElementType)]` — `FilteredElementCollector.OfClass(ConduitType)` sorted by name.
- `new_conduit(doc, type_id, level_id, p0, p1, diameter_ft) -> Conduit`.

- [ ] **Step 1:** implement. **Step 2:** pyflakes clean. **Step 3: Commit** `feat: add conduit helpers for batch 2`

### Task 4: Junction Box pushbutton (`D_JunctionBox.pushbutton`)

Flow: `box_symbols` → `forms.SelectFromList.show(labels, title=..., multiselect=False)` defaulting to the remembered label (section `falcon_junctionbox`, key `box_label`) → loop `PickObject(ObjectType.Element, ConduitFilter(), "Click a conduit where the junction box goes (Esc to finish)")`; for each pick: `dist = project_distance`; `snap_end(L, dist, mm_to_ft(300))` → 0/1: `place_box_at_end` at that end; None: `place_box` at the projected point. Each pick = one `all_or_nothing` inside the run's TransactionGroup (one Transaction per pick so the box appears immediately; the group is assimilated at Esc → one undo). Report count placed / connected / skipped.
- [ ] script.py, bundle.yaml → pyflakes → **Commit** `feat: add Junction Box tool`

### Task 5: Convert Line pushbutton (`C_ConvertLine.pushbutton`)

Flow: `CommandSwitchWindow` "Revit lines" / "CAD lines". Revit lines: pre-selection or `PickObjects(ObjectType.Element, CurveElementFilter)` (model + detail lines). CAD lines: `PickObjects(ObjectType.PointOnElement, ImportFilter)`, each ref → `ImportInstance.GetGeometryObjectFromReference(ref)`, transformed by `GetTotalTransform()`. Only `DB.Line` kept; arcs/others counted as skipped. Dialog `ConvertLine.xaml`: conduit type (combo), diameter mm (default 20), middle elevation mm (default 3000), ☑ add fittings at touching ends (default on). Remembered (section `falcon_convertline`). Level = `doc.ActiveView.GenLevel` (no level → alert). For each line: `new_conduit` with z = 0 points flattened, then `set_middle_elevation`. Then for `joint_pairs(segs, mm_to_ft(5))`: `joint_kind` → `connect_union` or `connect_elbow`; failure per joint listed, conduits kept (the conduits themselves are still valid). Report "Created N conduit(s), M fitting(s). Skipped: K arc/other line(s); joints that failed: …".
- [ ] script.py, ConvertLine.xaml, bundle.yaml → pyflakes + XAML parse → **Commit** `feat: add Convert Line tool`

### Task 6: Connect Conduit pushbutton (`B_ConnectConduit.pushbutton`)

Flow: pick conduit (`ConduitFilter`) near the end to connect → end = nearest end; pick target (`PickObject(ObjectType.Element, "Pick the conduit or device to connect to")`).
- Target conduit: if `joint_kind(dirA, dirB) == "union"` and the two lines are collinear in plan (perpendicular offset < 5 mm) and same height → move A's end to B's near end, `connect_union`. Else `X = line_intersection_xy`; if None → "These conduits are parallel but not in line". If heights differ by > 5 mm → "Different heights – not supported". Else set A's end and B's nearest end to X, `connect_elbow`.
- Target device: `free_conduit_connector(target, end)` (None → "No free conduit connector on that element"); `route_points(end, connector origin, connector BasisZ)`; first leg collinear with A (angle < 1°) → extend A instead of a new leg; else new legs with `new_conduit_like`; elbows between consecutive pieces; last leg end `ConnectTo` connector.
All inside `all_or_nothing`; one TransactionGroup. If no pattern fits: message, nothing changed.
- [ ] script.py, bundle.yaml → pyflakes → **Commit** `feat: add Connect Conduit tool`

### Task 7: Multi Fillet pushbutton (`H_MultiFillet.pushbutton`)

Flow: `PickObjects` bundle A ("Select the first group of parallel conduits, then Finish"), then bundle B. Counts differ / not two straight horizontal bundles → message. `pair_bundles` → for each pair (inner first): X = `line_intersection_xy`; trim/extend each conduit's end nearest X to X (`set_ends`), `connect_elbow`; then if the elbow has a writable instance parameter named "Bend Radius" (LookupParameter), set it to `inner_radius + k * bundle_spacing(A)` where inner_radius = the first elbow's value; else note "bend radius is set by the elbow family". Each pair all-or-nothing.
- [ ] script.py, bundle.yaml → pyflakes → **Commit** `feat: add Multi Fillet tool`

### Task 8: Home Run pushbutton (`G_HomeRun.pushbutton`)

Plan views only. Loop `PickObject` (elements with `MEPModel`) until Esc. Systems: `GetElectricalSystems()` if present else `ElectricalSystems`; first power system with `BaseEquipment`. Label `home_run_label(sys.PanelName, sys.CircuitNumber)`; None → listed "no circuit/panel". Arrow from device location point toward panel location (plan), `arrow_points(start, panel, length, mm_to_ft(150))`; draw 3 detail lines (`doc.Create.NewDetailCurve`) at the view's plane z (`view.GenLevel` plane via `SketchPlane` if present, else device z) ; text note `TextNote.Create(doc, view.Id, shaft_end + small offset, label, default TextNoteType)`. Length setting [600 mm] via Shift+click `config.py` (section `falcon_homerun`).
- [ ] script.py, config.py, bundle.yaml → pyflakes → **Commit** `feat: add Home Run tool`

### Task 9: Auto Dimension pushbutton (`A_AutoDimension.pushbutton`)

Plan views only. Conduits = straight, horizontal, from selection or all visible in the view. `bundles(lines, mm_to_ft(1000))`. Per bundle: direction d, perpendicular n; nearest parallel Grid (plan direction parallel within 1°, perpendicular distance ≤ 10 m) → reference `DB.Reference(grid)`; else nearest parallel wall within 10 m → its nearer side face reference (`HostObjectUtils.GetSideFaces`); none → skipped "no grid or wall within 10 m". References: grid/wall + `DB.Reference(conduit)` for each conduit in the bundle. Dimension line through the first conduit's midpoint moved along d by the offset setting [500 mm], running along n from the grid/wall to past the farthest conduit. `doc.Create.NewDimension(view, line, ReferenceArray)`; per-bundle all-or-nothing. Offset setting via Shift+click `config.py` (section `falcon_autodim`).
- [ ] script.py, config.py, bundle.yaml → pyflakes → **Commit** `feat: add Auto Dimension tool`

### Task 10: Line Cutter pushbutton (`F_LineCutter.pushbutton`)

Plan views only. Scope: selected conduits, else all conduits visible in the view. Delete previous filled regions in this view whose Comments = `FALCON_LINE_CUTTER`. Mask type: FilledRegionType named `Falcon Mask` (create by duplicating the first FilledRegionType: foreground = solid fill, white; background none; `IsMasking = True` where the property exists). For every crossing pair (`plan_intersection`): lower = smaller (z + r) top; rectangle `mask_rect(X, lower_dir, (upper_dia + 2*gap)/crossing_sin, lower_dia + mm_to_ft(20))` at the view plane z; `FilledRegion.Create(doc, type_id, view.Id, [CurveLoop])`; set its line style to `<Invisible lines>` when found; Comments = `FALCON_LINE_CUTTER`. Gap setting [50 mm] via Shift+click `config.py` (section `falcon_linecutter`). Report masks created / removed.
- [ ] script.py, config.py, bundle.yaml → pyflakes → **Commit** `feat: add Line Cutter tool`

### Task 11: Icons, README, checklists

- [ ] 7 icons (Pillow, scratch script); README sections for each tool; `docs/testing/<tool>.md` for each (setup, steps, expected, the Review Focus case, a "tested on Revit version: ____" line).
- [ ] Full verification: pytest + pyflakes + XAML parse + py3-only-syntax grep → **Commit** `docs: icons, README and checklists for batches 2-3`
