# ============================================================
# Shared Library
# ============================================================
# Module Name    : rzconduit
# Purpose        : Revit conduit helpers for the RZ Tools electrical
#                  tools - trace runs, split conduits, add elbows,
#                  place junction/pull boxes.
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Created Date   : 2026-11-12
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7
# ============================================================
"""Revit-side conduit operations. The decisions (where to cut, where a
box goes) come from rzgeom; this module only carries them out."""

import math

from pyrevit import DB
from Autodesk.Revit.DB.Electrical import Conduit
from Autodesk.Revit.DB.Structure import StructuralType

import rzgeom
from rzcolor import eid_int

BOX_WORDS = ("box", "junction")
BOX_CATEGORIES = (
    DB.BuiltInCategory.OST_ElectricalFixtures,
    DB.BuiltInCategory.OST_ConduitFitting,
    DB.BuiltInCategory.OST_ElectricalEquipment,
)
BOX_ONLY_CATEGORIES = (
    DB.BuiltInCategory.OST_ElectricalFixtures,
    DB.BuiltInCategory.OST_ElectricalEquipment,
)
TOL = 1e-6


# ------------------------------------------------------------- basics

def xyz(t):
    return DB.XYZ(t[0], t[1], t[2])


def tup(p):
    return (p.X, p.Y, p.Z)


def element_name(element):
    try:
        return element.Name
    except Exception:
        return DB.Element.Name.__get__(element)


def is_conduit(element):
    return isinstance(element, Conduit)


def ends(conduit):
    curve = conduit.Location.Curve
    return curve.GetEndPoint(0), curve.GetEndPoint(1)


def set_ends(conduit, p0, p1):
    conduit.Location.Curve = DB.Line.CreateBound(p0, p1)


def outer_radius(conduit):
    for bip in (DB.BuiltInParameter.RBS_CONDUIT_OUTER_DIAM_PARAM,
                DB.BuiltInParameter.RBS_CONDUIT_DIAMETER_PARAM):
        param = conduit.get_Parameter(bip)
        if param is not None and param.HasValue and param.AsDouble() > 0:
            return param.AsDouble() / 2.0
    return 0.0


def conduit_contains(conduit, point, tol=0.01):
    """True when point lies on the conduit's centreline (within tol ft)."""
    curve = conduit.Location.Curve
    result = curve.Project(point)
    return result is not None and result.Distance <= tol


def _category_is(element, bics):
    cat = element.Category
    if cat is None:
        return False
    cid = eid_int(cat.Id)
    return any(cid == int(b) for b in bics)


# --------------------------------------------------------- connectors

def connectors(element):
    """Physical (non-logical) connectors of a conduit or family instance."""
    manager = getattr(element, "ConnectorManager", None)
    if manager is None:
        mep = getattr(element, "MEPModel", None)
        manager = mep.ConnectorManager if mep is not None else None
    if manager is None:
        return []
    return [c for c in manager.Connectors
            if c.ConnectorType != DB.ConnectorType.Logical]


def end_connector(element, point):
    """End connector of element nearest to point."""
    best, best_d = None, None
    for conn in connectors(element):
        if conn.ConnectorType == DB.ConnectorType.Curve:
            continue
        d = conn.Origin.DistanceTo(point)
        if best is None or d < best_d:
            best, best_d = conn, d
    return best


def connected_others(conn):
    """Connectors on other elements that conn is physically joined to."""
    if conn is None or not conn.IsConnected:
        return []
    owner = eid_int(conn.Owner.Id)
    return [r for r in conn.AllRefs
            if eid_int(r.Owner.Id) != owner
            and r.ConnectorType != DB.ConnectorType.Logical]


# ------------------------------------------------------ create / split

def _copy_param(src, dst, bip):
    s = src.get_Parameter(bip)
    d = dst.get_Parameter(bip)
    if s is None or d is None or d.IsReadOnly or not s.HasValue:
        return
    try:
        st = s.StorageType
        if st == DB.StorageType.Double:
            d.Set(s.AsDouble())
        elif st == DB.StorageType.Integer:
            d.Set(s.AsInteger())
        elif st == DB.StorageType.String:
            d.Set(s.AsString() or "")
        elif st == DB.StorageType.ElementId:
            d.Set(s.AsElementId())
    except Exception:
        pass


def new_conduit_like(doc, src, p0, p1):
    """New conduit with src's type, size, level, service type, comments."""
    new = Conduit.Create(doc, src.GetTypeId(), p0, p1, src.ReferenceLevel.Id)
    for bip in (DB.BuiltInParameter.RBS_CONDUIT_DIAMETER_PARAM,
                DB.BuiltInParameter.RBS_CTC_SERVICE_TYPE,
                DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS,
                DB.BuiltInParameter.ELEM_PARTITION_PARAM):
        _copy_param(src, new, bip)
    return new


def split_conduit(doc, conduit, point):
    """Cut conduit at point. Original keeps start->point; the returned new
    conduit runs point->old end and takes over the old end's connections."""
    p0, p1 = ends(conduit)
    far = end_connector(conduit, p1)
    others = connected_others(far)
    for other in others:
        far.DisconnectFrom(other)
    set_ends(conduit, p0, point)
    new = new_conduit_like(doc, conduit, point, p1)
    new_far = end_connector(new, p1)
    for other in others:
        try:
            new_far.ConnectTo(other)
        except Exception:
            pass
    return new


def connect_elbow(doc, c1, c2):
    """Join two conduits with an elbow at their nearest ends.

    The elbow family comes from the conduit type's fitting settings.
    Returns the fitting, or None if Revit could not make it."""
    best = None
    for a in connectors(c1):
        for b in connectors(c2):
            d = a.Origin.DistanceTo(b.Origin)
            if best is None or d < best[0]:
                best = (d, a, b)
    if best is None:
        return None
    try:
        return doc.Create.NewElbowFitting(best[1], best[2])
    except Exception:
        return None


# --------------------------------------------------------- run tracing

def is_box_like(element):
    if _category_is(element, BOX_ONLY_CATEGORIES):
        return True
    symbol = getattr(element, "Symbol", None)
    family = symbol.Family.Name.lower() if symbol is not None else ""
    return any(word in family for word in BOX_WORDS)


def classify_fitting(fi):
    """"bend" | "fitting" | "box" | "branch" for a family instance on a run."""
    conns = connectors(fi)
    if len(conns) > 2:
        return "branch"
    if is_box_like(fi):
        return "box"
    if len(conns) == 2:
        out_a = tup(conns[0].CoordinateSystem.BasisZ)
        out_b = tup(conns[1].CoordinateSystem.BasisZ)
        if rzgeom.is_bend(rzgeom.bend_angle_deg(out_a, out_b)):
            return "bend"
    return "fitting"


def trace_run(doc, conduit, start_point):
    """Walk a conduit run from the end of conduit nearest start_point.

    Returns run items {"kind", "length", "vertical", "element",
    "p_start", "p_end"} in walk order (p_start = where the walk enters).
    Stops at a free end, a branch (added as kind "branch"), or a loop.
    """
    p0, p1 = ends(conduit)
    entry_pt = (p0, p1)[rzgeom.nearest_end(tup(p0), tup(p1), tup(start_point))]
    entry = end_connector(conduit, entry_pt)
    element = conduit
    items = []
    visited = set()

    while element is not None and eid_int(element.Id) not in visited:
        visited.add(eid_int(element.Id))
        if is_conduit(element):
            a, b = ends(element)
            if a.DistanceTo(entry.Origin) <= b.DistanceTo(entry.Origin):
                ps, pe = a, b
            else:
                ps, pe = b, a
            items.append({
                "kind": "straight", "length": ps.DistanceTo(pe),
                "vertical": rzgeom.is_vertical(tup(pe - ps)),
                "element": element, "p_start": ps, "p_end": pe,
            })
            exit_conn = end_connector(element, pe)
        else:
            kind = classify_fitting(element)
            conns = connectors(element)
            others = [c for c in conns if c.Id != entry.Id]
            exit_conn = others[0] if len(conns) == 2 else None
            p_end = exit_conn.Origin if exit_conn is not None else entry.Origin
            items.append({
                "kind": kind,
                "length": entry.Origin.DistanceTo(p_end),
                "vertical": False, "element": element,
                "p_start": entry.Origin, "p_end": p_end,
            })
            if kind == "branch" or exit_conn is None:
                break
        nxt = connected_others(exit_conn)
        if not nxt:
            break
        entry = nxt[0]
        element = entry.Owner
    return items


# ---------------------------------------------------------------- boxes

def box_symbols(doc):
    """[(label, FamilySymbol)] for junction/pull box families.

    Only families with "box"/"junction" in the name (or Electrical
    Fixture/Equipment boxes) when any exist, else every candidate."""
    candidates = []
    for sym in DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol):
        if not _category_is(sym, BOX_CATEGORIES):
            continue
        family = sym.Family.Name
        label = "{} : {}".format(family, element_name(sym))
        boxy = any(word in family.lower() for word in BOX_WORDS)
        candidates.append((boxy, label, sym))
    boxy_only = [c for c in candidates if c[0]]
    chosen = boxy_only if boxy_only else candidates
    return sorted([(label, sym) for _b, label, sym in chosen], key=lambda x: x[0])


def _set_offset_to(doc, inst, z):
    """Raise/lower inst so its location point sits at height z."""
    doc.Regenerate()
    loc = getattr(inst, "Location", None)
    if loc is None or not hasattr(loc, "Point"):
        return
    delta = z - loc.Point.Z
    if abs(delta) < TOL:
        return
    for bip in (DB.BuiltInParameter.INSTANCE_ELEVATION_PARAM,
                DB.BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM):
        param = inst.get_Parameter(bip)
        if param is not None and not param.IsReadOnly:
            param.Set(param.AsDouble() + delta)
            return
    DB.ElementTransformUtils.MoveElement(doc, inst.Id, DB.XYZ(0, 0, delta))


def place_box(doc, symbol, conduit, point):
    """Place a box at point on conduit, aligned with it.

    If the box has exactly two conduit connectors, the conduit is cut and
    both halves are connected to it. Returns (instance, connected)."""
    if not symbol.IsActive:
        symbol.Activate()
        doc.Regenerate()
    level = conduit.ReferenceLevel
    inst = doc.Create.NewFamilyInstance(point, symbol, level,
                                        StructuralType.NonStructural)
    _set_offset_to(doc, inst, point.Z)

    p0, p1 = ends(conduit)
    direction = p1 - p0
    angle = math.atan2(direction.Y, direction.X)
    if abs(angle) > TOL:
        axis = DB.Line.CreateBound(point, point + DB.XYZ.BasisZ)
        DB.ElementTransformUtils.RotateElement(doc, inst.Id, axis, angle)
    doc.Regenerate()

    box_conns = [c for c in connectors(inst)
                 if c.Domain == DB.Domain.DomainCableTrayConduit]
    if len(box_conns) != 2:
        return inst, False
    try:
        new = split_conduit(doc, conduit, point)
        start, _mid = ends(conduit)
        _mid2, finish = ends(new)
        near, far = sorted(box_conns, key=lambda c: c.Origin.DistanceTo(start))
        set_ends(conduit, start, near.Origin)
        set_ends(new, far.Origin, finish)
        doc.Regenerate()
        end_connector(conduit, near.Origin).ConnectTo(near)
        end_connector(new, far.Origin).ConnectTo(far)
        return inst, True
    except Exception:
        return inst, False
