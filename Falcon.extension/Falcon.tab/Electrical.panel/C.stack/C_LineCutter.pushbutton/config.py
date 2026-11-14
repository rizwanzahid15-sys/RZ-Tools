# Line Cutter - Shift+click settings (Falcon, Rizwan Zahid, v1.0.0, Revit 2020-2027, IronPython 2.7)
import falcon_view

falcon_view.ask_setting("Falcon - Line Cutter Settings", "falcon_linecutter", "gap_mm",
                   50.0, "Gap each side of the upper conduit (mm)", 0, 1000)
