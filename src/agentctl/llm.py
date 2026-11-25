"""LLM client wrapper with streaming using the official Groq SDK."""

from typing import Any, Callable

from groq import APIError, Groq

from agentctl.config import GROQ_API_KEY, MODEL_NAME


def _get_client() -> Groq:
    """Create and return a configured Groq client."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")
    return Groq(api_key=GROQ_API_KEY)


def _stream_once(
    client: Groq,
    kwargs: dict[str, Any],
    on_token: Callable[[str], None] | None,
) -> dict[str, Any]:
    """Execute one streaming completion call and collect text and tool calls."""
    stream = client.chat.completions.create(**kwargs)

    content_parts: list[str] = []
    tool_calls_by_index: dict[int, dict[str, str]] = {}

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        if delta.content:
            content_parts.append(delta.content)
            if on_token:
                on_token(delta.content)

        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                entry = tool_calls_by_index.setdefault(
                    tc_delta.index,
                    {"id": "", "name": "", "arguments": ""},
                )
                if tc_delta.id:
                    entry["id"] = tc_delta.id
                if tc_delta.function:
                    if tc_delta.function.name:
                        entry["name"] += tc_delta.function.name
                    if tc_delta.function.arguments:
                        entry["arguments"] += tc_delta.function.arguments

    tool_calls = [
        tool_calls_by_index[idx] for idx in sorted(tool_calls_by_index)
    ]

    return {
        "content": "".join(content_parts),
        "tool_calls": tool_calls,
    }


def call_llm(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    on_token: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Stream a chat completion from Groq, retrying once on malformed tool-call stream errors."""
    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": True,
    }
    if tools:
        kwargs["tools"] = [
            {"type": "function", "function": schema} for schema in tools
        ]
        # Let our agent loop return unknown-tool errors instead of failing on HTTP 400.
        kwargs["disable_tool_validation"] = True

    last_error: APIError | None = None
    for _attempt in range(2):
        try:
            return _stream_once(client, kwargs, on_token)
        except APIError as exc:
            last_error = exc
            if "tool call" not in str(exc).lower() and "json" not in str(exc).lower():
                break

    return {
        "content": f"Error from LLM provider: {last_error}",
        "tool_calls": [],
    }


if __name__ == "__main__":
    call_llm(
        [{"role": "user", "content": "Say hello in one short sentence."}],
        on_token=lambda token: print(token, end="", flush=True),
    )
    print()
