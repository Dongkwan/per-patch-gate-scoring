# Data Dictionary

Every file, every column. Units are seconds for time and counts for `n`
columns unless stated. Percentages are 0–100, not 0–1.

## Vocabulary

The article's unit of analysis is the **patch decision**, not the repair
episode. These terms are used consistently across all files.

| Term | Meaning |
|---|---|
| **Gate-live run** | A run in which the GVPV gate actually executed. Not the same as a run *configured* with the gate on: the disable toggle silently failed in three cells, so the gate was live there despite an intended-off configuration. |
| **Decision / adjudicated patch** | One `apply_patch` invocation that reached the gate and received a verdict. |
| **Admitted** | The gate returned `VERIFIED` and the patch proceeded to pytest. |
| **Rejected** | The gate returned `GVPV-FAIL`. The patch is never executed, so whether the rejection was correct is **not observable**. |
| **False acceptance (FA)** | An admitted patch that the next pytest run rejected. Directly observable. |
| **Unreached** | An `apply_patch` call that failed argument validation and never reached the gate (294 across the corpus). Excluded from all decision counts. |
| **Enforced oracle** | The `correct_value` the gate is taken to have checked the patch against. **Reconstructed, not observed** — see the caveat in `fa_events.csv`. |

---

## `data/perpatch_summary.json`

The authoritative derived artifact. All CSVs in `data/` are flat projections
of it. Top-level keys:

| Key | Type | Contents |
|---|---|---|
| `totals` | object | `runs`, `adjudicated`, `admitted`, `rejected`, `fa`, `rejection_rate`, `fa_rate` |
| `per_substudy` | object | The same counts keyed by sub-study name |
| `stratified_by_subject` | object | `admitted`, `fa`, `fa_rate` per application |
| `fa_by_subject` | object | FA count per application (a subset of the above) |
| `rejections_by_check` | object | Rejections attributed to Check 0/1/2/3 |
| `fa_taxonomy_auto` | object | FA counts per taxonomy class |
| `fa_events` | array | One object per false acceptance |
| `unreached_gate` | int | `apply_patch` calls that never reached the gate |
| `n_decisions` | int | Total adjudicated patches (188) |

## `data/per_substudy.csv`

| Column | Description |
|---|---|
| `substudy` | One of four: Android replication (n=5), Paired ablation (n=5), Extended paired (n=10), Wikipedia re-run (n=10) |
| `runs` | Gate-live runs in the sub-study |
| `admitted` | Patches the gate admitted |
| `rejected` | Patches the gate rejected |
| `false_acceptances` | Admitted patches the next pytest rejected |
| `fa_rate_pct` | `false_acceptances / admitted` × 100 |

`admitted + rejected` exceeds `runs` because a run adjudicates more than one
candidate patch. Columns sum to 180 runs, 143 admitted, 45 rejected, 41 FA.

## `data/fa_by_subject.csv` and `figures/fig2_fa_stratified.csv`

Identical content; the second is co-located with the figure it draws.

| Column | Description |
|---|---|
| `subject` | `ankidroid`, `newpipe`, or `wikipedia` |
| `admitted` | Patches admitted on that subject |
| `false_acceptances` | Of those, how many failed the next pytest |
| `fa_rate_pct` | 12.8, 25.0, and 43.3 respectively |

## `data/fa_taxonomy.csv`

| Column | Description |
|---|---|
| `class` | `A1` foreign-application identifier; `A2` collector sentinel string; `A3` non-locator value (ISO-8601 timestamp); `B` everything not provably invalid, undetermined |
| `n` | Count. A1 14, A2 4, A3 1, B 22 |

Group A = A1 + A2 + A3 = 19 of 41 (46.3 %): values that provably cannot be a
live UI fact. Group B is labelled **undetermined, not sound** — the logs
truncate both the report echo and the collected UI hierarchy, so those values
cannot be shown to be live facts either way.

## `data/fa_events.csv`

One row per false acceptance (41 rows).

| Column | Description |
|---|---|
| `log` | The run log the event was scored from, in `logs/` |
| `subject` | Application under test |
| `enforced_oracle` | The `correct_value` taken to have been enforced |
| `class` | Taxonomy class, as above |
| `oracle_source` | Which log line `enforced_oracle` was read from: `SymptomReport echo` (30 events) or `Check2 rejection` (11). The echo dominates, so what the taxonomy mostly classifies is the value the report supplied — the value a report-level precondition would screen. |

> **Caveat.** `enforced_oracle` is **reconstructed**. The logs truncate the
> arguments of every `apply_patch` call, so the value actually enforced on an
> admitted patch is never recorded. It is recovered from the nearest preceding
> Check 2 rejection message, or failing that from the report echo in the
> preceding `analyze_report` observation. Because the gate reads that value
> from the agent's own patch request, and the agent may restate it between
> attempts, the reconstruction can differ from the value applied. `class` is
> derived from `enforced_oracle` and inherits the uncertainty. Long values are
> truncated in the log and therefore in this column.

## `data/rejections_by_check.csv`

| Column | Description |
|---|---|
| `check` | `Check 0` patch parses; `Check 1` broken value absent; `Check 2` correct value present; `Check 3` assertion count preserved |
| `n` | Rejections attributed to that check |

Only Check 2 supplies positive correctness evidence; the others are sanity
constraints. Check 2 is skipped when the correct value is empty or is a
collector placeholder, so a patch can be admitted with no positive test
applied to it.

## `data/replication_n5.csv`

Contextual n=5 replication across both platforms (24 cells).

| Column | Description |
|---|---|
| `platform` | `android` or `web` |
| `app` | ankidroid, newpipe, wikipedia / ghost, opencart, taiga |
| `scenario` | `S1` locator fault, `S2` assertion fault |
| `backbone` | `qwen` (Qwen2.5-Coder-7B) or `llama` (Llama 3.1-8B) |
| `n` | Runs in the cell (always 5) |
| `successes` | Runs ending in a repaired, passing test |
| `mttr_mean_s`, `mttr_std_s` | Mean and SD over **successful runs only**; empty when there were none |
| `count_source` | Where `successes` was read from. `batch summary` for 22 cells. For two cells the batch aborted before writing its JSON summary, so the value is `run log (summary not written)`; their logs still record all five runs, none passing, so the 0/5 is observed rather than imputed. |

Totals: android 42/60, web 12/60.

## `data/holdouts.csv`

Two holdout studies built so that live grounding should have an advantage.

| Column | Description |
|---|---|
| `holdout` | `ambiguous_locator` or `dynapp` (pre-registered, runtime-only locators) |
| `arm` | `full_lara` (full pipeline) or the patch-only synthesizer |
| `scenario` | SA1/SA2 or SD1/SD2 |
| `n`, `successes` | Runs and repairs |
| `mttr_mean_s`, `mttr_sd_s` | Over successful runs only. **Sample** standard deviation (`n-1`) in both arms. The batch summaries in `run_summaries/` are not consistent on this — they carry a population SD for the patch-only arm and a sample SD for the full arm — so these columns are recomputed from `mttr_per_run_s` rather than copied. |
| `mttr_median_s` | Median over successful runs. Reported because the mean is a poor summary for these small, right-skewed samples; on SD2 the full-pipeline median is 97.7 s against a mean of 109.4 s. |
| `mttr_per_run_s` | The individual successful-run timings, space separated, so any other summary can be recomputed. |

Pooled: patch-only 20/20 against the full pipeline 15/20.

## `data/healenium.csv`

Production locator healing (Healenium 4.0.0) on the six web cells at n=3.

| Column | Description |
|---|---|
| `app`, `scenario`, `run` | Cell and run index |
| `broken_locator`, `correct_locator` | The seeded fault. In the three S2 cells the two are **identical**: an assertion-value fault leaves the locator untouched, so a locator healer has nothing to substitute. |
| `success` | Whether the locator was healed |
| `mttr_s` | Healing time; sub-second because it substitutes a locator in memory and never runs a repair loop |
| `healed_to` | The element healing resolved to, when it resolved to one. Empty in the four `not_healed` cells; `LOGIN` on Taiga S2, where the element was found and the test still failed on the text. On the one healed cell, Ghost S1, all three runs resolved to an element labelled `Forgot?` rather than the primary sign-in button the scenario targets — the arm's success criterion is only `is_displayed()` on whatever the healed selector returns, so the 3/3 does not establish that the intended control was recovered. |
| `error` | Failure mode: `not_healed` (no candidate similar enough to the broken selector) or `text_mismatch` (element found, assertion value still wrong). Empty on the healed cell. |

Total 3/18, all three on the same cell (Ghost S1).

## `figures/fig3_gvpv_paired.csv`

Every on/off cell in the three paired sub-studies (20 rows = 10 pairs).

| Column | Description |
|---|---|
| `substudy` | `paired_n5`, `extended_n10`, `wiki_rerun_n10` |
| `app`, `scenario`, `backbone` | Cell identity |
| `arm` | `on` or `off` |
| `n`, `successes` | Runs and repairs in that arm |
| `in_paired_contrast` | `yes` for the seven log-verified pairs plotted in Figure 3 |
| `exclusion_reason` | Why a pair was excluded; empty when included |

Three pairs are excluded because the off-arm toggle silently failed, leaving
the gate live in both arms so the pair measures nothing. One of those three is
additionally excluded because its seeded fault was absent from the on arm.
Filtering on `in_paired_contrast = yes` reproduces 42/60 against 38/60.

## `data/run_summaries/*.json`

The unaggregated per-run summaries the CSVs are built from, kept so that any
derivation above can be checked. File names carry a `_YYYYMMDD_HHMMSS` run
stamp. Common fields: `app`, `scenario`, `model_key`, `gvpv_on`, `elapsed_s`,
`log`, and either a `runs` array of `{run, success, mttr_s}` or an `sr`
string of the form `"4/5"`.

## `logs/*.log`

Raw stdout for the 180 gate-live runs (32 files). These are the input the
per-patch scorer reads to produce `data/perpatch_summary.json`. Naming:

```
exp1_<app>_<scenario>_<backbone>_<stamp>.log            Android replication
exp_gvpv_paired_<app>_<scenario>_<backbone>_gvpv_<arm>_<stamp>.log
exp_gvpv_ext_<app>_<scenario>_<backbone>_gvpv_<arm>_<stamp>.log
exp_wiki_gvpv_fixed_<scenario>_gvpv_<arm>_<stamp>.log
```

Grammar the scorer keys on: `Tool : apply_patch` opens a decision;
`[GVPV-FAIL] Check<N>:` or `[OK] Patch applied` is the verdict; the following
`run_pytest` `[PASSED]`/`[FAILED]` is the executable oracle. Logs truncate
tool arguments and long observations, which is the source of the
reconstruction caveat above.

### Agent names: logs against article

The logs use the agents' implementation names; the article uses their study
names. They are the same two agents.

| In the logs | In the article | Role |
|---|---|---|
| `[OpenClaw]` | LARA-D | Detector. Runs pytest, collects the live UI hierarchy, and emits the `SymptomReport`. Step cap 4. |
| `[RepairAgent]` | LARA-R | Repairer. Plans and applies the patch, and is the agent whose `apply_patch` call the gate adjudicates. Step cap 7. |
| `[Orchestrator]` | — | Drives the two-cycle episode and restores the original file when both cycles fail. |
| `[Bus]` | A2A message bus | Carries `goal`, `result`, `artifact`, and `shutdown` messages between the agents. |

`OpenClaw` is the local name of the detector implemented for this study. It is
**unrelated to any similarly named third-party project** — nothing outside this
study's own code is imported or depended on. The standalone proof-of-concept
agents under `poc/` use different step caps and were **not** used for any
reported run.

### Two things to expect when reading a log

**Paths are anonymised.** The author's local working directory has been
replaced throughout by the literal placeholder `<WORKSPACE>`, so a path reads
`<WORKSPACE>\app\wikipedia\test_experiment.py`. This is the only edit made to
the logs: no observation, verdict, timing, or ordering was altered. Re-running
the scorer over these files reproduces `data/perpatch_summary.json` key for
key, including all 41 `fa_events`.

**Progress messages are in Korean.** The orchestrator emitted its own status
lines in Korean; they carry no measurement and the scorer ignores them. The
recurring ones:

| Log line | Meaning |
|---|---|
| `[OpenClaw] ReAct 루프 시작` | detector agent's ReAct loop starts |
| `[RepairAgent] ReAct 루프 시작` | repair agent's ReAct loop starts |
| `[OpenClaw] 완료 (N steps)` | detector finished in N steps |
| `[Orchestrator] OpenClaw 결과:` | orchestrator reports the detector's result |
| `[OpenClaw] 메시지 버스 수신 대기...` | agent waiting on the message bus |
| `[Orchestrator] 2사이클 소진 → 원본 복구` | both repair cycles exhausted; original file restored |
| `[Fix] SymptomReport.failed_assertions 폴백 복원` | assertion list recovered from the pytest observation after the collector omitted it |
| `[Fix] SymptomReport.assertions actual 유추` | the `actual` value was inferred rather than collected |
| `shutdown → 종료` | agent terminating |

Korean also appears inside the seeded test files' docstrings, which the logs
echo when the agent reads a file — for example `Bug Type : 온보딩 화면
headline 텍스트 어서션 오류` ("onboarding screen headline text assertion
fault"). These are comments in the fixture, not measurements.

The last two `[Fix]` lines are worth noting: they mark places where the
pipeline repaired a defective `SymptomReport` before the gate saw it.
