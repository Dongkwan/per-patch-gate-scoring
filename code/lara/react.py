from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

LLM_API_KEY = "lm-studio"
TEMPERATURE = 0.0
MAX_TOKENS = 1024


@dataclass
class Tool:
    name: str
    description: str
    handler: Callable[[str], Any] | None


@dataclass
class AgentStep:
    step_num: int
    thought: str
    tool_name: str
    tool_input: str
    observation: str


@dataclass
class AgentResult:
    agent_name: str
    goal: str
    final_answer: str
    steps: list[AgentStep]
    success: bool
    error: str = ""


def parse_tool_call(text: str, available_tools: list[str]) -> tuple[str, str, str]:
    thought = ""
    tool_name = ""
    args = ""

    thought_m = re.search(
        r"Thought:\s*(.+?)(?=TOOL_CALL:|Action:|$)", text, re.DOTALL | re.IGNORECASE
    )
    if thought_m:
        thought = thought_m.group(1).strip()

    tc_m = re.search(r"TOOL_CALL:\s*(\w+)", text, re.IGNORECASE)
    args_m = re.search(r"ARGS:\s*(.+?)(?=\n\s*\n|\nTOOL_CALL:|\Z)", text, re.DOTALL | re.IGNORECASE)
    if tc_m:
        tool_name = tc_m.group(1).strip()
        args = args_m.group(1).strip() if args_m else ""
        return thought, tool_name, args

    act_m = re.search(r"Action:\s*(\w+)", text, re.IGNORECASE)
    inp_m = re.search(r"Action Input:\s*(.+?)(?=\nObservation:|\Z)", text, re.DOTALL | re.IGNORECASE)
    if act_m:
        tool_name = act_m.group(1).strip()
        args = inp_m.group(1).strip() if inp_m else ""
        return thought, tool_name, args

    for name in available_tools:
        if name.lower() in text.lower():
            tool_name = name
            args = text.strip()
            return thought, tool_name, args

    return thought or text.strip(), "finish", text.strip()


def build_system_prompt(name: str, role: str, tools: list[Tool]) -> str:
    tool_list = "\n".join(f"  - {t.name}: {t.description}" for t in tools)
    return (
        f"You are {name}. {role}\n\n"
        f"Available tools:\n{tool_list}\n\n"
        "IMPORTANT: Respond in EXACTLY this format every turn:\n\n"
        "Thought: <your step-by-step reasoning>\n"
        "TOOL_CALL: <tool_name>\n"
        "ARGS: <input for the tool>\n\n"
        "When goal is fully achieved:\n"
        "Thought: <final reasoning>\n"
        "TOOL_CALL: finish\n"
        "ARGS: <your final answer or result JSON>\n\n"
        "Rules:\n"
        "- Always include Thought, TOOL_CALL, and ARGS on separate lines\n"
        "- Use only the tool names listed above\n"
        "- Call finish only when the goal is fully complete"
    )


class ReactAgent:
    def __init__(
        self,
        name: str,
        role: str,
        tools: list[Tool],
        llm_base_url: str,
        llm_model: str,
        max_steps: int = 8,
    ) -> None:
        self.name = name
        self.tools = {t.name: t for t in tools}
        self.llm_base_url = llm_base_url
        self.llm_model = llm_model
        self.max_steps = max_steps
        self.system_prompt = build_system_prompt(name, role, tools)

    async def run(self, goal: str) -> AgentResult:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Goal: {goal}"},
        ]
        steps: list[AgentStep] = []
        tool_names = list(self.tools.keys())

        for step_num in range(1, self.max_steps + 1):
            try:
                llm_output = await self._call_llm(messages)
            except Exception as e:
                return AgentResult(
                    agent_name=self.name, goal=goal,
                    final_answer="", steps=steps,
                    success=False, error=f"LLM 호출 실패: {e}",
                )

            thought, tool_name, args = parse_tool_call(llm_output, tool_names)

            if tool_name.lower() == "finish":
                return AgentResult(
                    agent_name=self.name, goal=goal,
                    final_answer=args or thought,
                    steps=steps, success=True,
                )

            tool = self.tools.get(tool_name)
            if tool is None:
                observation = (
                    f"[Error] 알 수 없는 도구: '{tool_name}'. "
                    f"사용 가능한 도구: {tool_names}"
                )
            else:
                try:
                    if asyncio.iscoroutinefunction(tool.handler):
                        observation = await tool.handler(args)
                    else:
                        observation = await asyncio.to_thread(tool.handler, args)  # type: ignore[arg-type]
                except Exception as e:
                    observation = f"[Tool Error] {tool_name}: {e}"

            steps.append(AgentStep(
                step_num=step_num,
                thought=thought,
                tool_name=tool_name,
                tool_input=args,
                observation=str(observation),
            ))

            messages.append({"role": "assistant", "content": llm_output})
            messages.append({
                "role": "user",
                "content": f"Observation from {tool_name}:\n{observation}\n\nContinue.",
            })

        return AgentResult(
            agent_name=self.name, goal=goal,
            final_answer="max_steps exceeded",
            steps=steps, success=False, error="max_steps_exceeded",
        )

    async def _call_llm(self, messages: list[dict[str, str]]) -> str:
        client = AsyncOpenAI(base_url=self.llm_base_url, api_key=LLM_API_KEY)
        response = await client.chat.completions.create(
            model=self.llm_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        return response.choices[0].message.content or ""
