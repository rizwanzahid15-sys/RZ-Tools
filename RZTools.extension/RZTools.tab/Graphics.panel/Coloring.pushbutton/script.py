# ============================================================
# Tool Metadata
# ============================================================
# Tool Name      : Coloring
# Purpose        : Color a whole family, one of its types, or picked
#                  elements, so systems read clearly in plans and 3D.
# Author         : Rizwan Zahid
# Version        : 1.0.0
# Created Date   : 2026-11-12
# Updated Date   : 2026-11-12
# Status         : Production
#
# Target Revit   : Revit 2020 - 2027
# Platform       : pyRevit
# Python Version : IronPython 2.7
#
# Category       : BIM Automation
# Discipline     : All Disciplines (built for Electrical)
# Tool Type      : pyRevit Tool
#
# Input          : Color Family - families/types ticked in a list.
#                  Color Element - pre-selection or picked elements.
# Output         : Color Family - RZ_COLOR_* view filters on project views
#                  and their templates (3D optional).
#                  Color Element - view overrides in the active view and
#                  every 3D view.
#
# Dependencies   :
#   - pyRevit
#   - Revit API
#   - RZTools.extension/lib/rzcolor.py, rznaming.py, rztools_markup.py
#
# Features       :
#   - Search, "only used" filter, swatches showing current colors
#   - Remove color from selected / remove all Coloring colors
#   - Never changes the elements themselves - graphics only
#
# Changelog
# ------------------------------------------------------------
# v1.0.0
# - Initial Release
#
# License        : Proprietary
# Copyright      : (c) Rizwan Zahid. All Rights Reserved
# ============================================================

import os

import clr
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")

from System.Windows import Thickness, VerticalAlignment
from System.Windows.Controls import (TreeViewItem, StackPanel, CheckBox,
                                     TextBlock, Orientation)
from System.Windows.Shapes import Rectangle
from System.Windows.Media import SolidColorBrush, Color as WColor, Brushes

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException

import rzcolor
import rznaming

TITLE = "RZ Tools - Coloring"
SYSTEM_CATEGORIES = (
    DB.BuiltInCategory.OST_Conduit,
    DB.BuiltInCategory.OST_CableTray,
    DB.BuiltInCategory.OST_PipeCurves,
    DB.BuiltInCategory.OST_DuctCurves,
)

doc = revit.doc
uidoc = revit.uidoc


def _name(element):
    try:
        return element.Name
    except Exception:
        return DB.Element.Name.__get__(element)


# ------------------------------------------------------------ data

class FamilyEntry(object):
    def __init__(self, name, category):
        self.name = name
        self.category_name = category.Name
        self.category_id = category.Id
        self.types = []          # [(type name, type id int)]

    def add_type(self, type_name, type_id):
        self.types.append((type_name, rzcolor.eid_int(type_id)))


def used_type_ids():
    used = set()
    for el in DB.FilteredElementCollector(doc).WhereElementIsNotElementType():
        try:
            tid = el.GetTypeId()
        except Exception:
            continue
        if tid is not None and tid != DB.ElementId.InvalidElementId:
            used.add(rzcolor.eid_int(tid))
    return used


def collect_families():
    entries = {}
    for fam in DB.FilteredElementCollector(doc).OfClass(DB.Family):
        cat = fam.FamilyCategory
        if cat is None or cat.CategoryType != DB.CategoryType.Model:
            continue
        entry = FamilyEntry(fam.Name, cat)
        for sid in fam.GetFamilySymbolIds():
            entry.add_type(_name(doc.GetElement(sid)), sid)
        entries[(fam.Name, rzcolor.eid_int(cat.Id))] = entry

    for bic in SYSTEM_CATEGORIES:
        types = DB.FilteredElementCollector(doc).OfCategory(bic).WhereElementIsElementType()
        for etype in types:
            cat = etype.Category
            if cat is None:
                continue
            key = (etype.FamilyName, rzcolor.eid_int(cat.Id))
            if key not in entries:
                entries[key] = FamilyEntry(etype.FamilyName, cat)
            entries[key].add_type(_name(etype), etype.Id)

    return sorted(entries.values(), key=lambda e: e.name.lower())


# ------------------------------------------------------------ window

def _brush(color):
    return SolidColorBrush(WColor.FromRgb(color.Red, color.Green, color.Blue))


class ColorFamilyWindow(forms.WPFWindow):
    def __init__(self):
        forms.WPFWindow.__init__(
            self, os.path.join(os.path.dirname(__file__), "ColorFamily.xaml"))
        self.families = collect_families()
        self.used = used_type_ids()
        self.checked = set()       # keys: (family, type or None)
        self.nodes = []
        self.colors = rzcolor.filter_colors(doc)
        self.build_tree()

    # ---------- tree
    def _header(self, key, label, filter_key):
        panel = StackPanel()
        panel.Orientation = Orientation.Horizontal
        box = CheckBox()
        box.IsChecked = key in self.checked
        box.Tag = key
        box.Click += self.node_click
        box.VerticalAlignment = VerticalAlignment.Center
        swatch = Rectangle()
        swatch.Width = swatch.Height = 12
        swatch.Margin = Thickness(4, 0, 4, 0)
        swatch.Stroke = Brushes.Gray
        color = self.colors.get(filter_key)
        swatch.Fill = _brush(color) if color is not None else Brushes.Transparent
        text = TextBlock()
        text.Text = label
        panel.Children.Add(box)
        panel.Children.Add(swatch)
        panel.Children.Add(text)
        return panel

    def build_tree(self):
        self.tree.Items.Clear()
        needle = (self.search.Text or "").strip().lower()
        only_used = bool(self.only_used.IsChecked)
        for fam in self.families:
            types = fam.types
            if only_used:
                types = [t for t in types if t[1] in self.used]
                if not types:
                    continue
            fam_match = needle in fam.name.lower()
            if needle and not fam_match:
                types = [t for t in types if needle in t[0].lower()]
                if not types:
                    continue
            item = TreeViewItem()
            item.Header = self._header(
                (fam.name, None), u"{}   [{}]".format(fam.name, fam.category_name),
                rznaming.filter_name(fam.name))
            for type_name, _tid in sorted(types):
                child = TreeViewItem()
                child.Header = self._header(
                    (fam.name, type_name), type_name,
                    rznaming.filter_name(fam.name, type_name))
                item.Items.Add(child)
            item.IsExpanded = bool(needle)
            self.tree.Items.Add(item)

    def node_click(self, sender, args):
        if sender.IsChecked:
            self.checked.add(sender.Tag)
        else:
            self.checked.discard(sender.Tag)
        self.show_selected()

    def show_selected(self):
        if not self.checked:
            self.selected_text.Text = "Nothing selected"
            return
        lines = []
        for fam, typ in sorted(self.checked, key=lambda k: (k[0], k[1] or "")):
            lines.append(u"Type: {} : {}".format(fam, typ) if typ else u"Family: {}".format(fam))
        self.selected_text.Text = "\n".join(lines)

    def targets(self):
        """[(FamilyEntry, type name or None)] - a ticked family only counts
        when none of its types are ticked."""
        by_name = dict((f.name, f) for f in self.families)
        typed = set(k[0] for k in self.checked if k[1] is not None)
        result = []
        for fam, typ in self.checked:
            entry = by_name.get(fam)
            if entry is None or (typ is None and fam in typed):
                continue
            result.append((entry, typ))
        return result

    def refresh(self, message):
        self.colors = rzcolor.filter_colors(doc)
        self.build_tree()
        self.status.Text = message

    # ---------- events
    def search_changed(self, sender, args):
        self.build_tree()

    def filter_changed(self, sender, args):
        self.build_tree()

    def choose_click(self, sender, args):
        targets = self.targets()
        if not targets:
            self.status.Text = "Tick a family or a type first."
            return
        color = rzcolor.pick_color()
        if color is None:
            return
        include_3d = bool(self.also_3d.IsChecked)
        failures = []
        views_done = 0
        with revit.TransactionGroup("RZTools: Color Family"):
            with revit.Transaction("RZTools: Color Family"):
                views = rzcolor.target_views(doc, include_3d)
                ogs = rzcolor.color_override(doc, color)
                for entry, typ in targets:
                    try:
                        filt = rzcolor.ensure_filter(doc, entry.name, entry.category_id, typ)
                        views_done = max(views_done, rzcolor.apply_filter(views, filt, ogs))
                    except Exception as ex:
                        failures.append(u"{}: {}".format(entry.name, ex))
        if len(targets) == 1:
            entry, typ = targets[0]
            what = u'type "{} : {}"'.format(entry.name, typ) if typ else u'family "{}"'.format(entry.name)
        else:
            what = u"{} item(s)".format(len(targets))
        msg = u"Colored {} in {} view(s).".format(what, views_done)
        if not include_3d:
            msg += u" 3D views were left out."
        if failures:
            msg += u" Skipped: " + u"; ".join(failures)
        self.refresh(msg)

    def remove_click(self, sender, args):
        targets = self.targets()
        if not targets:
            self.status.Text = "Tick a family or a type first."
            return
        existing = rzcolor.rz_filters(doc)
        filters = [existing[n] for n in
                   (rznaming.filter_name(e.name, t) for e, t in targets) if n in existing]
        with revit.Transaction("RZTools: Remove Color"):
            count = rzcolor.delete_filters(doc, filters)
        self.refresh(u"Removed color from {} item(s).".format(count))

    def remove_all_click(self, sender, args):
        filters = list(rzcolor.rz_filters(doc).values())
        if not filters:
            self.status.Text = "There are no Coloring colors in this project."
            return
        if not forms.alert(u"Remove all {} Coloring color(s) from every view?".format(len(filters)),
                           title=TITLE, yes=True, no=True):
            return
        with revit.Transaction("RZTools: Remove All Colors"):
            count = rzcolor.delete_filters(doc, filters)
        self.refresh(u"Removed {} Coloring color(s).".format(count))

    def close_click(self, sender, args):
        self.Close()


# ------------------------------------------------------------ element mode

def color_element_mode():
    color = rzcolor.pick_color()
    if color is None:
        return
    total = 0
    views_3d = 0
    pre = list(uidoc.Selection.GetElementIds())
    if pre:
        with revit.Transaction("RZTools: Color Element"):
            n, views_3d = rzcolor.color_elements(doc, pre, color)
            total += n
    while True:
        try:
            ref = uidoc.Selection.PickObject(
                ObjectType.Element, "Pick elements to color (Esc to finish)")
        except OperationCanceledException:
            break
        with revit.Transaction("RZTools: Color Element"):
            n, views_3d = rzcolor.color_elements(doc, [ref.ElementId], color)
            total += n
    if total:
        forms.alert(u'Colored {} element(s) in view "{}" and in {} 3D view(s).'.format(
            total, doc.ActiveView.Name, views_3d), title=TITLE)


# ------------------------------------------------------------ main

if doc is None:
    forms.alert("Please open a Revit project first.", title=TITLE)
    script.exit()

choice = forms.CommandSwitchWindow.show(
    ["Color Family", "Color Element"], message="What do you want to color?")

if choice == "Color Family":
    ColorFamilyWindow().show_dialog()
elif choice == "Color Element":
    color_element_mode()
