"""The Falcon ribbon must follow pyRevit's bundle rules and the agreed
compact layout (small stacked buttons, Markup as a pulldown)."""
import os

TAB = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir,
                                   "Falcon.extension", "Falcon.tab"))
REPO = os.path.dirname(os.path.dirname(TAB))
MAX_PATH = 260


def children(folder):
    return sorted(d for d in os.listdir(folder)
                  if os.path.isdir(os.path.join(folder, d)))


def titles(folder):
    out = []
    for name in children(folder):
        with open(os.path.join(folder, name, "bundle.yaml"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("title:"):
                    out.append(line.split(":", 1)[1].strip())
    return out


def test_panels():
    assert children(TAB) == ["Electrical.panel", "Graphics.panel"]


def test_electrical_stacks_in_order():
    panel = os.path.join(TAB, "Electrical.panel")
    stacks = children(panel)
    assert all(s.endswith(".stack") for s in stacks)
    assert [titles(os.path.join(panel, s)) for s in stacks] == [
        ["Connect Conduit", "Convert Line", "Multi Fillet"],
        ["Junction Box", "Pull Box", "Conduit Cutter"],
        ["Auto Dimension", "Home Run", "Line Cutter"],
    ]


def test_graphics_stack_with_markup_pulldown():
    panel = os.path.join(TAB, "Graphics.panel")
    (stack,) = children(panel)
    assert stack.endswith(".stack")
    stack_dir = os.path.join(panel, stack)
    assert titles(stack_dir) == ["Coloring", "Markup"]
    pulldown = [d for d in children(stack_dir) if d.endswith(".pulldown")]
    assert len(pulldown) == 1
    assert titles(os.path.join(stack_dir, pulldown[0])) == [
        "Redline Markup", "Blue Markup", "Clear"]


def test_every_stack_has_two_or_three_items():
    for panel in children(TAB):
        for stack in children(os.path.join(TAB, panel)):
            n = len(children(os.path.join(TAB, panel, stack)))
            assert 2 <= n <= 3, (panel, stack, n)


def test_every_button_is_complete():
    found = 0
    for root, dirs, files in os.walk(TAB):
        if root.endswith(".pushbutton"):
            found += 1
            assert {"script.py", "bundle.yaml", "icon.png"} <= set(files), root
        if root.endswith(".pulldown"):
            assert {"bundle.yaml", "icon.png"} <= set(files), root
    assert found == 13


def test_paths_fit_windows_limit_in_main_folder():
    # Revit/IronPython can't open files past 260 characters. The real
    # extension lives ~45 characters higher than this worktree, so check
    # the paths relative to the repo plus a generous 120-character root.
    longest = 0
    for root, _dirs, files in os.walk(os.path.join(REPO, "Falcon.extension")):
        for name in files:
            rel = os.path.relpath(os.path.join(root, name), REPO)
            longest = max(longest, len(rel))
    assert 120 + longest < MAX_PATH, longest
