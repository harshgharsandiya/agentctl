"""Tool registry and shared path/output helpers for agentctl."""

from pathlib import Path
from typing import Any, Callable

MAX_OUTPUT_CHARS = 10_000


def resolve_safe_path(path: str) -> Path:
    """Resolve a path inside the current working directory or raise ValueError."""
    root = Path.cwd().resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Path '{path}' escapes the project directory.")
    return target


def truncate_output(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Truncate output exceeding the character limit with a clear notice."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n\n... [truncated: output exceeded {limit} characters]"


from agentctl.tools import read_file  # noqa: E402

TOOLS: dict[str, dict[str, Any]] = {
    "read_file": {
        "fn": read_file.read_file,
        "schema": read_file.SCHEMA,
    },
}


def get_tool_schemas() -> list[dict[str, Any]]:
    """Return JSON schemas for all registered tools."""
    return [entry["schema"] for entry in TOOLS.values()]


def get_tool(name: str) -> Callable[..., str] | None:
    """Return the tool function for the given name, or None if unknown."""
    entry = TOOLS.get(name)
    return entry["fn"] if entry else None


def run_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a registered tool by name and always return a string result."""
    fn = get_tool(name)
    if fn is None:
        available = ", ".join(TOOLS.keys())
        return f"Error: unknown tool '{name}'. Available tools: {available}."
    try:
        return str(fn(**arguments))
    except TypeError as exc:
        return f"Error: invalid arguments for '{name}': {exc}"
    except Exception as exc:
        return f"Error: tool '{name}' failed: {exc}"
