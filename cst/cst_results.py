"""Pulls S11, efficiency and far-field results from the solved BC09 CST project."""
import cmath
import csv
import json
import math
import os
import win32com.client as w

OUT = "data/initial_design"
os.makedirs(OUT, exist_ok=True)
app = w.GetActiveObject("CSTStudio.Application")
mws = app.Active3D()


def read_1d(path):
    r = mws.Result1DComplex(mws.ResultTree().GetFileFromTreeItem(path))
    n = r.GetN()
    return [(r.GetX(i), complex(r.GetYRe(i), r.GetYIm(i))) for i in range(n)]


summary = {}

# ---- S11
s11 = read_1d(r"1D Results\S-Parameters\S1,1")
rows = [(f, 20 * math.log10(abs(s))) for f, s in s11]
with open(os.path.join(OUT, "s11.csv"), "w", newline="") as fh:
    wr = csv.writer(fh)
    wr.writerow(["freq_GHz", "S11_dB", "Re", "Im"])
    for (f, s), (_, db) in zip(s11, rows):
        wr.writerow([f, db, s.real, s.imag])
fmin, dbmin = min(rows, key=lambda r: r[1])
summary["resonance_GHz"] = fmin
summary["S11_min_dB"] = dbmin


def interp_at(f0):
    for (f1, d1), (f2, d2) in zip(rows, rows[1:]):
        if f1 <= f0 <= f2:
            return d1 + (d2 - d1) * (f0 - f1) / (f2 - f1)


summary["S11_at_2.45_dB"] = interp_at(2.45)
gamma = 10 ** (summary["S11_at_2.45_dB"] / 20)
summary["VSWR_at_2.45"] = (1 + gamma) / (1 - gamma)

# -10 dB band around the minimum
i0 = rows.index((fmin, dbmin))
lo = hi = None
for i in range(i0, 0, -1):
    if rows[i - 1][1] > -10 >= rows[i][1]:
        (f1, d1), (f2, d2) = rows[i - 1], rows[i]
        lo = f1 + (-10 - d1) * (f2 - f1) / (d2 - d1)
        break
for i in range(i0, len(rows) - 1):
    if rows[i][1] <= -10 < rows[i + 1][1]:
        (f1, d1), (f2, d2) = rows[i], rows[i + 1]
        hi = f1 + (-10 - d1) * (f2 - f1) / (d2 - d1)
        break
summary["band_-10dB_GHz"] = [lo, hi]
summary["bandwidth_MHz"] = (hi - lo) * 1000 if lo and hi else None

# ---- efficiencies (linear, complex-stored)
for key, path in [("rad_eff", r"1D Results\Efficiencies\Rad. Efficiency [1]"),
                  ("tot_eff", r"1D Results\Efficiencies\Tot. Efficiency [1]")]:
    try:
        data = read_1d(path)
        f, v = min(data, key=lambda p: abs(p[0] - 2.45))
        summary[key + "_at_%.3f" % f] = abs(v)
    except Exception as e:
        summary[key + "_error"] = str(e)[:200]

with open(os.path.join(OUT, "summary.json"), "w") as fh:
    json.dump(summary, fh, indent=2)
print(json.dumps(summary, indent=2))
