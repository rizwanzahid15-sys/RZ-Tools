# Line Cutter - Shift+click settings (RZ Tools, Rizwan Zahid, v1.0.0, Revit 2020-2027, IronPython 2.7)
import rzview

rzview.ask_setting("RZ Tools - Line Cutter Settings", "rztools_linecutter", "gap_mm",
                   50.0, "Gap each side of the upper conduit (mm)", 0, 1000)
