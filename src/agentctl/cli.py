"""CLI entry point for agentctl."""

from collections import Counter
from pathlib import Path
import os
import re
import sys
import time
from typing import Any, Callable, Iterator, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.styles import Style
import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

from agentctl.agent import run_agent
from agentctl.history import compact_messages, load, make_session_id, save
from agentctl.tools import resolve_safe_path
from agentctl.tools.list_files import SKIP_DIRS

app = typer.Typer(add_completion=False, help="A simple CLI coding agent.")
console = Console()

PROMPT_STYLE = Style.from_dict(
    {
        "at-mention": "bg:#1e3a5f #7dd3fc bold",
    }
)


def _project_entries() -> list[str]:
    """Return sorted relative directory (ending with '/') and file paths in cwd."""
    root = Path.cwd().resolve()
    skip = SKIP_DIRS | {".pytest_cache", ".ruff_cache", ".mypy_cache"}
    entries: list[str] = []

    for current_dir, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip)
        rel_dir = Path(current_dir).resolve().relative_to(root)
        prefix = "" if rel_dir == Path(".") else rel_dir.as_posix() + "/"
        for dirname in dirnames:
            entries.append(f"{prefix}{dirname}/")
        for filename in sorted(filenames):
            entries.append(f"{prefix}{filename}")

    return entries


class AtMentionLexer(Lexer):
    """Highlight '@path' mentions in the interactive prompt."""

    def lex_document(
        self, document: Document
    ) -> Callable[[int], StyleAndTextTuples]:
        """Return a line lexer that styles '@...' tokens."""
        lines = document.lines

        def get_line(lineno: int) -> StyleAndTextTuples:
            line = lines[lineno]
            tokens: StyleAndTextTuples = []
            last = 0
            for match in re.finditer(r"(?:^|\s)(@[^\s]+)", line):
                start, end = match.span(1)
                if start > last:
                    tokens.append(("", line[last:start]))
                tokens.append(("class:at-mention", line[start:end]))
                last = end
            if last < len(line):
                tokens.append(("", line[last:]))
            return tokens

        return get_line


class AtPathCompleter(Completer):
    """Autocomplete relative project paths when the user types '@'."""

    def get_completions(
        self, document: Document, complete_event: Any
    ) -> Iterator[Completion]:
        """Yield file/folder completions after '@', inserting short names for unique files."""
        before = document.text_before_cursor
        match = re.search(r"(?:^|\s)@([^\s]*)$", before)
        if not match:
            return

        prefix = match.group(1).replace("\\", "/")
        all_entries = _project_entries()
        name_counts = Counter(
            Path(e).name for e in all_entries if not e.endswith("/")
        )
        entries = [e for e in all_entries if e != prefix]

        if "/" in prefix or prefix == "":
            base_dir = prefix.rsplit("/", 1)[0] + "/" if "/" in prefix else ""
            direct = [
                e for e in entries
                if e.startswith(prefix)
                and e.count("/", len(base_dir)) <= (1 if e.endswith("/") else 0)
            ]
            deeper = [e for e in entries if e.startswith(prefix) and e not in direct]
            candidates = direct + deeper
        else:
            starts = [e for e in entries if e.lower().startswith(prefix.lower())]
            contains = [
                e for e in entries
                if prefix.lower() in e.lower() and e not in starts
            ]
            candidates = starts + contains

        for item in candidates[:25]:
            if item.endswith("/"):
                yield Completion(
                    item,
                    start_position=-len(prefix),
                    display=item,
                    display_meta="dir",
                )
            else:
                short = Path(item).name
                insert_text = short if name_counts[short] == 1 else item
                meta = item if item != short else "file"
                yield Completion(
                    insert_text,
                    start_position=-len(prefix),
                    display=short,
                    display_meta=meta,
                )


def _expand_at_mentions(text: str) -> str:
    """Resolve '@path' or unique '@filename' tokens into full relative paths for the LLM."""
    all_files = [e for e in _project_entries() if not e.endswith("/")]

    def _replace(match: re.Match[str]) -> str:
        lead, raw_path = match.group(1), match.group(2)
        clean_path = raw_path.replace("\\", "/").rstrip("/")
        try:
            target = resolve_safe_path(clean_path)
            if target.exists():
                return f"{lead}{clean_path}"
        except ValueError:
            pass

        matches = [f for f in all_files if Path(f).name == clean_path]
        if len(matches) == 1:
            return f"{lead}{matches[0]}"
        return match.group(0)

    return re.sub(r"(^|\s)@([^\s]+)", _replace, text)


def _log_tool_call(name: str, arguments: dict[str, Any]) -> None:
    """Display tool activity in the terminal as the agent works."""
    formatted_args = ", ".join(f"{k}={v!r}" for k, v in arguments.items())
    console.print(f"[dim]→ {name}({formatted_args})[/dim]")


def _confirm_tool(name: str, arguments: dict[str, Any]) -> bool:
    """Ask the user to confirm file/folder changes or shell command execution."""
    if name == "run_command":
        summary = f"Run command: {arguments.get('command', '')}"
    elif name == "delete_folder" and arguments.get("recursive"):
        summary = f"delete_folder RECURSIVELY on {arguments.get('path', '')}"
    elif name in {"write_file", "edit_file", "create_folder", "delete_file", "delete_folder"}:
        summary = f"{name} on {arguments.get('path', '')}"
    else:
        summary = f"Run {name}"
    return typer.confirm(f"Allow {summary}?", default=False)


def _log_tool_result(name: str, result: str) -> None:
    """Show command output or short tool status directly in the terminal."""
    if name == "run_command":
        lines = result.splitlines()
        preview = "\n".join(lines[:15])
        if len(lines) > 15:
            preview += f"\n... ({len(lines) - 15} more lines)"
        console.print(f"[dim]{preview}[/dim]")
    elif result.startswith("Error:"):
        console.print(f"[yellow]{result}[/yellow]")


def _run_turn(
    task: str,
    session_id: str,
    messages: list[dict[str, Any]],
    yes: bool,
) -> list[dict[str, Any]]:
    """Execute one agent turn, stream rendered Markdown, and compact/save history."""
    resolved_task = _expand_at_mentions(task)
    buffer: list[str] = []
    live: Live | None = None
    streamed = False
    last_refresh = 0.0

    def _stop_live() -> None:
        nonlocal live
        if live is not None:
            if buffer:
                live.update(Markdown("".join(buffer)), refresh=True)
            live.stop()
            live = None
        buffer.clear()

    def _on_token(token: str) -> None:
        nonlocal live, streamed, last_refresh
        streamed = True
        if live is None:
            live = Live(
                Markdown(""),
                console=console,
                auto_refresh=False,
                vertical_overflow="visible",
            )
            live.start()
        buffer.append(token)
        now = time.monotonic()
        if now - last_refresh >= 0.03 or "\n" in token:
            live.update(Markdown("".join(buffer)), refresh=True)
            last_refresh = now

    def _on_tool(name: str, arguments: dict[str, Any]) -> None:
        nonlocal streamed
        _stop_live()
        streamed = False
        _log_tool_call(name, arguments)

    console.print("[dim]Thinking...[/dim]")
    try:
        answer = run_agent(
            resolved_task,
            messages=messages,
            yes=yes,
            on_tool_call=_on_tool,
            confirm_fn=_confirm_tool,
            on_token=_on_token,
            on_tool_result=_log_tool_result,
        )
    finally:
        _stop_live()

    cleaned = compact_messages(messages)
    save(session_id, cleaned)

    if streamed:
        console.print()
    elif answer:
        console.print(Markdown(answer))

    return cleaned


def _session_loop(
    session_id: str,
    messages: list[dict[str, Any]],
    yes: bool,
    initial_task: str | None = None,
) -> None:
    """Run an interactive chat loop with '@' file autocomplete until exit/Ctrl+C/Ctrl+Z."""
    console.print(
        f"[bold cyan]Chat session '{session_id}'[/bold cyan] "
        "[dim](type '@' for file paths, 'exit'/'quit' or Ctrl+C/Ctrl+Z to stop)[/dim]"
    )

    if initial_task:
        messages = _run_turn(initial_task, session_id, messages, yes)

    prompt_session: PromptSession[str] | None = None
    if sys.stdin.isatty():
        prompt_session = PromptSession(
            completer=AtPathCompleter(),
            lexer=AtMentionLexer(),
            style=PROMPT_STYLE,
            complete_while_typing=True,
            complete_style=CompleteStyle.COLUMN,
        )

    while True:
        try:
            if prompt_session is not None:
                user_input = prompt_session.prompt("\nYou > ").strip()
            else:
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
        except Exception as exc:
            console.print(f"\n[red]Error: {exc}[/red]")


@app.command()
def run(
    task: Optional[str] = typer.Argument(
        None,
        help="Task prompt for one-shot mode, or 'chat' for interactive mode.",
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
    """Run agentctl one-shot or enter interactive chat mode."""
    if task == "chat":
        session_id = session or make_session_id()
        messages = load(session_id)
        _session_loop(session_id, messages, yes=yes)
        return

    if session:
        messages = load(session)
        _session_loop(session, messages, yes=yes, initial_task=task)
        return

    if not task:
        console.print(
            "[yellow]Please provide a task or 'chat'. Example:[/yellow] agentctl \"what does config.py do?\" or agentctl chat"
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
