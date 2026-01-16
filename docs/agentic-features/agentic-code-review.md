# Agentic Code Review

> Refactor `glee.review` to use Codex API + native tools instead of CLI subprocess.

## Current State

```
glee review src/
    ↓ subprocess
codex CLI (handles everything: file reading, reasoning, output)
    ↓
Review result
```

**Problem**: We're delegating all agentic capabilities to the CLI. Glee is just a wrapper.

## Target State

```
glee review src/
    ↓
Glee Agent Runtime
    ├── LLM: Codex API (via OAuth)
    ├── Tools: core.file.*, core.git.*
    └── Loop: ReAct (Reason → Act → Observe)
    ↓
Review result
```

**Benefit**: Glee becomes a true agent. We control the tools, the loop, the prompts.

---

## Phase 1: Core Tools Module

### Tool Namespace

Single `core` namespace for native capabilities:

```
glee/core/
├── __init__.py
├── file.py      # File operations
├── git.py       # Git operations
└── shell.py     # Shell execution (sandboxed)
```

### core.file

| Tool | Description |
|------|-------------|
| `core.file.read(path)` | Read file contents |
| `core.file.write(path, content, mode?)` | Write file (overwrite/append) |
| `core.file.list(dir, glob?)` | List directory contents |
| `core.file.search(pattern, root?, limit?)` | Search for files by glob/regex |
| `core.file.stat(path)` | Get file metadata (size, mtime) |

```python
# glee/core/file.py
from pathlib import Path

def read(path: str) -> str:
    """Read file contents."""
    return Path(path).read_text()

def write(path: str, content: str, mode: str = "overwrite") -> None:
    """Write file contents."""
    p = Path(path)
    if mode == "append":
        with open(p, "a") as f:
            f.write(content)
    else:
        p.write_text(content)

def list_dir(dir: str, glob: str = "*") -> list[str]:
    """List directory contents."""
    return [str(p) for p in Path(dir).glob(glob)]

def search(pattern: str, root: str = ".", limit: int = 100) -> list[str]:
    """Search for files matching pattern."""
    results = []
    for p in Path(root).rglob(pattern):
        results.append(str(p))
        if len(results) >= limit:
            break
    return results

def stat(path: str) -> dict:
    """Get file metadata."""
    p = Path(path)
    s = p.stat()
    return {
        "path": str(p),
        "size": s.st_size,
        "mtime": s.st_mtime,
        "is_dir": p.is_dir(),
    }
```

### core.git

| Tool | Description |
|------|-------------|
| `core.git.status()` | Get working tree status |
| `core.git.diff(ref?, staged?)` | Get diff output |
| `core.git.log(limit?)` | Get recent commits |
| `core.git.show(ref)` | Show commit details |

```python
# glee/core/git.py
import subprocess

def _run(args: list[str], cwd: str = ".") -> str:
    """Run git command and return output."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr}")
    return result.stdout

def status(cwd: str = ".") -> str:
    """Get working tree status."""
    return _run(["status", "--porcelain"], cwd)

def diff(ref: str | None = None, staged: bool = False, cwd: str = ".") -> str:
    """Get diff output."""
    args = ["diff"]
    if staged:
        args.append("--staged")
    if ref:
        args.append(ref)
    return _run(args, cwd)

def log(limit: int = 10, cwd: str = ".") -> str:
    """Get recent commits."""
    return _run(["log", f"-{limit}", "--oneline"], cwd)

def show(ref: str, cwd: str = ".") -> str:
    """Show commit details."""
    return _run(["show", ref], cwd)
```

### core.shell (Sandboxed)

| Tool | Description |
|------|-------------|
| `core.shell.run(cmd, cwd?, timeout?)` | Run allowed command |

```python
# glee/core/shell.py
import subprocess

# Allowlist of safe commands
ALLOWED_COMMANDS = {
    "npm": ["test", "run", "build", "lint"],
    "yarn": ["test", "run", "build", "lint"],
    "pnpm": ["test", "run", "build", "lint"],
    "pytest": [],
    "ruff": ["check", "format"],
    "mypy": [],
    "eslint": [],
    "prettier": ["--check"],
}

def run(
    cmd: str,
    cwd: str = ".",
    timeout: int = 60,
) -> dict:
    """Run a sandboxed shell command."""
    parts = cmd.split()
    if not parts:
        raise ValueError("Empty command")

    binary = parts[0]
    if binary not in ALLOWED_COMMANDS:
        raise PermissionError(f"Command not allowed: {binary}")

    # Check subcommand if applicable
    allowed_subs = ALLOWED_COMMANDS[binary]
    if allowed_subs and len(parts) > 1:
        if parts[1] not in allowed_subs:
            raise PermissionError(f"Subcommand not allowed: {parts[1]}")

    result = subprocess.run(
        parts,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
```

---

## Phase 2: Tool Executor

The tool executor provides a unified interface for the agent to call tools.

```python
# glee/core/executor.py
from typing import Any
from glee.core import file, git, shell

# Tool registry
TOOLS = {
    "core.file.read": file.read,
    "core.file.write": file.write,
    "core.file.list": file.list_dir,
    "core.file.search": file.search,
    "core.file.stat": file.stat,
    "core.git.status": git.status,
    "core.git.diff": git.diff,
    "core.git.log": git.log,
    "core.git.show": git.show,
    "core.shell.run": shell.run,
}

def execute(tool_name: str, **kwargs: Any) -> Any:
    """Execute a tool by name."""
    if tool_name not in TOOLS:
        raise ValueError(f"Unknown tool: {tool_name}")
    return TOOLS[tool_name](**kwargs)

def get_tool_schemas() -> list[dict]:
    """Get tool schemas for LLM function calling."""
    return [
        {
            "type": "function",
            "function": {
                "name": "core.file.read",
                "description": "Read file contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to read"}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "core.file.list",
                "description": "List directory contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dir": {"type": "string", "description": "Directory path"},
                        "glob": {"type": "string", "description": "Glob pattern (default: *)"}
                    },
                    "required": ["dir"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "core.file.search",
                "description": "Search for files matching pattern",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "Glob pattern to search"},
                        "root": {"type": "string", "description": "Root directory (default: .)"},
                        "limit": {"type": "integer", "description": "Max results (default: 100)"}
                    },
                    "required": ["pattern"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "core.git.status",
                "description": "Get git working tree status",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cwd": {"type": "string", "description": "Repository path (default: .)"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "core.git.diff",
                "description": "Get git diff output",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ref": {"type": "string", "description": "Git ref to diff against"},
                        "staged": {"type": "boolean", "description": "Show staged changes only"},
                        "cwd": {"type": "string", "description": "Repository path (default: .)"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "core.git.log",
                "description": "Get recent git commits",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Number of commits (default: 10)"},
                        "cwd": {"type": "string", "description": "Repository path (default: .)"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "core.shell.run",
                "description": "Run a sandboxed shell command (allowlist only)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cmd": {"type": "string", "description": "Command to run"},
                        "cwd": {"type": "string", "description": "Working directory"},
                        "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)"}
                    },
                    "required": ["cmd"]
                }
            }
        },
    ]
```

---

## Phase 3: Codex API Client

Use the OAuth tokens to call Codex API directly.

```python
# glee/providers/codex.py
import httpx
import time
from glee.auth.storage import get_credentials, save_credentials, OAuthCredentials
from glee.auth.codex import refresh_access_token

# ChatGPT backend API (what Codex CLI uses)
CODEX_API_URL = "https://chatgpt.com/backend-api/codex/responses"

async def get_valid_token() -> tuple[str, str | None]:
    """Get a valid access token, refreshing if needed.

    Returns:
        Tuple of (access_token, account_id)
    """
    creds = get_credentials("codex")
    if not isinstance(creds, OAuthCredentials):
        raise ValueError("Codex OAuth not configured. Run: glee oauth codex")

    if creds.is_expired():
        new_tokens = await refresh_access_token(creds.refresh_token)
        if new_tokens is None:
            raise ValueError("Token refresh failed. Run: glee oauth codex")

        # Save refreshed tokens
        new_creds = OAuthCredentials(
            access_token=new_tokens.access_token,
            refresh_token=new_tokens.refresh_token,
            expires_at=int(time.time()) + new_tokens.expires_in,
            account_id=creds.account_id,
        )
        save_credentials("codex", new_creds)
        return new_tokens.access_token, creds.account_id

    return creds.access_token, creds.account_id

async def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str = "gpt-4o",
) -> dict:
    """Send chat completion request to Codex API."""
    token, account_id = await get_valid_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "originator": "codex_cli_rs",
    }
    if account_id:
        headers["chatgpt-account-id"] = account_id

    body = {
        "model": model,
        "messages": messages,
    }
    if tools:
        body["tools"] = tools

    async with httpx.AsyncClient() as client:
        response = await client.post(
            CODEX_API_URL,
            headers=headers,
            json=body,
            timeout=120,
        )
        response.raise_for_status()
        return response.json()
```

---

## Phase 4: Agent Loop (ReAct)

The agent loop implements the ReAct pattern: Reason → Act → Observe.

```python
# glee/agent/loop.py
import json
from typing import Any
from glee.providers import codex
from glee.core.executor import execute, get_tool_schemas

MAX_ITERATIONS = 20

SYSTEM_PROMPT = """You are a code review agent. You have access to these tools:

- core.file.read: Read file contents
- core.file.list: List directory contents
- core.file.search: Search for files by pattern
- core.git.status: Get git working tree status
- core.git.diff: Get git diff output
- core.git.log: Get recent commits

Your task is to review code and provide actionable feedback on:
1. Code quality and readability
2. Potential bugs or issues
3. Security concerns
4. Performance considerations
5. Best practices

Be specific. Reference line numbers. Suggest fixes."""

async def run_agent(
    task: str,
    context: list[str] | None = None,
) -> dict:
    """Run the agent loop for a task."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    # Add context files if provided
    if context:
        for path in context:
            try:
                content = execute("core.file.read", path=path)
                messages.append({
                    "role": "user",
                    "content": f"File: {path}\n```\n{content}\n```"
                })
            except Exception as e:
                messages.append({
                    "role": "user",
                    "content": f"Failed to read {path}: {e}"
                })

    tools = get_tool_schemas()
    iterations = 0

    for i in range(MAX_ITERATIONS):
        iterations = i + 1

        # REASON: Ask LLM what to do
        response = await codex.chat(messages, tools=tools)

        choice = response["choices"][0]
        message = choice["message"]
        messages.append(message)

        # Check if done
        if choice.get("finish_reason") == "stop":
            return {
                "status": "completed",
                "result": message.get("content", ""),
                "iterations": iterations,
            }

        # ACT: Execute tool calls
        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            # No tool calls and not stopped - might be an issue
            return {
                "status": "completed",
                "result": message.get("content", ""),
                "iterations": iterations,
            }

        for tool_call in tool_calls:
            func = tool_call["function"]
            name = func["name"]
            args = json.loads(func["arguments"])

            # Execute tool
            try:
                result = execute(name, **args)
                tool_result = str(result)
            except Exception as e:
                tool_result = f"Error: {e}"

            # OBSERVE: Add result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": tool_result,
            })

    return {
        "status": "max_iterations",
        "result": "Reached maximum iterations",
        "iterations": iterations,
    }
```

---

## Phase 5: Refactored glee.review

Update the CLI and MCP tool to use the agent loop.

```python
# In glee/cli.py - update review command

@app.command()
def review(
    target: str | None = typer.Argument(None),
    focus: str | None = typer.Option(None, "--focus", "-f"),
    agentic: bool = typer.Option(True, "--agentic/--legacy"),
) -> None:
    """Run code review.

    --agentic (default): Use Glee agent with Codex API
    --legacy: Use CLI subprocess (old behavior)
    """
    import asyncio
    from pathlib import Path

    if not agentic:
        # Fall back to old CLI-based review
        _legacy_review(target, focus)
        return

    # Build task
    review_target = target or "."
    task = f"Review the code in: {review_target}"
    if focus:
        task += f"\nFocus on: {focus}"

    # Determine context
    context = []
    if review_target.startswith("git:"):
        task += "\nUse core.git.diff to get the changes."
    elif Path(review_target).is_file():
        context = [review_target]
    else:
        task += f"\nUse core.file.list and core.file.read to explore the directory."

    # Run agent
    from glee.agent.loop import run_agent

    console.print(f"[dim]Running agentic review...[/dim]")
    result = asyncio.run(run_agent(task, context))

    if result["status"] == "completed":
        console.print(result["result"])
    else:
        console.print(f"[yellow]Review ended: {result['status']}[/yellow]")
```

---

## Implementation Order

### Week 1: Core Tools
- [ ] Create `glee/core/__init__.py`
- [ ] Implement `glee/core/file.py`
- [ ] Implement `glee/core/git.py`
- [ ] Implement `glee/core/shell.py`
- [ ] Implement `glee/core/executor.py`
- [ ] Add unit tests

### Week 2: Codex API Client
- [ ] Create `glee/providers/__init__.py`
- [ ] Implement `glee/providers/codex.py`
- [ ] Handle token refresh
- [ ] Test API calls

### Week 3: Agent Loop
- [ ] Create `glee/agent/__init__.py`
- [ ] Implement `glee/agent/loop.py`
- [ ] Test ReAct loop
- [ ] Handle edge cases

### Week 4: Integration
- [ ] Refactor `glee.review` CLI command
- [ ] Update `glee.review` MCP tool
- [ ] Add `--agentic/--legacy` flag
- [ ] End-to-end testing

---

## Future Tool Domains

Once `core` is stable, expand to other domains:

| Domain | Purpose | Tools |
|--------|---------|-------|
| `vcs` | Version control | gh (GitHub API), gitlab |
| `ops` | Operations | docker, process, ports |
| `data` | Databases | sql, kv (redis) |
| `info` | Information | web fetch, search |

Pattern: `{domain}.{resource}.{action}`

---

## Security Considerations

1. **Path sandboxing**: All file operations restricted to project root
2. **Command allowlist**: Only safe commands in `core.shell`
3. **No arbitrary network**: No raw HTTP requests from agent
4. **Timeout limits**: All operations have timeouts
5. **Token security**: OAuth tokens stored with 600 permissions
6. **Confirmation points**: Dangerous operations require user approval

---

## Open Questions

1. **API endpoint**: Use ChatGPT backend API or standard OpenAI API?
   - ChatGPT backend: What Codex CLI uses, same quotas
   - OpenAI API: Standard, but may need API key

2. **Streaming**: Support streaming responses?
   - Better UX for long reviews
   - More complex implementation

3. **Tool format**: Use OpenAI function calling format?
   - Yes: Native support, tested
   - Alternative: Custom format for flexibility

4. **Parallel tool calls**: Handle multiple tool calls in one response?
   - Yes: OpenAI API supports this
   - Implementation: Execute in parallel or sequential?
