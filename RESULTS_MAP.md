# Mapping from Reported Results to Data Files

Every number, table, and figure in the article, and the file it comes from.
Section numbers refer to the published version.

## Tables

| # | Caption | File |
|---|---|---|
| 1 | Prior repair systems, by evidence at repair time and pre-test check | — literature summary, no data file |
| 2 | SymptomReport fields GVPV depends on | — design description, no data file |
| 3 | Contextual n=5 replication | `data/replication_n5.csv` |
| 4 | Per-patch GVPV decisions and observed false acceptances | `data/per_substudy.csv`, `data/rejections_by_check.csv` |
| 5 | Classification of the 41 false acceptances | `data/fa_taxonomy.csv`, `data/fa_events.csv` |
| 6 | Full pipeline against patch-only synthesis on the two holdouts | `data/holdouts.csv` |
| 7 | Healenium 4.0.0 on the six web cells | `data/healenium.csv` |

## Figures

| # | Caption | Image | Data |
|---|---|---|---|
| 1 | Running example: the AnkiDroid locator-fault workflow | `figures/fig1_running_example.{pdf,png}` | schematic, none |
| 2 | False-acceptance rate by application | `figures/fig2_fa_stratified.{pdf,png}` | `figures/fig2_fa_stratified.csv` |
| 3 | Repair success rate with and without GVPV | `figures/fig3_gvpv_paired.{pdf,png}` | `figures/fig3_gvpv_paired.csv` |

## Findings

| Box | Answers | Files |
|---|---|---|
| Finding 1 | RQ1 and RQ2 | `data/per_substudy.csv`, `figures/fig3_gvpv_paired.csv` |
| Finding 2 | RQ1 | `data/fa_taxonomy.csv`, `data/fa_events.csv`, `data/rejections_by_check.csv` |
| Finding 3 | RQ3 | `data/holdouts.csv`, `data/healenium.csv` |

## Individual quantities

Ordered as they appear in the article.

### Abstract and Section 5 — the gate's per-patch record

| Quantity | Value | Where |
|---|---|---|
| Gate-live runs | 180 | `data/per_substudy.csv`, sum of `runs` |
| Patch decisions adjudicated | 188 | `perpatch_summary.json` → `n_decisions` |
| Rejected | 45 (23.9 %) | `data/per_substudy.csv`, sum of `rejected` |
| Admitted | 143 | `data/per_substudy.csv`, sum of `admitted` |
| False acceptances | 41 (28.7 %) | `data/per_substudy.csv`, sum of `false_acceptances` |
| `apply_patch` calls that never reached the gate | 294 | `perpatch_summary.json` → `unreached_gate` |
| Per-subject FA rates | 12.8 / 25.0 / 43.3 % | `data/fa_by_subject.csv` |
| Wikipedia's share of admissions / FAs | 42 % / 63 % | `data/fa_by_subject.csv` |

The 95 % cluster bootstrap CI on the FA rate, [12.2, 45.9] over 21 cells, is
computed by a script not included here (see README, *Source code*); the counts
it resamples are in `data/per_substudy.csv`.

### Section 5.2.2 — false-acceptance mechanism

| Quantity | Value | Where |
|---|---|---|
| Group A (provably not a live UI fact) | 19 of 41 (46.3 %) | `data/fa_taxonomy.csv` |
| A1 foreign-application identifier | 14 | `data/fa_taxonomy.csv` |
| A2 collector sentinel | 4 | `data/fa_taxonomy.csv` |
| A3 non-locator value | 1 | `data/fa_taxonomy.csv` |
| Group B (undetermined) | 22 (53.7 %) | `data/fa_taxonomy.csv` |
| Listing 1 trace | run 1, cycle 2 | `logs/exp_gvpv_ext_wikipedia_S2_qwen_gvpv_on_20260801_132044.log` |

Group A is carried by only four distinct strings across the 19 events, all of
which a schema, type, and namespace precondition on the report rejects on
sight. Inspect them with:

```bash
cut -d, -f3 data/fa_events.csv | sort | uniq -c | sort -rn
```

### Section 5.2.3 — paired on/off effect

| Quantity | Value | Where |
|---|---|---|
| Log-verified paired cells | 7 | `figures/fig3_gvpv_paired.csv`, `in_paired_contrast = yes` |
| With the gate | 42/60 | same, `arm = on` |
| Without the gate | 38/60 | same, `arm = off` |
| Difference | +6.7 pp | derived |
| All three excluded cells added back | 65/90 vs 60/90 (+5.6 pp) | all rows |
| Only the two with a real seeded fault added back | 55/80 vs 54/80 (+1.2 pp) | all rows except `wiki_rerun_n10` S1 |
| MTTR cost on the AnkiDroid S1 pair | 89.5 s vs 79.4 s (+12.7 %) | `data/run_summaries/exp_gvpv_paired_*.json` |

The exact sign test (p = 0.25) runs over the three discordant cells; the
Newcombe interval [−10.0, +22.9] pp is computed by a script not included here.

### Section 6 — boundary conditions

| Quantity | Value | Where |
|---|---|---|
| Patch-only against full pipeline | 20/20 vs 15/20 | `data/holdouts.csv` |
| Per-scenario MTTR, both arms | — | `data/holdouts.csv` |
| Healenium healed cells | 3/18 | `data/healenium.csv` |
| Healenium healing time | 0.051 s | `data/healenium.csv`, mean of successful `mttr_s` |

Fisher exact p = 0.047 and Cohen's h = −1.05 are computed by a script not
included here; the counts are in `data/holdouts.csv`.

## Results whose data is not in this repository

Included in the article but resting on sub-studies omitted here to keep the
repository small. All are exploratory or contextual, and no reported finding
depends on them. Available from the corresponding author on request.

| Result | Article location |
|---|---|
| Extended backbone sweep, six open-weight models | Supporting Information |
| Mined-real-fault replay, 13 of 15 cells | Section 6.3 |
| Fault-template diversification, 4 of 9 cells | Section 6.3 |
| Multi-fault and deep-navigation cells | Supporting Information |
| Raw logs for the holdout and Healenium studies | Section 6 (their per-run JSON summaries **are** included) |
