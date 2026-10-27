"""Runs CST simulations of the BC09 antenna for given parameter sets and logs the results.

Usage: python cst_sim.py <jobs.json> <results.csv>
jobs.json is a list of {param: value} dicts (unspecified params keep the baseline value).
"""
import csv
import json
import math
import os
import sys
import time
import win32com.client as w

BASE = {"W": 68, "L": 73, "Ls": 50, "Ws": 2, "ys": 10, "yf": -18, "gap": 0.94}
MAX_CELLS = 100000
FIELDS = ["run", "time", *BASE.keys(), "cells", "status", "f_res", "s11_min", "s11_245", "bw_lo", "bw_hi",
          "bw_mhz", "gain_rz_0", "gain_rz_180", "gain_rz_max", "fbr_db", "rad_eff_db", "tot_eff_db", "sec"]

mws = w.GetActiveObject("CSTStudio.Application").Active3D()


def s11_curve():
    path = mws.ResultTree().GetFileFromTreeItem(r"1D Results\S-Parameters\S1,1")
    r = mws.Result1DComplex(path)
    return [(r.GetX(i), 20 * math.log10(max(math.hypot(r.GetYRe(i), r.GetYIm(i)), 1e-12)))
            for i in range(r.GetN())]


def band(rows):
    i0 = min(range(len(rows)), key=lambda i: rows[i][1])
    if rows[i0][1] > -10:
        return None, None
    lo = hi = None
    for i in range(i0, 0, -1):
        (f1, d1), (f2, d2) = rows[i - 1], rows[i]
        if d1 > -10 >= d2:
            lo = f1 + (-10 - d1) * (f2 - f1) / (d2 - d1)
            break
    for i in range(i0, len(rows) - 1):
        (f1, d1), (f2, d2) = rows[i], rows[i + 1]
        if d1 <= -10 < d2:
            hi = f1 + (-10 - d1) * (f2 - f1) / (d2 - d1)
            break
    return lo, hi


def at(rows, f0):
    for (f1, d1), (f2, d2) in zip(rows, rows[1:]):
        if f1 <= f0 <= f2:
            return d1 + (d2 - d1) * (f0 - f1) / (f2 - f1)


def farfield():
    mws.SelectTreeItem(r"Farfields\farfield (f=2.45) [1]")
    ff = mws.FarfieldPlot()
    ff.Reset()
    ff.SetPlotMode("Realized Gain")
    ff.SetScaleLinear(False)
    pts = [(th, ph) for th in range(0, 181, 5) for ph in range(0, 360, 45)]
    for th, ph in pts:
        ff.AddListEvaluationPoint(th, ph, 0, "spherical", "frequency", 2.45)
    ff.CalculateList("")
    v = ff.GetList("Spherical abs")
    g = dict(zip(pts, v))
    return {"gain_rz_0": g[(0, 0)], "gain_rz_180": g[(180, 0)], "gain_rz_max": max(v),
            "fbr_db": g[(0, 0)] - g[(180, 0)],
            "rad_eff_db": ff.GetRadiationEfficiency(), "tot_eff_db": ff.GetTotalEfficiency()}


def simulate(params, run_id):
    p = dict(BASE, **params)
    row = {"run": run_id, "time": time.strftime("%H:%M:%S"), **p}
    t0 = time.time()
    mws.DeleteResults()
    for k, v in p.items():
        mws.StoreParameter(k, v)
    mws.Rebuild()
    me = mws.Mesh()
    me.Update()
    row["cells"] = me.GetNumberOfMeshCells()
    if row["cells"] > MAX_CELLS:
        row["status"] = "mesh_over_limit"
        return row
    if not mws.Solver().Start():
        row["status"] = "solver_failed"
        return row
    rows = s11_curve()
    f_res, s_min = min(rows, key=lambda r: r[1])
    lo, hi = band(rows)
    row.update(status="ok", f_res=f_res, s11_min=s_min, s11_245=at(rows, 2.45), bw_lo=lo, bw_hi=hi,
               bw_mhz=(hi - lo) * 1000 if lo and hi else 0)
    try:
        row.update(farfield())
    except Exception as e:
        row["status"] = "ok_no_farfield: " + str(e)[:80]
    row["sec"] = round(time.time() - t0, 1)
    return row


def main(jobs_file, out_csv):
    jobs = json.load(open(jobs_file))
    new = not os.path.exists(out_csv)
    start = 0 if new else sum(1 for _ in open(out_csv)) - 1
    with open(out_csv, "a", newline="") as fh:
        wr = csv.DictWriter(fh, FIELDS, extrasaction="ignore")
        if new:
            wr.writeheader()
        for i, job in enumerate(jobs):
            try:
                row = simulate(job, start + i)
            except Exception as e:
                row = {"run": start + i, **dict(BASE, **job), "status": "error: " + str(e)[:120]}
            wr.writerow(row)
            fh.flush()
            print(json.dumps({k: row.get(k) for k in ("run", "status", "f_res", "s11_min", "s11_245",
                                                      "bw_mhz", "gain_rz_0", "cells", "sec")}), flush=True)
    mws.Save()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
