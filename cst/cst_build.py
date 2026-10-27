"""Builds the BC09 wearable SIW cavity-backed slot antenna in CST Studio Suite (Learning Edition) via COM.

Origin: board centre at substrate bottom, +z points away from body (ground faces body).
All geometry is parametric, so the same project can later be swept for the ML dataset.
"""
import os
import win32com.client as w

PROJECT = os.path.abspath("cst_project/BC09_SIW_Antenna.cst")

PARAMS = {
    "Bx": 78, "By": 83,          # overall board
    "W": 68, "L": 73,            # via-centre rectangle
    "d": 2.4,                    # via diameter
    "h": 3.94, "t": 0.035,       # foam thickness, copper thickness
    "er": 1.575, "tand": 0.0238,
    "Ls": 50, "Ws": 2, "ys": 10,  # slot length, width, centre y
    "yf": -18,                   # feed centre y
    "a": 0.5, "b": 1.675,        # coax inner / outer radius
    "gap": 0.94,                 # probe tip gap to top copper
    "Lc": 5,                     # coax length below ground
    "er_coax": 2.1,
}
NX, NY = 16, 17                  # via intervals along W and L (66 vias total)


def via_positions():
    pts = []
    for i in range(NX + 1):                       # top and bottom rows (incl. corners)
        x = "-W/2+%d*W/%d" % (i, NX)
        pts += [(x, "-L/2"), (x, "L/2")]
    for j in range(1, NY):                        # side columns (corners already placed)
        y = "-L/2+%d*L/%d" % (j, NY)
        pts += [("-W/2", y), ("W/2", y)]
    return pts


def brick(name, comp, mat, x, y, z):
    return f'''With Brick
 .Reset
 .Name "{name}"
 .Component "{comp}"
 .Material "{mat}"
 .Xrange "{x[0]}", "{x[1]}"
 .Yrange "{y[0]}", "{y[1]}"
 .Zrange "{z[0]}", "{z[1]}"
 .Create
End With'''


def cyl(name, comp, mat, r_out, r_in, xc, yc, z):
    return f'''With Cylinder
 .Reset
 .Name "{name}"
 .Component "{comp}"
 .Material "{mat}"
 .OuterRadius "{r_out}"
 .InnerRadius "{r_in}"
 .Axis "z"
 .Zrange "{z[0]}", "{z[1]}"
 .Xcenter "{xc}"
 .Ycenter "{yc}"
 .Segments "0"
 .Create
End With'''


def build(mws):
    H = mws.AddToHistory
    for k, v in PARAMS.items():
        mws.StoreParameter(k, v)
    mws.Rebuild()

    H("units", '''With Units
 .Geometry "mm"
 .Frequency "GHz"
 .Time "ns"
End With''')
    H("frequency range", 'Solver.FrequencyRange "2", "3"')
    H("background", '''With Background
 .ResetBackground
 .Type "Normal"
End With''')
    H("boundaries", '''With Boundary
 .Xmin "expanded open"
 .Xmax "expanded open"
 .Ymin "expanded open"
 .Ymax "expanded open"
 .Zmin "expanded open"
 .Zmax "expanded open"
 .Xsymmetry "none"
 .Ysymmetry "none"
 .Zsymmetry "none"
 .MinimumDistanceType "Fraction"
 .MinimumDistancePerWavelengthNewMeshEngine "8"
 .MinimumDistanceReferenceFrequencyType "Center"
End With''')

    H("material foam", '''With Material
 .Reset
 .Name "Foam"
 .Type "Normal"
 .Epsilon "er"
 .Mu "1"
 .TanDGiven "True"
 .TanD "tand"
 .TanDFreq "2.45"
 .TanDModel "ConstTanD"
 .Colour "0.85", "0.9", "0.9"
 .Create
End With''')
    H("material copper", '''With Material
 .Reset
 .Name "Cu"
 .Type "Lossy metal"
 .Mu "1"
 .Sigma "5.8e7"
 .Colour "0.85", "0.55", "0.25"
 .Create
End With''')
    H("material ptfe", '''With Material
 .Reset
 .Name "PTFE"
 .Type "Normal"
 .Epsilon "er_coax"
 .Mu "1"
 .Colour "0.95", "0.95", "0.85"
 .Create
End With''')

    H("substrate", brick("substrate", "antenna", "Foam", ("-Bx/2", "Bx/2"), ("-By/2", "By/2"), ("0", "h")))
    H("ground", brick("ground", "antenna", "Cu", ("-Bx/2", "Bx/2"), ("-By/2", "By/2"), ("-t", "0")))
    H("ground hole", cyl("gnd_hole", "antenna", "Cu", "b", "0", "0", "yf", ("-t", "0")))
    H("subtract ground hole", 'Solid.Subtract "antenna:ground", "antenna:gnd_hole"')
    H("top copper", brick("top", "antenna", "Cu", ("-Bx/2", "Bx/2"), ("-By/2", "By/2"), ("h", "h+t")))
    H("slot", brick("slot", "antenna", "Cu", ("-Ls/2", "Ls/2"), ("ys-Ws/2", "ys+Ws/2"), ("h", "h+t")))
    H("subtract slot", 'Solid.Subtract "antenna:top", "antenna:slot"')

    vias = "\n".join(cyl("via%02d" % i, "vias", "Cu", "d/2", "0", x, y, ("0", "h"))
                     for i, (x, y) in enumerate(via_positions(), 1))
    H("vias", vias)

    H("coax outer", cyl("coax_outer", "feed", "Cu", "b+0.4", "b", "0", "yf", ("-Lc", "0")))
    H("coax dielectric", cyl("coax_diel", "feed", "PTFE", "b", "a", "0", "yf", ("-Lc", "0")))
    H("probe", cyl("probe", "feed", "Cu", "a", "0", "0", "yf", ("-Lc", "h-gap")))

    H("port", '''With Port
 .Reset
 .PortNumber "1"
 .NumberOfModes "1"
 .AdjustPolarization "False"
 .PolarizationAngle "0.0"
 .ReferencePlaneDistance "0"
 .TextSize "50"
 .Coordinates "Free"
 .Orientation "zmin"
 .PortOnBound "False"
 .ClipPickedPortToBound "False"
 .Xrange "-b", "b"
 .Yrange "yf-b", "yf+b"
 .Zrange "-Lc", "-Lc"
 .XrangeAdd "0.0", "0.0"
 .YrangeAdd "0.0", "0.0"
 .ZrangeAdd "0.0", "0.0"
 .SingleEnded "False"
 .Create
End With''')

    H("farfield monitor", '''With Monitor
 .Reset
 .Name "farfield (f=2.45)"
 .Domain "Frequency"
 .FieldType "Farfield"
 .MonitorValue "2.45"
 .ExportFarfieldSource "False"
 .Create
End With''')

    H("mesh settings", '''With Mesh
 .MeshType "PBA"
 .SetCreator "High Frequency"
End With
With MeshSettings
 .SetMeshType "Hex"
 .Set "Version", 1%
 .Set "StepsPerWaveNear", "8"
 .Set "StepsPerWaveFar", "8"
 .Set "StepsPerBoxNear", "10"
 .Set "StepsPerBoxFar", "1"
 .Set "UseRatioLimitGeometry", "1"
 .Set "RatioLimitGeometry", "10"
End With''')

    H("solver settings", '''ChangeSolverType "HF Time Domain"
With Solver
 .Method "Hexahedral"
 .SteadyStateLimit "-40"
 .StimulationPort "All"
 .StimulationMode "All"
 .MeshAdaption "False"
 .AutoNormImpedance "False"
 .CalculateModesOnly "False"
 .SParaSymmetry "False"
 .StoreTDResultsInCache "False"
 .FullDeembedding "False"
 .UseDistributedComputing "False"
End With''')


if __name__ == "__main__":
    os.makedirs(os.path.dirname(PROJECT), exist_ok=True)
    app = w.GetActiveObject("CSTStudio.Application")
    mws = app.NewMWS()
    build(mws)
    mws.SaveAs(PROJECT, False)
    print("built and saved:", PROJECT)
