"""Pytest unit tests for all agentctl tools and safety rules."""

from pathlib import Path
import sys

import pytest

from agentctl.tools import TOOLS, get_tool_schemas, run_tool
from agentctl.tools.create_folder import create_folder
from agentctl.tools.delete_file import delete_file
from agentctl.tools.delete_folder import delete_folder
from agentctl.tools.edit_file import edit_file
from agentctl.tools.list_files import list_files
from agentctl.tools.read_file import read_file
from agentctl.tools.run_command import run_command
from agentctl.tools.search_files import search_files
from agentctl.tools.write_file import write_file


def test_all_tools_registered() -> None:
    """All 9 expected tools are registered with matching schemas."""
    expected = {
        "read_file",
        "write_file",
        "edit_file",
        "create_folder",
        "delete_file",
        "delete_folder",
        "list_files",
        "search_files",
        "run_command",
    }
    assert set(TOOLS.keys()) == expected
    assert {s["name"] for s in get_tool_schemas()} == expected


def test_read_file_and_line_range(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """read_file returns full text or an inclusive 1-based line slice."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sample.txt").write_text("line1\nline2\nline3\n", encoding="utf-8")

    assert read_file("sample.txt") == "line1\nline2\nline3\n"
    assert read_file("sample.txt", start_line=2, end_line=3) == "line2\nline3\n"
    assert read_file("missing.txt").startswith("Error:")


def test_write_file_create_and_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """write_file creates parent directories and overwrites existing files."""
    monkeypatch.chdir(tmp_path)

    msg1 = write_file("sub/hello.txt", "first")
    assert "Wrote 5 characters" in msg1
    assert (tmp_path / "sub/hello.txt").read_text(encoding="utf-8") == "first"

    write_file("sub/hello.txt", "second")
    assert (tmp_path / "sub/hello.txt").read_text(encoding="utf-8") == "second"


def test_edit_file_single_zero_and_multiple_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """edit_file replaces exactly one match and errors on zero or multiple matches."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "code.py"
    target.write_text("x = 1\ny = 2\ny = 2\n", encoding="utf-8")

    assert edit_file("code.py", "x = 1", "x = 10").startswith("Edited")
    assert "x = 10" in target.read_text(encoding="utf-8")

    assert edit_file("code.py", "z = 99", "z = 0").startswith("Error:")
    assert edit_file("code.py", "y = 2", "y = 3").startswith("Error:")


def test_create_and_delete_folder_and_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """create_folder, delete_file, and delete_folder manage files and directories safely."""
    monkeypatch.chdir(tmp_path)

    assert create_folder("nested/dir").startswith("Created folder")
    assert (tmp_path / "nested/dir").is_dir()

    (tmp_path / "nested/dir/a.txt").write_text("hi", encoding="utf-8")
    # Non-empty folder requires recursive=True.
    assert delete_folder("nested/dir").startswith("Error:")
    assert delete_file("nested/dir").startswith("Error:")

    assert delete_file("nested/dir/a.txt").startswith("Deleted file")
    assert not (tmp_path / "nested/dir/a.txt").exists()

    assert delete_folder("nested/dir").startswith("Deleted folder")
    assert not (tmp_path / "nested/dir").exists()

    # Recursive delete removes non-empty folder, while root '.' is always protected.
    (tmp_path / "nested/sub").mkdir(parents=True)
    (tmp_path / "nested/sub/b.txt").write_text("data", encoding="utf-8")
    assert delete_folder("nested", recursive=True).startswith("Deleted folder")
    assert not (tmp_path / "nested").exists()
    assert delete_folder(".", recursive=True).startswith("Error:")


def test_list_files_skips_ignored_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """list_files lists project files while skipping .git, node_modules, __pycache__, .venv."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("print('hi')\n", encoding="utf-8")
    for ignored in (".git", "node_modules", "__pycache__", ".venv"):
        d = tmp_path / ignored
        d.mkdir()
        (d / "secret.txt").write_text("skip", encoding="utf-8")

    output = list_files(".")
    assert output == "app.py"


def test_search_files_matches_and_max_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """search_files returns 'file:line: text' matches capped at 50."""
    monkeypatch.chdir(tmp_path)
    lines = [f"match line {i}" for i in range(60)]
    (tmp_path / "notes.txt").write_text("\n".join(lines), encoding="utf-8")
    ignored = tmp_path / ".git"
    ignored.mkdir()
    (ignored / "config").write_text("match in git\n", encoding="utf-8")

    output = search_files("match")
    result_lines = output.splitlines()
    assert len(result_lines) == 50
    assert result_lines[0] == "notes.txt:1: match line 0"
    assert search_files("does_not_exist") == "No matches found."


def test_run_command_output_venv_and_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_command uses the active Python environment, captures output, and enforces timeout."""
    monkeypatch.chdir(tmp_path)

    res = run_command('python -c "import sys; print(sys.executable); print(\'err\', file=sys.stderr)"')
    assert "Exit code: 0" in res
    assert str(Path(sys.executable).resolve().parent).lower() in res.lower()
    assert "err" in res

    timeout_res = run_command('python -c "import time; time.sleep(2)"', timeout=1)
    assert "timed out" in timeout_res


def test_path_safety_rejects_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """All file and folder tools reject paths escaping the current working directory."""
    monkeypatch.chdir(tmp_path)

    assert read_file("../escape.txt").startswith("Error:")
    assert write_file("../escape.txt", "bad").startswith("Error:")
    assert edit_file("../escape.txt", "a", "b").startswith("Error:")
    assert create_folder("../escape_dir").startswith("Error:")
    assert delete_file("../escape.txt").startswith("Error:")
    assert delete_folder("../escape_dir").startswith("Error:")
    assert list_files("..").startswith("Error:")
    assert search_files("x", "..").startswith("Error:")


def test_output_truncation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Outputs longer than 10,000 characters are truncated with a notice."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "big.txt").write_text("a" * 12_000, encoding="utf-8")

    output = read_file("big.txt")
    assert len(output) < 12_000
    assert "truncated" in output


def test_confirmation_required_unless_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutating, delete, and shell tools require confirmation unless yes=True."""
    monkeypatch.chdir(tmp_path)

    for tool_name, args in (
        ("write_file", {"path": "a.txt", "content": "hi"}),
        ("create_folder", {"path": "sub"}),
        ("delete_file", {"path": "a.txt"}),
        ("delete_folder", {"path": "sub"}),
    ):
        declined = run_tool(
            tool_name,
            args,
            yes=False,
            confirm_fn=lambda _name, _args: False,
        )
        assert "cancelled" in declined

    accepted = run_tool(
        "write_file",
        {"path": "a.txt", "content": "hi"},
        yes=True,
    )
    assert "Wrote 2 characters" in accepted
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hi"
