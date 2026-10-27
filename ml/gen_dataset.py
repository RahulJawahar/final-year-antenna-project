"""Generates rule-checked Latin hypercube samples of the BC09 geometry for the ML dataset."""
import json
import sys
import numpy as np

RANGES = {"W": (62, 70), "L": (67, 75), "Ls": (40, 55), "Ws": (1.5, 4), "ys": (3, 15), "yf": (-30, -15)}
D, B, SHELL = 2.4, 1.675, 0.4


def feasible(p):
    """SIW design rules plus slot / feed / via clearance checks (same as the geometry generator)."""
    pw, pl = p["W"] / 16, p["L"] / 17
    return (p["d"] / 5 < 97.5 / 5 and pw <= 2 * D and pl <= 2 * D           # via leakage rules
            and p["Ls"] / 2 < p["W"] / 2 - D                                 # slot inside fence (x)
            and p["ys"] + p["Ws"] / 2 < p["L"] / 2 - D                       # slot inside fence (y)
            and abs(p["yf"]) + B + SHELL < p["L"] / 2 - D / 2                # feed clear of vias
            and p["yf"] + B + SHELL < p["ys"] - p["Ws"] / 2)                 # feed clear of slot


def lhs(n, seed):
    rng = np.random.default_rng(seed)
    keys = list(RANGES)
    cut = (np.arange(n)[:, None] + rng.random((n, len(keys)))) / n
    for j in range(len(keys)):
        cut[:, j] = rng.permutation(cut[:, j])
    out = []
    for row in cut:
        p = {k: round(RANGES[k][0] + u * (RANGES[k][1] - RANGES[k][0]), 2) for k, u in zip(keys, row)}
        p["gap"] = 0
        p["d"] = D
        if feasible(p):
            p.pop("d")
            out.append(p)
    return out


if __name__ == "__main__":
    n, seed, path = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    jobs = lhs(n, seed)
    json.dump(jobs, open(path, "w"), indent=1)
    print(len(jobs), "feasible of", n)
