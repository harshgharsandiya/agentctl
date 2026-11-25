"""Agent loop coordinating LLM calls and tool execution."""

import json
from typing import Any, Callable

from agentctl.config import MAX_STEPS
from agentctl.llm import call_llm
from agentctl.prompts import SYSTEM_PROMPT
from agentctl.tools import get_tool_schemas, run_tool


def _parse_arguments(raw_args: str) -> dict[str, Any] | str:
    """Parse JSON tool arguments, returning an error string if invalid."""
    if not raw_args.strip():
        return {}
    try:
        parsed = json.loads(raw_args)
    except json.JSONDecodeError as exc:
        return f"Error: invalid JSON tool arguments: {exc}"
    if not isinstance(parsed, dict):
        return "Error: tool arguments must be a JSON object."
    return parsed


def run_agent(
    task: str,
    messages: list[dict[str, Any]] | None = None,
    on_tool_call: Callable[[str, dict[str, Any]], None] | None = None,
) -> str:
    """Run the agent loop for a task until completion or MAX_STEPS."""
    history = messages if messages is not None else []
    if not history:
        history.append({"role": "system", "content": SYSTEM_PROMPT})
    history.append({"role": "user", "content": task})

    tool_schemas = get_tool_schemas()

    for _step in range(MAX_STEPS):
        reply = call_llm(history, tools=tool_schemas)
        tool_calls = reply["tool_calls"]

        if not tool_calls:
            history.append({"role": "assistant", "content": reply["content"]})
            return reply["content"]

        # Record the assistant's tool call request before appending tool outputs.
        history.append(
            {
                "role": "assistant",
                "content": reply["content"] or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            args = _parse_arguments(tc["arguments"])
            if isinstance(args, str):
                if on_tool_call:
                    on_tool_call(tc["name"], {"raw": tc["arguments"]})
                result = args
            else:
                if on_tool_call:
                    on_tool_call(tc["name"], args)
                result = run_tool(tc["name"], args)

            history.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                }
            )

    return f"Stopped: reached maximum step limit ({MAX_STEPS})."
