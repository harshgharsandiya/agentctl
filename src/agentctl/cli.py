"""CLI entry point for agentctl."""

from typing import Any, Optional

import typer
from rich.console import Console
from rich.markdown import Markdown

from agentctl.agent import run_agent
from agentctl.history import compact_messages, load, make_session_id, save

app = typer.Typer(add_completion=False, help="A simple CLI coding agent.")
console = Console()


def _log_tool_call(name: str, arguments: dict[str, Any]) -> None:
    """Display tool activity in the terminal as the agent works."""
    formatted_args = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
    console.print(f"[dim]→ {name}({formatted_args})[/dim]")


def _confirm_tool(name: str, arguments: dict[str, Any]) -> bool:
    """Ask the user to confirm write, edit, or shell command execution."""
    if name == "run_command":
        summary = f"Run command: {arguments.get('command', '')}"
    elif name in {"write_file", "edit_file"}:
        summary = f"{name} on {arguments.get('path', '')}"
    else:
        summary = f"Run {name}"
    return typer.confirm(f"Allow {summary}?", default=False)


def _run_turn(
    task: str,
    session_id: str,
    messages: list[dict[str, Any]],
    yes: bool,
) -> list[dict[str, Any]]:
    """Execute one agent turn, print the response, and compact/save history."""
    console.print("[dim]Thinking...[/dim]")
    answer = run_agent(
        task,
        messages=messages,
        yes=yes,
        on_tool_call=_log_tool_call,
        confirm_fn=_confirm_tool,
    )
    cleaned = compact_messages(messages)
    save(session_id, cleaned)
    console.print(Markdown(answer))
    return cleaned


def _session_loop(
    session_id: str,
    messages: list[dict[str, Any]],
    yes: bool,
    initial_task: str | None = None,
) -> None:
    """Run an interactive loop for a session until quit/exit/Ctrl+C/Ctrl+Z."""
    console.print(
        f"[bold cyan]Session '{session_id}'[/bold cyan] "
        "[dim](type 'exit' or 'quit', or press Ctrl+C / Ctrl+Z to stop)[/dim]"
    )

    if initial_task:
        messages = _run_turn(initial_task, session_id, messages, yes)

    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[dim]Session saved: sessions/{session_id}.json[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            console.print(f"[dim]Session saved: sessions/{session_id}.json[/dim]")
            break

        try:
            messages = _run_turn(user_input, session_id, messages, yes)
        except KeyboardInterrupt:
            console.print(f"\n[dim]Interrupted. Session saved: sessions/{session_id}.json[/dim]")
            break


@app.command()
def run(
    task: Optional[str] = typer.Argument(
        None,
        help="Task prompt to run in one-shot mode.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts for file edits and commands.",
    ),
    session: Optional[str] = typer.Option(
        None,
        "--session",
        "-s",
        help="Session ID to open in a loop and save conversation history.",
    ),
) -> None:
    """Run agentctl one-shot or stay in an interactive session loop."""
    if session:
        messages = load(session)
        _session_loop(session, messages, yes=yes, initial_task=task)
        return

    if not task:
        console.print(
            "[yellow]Please provide a task or --session. Example:[/yellow] agentctl \"what does config.py do?\""
        )
        raise typer.Exit(code=1)

    session_id = make_session_id()
    messages: list[dict[str, Any]] = []
    _run_turn(task, session_id, messages, yes=yes)
    console.print(f"[dim]Session saved: sessions/{session_id}.json[/dim]")


def main() -> None:
    """Entry point for the agentctl CLI."""
    app()


if __name__ == "__main__":
    main()
