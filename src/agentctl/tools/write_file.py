"""Tool for creating or overwriting files within the project directory."""

from agentctl.tools import resolve_safe_path

SCHEMA = {
    "name": "write_file",
    "description": "Create a new file or overwrite an existing file with the given content.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file to write.",
            },
            "content": {
                "type": "string",
                "description": "Full text content to write to the file.",
            },
        },
        "required": ["path", "content"],
    },
}


def write_file(path: str, content: str) -> str:
    """Create or overwrite a file at a safe project path."""
    try:
        target = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if target.exists() and target.is_dir():
        return f"Error: path is a directory: {path}"

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        return f"Error: failed to write '{path}': {exc}"

    return f"Wrote {len(content)} characters to {path}."
