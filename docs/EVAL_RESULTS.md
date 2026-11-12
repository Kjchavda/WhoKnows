# Ranking evaluation results

- Run date (UTC): 2026-11-12T12:05:05.202683+00:00
- Repository ID: 363150
- Commit: `b1ccc6c`
- Baseline: `legacy-graph`
- Holdout: 30%

Numbers are **not comparable** to earlier ad-hoc runs because this harness now matches the production path (bot filter, `ef_search`, and issue self-exclusion).

Metrics are macro-averaged per query. MRR confidence intervals use 1000 bootstrap resamples with seed 42. Paired intervals compare each preset with the baseline on the same queries.

## Overall

| Preset | Split | Queries | MRR (95% CI) | Paired MRR delta vs baseline (95% CI) | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Candidate recall | Mean candidates |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| semantic | train | 140 | 0.1652 [0.119, 0.215] | [-0.241, -0.141] | 0.0643 | 0.2357 | 0.2714 | 0.3143 | 0.4714 | 38.97 |
| semantic | test | 60 | 0.4653 [0.369, 0.570] | [-0.406, -0.209] | 0.3500 | 0.5333 | 0.6167 | 0.6667 | 0.8500 | 47.98 |
| legacy-graph | train | 140 | 0.3546 [0.280, 0.430] | [0.000, 0.000] | 0.2857 | 0.4214 | 0.4429 | 0.4643 | 0.4714 | 38.97 |
| legacy-graph | test | 60 | 0.7667 [0.675, 0.850] | [0.000, 0.000] | 0.7000 | 0.8500 | 0.8500 | 0.8500 | 0.8500 | 47.98 |
| legacy-pagerank | train | 140 | 0.3055 [0.239, 0.378] | [-0.078, -0.021] | 0.2286 | 0.3500 | 0.3929 | 0.4429 | 0.4714 | 38.97 |
| legacy-pagerank | test | 60 | 0.5699 [0.474, 0.665] | [-0.274, -0.122] | 0.4000 | 0.7167 | 0.8167 | 0.8500 | 0.8500 | 47.98 |
| v2-graph | train | 140 | 0.3582 [0.284, 0.432] | [-0.008, 0.017] | 0.2929 | 0.4214 | 0.4429 | 0.4643 | 0.4714 | 38.97 |
| v2-graph | test | 60 | 0.7667 [0.675, 0.850] | [-0.025, 0.025] | 0.7000 | 0.8500 | 0.8500 | 0.8500 | 0.8500 | 47.98 |
| v2-pagerank | train | 140 | 0.3990 [0.321, 0.475] | [0.013, 0.078] | 0.3429 | 0.4500 | 0.4571 | 0.4714 | 0.4714 | 38.97 |
| v2-pagerank | test | 60 | 0.8417 [0.750, 0.925] | [0.031, 0.122] | 0.8333 | 0.8500 | 0.8500 | 0.8500 | 0.8500 | 47.98 |
| v2-seeds | train | 140 | 0.3595 [0.285, 0.433] | [-0.000, 0.014] | 0.2929 | 0.4214 | 0.4429 | 0.4643 | 0.4714 | 38.97 |
| v2-seeds | test | 60 | 0.7861 [0.692, 0.869] | [0.000, 0.044] | 0.7333 | 0.8500 | 0.8500 | 0.8500 | 0.8500 | 47.98 |
| v2-seeds-cand | train | 140 | 0.4583 [0.393, 0.524] | [0.066, 0.140] | 0.2929 | 0.6071 | 0.6429 | 0.7214 | 0.9071 | 68.97 |
| v2-seeds-cand | test | 60 | 0.9139 [0.853, 0.967] | [0.083, 0.217] | 0.8667 | 0.9667 | 0.9667 | 0.9667 | 0.9667 | 77.98 |
| v2-pagerank-seeds-cand | train | 140 | 0.4481 [0.380, 0.523] | [0.057, 0.132] | 0.3429 | 0.4857 | 0.5143 | 0.6000 | 0.9071 | 68.97 |
| v2-pagerank-seeds-cand | test | 60 | 0.8500 [0.763, 0.927] | [0.039, 0.127] | 0.8333 | 0.8500 | 0.8500 | 0.8500 | 0.9667 | 77.98 |

## Answerable only

| Preset | Split | Queries | MRR (95% CI) | Paired MRR delta vs baseline (95% CI) | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Candidate recall | Mean candidates |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| semantic | train | 66 | 0.3505 [0.278, 0.425] | [-0.481, -0.321] | 0.1364 | 0.5000 | 0.5758 | 0.6667 | 1.0000 | 37.94 |
| semantic | test | 51 | 0.5474 [0.435, 0.653] | [-0.467, -0.249] | 0.4118 | 0.6275 | 0.7255 | 0.7843 | 1.0000 | 46.57 |
| legacy-graph | train | 121 | 0.4103 [0.330, 0.493] | [0.000, 0.000] | 0.3306 | 0.4876 | 0.5124 | 0.5372 | 0.5455 | 38.54 |
| legacy-graph | test | 59 | 0.7797 [0.692, 0.864] | [0.000, 0.000] | 0.7119 | 0.8644 | 0.8644 | 0.8644 | 0.8644 | 48.17 |
| legacy-pagerank | train | 121 | 0.3535 [0.283, 0.431] | [-0.088, -0.021] | 0.2645 | 0.4050 | 0.4545 | 0.5124 | 0.5455 | 38.54 |
| legacy-pagerank | test | 59 | 0.5795 [0.490, 0.677] | [-0.275, -0.129] | 0.4068 | 0.7288 | 0.8305 | 0.8644 | 0.8644 | 48.17 |
| v2-graph | train | 129 | 0.3887 [0.312, 0.465] | [-0.009, 0.020] | 0.3178 | 0.4574 | 0.4806 | 0.5039 | 0.5116 | 38.47 |
| v2-graph | test | 59 | 0.7797 [0.692, 0.870] | [-0.025, 0.025] | 0.7119 | 0.8644 | 0.8644 | 0.8644 | 0.8644 | 48.17 |
| v2-pagerank | train | 129 | 0.4331 [0.356, 0.514] | [0.016, 0.091] | 0.3721 | 0.4884 | 0.4961 | 0.5116 | 0.5116 | 38.47 |
| v2-pagerank | test | 59 | 0.8559 [0.771, 0.932] | [0.031, 0.127] | 0.8475 | 0.8644 | 0.8644 | 0.8644 | 0.8644 | 48.17 |
| v2-seeds | train | 129 | 0.3901 [0.315, 0.465] | [-0.000, 0.015] | 0.3178 | 0.4574 | 0.4806 | 0.5039 | 0.5116 | 38.47 |
| v2-seeds | test | 59 | 0.7994 [0.712, 0.884] | [0.000, 0.045] | 0.7458 | 0.8644 | 0.8644 | 0.8644 | 0.8644 | 48.17 |
| v2-seeds-cand | train | 129 | 0.4974 [0.435, 0.563] | [0.077, 0.157] | 0.3178 | 0.6589 | 0.6977 | 0.7829 | 0.9845 | 68.47 |
| v2-seeds-cand | test | 59 | 0.9294 [0.876, 0.975] | [0.085, 0.212] | 0.8814 | 0.9831 | 0.9831 | 0.9831 | 0.9831 | 78.17 |
| v2-pagerank-seeds-cand | train | 129 | 0.4863 [0.417, 0.561] | [0.066, 0.150] | 0.3721 | 0.5271 | 0.5581 | 0.6512 | 0.9845 | 68.47 |
| v2-pagerank-seeds-cand | test | 59 | 0.8644 [0.785, 0.937] | [0.038, 0.135] | 0.8475 | 0.8644 | 0.8644 | 0.8644 | 0.9831 | 78.17 |

## What changed and what moved

| Preset | Test MRR | Test Hit@3 | Test candidate recall | Paired MRR delta vs baseline (95% CI) |
|---|---:|---:|---:|---:|
| semantic | 0.4653 | 0.5333 | 0.8500 | [-0.406, -0.209] |
| legacy-graph | 0.7667 | 0.8500 | 0.8500 | [0.000, 0.000] |
| legacy-pagerank | 0.5699 | 0.7167 | 0.8500 | [-0.274, -0.122] |
| v2-graph | 0.7667 | 0.8500 | 0.8500 | [-0.025, 0.025] |
| v2-pagerank | 0.8417 | 0.8500 | 0.8500 | [0.031, 0.122] |
| v2-seeds | 0.7861 | 0.8500 | 0.8500 | [0.000, 0.044] |
| v2-seeds-cand | 0.9139 | 0.9667 | 0.9667 | [0.083, 0.217] |
| v2-pagerank-seeds-cand | 0.8500 | 0.8500 | 0.9667 | [0.039, 0.127] |

Test-split presets whose paired MRR-difference interval is entirely above zero: `v2-pagerank`, `v2-seeds-cand`, `v2-pagerank-seeds-cand`. These are candidates for owner review, not automatic promotions; `DEFAULT_PRESET` remains `legacy-graph`.

Known limitations: `pr_files` reflects each PR's final file set, and the `developers` table has no time dimension.
