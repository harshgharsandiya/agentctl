"""Tool for listing files in a project directory."""

import os
from pathlib import Path

from agentctl.tools import resolve_safe_path, truncate_output

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}

SCHEMA = {
    "name": "list_files",
    "description": "List files inside a directory, skipping .git, node_modules, __pycache__, and virtual environments.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative directory path to list (defaults to '.').",
            },
        },
        "required": [],
        "additionalProperties": False,
    },
}


def list_files(path: str = ".") -> str:
    """List files inside a safe directory path, skipping ignored directories."""
    try:
        target = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if not target.exists():
        return f"Error: directory not found: {path}"
    if not target.is_dir():
        return f"Error: not a directory: {path}"

    root = Path.cwd().resolve()
    files: list[str] = []

    for current_dir, dirnames, filenames in os.walk(target):
        # Prune ignored directories in-place so os.walk does not descend into them.
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            rel = (Path(current_dir) / filename).resolve().relative_to(root)
            files.append(rel.as_posix())

    if not files:
        return "(no files found)"
    return truncate_output("\n".join(files))
