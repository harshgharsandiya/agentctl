"""Tool for executing shell commands inside the project directory."""

import subprocess
from pathlib import Path

from agentctl.tools import truncate_output

SCHEMA = {
    "name": "run_command",
    "description": "Run a shell command in the project root and return stdout, stderr, and exit code.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (defaults to 30).",
            },
        },
        "required": ["command"],
    },
}


def run_command(command: str, timeout: int = 30) -> str:
    """Run a shell command in the current working directory and return output."""
    if not command.strip():
        return "Error: command cannot be empty."
    if timeout < 1:
        return "Error: timeout must be >= 1."

    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout} seconds."
    except OSError as exc:
        return f"Error: failed to run command: {exc}"

    output = (
        f"Exit code: {proc.returncode}\n"
        f"STDOUT:\n{proc.stdout}"
        f"STDERR:\n{proc.stderr}"
    )
    return truncate_output(output)
