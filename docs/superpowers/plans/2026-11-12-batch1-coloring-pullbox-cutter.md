# Batch 1 — Coloring, Pull Box, Conduit Cutter — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the shared conduit/colour libraries and the Coloring, Pull Box and Conduit Cutter pushbuttons to the RZ Tools pyRevit extension.

**Architecture:** All decision-making maths (walking a run, bend counting, crossing offsets, direction grouping, name sanitising) lives in Revit-free modules (`rzgeom.py`, `rznaming.py`) covered by pytest. Thin Revit-API modules (`rzconduit.py`, `rzcolor.py`, `rzsettings.py`) turn those decisions into model changes. Pushbutton scripts only collect input, call the libraries inside one `TransactionGroup`, and report.

**Tech Stack:** pyRevit, IronPython 2.7, Revit API (target Revit 2025, safe 2020–2027), WPF XAML via `pyrevit.forms.WPFWindow`; CPython 3.12 + pytest + pyflakes for offline checks.

**Spec:** `docs/superpowers/specs/2026-11-12-electrical-tools-design.md` (sections 2, 3, 4, 5.1–5.3, 6, 7)

## Global Constraints

- IronPython 2.7-safe syntax in every `.py` under `RZTools.extension/` (no f-strings, no type hints, no `print` statement, no `nonlocal`).
- `rzgeom.py` and `rznaming.py` import nothing from Revit/pyRevit/clr — stdlib `math` only.
- Every script/lib file starts with the same metadata header block style as `RZTools.extension/RZTools.tab/Markup.panel/D_RedlineMarkup.pushbutton/script.py` (Author: Rizwan Zahid, Target Revit 2020 - 2027, IronPython 2.7, Version 1.0.0, dates 2026-11-12).
- Internal lengths are Revit feet; user-facing lengths are mm or m. `1 ft = 304.8 mm` exactly.
- Each tool run is one `revit.TransactionGroup(...)` assimilated → single Ctrl+Z (Color Element excepted: commit per pick, like Markup).
- Per-element failures are caught, skipped, and listed in the final report as `<element id>: <reason>`; never abort the run for one element.
- Unexpected exception → roll back the TransactionGroup and show the traceback in the pyRevit output window.
- Filter names created by Coloring start with `RZ_COLOR_`.
- Defaults: pull box spacing 15 m, bends 2, after-bend offset 300 mm, bend angle window 80°–100°, vertical = more than 45° from horizontal; cutter clearance 50 mm, angle 30°, direction grouping tolerance 5°.

## Review Focus

1. Conduits in one bundle drawn in opposite directions (start/end swapped) must still be grouped together — test in Task 2.
2. User clicks the conduit near its *far* end instead of the panel end — tool must start from whichever end is nearest the click — test in Task 2.
3. A crossing too close to a conduit end to fit two 30° slopes → that conduit is skipped and reported, others still processed — test in Task 4.
4. A run shorter than the spacing with fewer bends than the limit → zero boxes and a clear "nothing needed" report, not an error — test in Task 3.
5. Family/type names containing characters Revit rejects in filter names (`: [ ] { } | ; < > ? ` ~ \`) → sanitised, still unique per family/type — test in Task 5.

---

### Task 1: Offline test harness + vector & unit helpers

**Files:**
- Create: `RZTools.extension/lib/rzgeom.py`
- Create: `tests/conftest.py`, `tests/test_rzgeom_basics.py`
- Create: `requirements-dev.txt` (`pytest`, `pyflakes`)

**Interfaces:**
- Produces (points/vectors are 3-tuples of floats):
  `mm_to_ft(mm) -> float`, `ft_to_mm(ft) -> float`, `m_to_ft(m) -> float`,
  `vsub(a, b)`, `vadd(a, b)`, `vscale(a, s)`, `vdot(a, b)`, `vlen(a)`, `vnorm(a)` (raises `ValueError` on zero length),
  `angle_between_deg(d1, d2) -> float` (0–180),
  `bend_angle_deg(out_a, out_b) -> float` = `180 - angle_between_deg(out_a, out_b)` (outward connector directions of a fitting; straight coupling → 0, 90° elbow → 90),
  `is_bend(angle_deg, lo=80.0, hi=100.0) -> bool`,
  `is_vertical(direction, max_deg=45.0) -> bool` (angle from horizontal plane > max_deg),
  `point_along(p0, p1, dist) -> point` (dist from p0 toward p1).

- [ ] **Step 1: Write failing tests** — `tests/conftest.py` inserts `RZTools.extension/lib` into `sys.path`. Tests:
  ```python
  def test_units(): assert mm_to_ft(304.8) == 1.0; assert m_to_ft(15) == pytest.approx(49.2126, abs=1e-4); assert ft_to_mm(1) == 304.8
  def test_bend_angles():
      assert bend_angle_deg((1,0,0),(-1,0,0)) == pytest.approx(0)
      assert bend_angle_deg((1,0,0),(0,1,0)) == pytest.approx(90)
      assert is_bend(90) and is_bend(80) and not is_bend(45) and not is_bend(0)
  def test_vertical():
      assert is_vertical((0,0,1)) and not is_vertical((1,0,0.2)) and is_vertical((1,0,2))
  def test_point_along(): assert point_along((0,0,0),(10,0,0),2.5) == pytest.approx((2.5,0,0))
  def test_vnorm_zero_raises(): pytest.raises(ValueError, vnorm, (0,0,0))
  ```
- [ ] **Step 2: Set up venv & run** — `python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-dev.txt`; add `.venv/` to `.gitignore`. Run `.venv/Scripts/python -m pytest tests -q` → FAIL (import error).
- [ ] **Step 3: Implement the functions above in `rzgeom.py`** with the header block; stdlib `math` only.
- [ ] **Step 4: Run** `.venv/Scripts/python -m pytest tests -q` → all pass.
- [ ] **Step 5: Commit** `feat: add rzgeom vector and unit helpers with tests`

### Task 2: Direction grouping, plan intersection, nearest end

**Files:** Modify `RZTools.extension/lib/rzgeom.py`; Create `tests/test_rzgeom_plan.py`

**Interfaces:**
- Produces:
  `nearest_end(p0, p1, pick) -> int` (0 or 1, by plan distance),
  `group_by_direction(dirs, tol_deg=5.0) -> list[list[int]]` (indices; `d` and `-d` are the same direction; compared in plan XY; groups ordered by first index),
  `plan_intersection(a0, a1, b0, b1) -> (t, u) or None` (segment params 0–1 in XY, None if parallel or no hit inside both segments),
  `crossing_sin(da, db) -> float` (|sin| of plan angle between directions).

- [ ] **Step 1: Failing tests**
  ```python
  def test_group_reversed_same():  # Review Focus 1
      g = group_by_direction([(1,0,0),(-1,0,0),(0,1,0),(1,0.03,0)])
      assert g == [[0,1,3],[2]]
  def test_nearest_end():  # Review Focus 2
      assert nearest_end((0,0,0),(10,0,0),(9,0.5,0)) == 1
      assert nearest_end((0,0,0),(10,0,0),(1,0,3)) == 0
  def test_plan_intersection():
      t,u = plan_intersection((0,0,0),(10,0,0),(4,-5,3),(4,5,3)); assert (t,u) == pytest.approx((0.4,0.5))
      assert plan_intersection((0,0,0),(10,0,0),(0,1,0),(10,1,0)) is None
      assert plan_intersection((0,0,0),(3,0,0),(4,-5,0),(4,5,0)) is None
  def test_crossing_sin(): assert crossing_sin((1,0,0),(1,1,0)) == pytest.approx(math.sqrt(0.5))
  ```
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat: add plan grouping and intersection helpers`

### Task 3: Pull box planner

**Files:** Modify `RZTools.extension/lib/rzgeom.py`; Create `tests/test_rzgeom_pullbox.py`

**Interfaces:**
- Consumes: nothing Revit. Input is a run as a list of dicts produced later by `rzconduit.trace_run`:
  `{"kind": "straight"|"bend"|"fitting"|"box", "length": float, "vertical": bool}` (`vertical` only meaningful for straights).
- Produces: `plan_pull_boxes(run, max_dist, max_bends, after_bend, start_bends=0) -> list[(seg_index, dist_along)]`

Algorithm (rules not determined by the signature):
```
dist = 0; bends = start_bends; pending = False   # pending = a box is owed at next horizontal straight
for i, seg in enumerate(run):
  kind "box": dist = 0; bends = 0; pending = False
  kind "bend": dist += length; bends += 1; if bends >= max_bends: pending = True
  kind "fitting": dist += length
  kind "straight":
    L = length; pos = 0.0   # pos = where the last box sits on this segment (or 0)
    if vertical: dist += L; if dist >= max_dist: pending = True; continue
    if pending:
        at = after_bend if L >= 2*after_bend else L/2
        place (i, at); pos = at; dist = 0; bends = 0; pending = False
    while dist + (L - pos) >= max_dist:
        at = pos + (max_dist - dist); place (i, at); pos = at; dist = 0; bends = 0
    dist += L - pos
```

- [ ] **Step 1: Failing tests** (units: metres for readability)
  ```python
  S=lambda L,v=False: {"kind":"straight","length":L,"vertical":v}
  B=lambda: {"kind":"bend","length":0.3,"vertical":False}
  def test_short_run_no_boxes():  # Review Focus 4
      assert plan_pull_boxes([S(10)],15,2,0.3) == []
  def test_distance_every_15():
      assert plan_pull_boxes([S(40)],15,2,0.3) == [(0,15),(0,30)]
  def test_two_bends_box_after_second():
      assert plan_pull_boxes([S(5),B(),S(3),B(),S(4)],15,2,0.3) == [(4,0.3)]
  def test_riser_counts_as_first_bend():
      assert plan_pull_boxes([S(5),B(),S(4)],15,2,0.3,start_bends=1) == [(2,0.3)]
  def test_short_segment_after_bends_uses_mid():
      assert plan_pull_boxes([B(),B(),S(0.4)],15,2,0.3) == [(2,0.2)]
  def test_existing_box_resets():
      assert plan_pull_boxes([S(10),{"kind":"box","length":0,"vertical":False},S(10)],15,2,0.3) == []
  def test_vertical_defers_to_next_horizontal():
      assert plan_pull_boxes([S(10),S(6,True),S(5)],15,2,0.3) == [(2,0.3)]
  ```
  Compare with `pytest.approx` on the distance values.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement per algorithm. **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat: add pull box placement planner`

### Task 4: Crossing offset geometry

**Files:** Modify `RZTools.extension/lib/rzgeom.py`; Create `tests/test_rzgeom_offset.py`

**Interfaces:**
- Produces:
  `required_rise(mover_z, mover_r, others, clearance, up) -> float` — `others` = list of `(z, r)`; up: `max(z+r) + clearance + mover_r - mover_z`; down: `min(z-r) - clearance - mover_r - mover_z`; returns `0.0` if the mover is already clear in the chosen direction.
  `offset_spans(length, crossings, run, end_clear) -> list[(s0, e0)]` — `crossings` = list of `(c, half_width)` along the mover (half_width already divided by `crossing_sin`); span per crossing = `(c - hw - run, c + hw + run)`; spans that overlap are merged; raises `ValueError("too close to end")` if any merged span has `s0 < end_clear` or `e0 > length - end_clear`.
  `dogleg_polyline(p0, p1, spans, rise, run) -> list[point]` — `[p0, A1, B1, C1, D1, A2, …, p1]` where A=`point_along(s0)`, B=`point_along(s0+run)`+rise z, C=`point_along(e0-run)`+rise z, D=`point_along(e0)`.
  `slope_run(rise, angle_deg) -> float` = `abs(rise) / tan(angle)`.

- [ ] **Step 1: Failing tests**
  ```python
  def test_rise_up_and_down():
      assert required_rise(0,0.05,[(0,0.05)],0.1,True) == pytest.approx(0.2)
      assert required_rise(0,0.05,[(0,0.05)],0.1,False) == pytest.approx(-0.2)
      assert required_rise(1.0,0.05,[(0,0.05)],0.1,True) == 0.0
  def test_slope_run_30(): assert slope_run(0.2,30) == pytest.approx(0.2/math.tan(math.radians(30)))
  def test_spans_merge_close_crossings():
      assert offset_spans(20,[(8,0.2),(9,0.2)],0.5,0.3) == [pytest.approx((7.3,9.7))]
  def test_spans_separate_far_crossings():
      assert len(offset_spans(20,[(4,0.2),(15,0.2)],0.5,0.3)) == 2
  def test_span_near_end_raises():  # Review Focus 3
      pytest.raises(ValueError, offset_spans, 10, [(0.5,0.2)], 0.5, 0.3)
  def test_dogleg_points():
      pts = dogleg_polyline((0,0,0),(10,0,0),[(4,6)],0.2,0.5)
      assert pts == [pytest.approx(p) for p in [(0,0,0),(4,0,0),(4.5,0,0.2),(5.5,0,0.2),(6,0,0),(10,0,0)]]
  ```
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat: add conduit crossing offset geometry`

### Task 5: Filter name sanitiser

**Files:** Create `RZTools.extension/lib/rznaming.py`, `tests/test_rznaming.py`

**Interfaces:**
- Produces: `PREFIX = "RZ_COLOR_"`; `filter_name(family, type_name=None) -> str` → `RZ_COLOR_<Family>` or `RZ_COLOR_<Family>__<Type>`; each forbidden char in ``\:{}[]|;<>?`~`` replaced by `_`; `parse_filter_name(name) -> (family, type_or_None) or None` (returns the sanitised parts; None if not RZ_COLOR_).

- [ ] **Step 1: Failing tests** (Review Focus 5)
  ```python
  def test_plain(): assert filter_name("PVC Box") == "RZ_COLOR_PVC Box"
  def test_type(): assert filter_name("Fixture","600x1200 - 120") == "RZ_COLOR_Fixture__600x1200 - 120"
  def test_forbidden(): assert filter_name("Box: 2-way [20mm]","T{1}") == "RZ_COLOR_Box_ 2-way _20mm___T_1_"
  def test_parse(): assert parse_filter_name("RZ_COLOR_A__B") == ("A","B"); assert parse_filter_name("Other") is None
  ```
- [ ] **Step 2–4:** FAIL → implement → PASS.
- [ ] **Step 5: Commit** `feat: add RZ colour filter naming`

### Task 6: Revit libraries — settings and colour

**Files:** Create `RZTools.extension/lib/rzsettings.py`, `RZTools.extension/lib/rzcolor.py`

**Interfaces:**
- `rzsettings.load(section, defaults) -> dict` (each key from `script.get_config(section).get_option(key, default)`); `rzsettings.save(section, values)` (setattr + `script.save_config()`).
- `rzcolor.eid_int(eid) -> int` (`.Value` if present else `.IntegerValue`).
- `rzcolor.pick_color(initial=None) -> DB.Color or None` — `Autodesk.Revit.UI.ColorSelectionDialog`; None on cancel.
- `rzcolor.color_override(doc, color) -> DB.OverrideGraphicSettings` — projection line colour + weight 6, surface foreground pattern = first solid fill `FillPatternElement`, surface foreground colour; cut line/fill same colour.
- `rzcolor.target_views(doc, include_3d) -> list[DB.View]` — for every non-template view: its template if `ViewTemplateId` valid else itself; plus unused templates; dedupe by id; skip sheets, schedules, legends, project browser/system views, views where `AreGraphicsOverridesAllowed()` is False; skip `ViewType.ThreeD` unless include_3d.
- `rzcolor.ensure_filter(doc, family_name, category_id, type_name=None) -> DB.ParameterFilterElement` — find by `rznaming.filter_name` or create; rules via `ParameterFilterRuleFactory.CreateEqualsRule(ElementId(BuiltInParameter.ALL_MODEL_FAMILY_NAME), value)` (try 2-arg, fall back to 3-arg with `True` for pre-2022), plus `ALL_MODEL_TYPE_NAME` when type_name, combined in one `ElementParameterFilter`.
- `rzcolor.apply_filter(views, filt, ogs) -> int` — `AddFilter` if missing, `SetFilterOverrides`, `SetFilterVisibility(True)`; count of views changed; per-view failures skipped.
- `rzcolor.rz_filters(doc) -> dict[name, ParameterFilterElement]`; `rzcolor.filter_color(doc, filt) -> DB.Color or None` (first view having it); `rzcolor.delete_filters(doc, filters) -> int`.
- `rzcolor.color_elements(doc, ids, color) -> (int, int)` — applies `color_override` via `rztools_markup.apply_override` in the active view and all non-template `View3D`; returns `(elements, views_3d)`.

- [ ] **Step 1:** Implement both modules with header blocks.
- [ ] **Step 2: Static check** `.venv/Scripts/python -m pyflakes RZTools.extension/lib/rzsettings.py RZTools.extension/lib/rzcolor.py` → no undefined names (unused-import warnings for clr references acceptable only if justified by a comment).
- [ ] **Step 3: Commit** `feat: add settings and colour Revit helpers`

### Task 7: Revit library — conduit helpers

**Files:** Create `RZTools.extension/lib/rzconduit.py`

**Interfaces:**
- Consumes: `rzgeom` (`bend_angle_deg`, `is_bend`, `is_vertical`, `vnorm`), `rzcolor.eid_int`.
- Produces:
  `xyz(t) -> DB.XYZ`, `tup(xyz) -> tuple`;
  `ends(conduit) -> (XYZ, XYZ)`; `outer_radius(conduit) -> float` (`RBS_CONDUIT_OUTER_DIAM_PARAM`/2, fallback `RBS_CONDUIT_DIAMETER_PARAM`/2);
  `end_connector(element, point) -> DB.Connector` (unused-or-used End connector nearest point);
  `new_conduit_like(doc, src, p0, p1) -> Conduit` (`Conduit.Create(doc, src.GetTypeId(), p0, p1, src.ReferenceLevel.Id)`, copy diameter, `RBS_CTC_SERVICE_TYPE`, comments, workset);
  `split_conduit(doc, conduit, point) -> Conduit` (original keeps p0→point; new piece point→p1 takes over every connection that was on the old p1 end);
  `connect_elbow(doc, c1, c2) -> FamilyInstance or None` (`doc.Create.NewElbowFitting` on the nearest connector pair; None + no exception if it fails);
  `classify_fitting(fi) -> "bend"|"fitting"|"box"|"branch"` (`>2` connectors → branch; category Electrical Fixtures/Equipment or family name containing "box"/"junction" (case-insensitive) → box; 2 connectors with `is_bend(bend_angle_deg(...))` → bend; else fitting);
  `trace_run(doc, conduit, start_point) -> list[dict]` — run items `{"kind", "length", "vertical", "element", "p_start", "p_end"}` from the nearest end of `conduit` (via `rzgeom.nearest_end`) following connected connectors; stops at an end with no connection, at a `branch` (appended as last item with kind "branch"), or at an element already visited; fitting length = distance between its two connector origins;
  `box_symbols(doc) -> list[(label, FamilySymbol)]` (categories Electrical Fixtures, Conduit Fittings, Electrical Equipment; those whose family name contains box/junction first; label `Family : Type`; sorted);
  `place_box(doc, symbol, conduit, point) -> (FamilyInstance, bool connected)` — activate symbol, `NewFamilyInstance(point, symbol, level, StructuralType.NonStructural)`, set `INSTANCE_ELEVATION_PARAM` = point.Z − level elevation, rotate about vertical axis through point to the conduit's plan angle; regenerate; if the instance has exactly 2 conduit connectors: `split_conduit` at point, pull each piece's touching end back to the matching box connector origin, `ConnectTo`; return connected flag.

- [ ] **Step 1:** Implement with header block.
- [ ] **Step 2:** `.venv/Scripts/python -m pyflakes RZTools.extension/lib/rzconduit.py` → clean.
- [ ] **Step 3: Commit** `feat: add conduit Revit helpers`

### Task 8: Coloring pushbutton

**Files:** Create `RZTools.extension/RZTools.tab/Graphics.panel/Coloring.pushbutton/{script.py,bundle.yaml,ColorFamily.xaml}`

**Interfaces:** Consumes `rzcolor.*`, `rznaming.*`, `rztools_markup` pick loop pattern.

- [ ] **Step 1: script.py** — `forms.CommandSwitchWindow.show(["Color Family", "Color Element"], message="What do you want to color?")`.
  - Color Element: `pick_color()`; preselection then `PickObject` loop (Esc ends), each pick its own `revit.Transaction("RZTools: Color Element")` calling `color_elements`; final `forms.alert("Colored N element(s) in view \"<name>\" and in M 3D view(s).")`.
  - Color Family: `ColorFamilyWindow(forms.WPFWindow)` loading `ColorFamily.xaml`: TextBox `search`, CheckBox `only_used` (default checked; used = family has at least one placed instance), TreeView `tree` of TreeViewItems whose headers are a horizontal StackPanel [CheckBox, 12×12 swatch Rectangle filled with current filter colour if any, TextBlock "Family  [Category]" / "Type"], CheckBox `also_3d`, Buttons `choose_btn`, `remove_btn`, `remove_all_btn`, `close_btn`, TextBlock `status`. Families from `FilteredElementCollector(doc).OfClass(DB.Family)` excluding annotation categories, plus system-family categories Conduits, Cable Trays, Pipes, Ducts (types grouped under their family name from `ALL_MODEL_FAMILY_NAME`). Search filters by substring on family or type name, case-insensitive.
  - Choose color: ticked type nodes → one filter per type; ticked family node with no ticked types → one family filter. In a TransactionGroup: `ensure_filter`, `apply_filter(target_views(doc, also_3d), …)`; refresh swatches; status `Colored <what> in N view(s).` + ` 3D views were left out.` when not ticked.
  - Remove from selected / Remove all: `delete_filters` (all = `rz_filters(doc).values()` after `forms.alert(..., yes=True, no=True)` confirm); status with count.
- [ ] **Step 2: bundle.yaml** — title `Coloring`, tooltip from spec 5.1, author Rizwan Zahid.
- [ ] **Step 3:** pyflakes on script.py → clean; XAML well-formed check: `.venv/Scripts/python -c "import xml.dom.minidom,sys;xml.dom.minidom.parse(sys.argv[1])" <xaml>`.
- [ ] **Step 4: Commit** `feat: add Coloring tool`

### Task 9: Pull Box pushbutton

**Files:** Create `RZTools.extension/RZTools.tab/Electrical.panel/I_PullBox.pushbutton/{script.py,bundle.yaml,PullBox.xaml}`

**Interfaces:** Consumes `rzgeom.plan_pull_boxes`, `rzgeom.m_to_ft`, `rzgeom.mm_to_ft`, `rzgeom.point_along`, `rzconduit.trace_run`, `rzconduit.box_symbols`, `rzconduit.place_box`, `rzsettings.load/save` (section `rztools_pullbox`, keys `distance_m=15`, `bends=2`, `riser=False`, `box_label=""`).

- [ ] **Step 1: script.py** — dialog (title "Pull Box", labels exactly: "Distance between pull boxes (m)", "Bends before a pull box", "The panel riser bend is hidden in plan, so it counts as the first bend", "Junction box", buttons Start/Cancel); validate distance > 0 and bends ≥ 1 (inline message, dialog stays open). No box families → alert "Load a junction box family first." and exit. `PickObject` with conduit-only `ISelectionFilter`, prompt "Click the conduit at the panel end". `trace_run` → `plan_pull_boxes(run, m_to_ft(d), bends, mm_to_ft(300), 1 if riser else 0)` → place boxes **from last to first** (so splitting doesn't shift earlier segments) at `point_along(seg.p_start, seg.p_end, dist)` on `seg.element`. One TransactionGroup "RZTools: Pull Box". Report: "Placed N pull box(es) along X m of conduit with Y bends." + branch note "Run branches at <id>; stopped there." + skipped list. Zero boxes → "No pull box needed: run is X m with Y bends."
- [ ] **Step 2: bundle.yaml** — title `Pull Box`.
- [ ] **Step 3:** pyflakes + XAML parse → clean.
- [ ] **Step 4: Commit** `feat: add Pull Box tool`

### Task 10: Conduit Cutter pushbutton

**Files:** Create `RZTools.extension/RZTools.tab/Electrical.panel/E_ConduitCutter.pushbutton/{script.py,config.py,bundle.yaml}`

**Interfaces:** Consumes `rzgeom` (`group_by_direction`, `plan_intersection`, `crossing_sin`, `required_rise`, `slope_run`, `offset_spans`, `dogleg_polyline`, `mm_to_ft`), `rzconduit` (`ends`, `outer_radius`, `new_conduit_like`, `connect_elbow`, `end_connector`), `rzsettings` (section `rztools_cutter`, `clearance_mm=50`, `angle_deg=30`).

- [ ] **Step 1: script.py**
  - Selection: straight conduits from pre-selection, else `PickObjects(ObjectType.Element, conduit_filter, "Select the crossing straight conduits, then click Finish")`.
  - `group_by_direction` → not exactly 2 groups → alert "Select two sets of conduits that cross each other." exit. Smaller group = mover; equal → `forms.alert("Both groups have N conduits. Which group should move?", options=["Group along <dir A>", "Group along <dir B>"])`.
  - `forms.alert("Which way should the smaller group of conduits go?", sub_msg="The group with fewer conduits is moved around the bigger group, so fewer conduits get offsets.", options=["Down - go under the other conduits", "Up - go over the other conduits"])`; None → exit.
  - Per mover: crossings = for each other conduit with a `plan_intersection` hit, `(t*L, (r_other + clearance + r_mover) / crossing_sin)`; no crossings → skip "does not cross". `rise = required_rise(...)`; 0 → skip "already clear". `run = slope_run(rise, angle)`; `spans = offset_spans(L, crossings, run, end_clear=2*r_mover + mm_to_ft(100))` (ValueError → skip with reason "crossing too close to the conduit end"). `pts = dogleg_polyline(...)`.
  - Build: remember connections on the old p1 end; set original curve to `pts[0]→pts[1]`; `new_conduit_like` for each consecutive pair after; move remembered connections to the last piece's end connector; `connect_elbow` for each consecutive pair (failure → listed, pieces left in place).
  - One TransactionGroup "RZTools: Conduit Cutter". Report: "Created N upward|downward offset(s) covering M crossing(s) with <angle>-degree elbows." + "Revit's conduit settings choose the fittings and minimum bend settings." + Skipped list.
- [ ] **Step 2: config.py** — `forms.ask_for_string` twice (clearance mm, angle °; angle must be 15–60, clearance ≥ 0) → `rzsettings.save`.
- [ ] **Step 3: bundle.yaml** — title `Conduit Cutter`, tooltip mentions Shift+click for settings.
- [ ] **Step 4:** pyflakes on both → clean.
- [ ] **Step 5: Commit** `feat: add Conduit Cutter tool`

### Task 11: Icons, README, manual test checklists

**Files:** Create `icon.png` (96×96, transparent) in the three new pushbutton folders; Create `docs/testing/coloring.md`, `docs/testing/pull-box.md`, `docs/testing/conduit-cutter.md`; Modify `README.md`.

- [ ] **Step 1: Icons** — generate with Pillow from a scratch script (not committed): Coloring = 4 coloured squares; Pull Box = conduit line with orange square at the end; Conduit Cutter = straight line crossed by a line with a 30° hump.
- [ ] **Step 2: Checklists** — each lists setup (Revit 2025 model with …), numbered steps, expected result, and the Review Focus case for that tool.
- [ ] **Step 3: README** — new "Electrical" and "Graphics" sections describing the three tools in modeller language + Shift+click settings + how to run offline tests.
- [ ] **Step 4: Full verification** — `.venv/Scripts/python -m pytest tests -q` → all pass; `.venv/Scripts/python -m pyflakes RZTools.extension` → no undefined names.
- [ ] **Step 5: Commit** `docs: add icons, README and test checklists for batch 1`
