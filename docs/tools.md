# Tools

Tools are external capabilities that agents can use. Each tool is a YAML file in `.glee/tools/` that contains **everything** the agent needs to understand and use an API.

**Key sections:**
- `name`, `description` - What the tool does
- `parameters` - Input parameters with types, descriptions, and `category`:
  - `path` - URL path params: `/repos/${repo}/issues`
  - `query` - Query string: `?q=${query}&count=${count}`
  - `hash` - URL fragment: `#${section}` (for SPAs, browser automation)
  - `body` - Request body (POST/PUT)
  - `header` - HTTP headers
- `api` - How to call the external API (endpoint, method, headers, body)
- `response` - How to parse the response
- `secrets` - Credentials (can reference env vars)
- `examples` - **Critical** - Concrete usage examples help agents understand how to use the tool

## Tool Definition Format

```yaml
# .glee/tools/web-search.yml
name: web_search
description: Search the web for information using Brave Search API

# What the agent sees and can use
parameters:
  - name: query
    type: string
    description: The search query
    category: query  # url | query | body | header
    required: true
  - name: count
    type: integer
    description: Number of results to return
    category: query
    default: 10
  - name: freshness
    type: string
    description: Time filter (day, week, month, year)
    category: query
    required: false

# How to call the API
api:
  endpoint: https://api.search.brave.com/res/v1/web/search
  method: GET
  headers:
    Accept: application/json
    X-Subscription-Token: ${BRAVE_API_KEY}
  query_params:
    q: ${query}
    count: ${count}
    freshness: ${freshness}

# How to parse the response
response:
  results_path: web.results
  fields:
    - name: title
      path: title
    - name: url
      path: url
    - name: description
      path: description

# Credentials (can reference env vars or secrets)
secrets:
  BRAVE_API_KEY: ${env:BRAVE_API_KEY}

# Examples - critical for agents to understand usage
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
# .glee/tools/github-issues.yml
name: github_issues
description: List or create GitHub issues

parameters:
  - name: action
    type: string
    enum: [list, create, get]
    category: path  # path | query | hash | body | header
    required: true
  - name: repo
    type: string
    description: Repository in format owner/repo
    category: path
    required: true
  - name: title
    type: string
    description: Issue title (for create)
    category: body
  - name: body
    type: string
    description: Issue body (for create)
    category: body

api:
  base_url: https://api.github.com
  endpoints:
    list:
      path: /repos/${repo}/issues
      method: GET
    create:
      path: /repos/${repo}/issues
      method: POST
      body:
        title: ${title}
        body: ${body}
    get:
      path: /repos/${repo}/issues/${issue_number}
      method: GET
  headers:
    Authorization: Bearer ${GITHUB_TOKEN}
    Accept: application/vnd.github+json

secrets:
  GITHUB_TOKEN: ${env:GITHUB_TOKEN}

examples:
  - description: List open issues in a repo
    params:
      action: list
      repo: "anthropics/claude-code"
    expected_output: |
      [{"number": 123, "title": "Bug in parsing", "state": "open"}, ...]

  - description: Create a new issue
    params:
      action: create
      repo: "myorg/myrepo"
      title: "Add dark mode support"
      body: "Users have requested dark mode..."
    expected_output: |
      {"number": 456, "title": "Add dark mode support", "html_url": "https://github.com/myorg/myrepo/issues/456"}
```

```yaml
# .glee/tools/slack-notify.yml
name: slack_notify
description: Send a message to a Slack channel

parameters:
  - name: channel
    type: string
    description: Channel name or ID
    category: body
    required: true
  - name: message
    type: string
    description: Message text
    category: body
    required: true
  - name: thread_ts
    type: string
    description: Thread timestamp (for replies)
    category: body

api:
  endpoint: https://slack.com/api/chat.postMessage
  method: POST
  headers:
    Authorization: Bearer ${SLACK_BOT_TOKEN}
    Content-Type: application/json
  body:
    channel: ${channel}
    text: ${message}
    thread_ts: ${thread_ts}

secrets:
  SLACK_BOT_TOKEN: ${env:SLACK_BOT_TOKEN}

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

## How Agents Use Tools

1. Agent reads tool definition (name, description, parameters)
2. Agent decides to use tool based on task
3. Agent generates parameter values
4. Glee executes the API call using the `api` section
5. Glee parses response using the `response` section
6. Agent receives clean result

```
Agent: "I need to search for Python frameworks"
    ↓ reads .glee/tools/web-search.yml
Agent: "I'll use web_search with query='best python frameworks'"
    ↓ glee_tool(name="web_search", params={query: "best python frameworks"})
Glee: executes HTTP request to Brave API
    ↓ parses response
Agent: receives [{title, url, description}, ...]
```

## Directory Structure

```
.glee/
├── config.yml
├── agents/           # Reusable workers
├── workflows/        # Orchestration
├── tools/            # External APIs
│   ├── web-search.yml
│   ├── github-issues.yml
│   ├── slack-notify.yml
│   └── ...
└── sessions/
```

## AI-Native Tool Creation

Agents can also **create new tools**. If an agent needs to use an API that doesn't have a tool definition, it can:

1. Read the API documentation (via web search or provided docs)
2. Create a new `.glee/tools/*.yml` file
3. Use the new tool

This enables fully autonomous operation — agents aren't limited to pre-defined tools.

## MCP Tools

### `glee_tool`

Execute a tool defined in `.glee/tools/`:

```python
glee_tool(
    name="web_search",              # Tool name (matches .glee/tools/{name}.yml)
    params={                         # Parameters for the tool
        "query": "best python frameworks",
        "count": 5
    }
)
# Returns: [{"title": "...", "url": "...", "description": "..."}, ...]
```

### `glee_tool_create`

Create a new tool definition (AI-native):

```python
glee_tool_create(
    name="weather",
    definition={
        "description": "Get current weather for a location",
        "parameters": [...],
        "api": {...},
        "secrets": {...}
    }
)
# Creates .glee/tools/weather.yml
```

### `glee_tools_list`

List available tools:

```python
glee_tools_list()
# Returns:
# [
#   {"name": "web_search", "description": "Search the web..."},
#   {"name": "github_issues", "description": "List or create GitHub issues"},
#   {"name": "slack_notify", "description": "Send a message to Slack"}
# ]
```

## Implementation

### Phase 3: Tools (v0.5)
- [ ] `.glee/tools/*.yml` format
- [ ] `glee_tool` MCP tool (execute tools)
- [ ] `glee_tool_create` MCP tool (AI creates tools)
- [ ] `glee_tools_list` MCP tool
- [ ] Built-in tools: web_search, http_request
