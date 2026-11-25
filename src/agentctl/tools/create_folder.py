"""Tool for creating folders within the project directory."""

from agentctl.tools import resolve_safe_path

SCHEMA = {
    "name": "create_folder",
    "description": "Create a folder (and any missing parent folders) inside the project.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path of the folder to create.",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}


def create_folder(path: str) -> str:
    """Create a directory at a safe project path."""
    try:
        target = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if target.exists() and target.is_file():
        return f"Error: a file already exists at '{path}'."

    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return f"Error: failed to create folder '{path}': {exc}"

    return f"Created folder: {path}."
