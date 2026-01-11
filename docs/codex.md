# Codex Integration

This document explains how Glee connects to OpenAI Codex and compares it with OpenCode's approach.

## Background: Third-Party CLI Access to Codex

OpenAI now officially supports third-party CLI tools connecting to Codex. The [Codex authentication documentation](https://developers.openai.com/codex/auth/) describes two primary methods:

1. **ChatGPT OAuth Login** - Opens a browser for OAuth flow, returns access token
2. **API Key Authentication** - Direct API key from OpenAI dashboard

For headless environments, OpenAI provides:
- **Device Code Authentication** (beta) - Run `codex login --device-auth` after enabling in ChatGPT settings
- **Credential Transfer** - Copy `~/.codex/auth.json` between machines

## Glee's Approach: CLI Subprocess

Glee uses a simple subprocess-based approach to invoke Codex:

```
glee/agents/codex.py
```

### How It Works

1. **CLI Invocation**: Glee spawns the `codex` CLI as a subprocess
2. **Command Format**: `codex exec --json --full-auto "<prompt>"`
3. **Output Parsing**: Parses JSONL output to extract agent responses

```python
args = [
    self.command,  # "codex"
    "exec",
    "--json",
    "--full-auto",
    prompt,
]
result = self._run_subprocess(args, prompt=prompt, timeout=timeout)
```

### Key Design Decisions

- **Relies on local Codex CLI**: User must have `codex` installed and authenticated
- **Uses `--full-auto` mode**: Runs non-interactively without user approval prompts
- **JSON output**: Parses structured JSONL for programmatic access
- **Streaming support**: Can stream output in real-time via `_run_subprocess_streaming`

### Pros
- Simple to implement and maintain
- Leverages existing Codex CLI authentication
- No need to manage OAuth tokens directly
- Works with any Codex authentication method the user has configured

### Cons
- Requires Codex CLI to be installed separately
- Depends on CLI output format stability
- Less control over the underlying API interactions

## OpenCode's Approach: Direct OAuth API

OpenCode takes a fundamentally different approach by implementing OAuth authentication directly and calling the Codex API:

```
packages/opencode/src/plugin/codex.ts
```

### How It Works

1. **OAuth Flow**: Implements full PKCE OAuth flow with OpenAI's auth server
2. **Token Management**: Handles access/refresh tokens, automatic refresh
3. **Direct API Calls**: Routes requests to `https://chatgpt.com/backend-api/codex/responses`

```typescript
const CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
const ISSUER = "https://auth.openai.com"
const CODEX_API_ENDPOINT = "https://chatgpt.com/backend-api/codex/responses"
```

### OAuth Implementation Details

1. **Local OAuth Server**: Starts HTTP server on port 1455 for callback
2. **PKCE Challenge**: Generates code verifier/challenge for security
3. **Browser Authorization**: Opens `https://auth.openai.com/oauth/authorize` with params:
   - `client_id`: OpenCode's registered client ID
   - `scope`: `openid profile email offline_access`
   - `codex_cli_simplified_flow`: true
   - `originator`: "opencode"
4. **Token Exchange**: Exchanges authorization code for tokens
5. **Account ID Extraction**: Parses JWT claims for `chatgpt_account_id`

### Request Routing

OpenCode intercepts API requests and rewrites them:

```typescript
// Rewrite URL to Codex endpoint
const url = parsed.pathname.includes("/v1/responses") ||
            parsed.pathname.includes("/chat/completions")
  ? new URL(CODEX_API_ENDPOINT)
  : parsed

// Set authorization header with access token
headers.set("authorization", `Bearer ${currentAuth.access}`)

// Set ChatGPT-Account-Id header for organization subscriptions
if (authWithAccount.accountId) {
  headers.set("ChatGPT-Account-Id", authWithAccount.accountId)
}
```

### Supported Models (via OAuth)

OpenCode filters to specific Codex models for OAuth users:
- `gpt-5.1-codex-max`
- `gpt-5.1-codex-mini`
- `gpt-5.2`
- `gpt-5.2-codex`

### Pros
- No external CLI dependency
- Full control over authentication and API calls
- Can integrate deeply with OpenCode's model/provider system
- Supports ChatGPT Pro/Plus subscription (no API costs)

### Cons
- Complex OAuth implementation to maintain
- Must track OpenAI's authentication changes
- Requires registered client ID

## Comparison Summary

| Aspect | Glee (CLI) | Glee (Direct) | OpenCode |
|--------|------------|---------------|----------|
| **Connection Method** | CLI subprocess | Direct OAuth API | Direct OAuth API |
| **Setup Command** | `codex login` | `glee connect codex` | `/connect` |
| **Authentication** | Delegates to Codex CLI | Custom OAuth | Custom OAuth |
| **Dependency** | Requires `codex` CLI | Self-contained | Self-contained |
| **API Endpoint** | N/A (uses CLI) | Codex backend API | Codex backend API |
| **Token Management** | Handled by Codex CLI | Glee manages | OpenCode manages |
| **Subscription Support** | Any (via CLI) | ChatGPT Pro/Plus | ChatGPT Pro/Plus |

## Glee Direct Connection

Glee supports direct OAuth connection to Codex (similar to OpenCode's approach):

```bash
glee connect codex
```

This command:
1. Starts a local OAuth server for the callback
2. Opens browser for ChatGPT authentication
3. Exchanges authorization code for tokens
4. Stores credentials in `.glee/auth/codex.json`

### Implementation Requirements

To implement this, Glee needs:
1. OAuth PKCE flow similar to OpenCode
2. Token storage and automatic refresh
3. Direct HTTP calls to Codex API endpoint (`chatgpt.com/backend-api/codex/responses`)

## References

- [OpenAI Codex CLI](https://developers.openai.com/codex/cli/)
- [OpenAI Codex Authentication](https://developers.openai.com/codex/auth/)
- [OpenAI Codex SDK](https://developers.openai.com/codex/sdk/)
- [OpenCode Codex Plugin](https://github.com/opencode/opencode)
- [Third-party OAuth Plugin Example](https://github.com/numman-ali/opencode-openai-codex-auth)
