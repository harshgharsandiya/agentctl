"""Tool for reading file contents within the project directory."""

from agentctl.tools import resolve_safe_path, truncate_output

SCHEMA = {
    "name": "read_file",
    "description": "Read the text contents of a file, optionally within a 1-based inclusive line range.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file to read.",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional 1-based starting line number (inclusive).",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional 1-based ending line number (inclusive).",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}


def read_file(
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Return file text for a safe project path, optionally sliced by line range."""
    try:
        target = resolve_safe_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if not target.exists():
        return f"Error: file not found: {path}"
    if not target.is_file():
        return f"Error: not a file: {path}"

    if start_line is not None and start_line < 1:
        return "Error: start_line must be >= 1."
    if end_line is not None and end_line < 1:
        return "Error: end_line must be >= 1."
    if start_line is not None and end_line is not None and end_line < start_line:
        return "Error: end_line must be >= start_line."

    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Error: failed to read '{path}': {exc}"

    if start_line is not None or end_line is not None:
        lines = text.splitlines(keepends=True)
        start_idx = (start_line - 1) if start_line is not None else 0
        end_idx = end_line if end_line is not None else len(lines)
        text = "".join(lines[start_idx:end_idx])

    return truncate_output(text)
