# Build Your Own Coding Agent: Simple Guide

This guide explains how `agentctl` is built, step by step. Follow the phases in order. Each phase ends with something you can run and test.

**What you need:** Python 3.10+, a Groq API key, and basic Python knowledge.

---

## The Big Idea

A coding agent is an **LLM in a loop with tools**.

```
You: "add a function to utils.py"
  → LLM decides: call read_file("utils.py")
  → Your code runs the tool, returns the text
  → LLM decides: call edit_file(...)
  → Your code runs the tool
  → LLM says: "Done."
```

The LLM never touches your files. It only _asks_ for a tool, and your code decides whether to run it.

---

## Phase 1: Call the LLM

**Files:** `config.py`, `llm.py`

Goal: send a message, print the reply.

- `config.py` holds the model name and loads the API key from `.env`.
- `llm.py` is the **only** file that imports the provider SDK. Switching models later touches one file.

Test: run a tiny script that prints a reply to "Say hello."

---

## Phase 2: Wrap it in a CLI

**File:** `cli.py`

Goal: run `agentctl "your task"` from the terminal.

Use **Typer**. One command takes a task string and passes it to the agent. Keep CLI code separate from agent logic so the agent can be reused later (for example, in a web API).

---

## Phase 3: Add a tool and the agent loop

**Files:** `tools/__init__.py`, `tools/read_file.py`, `agent.py`

### What is a tool?

A tool is two things:

1. A **schema** that tells the model the tool's name, purpose, and parameters
2. A **Python function** that does the work

```python
# Schema (what the model sees)
{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a text file inside the project.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
}

# Function (what your code runs)
def read_file(path: str) -> str:
    ...
```

The **registry** in `tools/__init__.py` maps tool names to functions and collects all schemas.

### The agent loop

```python
def run_agent(history, task):
    history.append({"role": "user", "content": task})

    for step in range(MAX_STEPS):
        reply = call_llm(history, TOOL_SCHEMAS)
        history.append(reply.message)

        if not reply.tool_calls:          # no tools requested = done
            return reply.text

        for call in reply.tool_calls:
            result = run_tool(call.name, call.arguments)
            history.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })

    return "Stopped: max steps reached."
```

Three things make this work:

- **History** carries every message and tool result, so the model remembers what happened.
- **No tool calls** means the model is finished.
- **`MAX_STEPS`** stops infinite loops.

Test: ask "what does config.py do?" and watch it call `read_file`.

---

## Phase 4: Add the remaining tools and safety

**Files:** the rest of `tools/`

Add `write_file`, `edit_file`, `list_files`, `search_files`, `run_command`, and the folder/delete tools.

Follow these rules for **every** tool:

1. **Return strings, even for errors.** Return `"Error: file not found"` instead of crashing, so the model can recover.
2. **Truncate long output** (for example, over 10,000 characters) to protect the context window.
3. **Keep paths inside the project.**
4. **Ask for confirmation** before anything that changes things.

### Path safety

```python
from pathlib import Path

ROOT = Path.cwd().resolve()

def safe_path(user_path: str) -> Path:
    full = (ROOT / user_path).resolve()
    if not full.is_relative_to(ROOT):
        raise ValueError("Path is outside the project.")
    return full
```

`resolve()` collapses `..` tricks before the check, so `../../secret.txt` gets blocked.

### Confirmation

```python
def confirm(action: str) -> bool:
    return input(f"Allow: {action}? (y/n) ").strip().lower() == "y"
```

Skip this check when the user passes `--yes`.

### Safe edits

`edit_file` replaces text only when `old_text` matches **exactly once**. Zero matches or multiple matches return an error. This prevents accidental large changes.

Test: write pytest tests for each tool, including bad paths and missing files.

---

## Phase 5: Save sessions

**File:** `history.py`

- Keep the message list in memory.
- `save(name)` writes it to `sessions/<name>.json`.
- `load(name)` reads it back.
- **Compaction:** when history grows too long, shrink old content (for example, trim old tool outputs) so you stay within the model's context limit.

Test: start a session, quit, resume it with `--session`, and ask about earlier messages.

---

## Phase 6: Streaming and chat mode

**Files:** `llm.py`, `cli.py`

### Streaming

Request streamed responses and print text as it arrives. Use **Rich** to render Markdown live.

**Watch out:** tool calls also arrive in pieces. The arguments come as many small string chunks, grouped by an index. Join the chunks for each index, then parse the JSON once the stream ends.

```python
tool_calls = {}                       # index → {id, name, arguments}

for chunk in stream:
    for tc in chunk.choices[0].delta.tool_calls or []:
        entry = tool_calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
        if tc.id:
            entry["id"] = tc.id
        if tc.function.name:
            entry["name"] = tc.function.name
        if tc.function.arguments:
            entry["arguments"] += tc.function.arguments

# After the stream: json.loads(entry["arguments"]) for each call
```

### Chat mode

A `while True` loop that reads input, runs the agent, prints the answer, and exits on `exit`. Use **prompt_toolkit** for `@` file autocomplete.

---

## Phase 7: Polish

- Write tests for all tools
- Add a demo screenshot or GIF to the README
- Write a short Limitations section
- Test a fresh clone: follow your own install steps

---

## Common Mistakes

| Mistake                       | Fix                                        |
| ----------------------------- | ------------------------------------------ |
| Tool crashes the whole loop   | Catch errors and return them as text       |
| Model edits the wrong place   | Make `edit_file` require exactly one match |
| Agent loops forever           | Set `MAX_STEPS`                            |
| Context gets too big          | Truncate output and compact history        |
| Tool-call JSON fails to parse | Join all streamed chunks before parsing    |
| Provider SDK used everywhere  | Import it only in `llm.py`                 |

---

## Ideas for Next Steps

- Run commands in a sandbox (Docker) instead of your machine
- Show a diff preview before edits and add undo
- Add retries for rate limits and network errors
- Track token usage and cost
- Support more providers
- Wrap `agent.py` in a web API for a cloud agent
