from __future__ import annotations

import json
import os
import re
import subprocess

from openai import AsyncOpenAI

from lara.detector import ELEMENT_NOT_FOUND_SENTINEL
from lara.gate import validate_patch
from lara.react import LLM_API_KEY, ReactAgent, Tool

ANDROID_SDK = os.environ.get("ANDROID_HOME", "")
PYTEST_TIMEOUT_S = 90
ANALYZE_MAX_TOKENS = 512
REPAIR_MAX_STEPS = 7
GVPV_DISABLED_ENV = "LARA_GVPV_DISABLED"

DIRECTIVE_PLACEHOLDERS = {"(unknown)", "unknown", "(element not found)", ELEMENT_NOT_FOUND_SENTINEL, ""}
NESTED_CLI_ENV_VARS = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_EXECPATH", "CLAUDE_CODE_SESSION_ID")

REPAIR_ROLE = (
    "You are an Android test repair agent. "
    "You receive a SymptomReport describing Appium test failures against an Android app. "
    "Analyze the report, read the test file, apply a patch to fix all failures, "
    "and verify the fix by running the tests. "
    "Use analyze_report first to understand what resource-ids or text values need correction."
)


def make_analyze_tool(llm_base_url: str, llm_model: str) -> Tool:
    async def handler(report_input: str) -> str:
        test_code = "(could not read test file)"
        try:
            report = json.loads(report_input.strip())
            ui_text    = json.dumps(report.get("ui_facts", report.get("dom_facts", {})), indent=2)
            errors     = report.get("raw_error_output", report_input)[:1500]
            assertions = report.get("failed_assertions", [])
            test_file_path = report.get("test_file", "")
            if test_file_path:
                try:
                    with open(test_file_path, "r", encoding="utf-8") as f:
                        test_code = f.read()
                except Exception:
                    pass
            assertion_text = "\n".join(
                (
                    f"  Test: {a.get('test_name','')}\n"
                    f"    Type: {a.get('type','')}\n"
                    f"    What the test code uses/asserts (THE WRONG VALUE): '{a.get('expected','')}'\n"
                    f"    What the UI shows at runtime (THE CORRECT VALUE): '{a.get('actual','')}'"
                )
                for a in assertions
            ) or "  (see raw_error_output)"
        except Exception:
            ui_text        = "(JSON parsing failed — using raw input)"
            errors         = report_input[:1500]
            assertion_text = "(see raw errors)"

        prompt = (
            "You are a QA analysis sub-agent for Android app testing.\n"
            "CRITICAL RULES:\n"
            "- Use ONLY the test function names listed in 'Failing assertions'. Do NOT invent names.\n"
            "- 'What the test code uses/asserts' = THE WRONG VALUE currently in the test.\n"
            "- 'What the UI shows at runtime' = THE CORRECT VALUE from the live app.\n"
            "- The fix is: replace the WRONG value with the CORRECT value from the UI.\n\n"
            f"Actual test file content:\n{test_code[:1200]}\n\n"
            f"Android UI hierarchy (ground truth from adb dump):\n{ui_text}\n\n"
            f"Failing assertions:\n{assertion_text}\n\n"
            f"Raw error excerpt:\n{errors}\n\n"
            "For EACH failing assertion, output:\n"
            "1. Exact test function name (copy from assertions above)\n"
            "2. Wrong value in the test (copy from 'What the test code uses/asserts')\n"
            "3. Correct value to use (from UI hierarchy or runtime value)\n\n"
            "Output only the numbered correction list. Be precise and use only the given information.\n"
            "After the list, on two separate lines write exactly:\n"
            "BROKEN_VALUE: <exact wrong string currently in the test>\n"
            "CORRECT_VALUE: <exact correct string from the UI hierarchy>"
        )

        client = AsyncOpenAI(base_url=llm_base_url, api_key=LLM_API_KEY)
        response = await client.chat.completions.create(
            model=llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=ANALYZE_MAX_TOKENS,
        )
        return response.choices[0].message.content or "(no response from Qwen)"

    return Tool(
        name="analyze_report",
        description=(
            "Use Qwen sub-agent to analyze an Android SymptomReport "
            "and produce a numbered repair plan for Appium test corrections. "
            "ARGS: SymptomReport JSON string."
        ),
        handler=handler,
    )


def make_read_file_tool() -> Tool:
    def handler(path: str) -> str:
        path = path.strip().splitlines()[0].strip().strip("\"'")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"[Error] {e}"

    return Tool(
        name="read_file",
        description="Read a file and return its content. ARGS: file path.",
        handler=handler,
    )


def parse_patch_args(args_str: str) -> dict:
    data: dict = {}
    start = args_str.find("{")
    end   = args_str.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(args_str[start:end + 1])
        except Exception:
            pass
    if not data:
        for key in ("test_file", "repair_plan", "report_summary"):
            m = re.search(rf"{key}=(.+?)(?=,\s*\w+=|\Z)", args_str, re.DOTALL)
            if m:
                data[key] = m.group(1).strip()
    return data


def build_patch_prompt(data: dict, repair_plan: str, report_summary: str, current_code: str) -> str:
    bv = (data.get("broken_value") or "").strip().strip("\"'`")
    cv = (data.get("correct_value") or "").strip().strip("\"'`")
    if bv and cv and cv not in DIRECTIVE_PLACEHOLDERS and bv != cv:
        directive = (
            f"REPLACE the literal string {bv!r} with the literal string {cv!r} "
            f"everywhere it appears in the test code. "
            f"Do not change anything else — comments, docstrings, imports, "
            f"other identifiers, whitespace, and line endings must be preserved.\n"
        )
    else:
        directive = (
            "Apply the repair plan to the test code. Modify only what the plan explicitly "
            "identifies; do not rewrite unrelated code, docstrings, or imports.\n"
        )
    return (
        f"{directive}\n"
        "Output ONLY the complete corrected Python file "
        "(no markdown fences, no explanations, no summary of changes).\n\n"
        f"=== REPAIR PLAN ===\n{repair_plan}\n\n"
        f"=== CONTEXT ===\n{report_summary[:500]}\n\n"
        f"=== CURRENT FILE ===\n{current_code}"
    )


def extract_code(raw: str) -> str:
    patched = raw
    for marker in ["```python", "```"]:
        if marker in raw:
            start = raw.find(marker) + len(marker)
            end   = raw.find("```", start)
            if end > start:
                patched = raw[start:end].strip()
                break
    return patched


def make_apply_patch_tool() -> Tool:
    def handler(args_str: str) -> str:
        data = parse_patch_args(args_str)
        test_file      = data.get("test_file", "").strip().strip("\"'")
        repair_plan    = data.get("repair_plan", "")
        report_summary = data.get("report_summary", "")

        if not test_file or not repair_plan:
            return (
                "[Error] ARGS must include test_file and repair_plan. "
                'Example: {"test_file": "app/wikipedia/scenarios/s2_wrong_text.py", '
                '"repair_plan": "1. ...", "report_summary": "..."}'
            )

        try:
            with open(test_file, "r", encoding="utf-8") as f:
                current_code = f.read()
        except Exception as e:
            return f"[Error reading {test_file}] {e}"

        prompt = build_patch_prompt(data, repair_plan, report_summary, current_code)
        env = {k: v for k, v in os.environ.items() if k.upper() not in NESTED_CLI_ENV_VARS}
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace", env=env,
        )

        raw = (result.stdout or "").strip()
        if not raw:
            return "[Error] Claude CLI returned no output"

        patched = extract_code(raw)
        if not patched:
            return "[Error] Could not extract code from Claude response"

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(patched)

        if os.environ.get(GVPV_DISABLED_ENV) == "1":
            return f"[OK] Patch applied to {test_file} (GVPV disabled)"

        broken_value  = data.get("broken_value", "").strip()
        correct_value = data.get("correct_value", "").strip()
        failure = validate_patch(patched, current_code, broken_value, correct_value)
        if failure is not None:
            return failure
        return f"[OK] Patch applied to {test_file} ({len(patched)} chars written)"

    return Tool(
        name="apply_patch",
        description=(
            "Use Claude Code CLI to generate and apply a patch to an Appium test file, then validate via GVPV. "
            "ARGS: JSON with keys: test_file (path), repair_plan (string), report_summary (string), "
            "broken_value (optional: exact wrong string in test), "
            "correct_value (optional: exact correct replacement string). "
            'Example: {"test_file": "app/ankidroid/scenarios/s1_wrong_resource_id.py", '
            '"repair_plan": "1. ...", "broken_value": "start_button", "correct_value": "get_started"}'
        ),
        handler=handler,
    )


def make_run_pytest_tool(python_exe: str, conftest_dir: str) -> Tool:
    def handler(test_file: str) -> str:
        test_file = test_file.strip().strip("\"'")
        result = subprocess.run(
            [python_exe, "-m", "pytest", test_file,
             "-v", "--tb=short", "--no-header",
             f"--rootdir={conftest_dir}"],
            capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace",
            env={
                **os.environ,
                "ANDROID_HOME":     ANDROID_SDK,
                "ANDROID_SDK_ROOT": ANDROID_SDK,
            },
            timeout=PYTEST_TIMEOUT_S,
        )
        output = (result.stdout or "") + (result.stderr or "")
        status = "PASSED" if result.returncode == 0 else "FAILED"
        return f"[{status}]\n{output[:2000]}"

    return Tool(
        name="run_pytest",
        description="Run Appium pytest to verify the patch. ARGS: path to test file.",
        handler=handler,
    )


def create_repair_agent(
    python_exe: str,
    conftest_dir: str,
    llm_base_url: str,
    llm_model: str,
) -> ReactAgent:
    tools = [
        make_analyze_tool(llm_base_url, llm_model),
        make_read_file_tool(),
        make_apply_patch_tool(),
        make_run_pytest_tool(python_exe, conftest_dir),
        Tool(
            name="finish",
            description="Signal repair complete. ARGS: result summary (success or failure reason).",
            handler=None,
        ),
    ]
    return ReactAgent(
        name="RepairAgent",
        role=REPAIR_ROLE,
        tools=tools,
        llm_base_url=llm_base_url,
        llm_model=llm_model,
        max_steps=REPAIR_MAX_STEPS,
    )
