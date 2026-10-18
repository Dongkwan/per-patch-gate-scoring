# Mapping from Reported Results to Data Files

Every table, figure, and finding of the revised article, and the file it
comes from. Table, figure, and section numbers refer to the revised version.
Figure files in `figures/` keep the submitted version's numbering, shown in
the Image column.

`audit` below means `data/gate_evidence_audit.json`.

## Tables

| # | Caption | File |
|---|---|---|
| 1 | Prior repair systems, by evidence at repair time and pre-test check | literature summary, no data file |
| 2 | SymptomReport fields GVPV depends on | design description; code in `code/lara/report.py` |
| 3 | Per-decision log record | specification, no data file |
| 4 | Contextual n=5 replication | `data/replication_n5.csv` |
| 5 | Per-decision GVPV outcomes | `data/per_substudy.csv` |
| 6 | The 45 rejections, by condition and enforced value | `data/rejections_by_check.csv`; audit → `check2_rejections_by_enforced_value`, `check2_enforced_values` |
| 7 | Evidence state of the 143 admissions | audit → `analyze_input`, `admitted_after_check2_rejection_same_loop`, `traceability`, `visible_value_precondition` |
| 8 | The 41 false acceptances, by visible replacement value | `data/fa_taxonomy.csv`, `data/fa_events.csv` |
| 9 | Full pipeline against patch-only synthesis on the two holdouts | `data/holdouts.csv` |
| SI S6 | Healenium probe on the six web cells | `data/healenium.csv` |

## Figures

| # | Caption | Image | Data |
|---|---|---|---|
| 1 | Path by which a value reaches the gate | none (drawn in the article) | code: `code/lara/repair_agent.py`, `code/lara/gate.py` |
| 2 | Running example: the AnkiDroid locator-fault workflow | `figures/fig1_running_example.{pdf,png}` | schematic, none |
| 3 | False-acceptance rate by application | `figures/fig2_fa_stratified.{pdf,png}` | `figures/fig2_fa_stratified.csv` |
| 4 | Repair success rate with and without GVPV | `figures/fig3_gvpv_paired.{pdf,png}` | `figures/fig3_gvpv_paired.csv` |

## Findings

| Box | Answers | Files |
|---|---|---|
| Finding 1 | RQ1 and RQ2 | `data/per_substudy.csv`, `data/rejections_by_check.csv`, audit, `figures/fig3_gvpv_paired.csv` |
| Finding 2 | RQ1 | audit, `data/fa_taxonomy.csv`, `data/fa_events.csv` |
| Finding 3 | RQ3 | `data/holdouts.csv`, `data/healenium.csv` |

## Individual quantities

### Sections 4.3.1 — decisions and false acceptances

| Quantity | Value | Where |
|---|---|---|
| Gate-live runs | 180 | `data/per_substudy.csv`, sum of `runs` |
| Gate decisions | 188 | `data/perpatch_summary.json` → `n_decisions`; audit → `decisions` |
| Admitted / rejected | 143 / 45 | `data/per_substudy.csv` |
| False acceptances | 41 (28.7 %) | `data/per_substudy.csv`, sum of `false_acceptances` |
| Admitted with no subsequent verdict | 1 | audit → `admitted_no_verdict` |
| `apply_patch` calls that never reached the gate | 294 | `data/perpatch_summary.json` → `unreached_gate` |
| Per-subject FA rates | 12.8 / 25.0 / 43.3 % | `data/fa_by_subject.csv` |
| Wikipedia's share of admissions / FAs | 42 % / 63 % | `data/fa_by_subject.csv` |

The 95 % cluster bootstrap CI, [12.2, 45.9] over 21 cells, is computed by a
script not included here; the counts it resamples are in
`data/perpatch_summary.json`.

### Section 4.3.2 — what the rejections were

| Quantity | Value | Where |
|---|---|---|
| Parse failures / Check 1 / Check 2 / Check 3 | 9 / 3 / 33 / 0 | `data/rejections_by_check.csv` |
| Check 2 rejections enforcing a value that cannot be a live UI fact | 16 (foreign package 10, sentinel 5, timestamp 1) | audit → `check2_rejections_by_enforced_value` |
| Check 2 rejections whose value passes the precondition | 17 (4 not UI facts on inspection, 13 plausibly live) | audit → `check2_rejections_by_enforced_value.pass`, `check2_enforced_values` |
| Rejected patches executed by a later test | 5 (4 failed, 1 passed) | audit → `rejected_patch_executed`, `rejected_patch_next_event` |
| Time-saved upper bound | 68 min (45 × 90 s); 48 min (32 × 90 s) | derived |

### Section 4.3.3 — evidence behind the admissions

| Quantity | Value | Where |
|---|---|---|
| Analysis step received the report / a placeholder / no analysis step | 118 / 17 / 8 admissions | audit → `analyze_input` (FA + TA + no_verdict) |
| Request re-issued after a Check 2 rejection | 14 (9 FA) | audit → `admitted_after_check2_rejection_same_loop` |
| Visible value is the collector sentinel | 7 (4 FA) | audit → `traceability.sentinel_visible_on_admission` |
| No replacement value visible | 23 (5 FA) | audit → `visible_value_precondition` (`not_visible`) |
| Untraceable / traceable admissions | 44 (20 FA) / 99 (21 FA) | audit → `traceability` |
| Decisions after a placeholder analysis call | 36 of 188 | audit → `analyze_input` (`stub` across all outcomes) |

The indicator rows overlap; their counts sum to 69, and their union is the 44
untraceable admissions.

### Section 4.3.4 — visible values and the precondition replay

| Quantity | Value | Where |
|---|---|---|
| Group A (visible value cannot be a live UI fact) | 19 of 41: A1 14, A2 4, A3 1 | `data/fa_taxonomy.csv` |
| Group B (undetermined) | 22 | `data/fa_taxonomy.csv` |
| Replay: flagged admissions | 25 (19 FA, 6 TA) | audit → `precondition_replay` |
| Replay: admissions with no visible value | 23 (5 FA, 18 TA) | audit → `precondition_replay` |
| Listing 1 trace | run 1, cycle 2 | `logs/exp_gvpv_ext_wikipedia_S2_qwen_gvpv_on_20260801_132044.log` |

### Section 4.3.5 — paired on/off effect

| Quantity | Value | Where |
|---|---|---|
| Log-verified paired cells | 7 | `figures/fig3_gvpv_paired.csv`, `in_paired_contrast = yes` |
| With / without the gate | 42/60 vs 38/60 | same, by `arm` |
| Without the run that ended on a rejected patch | 41/60 vs 38/60 | audit → `rejected_patch_executed` (the passing one) |
| All three excluded cells added back | 65/90 vs 60/90 | all rows |
| Only the two with a real seeded fault added back | 55/80 vs 54/80 | all rows except `wiki_rerun_n10` S1 |
| MTTR on the AnkiDroid S1 pair | 89.5 s vs 79.4 s | `data/run_summaries/exp_gvpv_paired_*.json` |

The sign tests (p = 0.25, p = 0.5) and the Newcombe interval
[−10.0, +22.9] pp are computed by scripts not included here.

### Section 5 — boundary conditions

| Quantity | Value | Where |
|---|---|---|
| Patch-only against full pipeline | 20/20 vs 15/20 | `data/holdouts.csv` |
| Per-scenario MTTR, both arms | — | `data/holdouts.csv` |
| Healenium healed runs (exploratory) | 3/18, Ghost S1 only | `data/healenium.csv` |

## Results whose data is not in this repository

Exploratory sub-studies that no reported finding depends on. Available from
the corresponding author on request.

| Result | Article location |
|---|---|
| Extended backbone sweep | Supporting Information S1, S6 |
| Mined-real-fault replay, 13 of 15 cells | Section 5.2 |
| Fault-template diversification, 4 of 9 cells | Section 5.2 |
| Multi-fault and deep-navigation cells | Supporting Information S7 |
| Raw logs for the holdout and Healenium runs | Section 5 (per-run JSON summaries **are** included) |
