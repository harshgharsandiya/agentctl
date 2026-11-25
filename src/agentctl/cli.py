"""CLI entry point for agentctl."""

from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown

from agentctl.agent import run_agent

app = typer.Typer(add_completion=False, help="A simple CLI coding agent.")
console = Console()


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
) -> None:
    """Run agentctl with a one-shot task prompt."""
    if not task:
        console.print(
            "[yellow]Please provide a task. Example:[/yellow] agentctl \"what does config.py do?\""
        )
        raise typer.Exit(code=1)

    _ = yes  # Reserved for tool confirmations in Phase 4.
    answer = run_agent(task)
    console.print(Markdown(answer))


def main() -> None:
    """Entry point for the agentctl CLI."""
    app()


if __name__ == "__main__":
    main()
