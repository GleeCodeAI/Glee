# How CLI Agents Work

This document explains how Glee orchestrates CLI-based AI agents and how those agents perform autonomous "agentic" tasks.

## The Key Insight

**CLI agents like Codex, Claude Code, and Gemini CLI are themselves full-featured agents with built-in tools.** They're not "dumb" CLIs that just return text.

When Glee invokes an agent via subprocess, that agent runs autonomously within its own process, using its own tools (file reading, web search, code execution, etc.).

## Architecture

```
Glee (orchestrator)
    ↓ subprocess call: `codex exec --json --full-auto "prompt"`

Codex CLI (runs as its own process)
    ├── Receives prompt
    ├── Autonomously decides what to do
    ├── Uses ITS OWN built-in tools:
    │   ├── File reading
    │   ├── Code search/grep
    │   ├── Web search
    │   ├── Code execution
    │   └── etc.
    ├── Thinks, acts, observes, repeats
    └── Returns final response

Glee
    ↓ collects output
    ↓ orchestrates next agent
```

## Analogy

Think of it like hiring a contractor:

- **Glee** = Project manager who assigns tasks to contractors
- **Codex/Claude/Gemini** = Skilled contractors with their own toolboxes

The project manager says "review this building's foundation" - they don't hand the contractor individual tools. The contractor shows up with their own equipment and expertise, does the job autonomously, and reports back.

## What Glee Actually Does

Glee doesn't give agents their capabilities. It:

1. **Routes tasks** to the right agent (coder vs reviewer)
2. **Injects context** (shared memory, project info)
3. **Coordinates** multiple agents (parallel reviews)
4. **Aggregates results**

The "agentic stuff" happens entirely within each CLI agent's process. Glee just orchestrates *who* does *what*, not *how* they do it.

## Agent Invocation Examples

### Codex

```bash
codex exec --json --full-auto "prompt"
```

| Flag | What it does |
|------|--------------|
| `exec` | Runs Codex in **agentic mode** (not just chat) |
| `--json` | Outputs structured JSONL for parsing |
| `--full-auto` | **No human confirmation** - Codex autonomously uses tools without asking |

With these flags, Codex will autonomously:
- Read files it needs
- Write/edit code
- Run shell commands
- Search the codebase
- Execute code to test things

### Claude Code

```bash
claude -p "prompt"
```

The `-p` flag runs Claude Code in non-interactive (print) mode.

### Gemini CLI

```bash
gemini -p "prompt"
```

## Debugging and Logging

### Codex

Codex doesn't have a dedicated `--verbose` or `--debug` flag. Options for debugging:

1. **Use `--json`** - Outputs every event as newline-delimited JSON (tool calls, responses, everything)

2. **Configure in `~/.codex/config.toml`**:
   ```toml
   [telemetry]
   exporter = "file"  # or "none", "otlp"

   model_verbosity = "high"  # low | medium | high
   ```

3. **Output to file**:
   ```bash
   codex exec --json --full-auto "prompt" --output-last-message ./debug.txt
   ```

### Claude Code

```bash
claude -p "prompt" --verbose
```

### Gemini CLI

```bash
gemini -p "prompt" --verbosity=verbose
```

## References

- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference/)
- [Codex Config Docs](https://github.com/openai/codex/blob/main/docs/config.md)
