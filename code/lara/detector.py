from __future__ import annotations

import json
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET

from lara.react import ReactAgent, Tool

ANDROID_SDK = os.environ.get("ANDROID_HOME", "")
ADB = os.environ.get("ADB", "adb")
ADB_ENV = {
    **os.environ,
    "ANDROID_HOME": ANDROID_SDK,
    "ANDROID_SDK_ROOT": ANDROID_SDK,
}
PYTEST_TIMEOUT_S = 90
DETECTOR_MAX_STEPS = 4

ELEMENT_NOT_FOUND_SENTINEL = "(element not found — wrong resource-id or selector)"

DETECTOR_ROLE = (
    "You are an Android QA agent. Follow this EXACT 3-step workflow:\n"
    "  Step 1: run_pytest(test_file_path) — run Appium test, get structured failures\n"
    "  Step 2: collect_ui_hierarchy(app_package) — relaunch app, collect live Android UI\n"
    "  Step 3: finish(SymptomReport_JSON) — submit the report\n\n"
    "For the finish call, build SymptomReport JSON with these keys:\n"
    "  test_file         : the test file path (string)\n"
    "  app_package       : com.ichi2.anki (string)\n"
    "  ui_facts          : COPY entire JSON object from collect_ui_hierarchy result\n"
    "  failed_assertions : COPY the 'assertions' array from run_pytest FAILURES section\n"
    "  raw_error_output  : COPY the RAW OUTPUT section from run_pytest result\n\n"
    "IMPORTANT: If run_pytest returns [PASSED], call finish('ALL_TESTS_PASSED') immediately.\n"
    "Do NOT try to fix tests — only observe and report."
)


def parse_pytest_failures(output: str) -> dict:
    test_names = re.findall(r"FAILED\s.*?::(\w+)", output)
    assertions = []

    text_pattern = re.compile(r"assert '(.+?)' == '(.+?)'", re.DOTALL)
    handled = set()
    for i, m in enumerate(text_pattern.finditer(output)):
        name = test_names[i] if i < len(test_names) else f"test_{i}"
        assertions.append({
            "test_name": name,
            "type":      "text_mismatch",
            "expected":  m.group(2).strip(),
            "actual":    m.group(1).strip(),
        })
        handled.add(name)

    if re.search(r"NoSuchElementException|NoSuchElement", output):
        selector_m = re.search(
            r'find_element\([^,]+,\s*["\']([^"\']+)["\']', output,
        )
        wrong_selector = selector_m.group(1) if selector_m else "(unknown)"
        for name in test_names:
            if name not in handled:
                assertions.append({
                    "test_name": name,
                    "type":      "element_not_found",
                    "expected":  wrong_selector,
                    "actual":    ELEMENT_NOT_FOUND_SENTINEL,
                })

    return {"failed_tests": test_names, "assertions": assertions}


def make_run_pytest_tool(python_exe: str, conftest_dir: str) -> Tool:
    def handler(test_file: str) -> str:
        test_file = test_file.strip().strip("\"'").splitlines()[0].strip()
        result = subprocess.run(
            [python_exe, "-m", "pytest", test_file,
             "-v", "--tb=long", "--no-header",
             f"--rootdir={conftest_dir}"],
            capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace",
            env=ADB_ENV, timeout=PYTEST_TIMEOUT_S,
        )
        output = (result.stdout or "") + (result.stderr or "")
        status = "PASSED" if result.returncode == 0 else "FAILED"

        if result.returncode != 0:
            parsed = parse_pytest_failures(output)
            failures_json = json.dumps(parsed, ensure_ascii=False, indent=2)
            return (
                f"[{status}]\n"
                f"=== FAILURES (JSON) ===\n{failures_json}\n"
                f"=== RAW OUTPUT ===\n{output[:2000]}"
            )
        return f"[{status}]\n{output[:2000]}"

    return Tool(
        name="run_pytest",
        description=(
            "Run Appium pytest on a test file. "
            "Returns [PASSED] or [FAILED] with structured FAILURES (JSON) and RAW OUTPUT. "
            "ARGS: path to the test file."
        ),
        handler=handler,
    )


def summarize_hierarchy(app_identifier: str, raw: bytes) -> str:
    xml_end = raw.rfind(b"</hierarchy>")
    if xml_end == -1:
        return json.dumps({"error": "uiautomator dump failed"})
    xml_bytes = raw[: xml_end + 12]

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        return json.dumps({"error": f"XML parse error: {e}"})

    buttons, text_views, edit_texts = [], [], []
    for n in root.findall(".//*"):
        rid       = n.get("resource-id", "")
        text      = n.get("text", "")
        desc      = n.get("content-desc", "")
        cls       = n.get("class", "")
        clickable = n.get("clickable", "false") == "true"
        short_id  = rid.split("/")[-1] if "/" in rid else rid

        if "Button" in cls or clickable:
            buttons.append({
                "resource_id":  short_id,
                "full_id":      rid,
                "text":         text,
                "content_desc": desc,
                "clickable":    clickable,
            })
        elif "TextView" in cls and text:
            text_views.append({"resource_id": short_id, "text": text})
        elif "EditText" in cls:
            edit_texts.append({"resource_id": short_id, "text": text, "content_desc": desc})

    return json.dumps({
        "app":        app_identifier,
        "buttons":    buttons,
        "text_views": text_views,
        "edit_texts": edit_texts,
    }, ensure_ascii=False, indent=2)


def make_collect_ui_tool() -> Tool:
    def handler(app_identifier: str) -> str:
        app_identifier = app_identifier.strip().strip("\"'").splitlines()[0].strip()
        subprocess.run(
            [ADB, "shell", "pm", "clear", app_identifier],
            capture_output=True, timeout=10, env=ADB_ENV, check=False,
        )
        time.sleep(1)
        subprocess.run(
            [ADB, "shell", "monkey", "-p", app_identifier,
             "-c", "android.intent.category.LAUNCHER", "1"],
            capture_output=True, timeout=10, env=ADB_ENV, check=False,
        )
        time.sleep(4)
        raw = subprocess.run(
            [ADB, "exec-out", "uiautomator", "dump", "/dev/tty"],
            capture_output=True, timeout=20, env=ADB_ENV, check=False,
        ).stdout
        return summarize_hierarchy(app_identifier, raw)

    return Tool(
        name="collect_ui_hierarchy",
        description=(
            "Relaunch the Android app then use adb uiautomator dump to collect live UI hierarchy. "
            "Returns JSON with buttons (resource_id, full_id, text, content_desc), text_views, edit_texts. "
            "ARGS: Android app package name (e.g. com.ichi2.anki)."
        ),
        handler=handler,
    )


def create_detector_agent(
    python_exe: str,
    conftest_dir: str,
    llm_base_url: str,
    llm_model: str,
) -> ReactAgent:
    tools = [
        make_run_pytest_tool(python_exe, conftest_dir),
        make_collect_ui_tool(),
        Tool(
            name="finish",
            description=(
                "Submit the SymptomReport JSON. "
                "ARGS: JSON with keys: test_file, app_package, ui_facts, "
                "failed_assertions, raw_error_output. "
                "If all tests PASSED, ARGS: 'ALL_TESTS_PASSED'."
            ),
            handler=None,
        ),
    ]
    return ReactAgent(
        name="OpenClaw",
        role=DETECTOR_ROLE,
        tools=tools,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        max_steps=DETECTOR_MAX_STEPS,
    )
