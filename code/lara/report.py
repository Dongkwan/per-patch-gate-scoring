from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class FailedAssertion:
    test_name: str
    assertion_type: str
    expected_value: str
    actual_value: str


@dataclass
class SymptomReport:
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    target_url: str = ""
    test_file: str = ""
    raw_error_output: str = ""
    dom_facts: dict = field(default_factory=dict)
    failed_assertions: list[FailedAssertion] = field(default_factory=list)
