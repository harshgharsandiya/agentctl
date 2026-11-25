"""Tool for plain-text search across project files."""

import os
from pathlib import Path

from agentctl.tools import resolve_safe_path, truncate_output

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
MAX_MATCHES = 50

SCHEMA = {
    "name": "search_files",
    "description": "Search for plain text across files, returning up to 50 'file:line: text' matches.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Plain-text string to search for.",
            },
            "path": {
                "type": "string",
                "description": "Relative file or directory path to search in (defaults to '.').",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}


def _iter_files(target: Path) -> list[Path]:
    """Return all non-ignored files under target."""
    if target.is_file():
        return [target]

    collected: list[Path] = []
    for current_dir, dirnames, filenames in os.walk(target):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            collected.append(Path(current_dir) / filename)
    return collected


def search_files(query: str, path: str = ".") -> str:
    """Search for plain text across files under a safe path (max 50 matches)."""
    if not query:
        return "Error: query cannot be empty."

    try:
        target = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if not target.exists():
        return f"Error: path not found: {path}"

    root = Path.cwd().resolve()
    matches: list[str] = []

    for file_path in _iter_files(target):
        try:
            raw = file_path.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw:
            continue  # Skip binary files.

        rel = file_path.resolve().relative_to(root).as_posix()
        text = raw.decode("utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if query in line:
                matches.append(f"{rel}:{line_no}: {line}")
                if len(matches) >= MAX_MATCHES:
                    return truncate_output("\n".join(matches))

    if not matches:
        return "No matches found."
    return truncate_output("\n".join(matches))
