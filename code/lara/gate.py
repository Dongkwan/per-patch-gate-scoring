from __future__ import annotations

import ast
import re

GVPV_PLACEHOLDERS = {"(unknown)", "unknown", "(element not found)", ""}


def parse(src: str) -> ast.Module | None:
    try:
        return ast.parse(src)
    except SyntaxError:
        return None


def count_asserts(tree: ast.AST) -> int:
    return sum(1 for n in ast.walk(tree) if isinstance(n, ast.Assert))


def code_only(src: str, tree: ast.AST) -> str:
    docstring_ranges = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                docstring_ranges.append((body[0].lineno, body[0].end_lineno))
    lines = src.splitlines(keepends=True)
    kept = []
    for i, line in enumerate(lines, start=1):
        in_doc = any(a <= i <= b for a, b in docstring_ranges)  # type: ignore[operator]
        if in_doc:
            continue
        code_part = re.sub(r"#[^\n]*$", "", line)
        kept.append(code_part)
    return "".join(kept)


def validate_patch(patched: str, original: str, broken_value: str, correct_value: str) -> str | None:
    patched_tree = parse(patched)
    if patched_tree is None:
        return "[GVPV-FAIL] SyntaxError: patched file is not valid Python"

    patched_code_only = code_only(patched, patched_tree)
    if broken_value and broken_value in patched_code_only:
        return f"[GVPV-FAIL] Check1: broken value '{broken_value}' still present in patched file"

    if correct_value and correct_value not in GVPV_PLACEHOLDERS and correct_value not in patched_code_only:
        return f"[GVPV-FAIL] Check2: correct value '{correct_value}' not found in patched file"

    orig_tree = parse(original)
    orig_n = count_asserts(orig_tree) if orig_tree is not None else -1
    patched_n = count_asserts(patched_tree)
    if orig_n >= 0 and patched_n < orig_n:
        return (
            f"[GVPV-FAIL] Check3: assert count decreased "
            f"{orig_n} → {patched_n} (assertion deleted)"
        )
    return None
