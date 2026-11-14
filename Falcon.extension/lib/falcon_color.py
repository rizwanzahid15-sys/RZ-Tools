# ============================================================
# Shared Library
# ============================================================
# Module Name    : falcon_color
# Purpose        : Colour overrides and FALCON_COLOR_* view filters for the
#                  Coloring tool.
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Created Date   : 2026-11-12
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7
# ============================================================
"""Revit-side colour helpers.

Color Family works through view filters (one per family or type) so the
colour follows every element of that family, including ones placed later.
Color Element works through per-element view overrides.
"""

from System.Collections.Generic import List

from pyrevit import DB
from Autodesk.Revit.UI import ColorSelectionDialog, ItemSelectionDialogResult

import falcon_naming
import falcon_markup

# View types that can carry filters and are worth colouring.
PLAN_LIKE_TYPES = (
    DB.ViewType.FloorPlan,
    DB.ViewType.CeilingPlan,
    DB.ViewType.EngineeringPlan,
    DB.ViewType.AreaPlan,
    DB.ViewType.Section,
    DB.ViewType.Elevation,
    DB.ViewType.Detail,
)


def eid_int(eid):
    """Integer value of an ElementId on every Revit version."""
    value = getattr(eid, "Value", None)
    if value is not None:
        return int(value)
    return int(eid.IntegerValue)


def pick_color(initial=None):
    """Revit's colour dialog. Returns DB.Color, or None if cancelled."""
    dlg = ColorSelectionDialog()
    if initial is not None:
        dlg.OriginalColor = initial
        dlg.SelectedColor = initial
    if dlg.Show() == ItemSelectionDialogResult.Confirmed:
        return dlg.SelectedColor
    return None


def _solid_fill_id(doc):
    for fpe in DB.FilteredElementCollector(doc).OfClass(DB.FillPatternElement):
        pattern = fpe.GetFillPattern()
        if pattern is not None and pattern.IsSolidFill:
            return fpe.Id
    return None


def color_override(doc, color):
    """Lines, surfaces and cut faces all in one colour."""
    ogs = DB.OverrideGraphicSettings()
    ogs.SetProjectionLineColor(color)
    ogs.SetProjectionLineWeight(6)
    ogs.SetCutLineColor(color)
    solid = _solid_fill_id(doc)
    if solid is not None:
        ogs.SetSurfaceForegroundPatternId(solid)
        ogs.SetSurfaceForegroundPatternColor(color)
        ogs.SetCutForegroundPatternId(solid)
        ogs.SetCutForegroundPatternColor(color)
    return ogs


def _template_controls_filters(template):
    """False when the template leaves V/G Filters to each view."""
    filters_param = eid_int(DB.ElementId(DB.BuiltInParameter.VIS_GRAPHICS_FILTERS))
    for pid in template.GetNonControlledTemplateParameterIds():
        if eid_int(pid) == filters_param:
            return False
    return True


def _overrides_allowed(view):
    try:
        return view.AreGraphicsOverridesAllowed()
    except Exception:
        return False


def target_views(doc, include_3d):
    """Views and templates that should carry the colour filters.

    A view controlled by a template is coloured through its template
    (so re-applying the template keeps the colour), unless the template
    does not control filters - then the view itself gets the filter.
    """
    allowed = list(PLAN_LIKE_TYPES)
    if include_3d:
        allowed.append(DB.ViewType.ThreeD)

    result = {}
    views = DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
    templates_by_id = dict((eid_int(v.Id), v) for v in views if v.IsTemplate)

    for view in views:
        if view.ViewType not in allowed or not _overrides_allowed(view):
            continue
        if view.IsTemplate:
            if _template_controls_filters(view):
                result[eid_int(view.Id)] = view
            continue
        template_id = view.ViewTemplateId
        if template_id is not None and template_id != DB.ElementId.InvalidElementId:
            template = templates_by_id.get(eid_int(template_id))
            if template is not None and _template_controls_filters(template):
                continue  # handled by its template
        result[eid_int(view.Id)] = view
    return list(result.values())


def _equals_rule(bip, value):
    pid = DB.ElementId(bip)
    try:
        return DB.ParameterFilterRuleFactory.CreateEqualsRule(pid, value)
    except TypeError:
        # Revit 2021 and older: (id, value, caseSensitive)
        return DB.ParameterFilterRuleFactory.CreateEqualsRule(pid, value, True)


def falcon_filters(doc):
    """{name: ParameterFilterElement} for every filter this tool created."""
    found = {}
    for filt in DB.FilteredElementCollector(doc).OfClass(DB.ParameterFilterElement):
        if filt.Name.startswith(falcon_naming.PREFIX):
            found[filt.Name] = filt
    return found


def ensure_filter(doc, family_name, category_id, type_name=None):
    """Find or create the Falcon filter for a family (or one of its types)."""
    name = falcon_naming.filter_name(family_name, type_name)
    rules = List[DB.FilterRule]()
    rules.Add(_equals_rule(DB.BuiltInParameter.ALL_MODEL_FAMILY_NAME, family_name))
    if type_name is not None:
        rules.Add(_equals_rule(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME, type_name))
    element_filter = DB.ElementParameterFilter(rules)
    categories = List[DB.ElementId]()
    categories.Add(category_id)

    existing = falcon_filters(doc).get(name)
    if existing is not None:
        existing.SetCategories(categories)
        existing.SetElementFilter(element_filter)
        return existing
    return DB.ParameterFilterElement.Create(doc, name, categories, element_filter)


def apply_filter(views, filt, ogs):
    """Add filt with ogs to each view. Returns how many views took it."""
    count = 0
    for view in views:
        try:
            if not view.IsFilterApplied(filt.Id):
                view.AddFilter(filt.Id)
            view.SetFilterOverrides(filt.Id, ogs)
            view.SetFilterVisibility(filt.Id, True)
            count += 1
        except Exception:
            pass
    return count


def filter_colors(doc):
    """{filter name: DB.Color} read from the first view that uses each."""
    filters = falcon_filters(doc)
    by_id = dict((eid_int(f.Id), name) for name, f in filters.items())
    colors = {}
    for view in DB.FilteredElementCollector(doc).OfClass(DB.View):
        if len(colors) == len(by_id):
            break
        try:
            applied = view.GetFilters()
        except Exception:
            continue
        for fid in applied:
            name = by_id.get(eid_int(fid))
            if name is None or name in colors:
                continue
            color = view.GetFilterOverrides(fid).ProjectionLineColor
            if color is not None and color.IsValid:
                colors[name] = color
    return colors


def delete_filters(doc, filters):
    """Delete filters (Revit removes them from every view). Returns count."""
    count = 0
    for filt in filters:
        try:
            doc.Delete(filt.Id)
            count += 1
        except Exception:
            pass
    return count


def color_elements(doc, ids, color):
    """Colour elements in the active view and every 3D view.

    Returns (element count, number of 3D views coloured).
    """
    ogs = color_override(doc, color)
    active = doc.ActiveView
    falcon_markup.apply_override(doc, active, ids, ogs)
    views_3d = 0
    for view in DB.FilteredElementCollector(doc).OfClass(DB.View3D):
        if view.IsTemplate or view.Id == active.Id:
            continue
        falcon_markup.apply_override(doc, view, ids, ogs)
        views_3d += 1
    return (len(ids), views_3d)
