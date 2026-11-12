# Auto Dimension - Shift+click settings (RZ Tools, Rizwan Zahid, v1.0.0, Revit 2020-2027, IronPython 2.7)
import rzview

rzview.ask_setting("RZ Tools - Auto Dimension Settings", "rztools_autodim", "offset_mm",
                   500.0, "Distance from the conduit midpoint to the dimension line (mm)",
                   -100000, 100000)
