"""Tool registry and shared path/output/confirmation helpers for agentctl."""

from pathlib import Path
from typing import Any, Callable

MAX_OUTPUT_CHARS = 10_000
CONFIRM_TOOLS = {
    "write_file",
    "edit_file",
    "create_folder",
    "delete_file",
    "delete_folder",
    "run_command",
}


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


def _default_confirm(name: str, arguments: dict[str, Any]) -> bool:
    """Prompt the user on stdin to confirm a mutating or shell tool call."""
    answer = input(f"Allow {name} with {arguments}? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


from agentctl.tools import (  # noqa: E402
    create_folder,
    delete_file,
    delete_folder,
    edit_file,
    list_files,
    read_file,
    run_command,
    search_files,
    write_file,
)

TOOLS: dict[str, dict[str, Any]] = {
    "read_file": {
        "fn": read_file.read_file,
        "schema": read_file.SCHEMA,
    },
    "write_file": {
        "fn": write_file.write_file,
        "schema": write_file.SCHEMA,
    },
    "edit_file": {
        "fn": edit_file.edit_file,
        "schema": edit_file.SCHEMA,
    },
    "create_folder": {
        "fn": create_folder.create_folder,
        "schema": create_folder.SCHEMA,
    },
    "delete_file": {
        "fn": delete_file.delete_file,
        "schema": delete_file.SCHEMA,
    },
    "delete_folder": {
        "fn": delete_folder.delete_folder,
        "schema": delete_folder.SCHEMA,
    },
    "list_files": {
        "fn": list_files.list_files,
        "schema": list_files.SCHEMA,
    },
    "search_files": {
        "fn": search_files.search_files,
        "schema": search_files.SCHEMA,
    },
    "run_command": {
        "fn": run_command.run_command,
        "schema": run_command.SCHEMA,
    },
}


def get_tool_schemas() -> list[dict[str, Any]]:
    """Return JSON schemas for all registered tools."""
    return [entry["schema"] for entry in TOOLS.values()]


def get_tool(name: str) -> Callable[..., str] | None:
    """Return the tool function for the given name, or None if unknown."""
    entry = TOOLS.get(name)
    return entry["fn"] if entry else None


def run_tool(
    name: str,
    arguments: dict[str, Any],
    yes: bool = False,
    confirm_fn: Callable[[str, dict[str, Any]], bool] | None = None,
) -> str:
    """Execute a registered tool by name and always return a string result."""
    fn = get_tool(name)
    if fn is None:
        available = ", ".join(TOOLS.keys())
        return f"Error: unknown tool '{name}'. Available tools: {available}."

    if name in CONFIRM_TOOLS and not yes:
        prompter = confirm_fn or _default_confirm
        if not prompter(name, arguments):
            return f"Error: {name} cancelled by user."

    try:
        return str(fn(**arguments))
    except TypeError as exc:
        return f"Error: invalid arguments for '{name}': {exc}"
    except Exception as exc:
        return f"Error: tool '{name}' failed: {exc}"
