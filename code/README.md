# GVPV gate and Lara repair loop: code excerpt

Core code of the pipeline evaluated in the article (AnkiDroid version), provided for reading; it is not runnable as-is. Runners, test scenarios, and analysis scripts are available from the author on request.

- `lara/gate.py`: GVPV Checks 0–3 (Algorithm 1)
- `lara/repair_agent.py`: repair agent; `apply_patch` writes the patch, then calls the gate
- `lara/detector.py`: detector agent; pytest failure parsing and the ADB UI collector
- `lara/orchestrator.py`, `lara/report.py`: detect–repair cycle and the SymptomReport
- `lara/react.py`: ReAct loop shared by both agents

Defects reported in Section 3.2 of the article:
- (a) The gate checks the agent's request values (`repair_agent.py:214`), not the SymptomReport.
- (b) `analyze_report` accepts any string; the agent sometimes passed its own ARGS hint (`repair_agent.py:96`).
- (c) `GVPV_PLACEHOLDERS` (`gate.py:6`) omits the collector sentinel (`detector.py:22`).
- (d) The patch is written before the gate (`repair_agent.py:209`) and restored only when cycles run out (`orchestrator.py:201`).
