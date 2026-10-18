# Operating a Pre-Test Validation Gate in an LLM-Based UI Test Repair Loop — Data and Code Excerpt

Replication material for:

> Dong Kwan Kim. *Operating a Pre-Test Validation Gate in an LLM-Based UI
> Test Repair Loop: What It Caught, What It Missed, and How to Score It.*
> **Software: Practice and Experience**, 2026 (revised version).

This repository holds:

- the raw logs of the 180 gate-live runs;
- the derived data and figures behind the reported results, including the
  evidence audit added in revision;
- an excerpt of the source code of the evaluated pipeline (`code/`): the gate,
  the two agents, the orchestration loop, and the SymptomReport type;
- a data dictionary, and a map from each reported result to its file.

The submitted version of the article was titled *Episode-Level Evaluation
Hides False Acceptances: Per-Patch Scoring of Validation Gates for UI Test
Repair*. The data are the same runs; the revision reframed the article as an
experience report and added the evidence audit.

---

## What the study measured

A pre-test gate, Grounding-Verified Patch Validation (GVPV), checks each
LLM-generated patch before the test run. It has four lexical checks: the file
parses (Check 0), the broken value is gone (Check 1), the replacement value
is present (Check 2), and the assertion count did not fall (Check 3). Every
quantity here is keyed to **gate decisions**, not repair episodes. Each
admission is paired with the verdict of the next test run.

| | |
|---|---|
| Gate-live runs | 180 |
| Gate decisions | 188 |
| Admitted | 143 |
| Rejected | 45 (9 parse failures, 3 Check 1, 33 Check 2, 0 Check 3) |
| Admitted but failed the next test (false acceptance) | 41 (28.7 %) |

Scored only over the final patches of successful episodes, the same runs show
zero false acceptances, as they must for any gate.

## What the evidence audit added

The gate takes its expected values from the repair agent's own `apply_patch`
request, not from the SymptomReport. The audit
(`data/gate_evidence_audit.json`, one record per decision in
`data/gate_evidence_audit_events.json`) re-walks the same 188 decisions and
records what the logs show about the evidence behind each one.

- **36 of 188 decisions** followed an `analyze_report` call that received a
  placeholder string instead of the report.
- **44 of 143 admissions** were made under conditions in which the logs do
  not establish that the enforced value came from the report. They failed
  the next test at 45.5 %, against 21.2 % for the other 99 (descriptive;
  decisions pooled across cells).
- **16 of 33 Check 2 rejections** enforced a value that cannot be a live UI
  fact: a foreign-package identifier, the collector's sentinel, or a
  timestamp.
- **Rejected patches are not rolled back.** Five were executed by a later
  test: four failed and one passed. These are the only observations of
  rejection correctness.
- **A precondition replay** over the visible values flags 25 admissions:
  19 that failed and 6 that passed. A further 23 admissions have no visible
  value. This is an offline replay, not a re-run, and not a demonstrated fix.

## Repository layout

```
code/                        excerpt of the evaluated pipeline (see code/README.md)
data/
  perpatch_summary.json      per-decision scoring of the gate (authoritative)
  gate_evidence_audit.json   evidence audit: aggregate counts
  gate_evidence_audit_events.json  evidence audit: one record per decision
  per_substudy.csv           decisions and FA counts per sub-study
  fa_by_subject.csv          FA rate per application
  fa_taxonomy.csv            FAs by the replacement value visible in the log
  fa_events.csv              one row per false acceptance
  rejections_by_check.csv    rejections attributed to each gate check
  replication_n5.csv         contextual n=5 replication, both platforms
  holdouts.csv               two holdout studies, full pipeline vs patch-only
  healenium.csv              exploratory Healenium probe
  run_summaries/             per-run JSON summaries (10 files)
logs/                        raw logs of the 180 gate-live runs (32 files)
figures/                     figure images and data (file names keep the
                             submitted version's numbering; see RESULTS_MAP.md)
DATA_DICTIONARY.md           every column of every file
RESULTS_MAP.md               each reported table/figure/finding -> its file
```

## Reproducing the paired contrast

The on/off contrast (Figure 4 of the revised article) can be reproduced from
`figures/fig3_gvpv_paired.csv` alone:

```bash
python - <<'EOF'
import csv
rows = [r for r in csv.DictReader(open('figures/fig3_gvpv_paired.csv'))
        if r['in_paired_contrast'] == 'yes']
for arm in ('on', 'off'):
    a = [r for r in rows if r['arm'] == arm]
    print(arm, sum(int(r['successes']) for r in a), '/', sum(int(r['n']) for r in a))
EOF
# on 42 / 60
# off 38 / 60
```

The contrast supports neither benefit nor equivalence. The sign test over the
three discordant cells gives p = 0.25. One gate-on success ended on a patch
the gate had rejected; not crediting it gives 41/60 against 38/60
(p = 0.5). Relaxing the exclusion rule moves the result:

| Cells admitted | With gate | Without gate | Difference |
|---|---|---|---|
| Seven log-verified (reported) | 42/60 | 38/60 | +6.7 pp |
| All three excluded added back | 65/90 | 60/90 | +5.6 pp |
| Only the two with a real seeded fault | 55/80 | 54/80 | +1.2 pp |

Three Wikipedia cells are excluded because the gate's disable toggle silently
failed in their off arm. Every excluded cell is in
`figures/fig3_gvpv_paired.csv` with `in_paired_contrast = no` and an
`exclusion_reason`.

## Scope and known limits of this data

- **The enforced value is not in the logs.** The logs truncate the arguments
  of every `apply_patch` call. For admissions, the value the gate checked is
  therefore unknown. `fa_events.csv` and `fa_taxonomy.csv` use the
  replacement value *visible* in the log before each admission, which is not
  necessarily the value the gate applied. For the sentinel class it cannot
  have been.
- **Group B of the taxonomy is undetermined, not sound.** It carries no
  evidence that the remaining false acceptances are fixable by any
  precondition.
- **Rejection correctness is unobserved** except for the five rejected
  patches that a later test executed.
- **The time saved is an upper bound.** 45 rejections × 90 s ≈ 68 min,
  assuming every rejection displaced a full cycle and was correct. Removing
  the executed rejections and the parse failures (13 patches together) leaves
  32 rejections, about 48 min, under the same assumption.
- **MTTR is a mean over successful runs only.** `holdouts.csv` also carries
  medians and per-run timings.
- **Seeded faults**, not mined real ones, back the main results. The holdouts
  did not test whether live grounding is necessary: a patch-only synthesizer
  sidestepped them by changing locator strategy.

## How the logs were prepared

The logs in `logs/` are the raw run output with exactly one edit: the
author's local working directory was replaced throughout by the placeholder
`<WORKSPACE>`. No observation, verdict, timing, or ordering was changed.

The orchestrator wrote its progress messages in Korean, and the seeded test
fixtures carry Korean docstrings that the logs echo. Neither carries any
measurement. `DATA_DICTIONARY.md` translates the recurring lines.

## What is not here

- The remaining source code: experiment runners, pytest fixtures and seeded
  fault scenarios, web collectors, the Healenium probe, the per-decision
  scorer (`score_patches.py`), the evidence-audit script
  (`gate_evidence_audit.py`), and the statistics scripts.
- Raw logs of exploratory sub-studies that no reported finding depends on:
  extended backbone sweeps, mined-real-fault replay, fault-template
  diversification, web replication, multi-fault and deep-navigation cells,
  and the holdout and Healenium runs (their per-run JSON summaries **are**
  included, in `data/run_summaries/`).

These are available from the corresponding author on request.

## Citation

```bibtex
@article{Kim2026Gate,
  author  = {Kim, Dong Kwan},
  title   = {Operating a Pre-Test Validation Gate in an {LLM}-Based {UI} Test
             Repair Loop: What It Caught, What It Missed, and How to Score It},
  journal = {Software: Practice and Experience},
  year    = {2026}
}
```

## License

Data and figures are released under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). No license is
granted for the code excerpt in `code/`; it is provided for inspection.
