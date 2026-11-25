"""LLM client wrapper using the official Groq SDK."""

from typing import Any

from groq import Groq

from agentctl.config import GROQ_API_KEY, MODEL_NAME


def _get_client() -> Groq:
    """Create and return a configured Groq client."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")
    return Groq(api_key=GROQ_API_KEY)


def call_llm(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send messages (and optional tools) to Groq and return the parsed reply."""
    client = _get_client()
    kwargs: dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = [
            {"type": "function", "function": schema} for schema in tools
        ]
        # Let our agent loop return unknown-tool errors instead of failing on HTTP 400.
        kwargs["disable_tool_validation"] = True

    response = client.chat.completions.create(**kwargs)
    message = response.choices[0].message

    tool_calls = [
        {
            "id": tc.id,
            "name": tc.function.name,
            "arguments": tc.function.arguments,
        }
        for tc in (message.tool_calls or [])
    ]

    return {
        "content": message.content or "",
        "tool_calls": tool_calls,
    }


if __name__ == "__main__":
    reply = call_llm(
        [{"role": "user", "content": "Say hello in one short sentence."}]
    )
    print(reply["content"])
