"""Tool for deleting folders within the project directory."""

from pathlib import Path
import shutil

from agentctl.tools import resolve_safe_path

SCHEMA = {
    "name": "delete_folder",
    "description": "Delete a folder inside the project directory (empty by default, or recursive=true for non-empty).",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path of the folder to delete.",
            },
            "recursive": {
                "type": "boolean",
                "description": "Set true to delete a non-empty folder and its contents (defaults to false).",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}


def delete_folder(path: str, recursive: bool = False) -> str:
    """Delete an empty or non-empty folder at a safe project path."""
    try:
        target = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    root = Path.cwd().resolve()
    if target == root:
        return "Error: cannot delete the project root directory."
    if target.name == ".git":
        return "Error: cannot delete the .git directory."
    if not target.exists():
        return f"Error: folder not found: {path}"
    if not target.is_dir():
        return f"Error: '{path}' is a file; use delete_file instead."

    try:
        if recursive:
            shutil.rmtree(target)
        else:
            target.rmdir()
    except OSError as exc:
        if not recursive:
            return f"Error: folder '{path}' is not empty (or cannot be removed): {exc}"
        return f"Error: failed to delete folder '{path}': {exc}"

    return f"Deleted folder: {path}."
