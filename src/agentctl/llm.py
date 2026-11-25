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
        kwargs["tools"] = tools

    response = client.chat.completions.create(**kwargs)
    message = response.choices[0].message

    return {
        "content": message.content or "",
        "tool_calls": [],
    }


if __name__ == "__main__":
    reply = call_llm(
        [{"role": "user", "content": "Hello, can you tell me a joke?"}]
    )
    print(reply["content"])
