# Tools

Tools are external capabilities that agents can use. Each tool is defined by a YAML manifest in `.glee/tools/<tool_name>/tool.yml` that contains everything the agent needs to understand and execute a capability (HTTP API, shell command, or Python function).

Unlike Claude Code skills, Glee tools are reusable across agents and workflows. The tool definition is the single, shared interface.

Tools are directories, not single files. This keeps manifests clean and allows supporting materials (scripts, assets, templates) to live alongside the tool.

**Naming:** Directory name must match `name` in `tool.yml` and must be a valid directory name (no enforced casing).

**Key sections:**
- `name`, `description`, `kind`, `version` - Identity and tool type
- `inputs.schema` - JSON Schema for all inputs
- `outputs` - Output format and optional JSON Schema
- `exec` - Execution details for exactly one of: `http`, `command`, `python`
- `permissions` - Network, filesystem, and secrets access (secrets map uses typed entries; values are read from env vars with the same key)
- `approval` - Whether user approval is required (`reason` only needed when `required: true`)
- `examples` - Concrete usage examples help agents understand how to use the tool

Inputs schema (JSON Schema 2020-12):

```yaml
inputs:
  schema:
    type: object
    additionalProperties: false
    required: [query]
    properties:
      query:
        type: string
      count:
        type: integer
        default: 10
      freshness:
        type: string
```

Outputs schema (JSON Schema 2020-12):

```yaml
outputs:
  format: json
  schema:
    type: array
    items:
      type: object
      additionalProperties: false
      required: [title, url, description]
      properties:
        title: {type: string}
        url: {type: string}
        description: {type: string}
```

Glee validates inputs against `inputs.schema` before execution. If `outputs.schema` is provided, Glee validates outputs after execution; otherwise, the raw output is returned as-is.

Permissions schema:

```yaml
permissions:
  network: false
  fs:
    read: ["."]
    write: []
  secrets:
    BRAVE_API_KEY:
      type: string
      required: true
```

Notes:
- `permissions.fs.read` and `permissions.fs.write` entries are resolved from the project root (the directory containing `.glee/`) when relative paths are used.

Secret resolution:

```text
Glee reads secrets from environment variables by name.
If a secret is listed in permissions, it must exist in env.
```


## Tool Definition Format

```yaml
# .glee/tools/web_search/tool.yml
name: web_search
description: Search the web for information using Brave Search API
kind: http
version: 1

inputs:
  schema:
    type: object
    additionalProperties: false
    required: [query]
    properties:
      query:
        type: string
        description: The search query
      count:
        type: integer
        description: Number of results to return
        default: 10
      freshness:
        type: string
        description: Time filter (day, week, month, year)

outputs:
  format: json
  schema:
    type: array
    items:
      type: object
      additionalProperties: false
      required: [title, url, description]
      properties:
        title: {type: string}
        url: {type: string}
        description: {type: string}

exec:
  http:
    method: GET
    url: https://api.search.brave.com/res/v1/web/search
    headers:
      Accept: application/json
      X-Subscription-Token: ${BRAVE_API_KEY}
    query:
      q: ${query}
      count: ${count}
      freshness: ${freshness}
    response:
      json_path: web.results
      fields:
        - name: title
          path: title
        - name: url
          path: url
        - name: description
          path: description

permissions:
  network: true
  fs:
    read: []
    write: []
  secrets:
    BRAVE_API_KEY:
      type: string
      required: true

approval:
  required: true
  reason: Accesses external API with secrets

examples:
  - description: Search for Python web frameworks
    params:
      query: "best python web frameworks 2025"
      count: 5
    expected_output: |
      [
        {"title": "FastAPI - Modern Python Framework", "url": "https://fastapi.tiangolo.com", "description": "..."},
        {"title": "Django - The Web Framework for Perfectionists", "url": "https://djangoproject.com", "description": "..."}
      ]

  - description: Search for recent AI news
    params:
      query: "artificial intelligence news"
      count: 10
      freshness: "week"
    expected_output: |
      [{"title": "...", "url": "...", "description": "..."}, ...]
```

## More Examples

```yaml
# .glee/tools/slack_notify/tool.yml
name: slack_notify
description: Send a message to a Slack channel
kind: http
version: 1

inputs:
  schema:
    type: object
    additionalProperties: false
    required: [channel, message]
    properties:
      channel:
        type: string
        description: Channel name or ID
      message:
        type: string
        description: Message text
      thread_ts:
        type: string
        description: Thread timestamp (for replies)

outputs:
  format: json

exec:
  http:
    method: POST
    url: https://slack.com/api/chat.postMessage
    headers:
      Authorization: Bearer ${SLACK_BOT_TOKEN}
      Content-Type: application/json
    body:
      channel: ${channel}
      text: ${message}
      thread_ts: ${thread_ts}

permissions:
  network: true
  fs:
    read: []
    write: []
  secrets:
    SLACK_BOT_TOKEN:
      type: string
      required: true

approval:
  required: true
  reason: Sends messages to external service

examples:
  - description: Send a notification to #general
    params:
      channel: "general"
      message: "Deployment complete! v2.0.0 is now live."
    expected_output: |
      {"ok": true, "ts": "1234567890.123456"}

  - description: Reply in a thread
    params:
      channel: "C1234567890"
      message: "Fixed in the latest commit."
      thread_ts: "1234567890.123456"
    expected_output: |
      {"ok": true, "ts": "1234567890.789012"}
```

```yaml
# .glee/tools/repo_scan/tool.yml
name: repo_scan
description: Scan repo for TODOs
kind: command
version: 1

inputs:
  schema:
    type: object
    additionalProperties: false
    properties:
      path:
        type: string
        description: Directory to scan
        default: "."

outputs:
  format: text

exec:
  command:
    entrypoint: ./scripts/scan_todos.sh
    args: ["${path}"]
    cwd: .
    stdout:
      format: text
    exit_codes_ok: [0]
    timeout_ms: 30000

permissions:
  network: false
  fs:
    read: ["."]
    write: []
  secrets: {}

approval:
  required: false

examples:
  - description: Scan current repo
    params:
      path: "."
    expected_output: |
      Scan complete.
      Matches found: 2
```

```yaml
# .glee/tools/repo_stats/tool.yml
name: repo_stats
description: Compute repo stats (files, LOC)
kind: python
version: 1

inputs:
  schema:
    type: object
    additionalProperties: false
    properties:
      path:
        type: string
        description: Directory to analyze
        default: "."

outputs:
  format: json

exec:
  python:
    module: tools.repo_stats
    function: run
    args: ["${path}"]
    venv: .venv
    cwd: .
    return: json
    timeout_ms: 30000

permissions:
  network: false
  fs:
    read: ["."]
    write: []
  secrets: {}

approval:
  required: false

examples:
  - description: Get stats for current repo
    params:
      path: "."
    expected_output: |
      {"files": 120, "loc": 15342}
```

## How Agents Use Tools

1. Agent reads tool definition (name, description, inputs.schema, kind)
2. Agent decides to use tool based on task
3. Agent generates input values (validated against `inputs.schema`)
4. Glee executes the tool using the `exec` block for its `kind`
5. Glee validates and normalizes output using the `outputs` section
6. Agent receives clean result

```
Agent: "I need to search for Python frameworks"
    -> reads .glee/tools/web_search/tool.yml
Agent: "I'll use web_search with query='best python frameworks'"
    -> glee_tool(name="web_search", params={query: "best python frameworks"})
Glee: executes HTTP request to Brave API
    -> parses response
Agent: receives [{title, url, description}, ...]
```

## Error Handling

Glee handles errors at each execution stage:

| Error Type | Behavior |
|------------|----------|
| Input validation fails | Returns error with schema violations, tool not executed |
| HTTP request fails (network/timeout) | Returns error with status code and message |
| Command exits with code not in `exit_codes_ok` | Returns error with exit code and stderr |
| Python function raises exception | Returns error with exception type and message |
| Timeout exceeded | Process killed, returns timeout error |
| Output validation fails | Returns warning (output still returned) |
| Secret not found in environment | Returns error, tool not executed |

Agents receive structured error responses they can use to retry, fallback, or report to the user.

## HTTP Response Handling

For `kind: http` tools, response processing works as follows:

- **`response.json_path`:** If set, extracts a nested value (e.g., `web.results` extracts `response["web"]["results"]`) and uses it as the response body for any further processing.
- **`response.fields`:** Optional projection step that defines the final output shape. Each entry has a `name` (output key) and a `path` (where to read the value from in the current response body). If the response body is a list, the mapping is applied to each item and returns a list of mapped objects.
- **Default behavior:** If `response.json_path` is not set, the raw JSON response body is used. If `response.fields` is not set, the current response body is returned as-is.

Example (project each item to `{title, url}`):

```yaml
exec:
  http:
    response:
      json_path: web.results
      fields:
        - name: title
          path: title
        - name: url
          path: url
```

Input JSON (excerpt) and output:

```json
// Raw response body
{"web":{"results":[{"title":"A","url":"https://a","description":"..."}]}}
```

```json
// After json_path: web.results
[{"title":"A","url":"https://a","description":"..."}]
```

```json
// After fields mapping
[{"title":"A","url":"https://a"}]
```

## Tool Storage and Discovery

Glee loads tools from `.glee/tools/<tool_name>/tool.yml`.

All relative paths in tool manifests are resolved from the project root (the directory containing `.glee/`). This includes `exec.command.entrypoint`, `exec.command.cwd`, `exec.python.cwd`, `exec.python.venv`, and `permissions.fs.*`. Absolute paths are honored.

Tool directories can include supporting materials next to the manifest:

```
.glee/
└── tools/
    └── web_search/
        ├── tool.yml
        ├── scripts/
        ├── assets/
        └── README.md
```

## Directory Structure

```
.glee/
├── config.yml
├── agents/           # Reusable workers
├── workflows/        # Orchestration
├── tools/            # Tools (HTTP, command, python)
│   ├── web_search/
│   ├── repo_scan/
│   ├── repo_stats/
│   ├── slack_notify/
│   └── ...
└── sessions/
```

## Schema and Linting

Tool manifest schema: `glee/schemas/tool.schema.json`

Lint tools under a project root:

```bash
glee lint
# or
glee lint --root path/to/project
```

## AI-Native Tool Creation

Agents can also **create new tools**. If an agent needs a capability that doesn't have a tool definition, it can:

1. Read the relevant documentation (API, CLI, or script) via web search or provided docs
2. Create a new manifest in `.glee/tools/<name>/tool.yml`
3. Use the new tool

This enables fully autonomous operation - agents aren't limited to pre-defined tools.

## MCP Tools

### `glee_tool`

Execute a tool defined in `.glee/tools/`:

```python
glee_tool(
    name="web_search",              # Tool name (matches .glee/tools/{name}/tool.yml)
    params={                         # Parameters for the tool
        "query": "best python frameworks",
        "count": 5
    }
)
# Returns: [{"title": "...", "url": "...", "description": "..."}, ...]
```

### `glee_tool_create`

Create a new tool definition (AI-native). The `definition` follows the same structure as `tool.yml`:

```python
glee_tool_create(
    name="weather",
    definition={
        "description": "Get current weather for a location",
        "kind": "http",
        "version": 1,
        "inputs": {
            "schema": {
                "type": "object",
                "required": ["location"],
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                }
            }
        },
        "outputs": {"format": "json"},
        "exec": {
            "http": {
                "method": "GET",
                "url": "https://api.weather.com/v1/current",
                "query": {"q": "${location}"},
                "headers": {"Authorization": "Bearer ${WEATHER_API_KEY}"}
            }
        },
        "permissions": {
            "network": True,
            "fs": {"read": [], "write": []},
            "secrets": {"WEATHER_API_KEY": {"type": "string", "required": True}}
        },
        "approval": {"required": True, "reason": "Accesses external API"}
    }
)
# Creates .glee/tools/weather/tool.yml
```

### `glee_tools_list`

List available tools:

```python
glee_tools_list()
# Returns:
# [
#   {"name": "web_search", "description": "Search the web..."},
#   {"name": "repo_scan", "description": "Scan repo for TODOs"},
#   {"name": "slack_notify", "description": "Send a message to Slack"}
# ]
```

---

## Roadmap

> **Note:** This section tracks implementation progress. See also: [subagents.md](subagents.md), [workflows.md](workflows.md).

### Phase 1: glee_task (v0.3) ✓
- [x] Design docs (subagents.md, workflows.md, tools.md)
- [x] `glee_task` MCP tool - spawn CLI agents (codex, claude, gemini)
- [x] Session management (generate ID, store context)
- [x] Context injection (AGENTS.md + memories)
- [x] Basic logging to `.glee/stream_logs/`

### Phase 2: Tools (v0.4)
- [ ] Tool manifest format (directory tool.yml)
- [ ] `glee_tool` MCP tool (execute tools)
- [ ] `glee_tool_create` MCP tool (AI creates tools)
- [ ] `glee_tools_list` MCP tool
- [ ] Built-in tools: web_search, http_request

### Phase 3: Agents (v0.5)
- [ ] `.glee/agents/*.yml` format
- [ ] `glee_agent_create` MCP tool (AI creates agents)
- [ ] `glee agents import` from Claude/Gemini formats
- [ ] Agent selection heuristics

### Phase 4: Workflows (v0.6+)
- [ ] `.glee/workflows/*.yml` format
- [ ] `glee_workflow` MCP tool
- [ ] Nested workflows
- [ ] Parallel/DAG execution
