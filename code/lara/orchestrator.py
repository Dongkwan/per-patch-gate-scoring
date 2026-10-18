from __future__ import annotations

import json
import re
import shutil
import time

from lara.react import AgentResult, ReactAgent
from lara.report import FailedAssertion, SymptomReport

REPORT_PLACEHOLDER_PREFIXES = ("(element not found", "(unknown", "(no such element")
UI_COLLECTOR_TOOLS = ("collect_ui_hierarchy", "collect_dom")
GENERIC_ID_TOKENS = {"button", "text", "view", "layout", "container", "item"}


def detect_goal(test_file: str, target_url: str) -> str:
    return (
        f"You are a QA agent. Investigate the test suite '{test_file}' "
        f"against the live application at '{target_url}'. "
        f"Use your available tools to determine whether any tests are failing and why. "
        f"When done, call finish with either 'ALL_TESTS_PASSED' or a SymptomReport JSON "
        f"with keys: test_file, app_package, ui_facts, failed_assertions, raw_error_output."
    )


def repair_goal(symptom: SymptomReport, final_answer: str, test_file: str) -> str:
    symptom_json = json.dumps({
        "test_file": symptom.test_file,
        "app_package": symptom.target_url,
        "ui_facts": symptom.dom_facts,
        "failed_assertions": [
            {
                "test_name":  fa.test_name,
                "type":       fa.assertion_type,
                "expected":   fa.expected_value,
                "actual":     fa.actual_value,
            }
            for fa in symptom.failed_assertions
        ],
        "raw_error_output": symptom.raw_error_output[:1500],
    }, ensure_ascii=False, indent=2)
    return (
        f"You are a repair agent. The tests in '{test_file}' are failing. "
        f"Here is the diagnostic report (A2A artifact #{symptom.report_id}).\n"
        f"USE the corrected SymptomReport JSON below as your source of truth "
        f"(assertions.actual has already been resolved via UI hierarchy heuristic where possible):\n"
        f"=== CORRECTED SymptomReport JSON ===\n{symptom_json}\n"
        f"=== END SymptomReport ===\n\n"
        f"For reference, the OpenClaw agent original final_answer was:\n"
        f"{final_answer[:1200]}\n\n"
        f"Use your tools to analyze the failures, fix the test file, and verify the fix passes. "
        f"When done, call finish with a result summary."
    )


def is_passing(answer: str) -> bool:
    a = answer.upper()
    if "ALL_TESTS_PASSED" in a:
        return True
    if "PASSED" in a and "FAILED" not in a:
        return True
    return "ALL TESTS PASS" in a.lower()


def _assertion_from(a: dict) -> FailedAssertion:
    return FailedAssertion(
        test_name=a.get("test_name", ""),
        assertion_type=a.get("type", a.get("assertion_type", "")),
        expected_value=a.get("expected", a.get("expected_value", "")),
        actual_value=a.get("actual", a.get("actual_value", "")),
    )


def guess_correct_value_from_ui(expected: str, ui_facts: dict) -> str:
    if not expected or not isinstance(ui_facts, dict):
        return ""
    buttons = ui_facts.get("buttons") or []
    if not buttons:
        return ""
    tail = expected.rsplit("/", 1)[-1] if "/" in expected else expected
    hints = [w for w in re.split(r"[_\-\.\s:]+", tail) if len(w) >= 3]
    if not hints:
        return ""

    scored_hints = [h for h in hints if h.lower() not in GENERIC_ID_TOKENS] or hints

    best_score = 0
    best_candidate = ""
    for btn in buttons:
        rid = (btn.get("full_id") or btn.get("resource_id") or "").lower()
        text_val = (btn.get("text") or "")
        haystack = f"{rid} {text_val.lower()}"
        score = sum(1 for h in scored_hints if h.lower() in haystack)
        if score > best_score:
            best_score = score
            best_candidate = btn.get("full_id") or btn.get("resource_id") or text_val
    return best_candidate if best_score >= 1 else ""


def parse_symptom_report(
    answer: str, test_file: str, target_url: str,
    step_details: list | None = None,
) -> SymptomReport:
    report = SymptomReport(
        test_file=test_file,
        target_url=target_url,
        raw_error_output=answer[:2000],
    )
    json_m = re.search(r'\{[\s\S]*\}', answer)
    if json_m:
        try:
            data = json.loads(json_m.group())
            report.dom_facts = data.get("ui_facts", data.get("dom_facts", {}))
            for a in data.get("failed_assertions", []):
                report.failed_assertions.append(_assertion_from(a))
        except Exception:
            pass

    if not report.failed_assertions and step_details:
        for step in reversed(step_details):
            if step.get("tool") != "run_pytest":
                continue
            obs = step.get("observation", "")
            m = re.search(
                r"=== FAILURES \(JSON\) ===\s*(\{[\s\S]*?\})\s*=== RAW OUTPUT ===",
                obs,
            )
            if not m:
                continue
            try:
                parsed = json.loads(m.group(1))
            except Exception:
                break
            for a in parsed.get("assertions", []):
                report.failed_assertions.append(_assertion_from(a))
            break

    ui_facts: dict = report.dom_facts or {}
    if (not ui_facts or not ui_facts.get("buttons")) and step_details:
        for step in reversed(step_details):
            if step.get("tool") not in UI_COLLECTOR_TOOLS:
                continue
            try:
                candidate = json.loads(step.get("observation", "") or "{}")
            except Exception:
                candidate = {}
            if candidate.get("buttons"):
                ui_facts = candidate
                break
    for fa in report.failed_assertions:
        actual = (fa.actual_value or "").strip()
        if not any(actual.startswith(p) for p in REPORT_PLACEHOLDER_PREFIXES):
            continue
        guess = guess_correct_value_from_ui(fa.expected_value, ui_facts)
        if guess:
            fa.actual_value = guess

    return report


def step_details(result: AgentResult) -> list[dict]:
    return [{"tool": s.tool_name, "observation": s.observation} for s in result.steps]


async def run_repair_loop(
    detector: ReactAgent,
    repairer: ReactAgent,
    test_file: str,
    target_url: str,
    max_cycles: int = 3,
) -> dict:
    pipeline_start = time.time()
    backup_file = test_file + ".bak"
    shutil.copy(test_file, backup_file)

    summary = {
        "success": False,
        "cycles_used": 0,
        "mttr_seconds": 0.0,
        "total_steps": 0,
    }

    for cycle in range(1, max_cycles + 1):
        detected = await detector.run(detect_goal(test_file, target_url))
        final_answer = detected.final_answer
        summary["total_steps"] += len(detected.steps)

        if is_passing(final_answer):
            summary["success"] = True
            summary["cycles_used"] = cycle - 1
            summary["mttr_seconds"] = round(time.time() - pipeline_start, 2)
            break

        symptom = parse_symptom_report(
            final_answer, test_file, target_url,
            step_details=step_details(detected),
        )
        repaired = await repairer.run(repair_goal(symptom, final_answer, test_file))
        summary["total_steps"] += len(repaired.steps)
    else:
        shutil.copy(backup_file, test_file)

    return summary
