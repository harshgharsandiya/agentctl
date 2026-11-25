"""In-memory message list helpers, compaction, and JSON session persistence."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from agentctl.config import SESSIONS_DIR

DEFAULT_MAX_MESSAGES = 40
DEFAULT_MAX_TOOL_CHARS = 400


def _session_path(session_id: str) -> Path:
    """Return a safe JSON path inside SESSIONS_DIR for the given session ID."""
    if not session_id or Path(session_id).name != session_id or ".." in session_id:
        raise ValueError(f"Invalid session_id: {session_id!r}")
    return SESSIONS_DIR / f"{session_id}.json"


def make_session_id() -> str:
    """Generate a timestamp-based session ID."""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def compact_messages(
    messages: list[dict[str, Any]],
    max_messages: int = DEFAULT_MAX_MESSAGES,
    max_tool_chars: int = DEFAULT_MAX_TOOL_CHARS,
) -> list[dict[str, Any]]:
    """Shrink history by dropping failed tool retries, truncating tool outputs, and trimming old turns."""
    compacted: list[dict[str, Any]] = []
    i = 0

    while i < len(messages):
        msg = messages[i]
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            j = i + 1
            while j < len(messages) and messages[j].get("role") == "tool":
                j += 1
            tool_msgs = messages[i + 1 : j]

            # Drop assistant+tool batches where every tool call returned an Error.
            if tool_msgs and all(
                str(tm.get("content", "")).startswith("Error:") for tm in tool_msgs
            ):
                i = j
                continue

            compacted.append(msg)
            for tm in tool_msgs:
                content = str(tm.get("content", ""))
                if len(content) > max_tool_chars:
                    content = f"{content[:max_tool_chars]}\n... [compacted]"
                compacted.append({**tm, "content": content})
            i = j
            continue

        compacted.append(msg)
        i += 1

    # Trim oldest full user turns while keeping the system prompt at index 0.
    while len(compacted) > max_messages:
        user_indices = [
            idx for idx, m in enumerate(compacted) if m.get("role") == "user"
        ]
        if len(user_indices) <= 1:
            break
        first_user, second_user = user_indices[0], user_indices[1]
        compacted = compacted[:first_user] + compacted[second_user:]

    return compacted


def save(session_id: str, messages: list[dict[str, Any]]) -> Path:
    """Compact and save the message list to sessions/<session_id>.json."""
    path = _session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = compact_messages(messages)
    path.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
    return path


def load(session_id: str) -> list[dict[str, Any]]:
    """Load messages from sessions/<session_id>.json, or return [] if missing."""
    path = _session_path(session_id)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Corrupt session file: {path}")
    return data
