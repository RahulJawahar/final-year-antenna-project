# Machine Learning-Assisted Design and Parameter Optimization of a Compact Wearable SIW Antenna for WBAN Applications

Final year project, batch BC09 — Department of ECE, KPR Institute of Engineering and Technology.
Team: Rahul J, Nandha Kishore VS, Siva Saran S. Guide: Dr. T. Jagadesh.

A 2.45 GHz cavity-backed slot antenna in substrate integrated waveguide (SIW) technology on a flexible
foam substrate, tuned in CST Studio Suite and optimized with an XGBoost surrogate model.
This repository holds the **simulation and machine learning** part of the project (fabrication and
measurement are not yet done).

## Antenna

- Board 78 × 83 mm, foam substrate h = 3.94 mm, εr = 1.575, tan δ = 0.0238, copper 0.035 mm
- 66 perimeter vias, Ø 2.4 mm, forming a rectangular SIW cavity
- Rectangular radiating slot in the top copper; full ground plane facing the body
- 50 Ω coaxial probe feed from the ground side
- Origin at the board centre on the substrate bottom; +z points away from the body

## Results (CST Studio Suite 2026 Learning Edition, time-domain solver)

| | Initial design | Tuned baseline | ML-optimized (CST-verified) |
|---|---|---|---|
| Cavity W × L (mm) | 68 × 73 | 64.5 × 69.5 | 63.58 × 69.56 |
| Slot Ls × Ws, centre ys (mm) | 50 × 2, 10 | 50 × 2, 10 | 54.25 × 3.44, 10.59 |
| Feed yf (mm) / probe gap (mm) | −18 / 0.94 | −24 / 0 | −20.29 / 0 |
| Resonance (GHz) | 2.303 | 2.452 | 2.454 |
| S11 at 2.45 GHz (dB) | −0.13 | −31.6 | −15.6 |
| −10 dB band (GHz) | — | 2.423 – 2.482 | 2.417 – 2.493 |
| Bandwidth (MHz) | 0 | 59.4 | **76.1** |
| Realized gain, θ = 0° (dBi) | −16.8 | 1.51 | **2.84** |
| Front-to-back ratio (dB) | 15.2 | 15.3 | 15.3 |
| Total efficiency (%) | 0.5 | 34.2 | **46.2** |

The initial design was strongly mismatched. Tuning showed the probe-to-top-wall gap was the dominant
matching parameter; the probe is soldered to the top copper in the tuned and optimized designs.

### XGBoost surrogate (87 CST samples, 69 train / 18 held-out test)

| Output | R² | MAE | RMSE |
|---|---|---|---|
| Resonant frequency (GHz) | 0.853 | 0.020 | 0.027 |
| S11 at 2.45 GHz (dB) | 0.251 | 4.34 | 6.02 |
| −10 dB bandwidth (MHz) | 0.630 | 10.58 | 15.01 |
| Realized gain (dBi) | 0.905 | 0.95 | 1.16 |

200,000 rule-checked random geometries were screened; candidates were re-simulated in CST, added back
to the training data (one active-learning round), and the best verified design is the one above.
In total 107 CST simulations were run.

## Repository layout

```
cst/
  cst_build.py      builds the parametric antenna model in CST over COM (initial design)
  cst_sim.py        runs CST for a list of parameter sets and logs S11, bandwidth, gain, F/B, efficiency
  cst_results.py    extracts S11 and efficiencies of the currently open project
ml/
  gen_dataset.py    Latin hypercube sampling with SIW design-rule / clearance checks
  train_xgb.py      trains XGBoost models and searches for improved geometries
data/
  runs.csv          30 tuning runs (run 27 = tuned baseline)
  dataset.csv       70 Latin hypercube dataset runs
  validate.csv      ML round 1 candidates re-simulated in CST
  validate2.csv     ML round 2 candidates re-simulated in CST
  final.csv         final ML-optimized design
  ml_metrics*.json  held-out accuracy per round;  ml_candidates*.csv  predicted candidates
  *jobs*.json, explore*.json, tune*.json   parameter sets fed to cst_sim.py
  initial_design/   S11 curve and summary of the very first simulation
cst_project/
  BC09_SIW_Antenna.cst   CST Learning Edition project (results folder not included)
```

## How to reproduce

Requirements: Windows, CST Studio Suite 2026 (Learning Edition is enough), Python 3 with
`pip install -r requirements.txt`. CST must be running; the scripts attach to it over COM.
Run all commands from the repository root.

```bash
python cst/cst_build.py                                      # build the model in a new CST project
python cst/cst_sim.py data/final_job.json data/my_runs.csv   # simulate any parameter sets
python ml/gen_dataset.py 70 7 data/dataset_jobs.json         # regenerate the LHS samples
python ml/train_xgb.py 2                                     # train models and search candidates
```

Each simulation takes about one minute. The Learning Edition limits the mesh to 100,000 hexahedral
cells, so the mesh density, the λ/8 air spacing and the 2–3 GHz band are chosen to stay under that
limit; expect small shifts with a finer mesh in the full edition.

## Limitations / next steps

- Fabrication and VNA measurement of the optimized design
- Confirm the foam permittivity and loss tangent in the laboratory
- Extend the band to cover the full 2.400–2.4835 GHz ISM band
- On-body (SAR) and bending analysis
