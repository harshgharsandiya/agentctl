"""Tool for deleting files within the project directory."""

from agentctl.tools import resolve_safe_path

SCHEMA = {
    "name": "delete_file",
    "description": "Delete a single file inside the project directory.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path of the file to delete.",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}


def delete_file(path: str) -> str:
    """Delete a file at a safe project path."""
    try:
        target = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if not target.exists():
        return f"Error: file not found: {path}"
    if target.is_dir():
        return f"Error: '{path}' is a folder; use delete_folder instead."

    try:
        target.unlink()
    except OSError as exc:
        return f"Error: failed to delete file '{path}': {exc}"

    return f"Deleted file: {path}."
