# Ranking evaluation results

- Run date (UTC): 2026-11-12T11:31:37.658150+00:00
- Repository ID: 363150
- Commit: `5405455`
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

## Answerable only

| Preset | Split | Queries | MRR (95% CI) | Paired MRR delta vs baseline (95% CI) | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Candidate recall | Mean candidates |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| semantic | train | 66 | 0.3505 [0.278, 0.425] | [-0.481, -0.321] | 0.1364 | 0.5000 | 0.5758 | 0.6667 | 1.0000 | 37.94 |
| semantic | test | 51 | 0.5474 [0.435, 0.653] | [-0.467, -0.249] | 0.4118 | 0.6275 | 0.7255 | 0.7843 | 1.0000 | 46.57 |
| legacy-graph | train | 121 | 0.4103 [0.330, 0.493] | [0.000, 0.000] | 0.3306 | 0.4876 | 0.5124 | 0.5372 | 0.5455 | 38.54 |
| legacy-graph | test | 59 | 0.7797 [0.692, 0.864] | [0.000, 0.000] | 0.7119 | 0.8644 | 0.8644 | 0.8644 | 0.8644 | 48.17 |
| legacy-pagerank | train | 121 | 0.3535 [0.283, 0.431] | [-0.088, -0.021] | 0.2645 | 0.4050 | 0.4545 | 0.5124 | 0.5455 | 38.54 |
| legacy-pagerank | test | 59 | 0.5795 [0.490, 0.677] | [-0.275, -0.129] | 0.4068 | 0.7288 | 0.8305 | 0.8644 | 0.8644 | 48.17 |
