"""Tool for executing shell commands inside the project directory."""

import os
from pathlib import Path
import subprocess
import sys

from agentctl.tools import truncate_output

SCHEMA = {
    "name": "run_command",
    "description": "Run a shell command in the project root (e.g. install dependencies, run tests/scripts) and return exit code, stdout, and stderr.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (defaults to 60; use 120+ for installing packages).",
            },
        },
        "required": ["command"],
        "additionalProperties": False,
    },
}


def _build_env() -> dict[str, str]:
    """Ensure the active Python environment's Scripts/bin directory is first on PATH."""
    env = os.environ.copy()
    py_dir = str(Path(sys.executable).resolve().parent)
    current_path = env.get("PATH", "")
    if py_dir not in current_path.split(os.pathsep):
        env["PATH"] = f"{py_dir}{os.pathsep}{current_path}" if current_path else py_dir
    return env


def run_command(command: str, timeout: int = 60) -> str:
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
            env=_build_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout} seconds."
    except OSError as exc:
        return f"Error: failed to run command: {exc}"

    stdout = proc.stdout.strip() or "(empty)"
    stderr = proc.stderr.strip() or "(empty)"
    output = (
        f"Exit code: {proc.returncode}\n"
        f"STDOUT:\n{stdout}\n"
        f"STDERR:\n{stderr}"
    )
    return truncate_output(output)
