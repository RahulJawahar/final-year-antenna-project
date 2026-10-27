"""Trains XGBoost surrogates on the CST dataset and searches for improved BC09 geometries."""
import json
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, train_test_split
from xgboost import XGBRegressor

from gen_dataset import RANGES, feasible

FEATURES = ["W", "L", "Ls", "Ws", "ys", "yf"]
TARGETS = {"f_res": "Resonant frequency (GHz)", "s11_245": "S11 at 2.45 GHz (dB)",
           "bw_mhz": "-10 dB bandwidth (MHz)", "gain_rz_0": "Realized gain (dBi)"}

import glob, sys
frames = [pd.read_csv(f) for f in ["data/dataset.csv", "data/runs.csv"] + sorted(glob.glob("data/validate*.csv"))]
ROUND = sys.argv[1] if len(sys.argv) > 1 else ""
df = pd.concat(frames, ignore_index=True)
df = df[(df["status"] == "ok") & (df["gap"] == 0)].reset_index(drop=True)
print("usable samples:", len(df))

train, test = train_test_split(df, test_size=0.2, random_state=42)
grid = {"n_estimators": [200, 400], "max_depth": [2, 3, 4], "learning_rate": [0.05, 0.1]}
models, metrics = {}, {}
for t, label in TARGETS.items():
    gs = GridSearchCV(XGBRegressor(subsample=0.9, colsample_bytree=0.9, random_state=0), grid,
                      cv=KFold(5, shuffle=True, random_state=0), scoring="neg_mean_absolute_error")
    gs.fit(train[FEATURES], train[t])
    m = gs.best_estimator_
    pred = m.predict(test[FEATURES])
    metrics[t] = {"label": label, "r2": r2_score(test[t], pred), "mae": mean_absolute_error(test[t], pred),
                  "rmse": float(np.sqrt(mean_squared_error(test[t], pred))), "params": gs.best_params_}
    m.fit(df[FEATURES], df[t])          # refit on all data for the search
    models[t] = m
    print(t, {k: v for k, v in metrics[t].items() if k != "label"})

# ---- candidate search over rule-checked random geometries
rng = np.random.default_rng(1)
cand = pd.DataFrame({k: rng.uniform(*RANGES[k], 200000) for k in FEATURES})
ok = [feasible(dict(r, d=2.4)) for r in cand.to_dict("records")]
cand = cand[ok].round(2).reset_index(drop=True)
for t, m in models.items():
    cand[t] = m.predict(cand[FEATURES])
good = cand[(cand["s11_245"] <= -15) & ((cand["f_res"] - 2.45).abs() <= 0.01)].copy()
good["score"] = good["bw_mhz"] + 10 * good["gain_rz_0"]
top = good.sort_values("score", ascending=False)
# keep diverse picks: skip near-duplicates of an already chosen geometry
picks = []
for _, r in top.iterrows():
    if all(np.abs(r[FEATURES].values - p[FEATURES].values).max() > 1.0 for p in picks):
        picks.append(r)
    if len(picks) == 3:
        break
picks = pd.DataFrame(picks)
print("candidates evaluated:", len(cand), "meeting constraints:", len(good))
print(picks.to_string())

json.dump(metrics, open("data/ml_metrics%s.json" % ROUND, "w"), indent=2)
picks.to_csv("data/ml_candidates%s.csv" % ROUND, index=False)
json.dump([dict({k: float(r[k]) for k in FEATURES}, gap=0) for _, r in picks.iterrows()],
          open("data/validate_jobs%s.json" % ROUND, "w"), indent=1)
json.dump({"n_samples": len(df), "n_train": len(train), "n_test": len(test), "n_candidates": len(cand),
           "n_meeting_constraints": len(good)}, open("data/ml_info%s.json" % ROUND, "w"), indent=2)
