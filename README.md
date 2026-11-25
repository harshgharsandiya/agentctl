# agentctl

A simple CLI coding agent that reads, edits, and runs code from your terminal.

> 🚧 Early development

## How it works

You give a task. The agent thinks, uses a tool, checks the result, and repeats until done.

```
Task → LLM → Tool call → Result → LLM → ... → Done
```

## Core Concepts

- **LLM Calling:** one provider, one model
- **Agent loop:** runs until done, with a max-iterations limit
- **Tools:** read, write, edit, list, search, run command
- **Context History:** kept in memory, saved to JSON
- **Streaming Response:** see the output live
- **Interaction Mode:** one-shot and interactive chat

## Tools

| Tool | What it does |
|---|---|
| `read_file` | Read a file |
| `write_file` | Create or overwrite a file |
| `edit_file` | Replace text in a file |
| `list_files` | List files in a folder |
| `search_files` | Search text across the project |
| `run_command` | Run a shell command |

## Usage

```bash
# One-shot
agentctl "add a function to utils.py and run the tests"

# Interactive chat
agentctl chat
```

## Safety

- File access stays inside the project folder
- Asks for your approval before writing files or running commands

## Roadmap

- [ ] Call the LLM
- [ ] CLI skeleton
- [ ] Agent loop + `read_file`
- [ ] Remaining tools
- [ ] Context history (JSON)
- [ ] Streaming
- [ ] Interactive chat mode

## License

MIT