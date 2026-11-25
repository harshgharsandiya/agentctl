"""Tool for replacing an exact text snippet inside a file."""

from agentctl.tools import resolve_safe_path

SCHEMA = {
    "name": "edit_file",
    "description": "Replace exactly one occurrence of old_text with new_text in a file.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file to edit.",
            },
            "old_text": {
                "type": "string",
                "description": "Exact existing text to replace (must match once).",
            },
            "new_text": {
                "type": "string",
                "description": "Replacement text.",
            },
        },
        "required": ["path", "old_text", "new_text"],
    },
}


def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace exactly one occurrence of old_text with new_text in a safe project path."""
    try:
        target = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if not target.exists():
        return f"Error: file not found: {path}"
    if not target.is_file():
        return f"Error: not a file: {path}"
    if not old_text:
        return "Error: old_text cannot be empty."

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Error: failed to read '{path}': {exc}"

    matches = text.count(old_text)
    if matches == 0:
        return f"Error: old_text not found in {path}."
    if matches > 1:
        return f"Error: expected 1 match in {path}, found {matches}."

    updated = text.replace(old_text, new_text, 1)
    try:
        target.write_text(updated, encoding="utf-8")
    except OSError as exc:
        return f"Error: failed to write '{path}': {exc}"

    return f"Edited {path} (1 replacement)."
