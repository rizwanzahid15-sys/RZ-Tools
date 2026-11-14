# Auto Dimension - Shift+click settings (Falcon, Rizwan Zahid, v1.0.0, Revit 2020-2027, IronPython 2.7)
import falcon_view

falcon_view.ask_setting("Falcon - Auto Dimension Settings", "falcon_autodim", "offset_mm",
                   500.0, "Distance from the conduit midpoint to the dimension line (mm)",
                   -100000, 100000)
