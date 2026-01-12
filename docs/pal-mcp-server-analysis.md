# PAL MCP Server Analysis

This document analyzes the [pal-mcp-server](https://github.com/fahad/pal-mcp-server) project - an MCP server that orchestrates multiple AI models and CLIs for collaborative, multi-model AI development workflows.

**Version analyzed**: 9.8.2

---

## 1. Project Purpose & Goals

PAL MCP (Provider Abstraction Layer - Model Context Protocol) serves as an orchestration layer with several key purposes:

- **Multi-Model Orchestration**: Unite Claude Code, Codex CLI, Gemini CLI with multiple LLM providers (OpenAI, Gemini, X.AI/Grok, Azure, OpenRouter, Ollama, DIAL)
- **Conversation Continuity**: Preserve context across tool switches and model changes
- **Specialized Workflows**: Provide domain-specific tools (code review, debugging, security audits, planning)
- **CLI-to-CLI Bridging (clink)**: Enable subagent orchestration where one CLI can spawn isolated instances of other CLIs
- **Professional AI Collaboration**: Enable multi-model debates, consensus-building, and sequential expertise analysis

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────┐
│   MCP Clients (Claude Code, Codex, etc.) │
└────────────┬────────────────────────────┘
             │ JSON-RPC over stdio
             ▼
┌─────────────────────────────────────────┐
│       server.py (MCP Server Core)        │
│  - Tool registration & discovery         │
│  - Request routing & response handling   │
│  - Provider configuration management     │
└────────────┬────────────────────────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌─────────────────────────────────────────┐
│     Tools Layer (18 specialized tools)   │
│  ├─ SimpleTool: chat, challenge, debug   │
│  ├─ WorkflowTools: codereview, consensus │
│  └─ SpecialTools: clink, apilookup       │
└────────────┬────────────────────────────┘
             │
┌────────────┼────────────────────────────┐
│    Providers (6 model backend systems)   │
│  ├─ GeminiModelProvider (Google)         │
│  ├─ OpenAIModelProvider (OpenAI)         │
│  ├─ AzureOpenAIProvider (Azure)          │
│  ├─ XAIModelProvider (Grok)              │
│  ├─ CustomProvider (Ollama, vLLM, etc)   │
│  └─ OpenRouterProvider (Aggregator)      │
└────────────┬────────────────────────────┘
             │
        ┌────┴────┐
        ▼         ▼
    External AI APIs + Local Models
```

**Key Design Principles:**

- **Stateless MCP Server**: Requests are independent; conversation state tracked externally
- **Plugin Architecture**: Tools and providers are pluggable
- **Provider Priority**: Google > OpenAI > Azure > XAI > DIAL > Custom > OpenRouter
- **Tool Filtering**: `DISABLED_TOOLS` env var controls which tools are active

---

## 3. Technologies & Dependencies

**Core Dependencies:**

```toml
mcp>=1.0.0                    # Model Context Protocol server framework
google-genai>=1.19.0          # Google Gemini API client
openai>=1.55.2                # OpenAI API client
pydantic>=2.0.0               # Data validation & serialization
python-dotenv>=1.0.0          # Environment variable management
```

**Key Technologies:**

- Python 3.9+ (3.12 recommended)
- Asyncio for async I/O
- JSON-RPC 2.0 protocol via MCP
- Logging with rotating file handlers (20MB limits)
- Git integration for changes detection

**Development Tools:**

- **uv**: Package manager
- **Ruff/Black**: Linting and formatting
- **pytest**: Testing with VCR cassettes for HTTP replay

---

## 4. MCP Server Implementation

### Initialization Flow

```python
# server.py entry point
1. Configure logging (rotating file handlers)
2. Configure provider authentication (reads API keys from env)
3. Register enabled providers with ModelProviderRegistry
4. Instantiate all tools (stateless singletons)
5. Apply tool filtering (DISABLED_TOOLS)
6. Initialize MCP server with tool catalog
7. Listen on stdio for JSON-RPC requests
```

### Request Handling

```
1. MCP Client sends JSON-RPC "tools/call" request
2. server.py routes to appropriate tool
3. Tool prepares prompt (validates input, reads files, manages context)
4. Tool calls selected model via ModelProviderRegistry
5. Tool formats response (TextContent with MCP annotations)
6. Response sent back via JSON-RPC
```

### Response Format

```python
ToolOutput:
  - status: "success" | "error" | "partial"
  - content: List[TextContent]
  - continuation_id: Optional[str]  # For resuming conversations
  - conversation_context: Optional[str]  # Previous turns for context revival
  - prompt_size_warning: Optional[str]  # MCP size limit alerts
```

### Configuration

- **`.env` file**: API keys, model defaults, temperature, tool settings
- **Tool enabling**: `DISABLED_TOOLS=analyze,refactor,testgen`
- **Logging**: `LOG_LEVEL=DEBUG`
- **Conversation limits**: `CONVERSATION_TIMEOUT_HOURS=6`, `MAX_CONVERSATION_TURNS=50`

---

## 5. Key Components

### A. Tools (18 specialized tools)

**Collaboration & Planning** (enabled by default):

| Tool | Type | Purpose |
|------|------|---------|
| `chat` | SimpleTool | General development chat with file/image context |
| `clink` | Special | Bridge requests to external CLI agents |
| `thinkdeep` | WorkflowTool | Extended reasoning with configurable thinking modes |
| `planner` | WorkflowTool | Structured project planning |
| `consensus` | WorkflowTool | Multi-model debate/voting with stance-steering |

**Code Analysis & Quality**:

| Tool | Type | Purpose |
|------|------|---------|
| `codereview` | WorkflowTool | Multi-pass code review with severity levels |
| `precommit` | WorkflowTool | Change validation before committing |
| `debug` | WorkflowTool | Root cause analysis with hypothesis tracking |
| `challenge` | SimpleTool | Critical analysis (prevents reflexive agreement) |

**Advanced Tools** (disabled by default):

| Tool | Purpose |
|------|---------|
| `analyze` | Codebase architecture understanding |
| `refactor` | Intelligent code refactoring |
| `testgen` | Test generation with edge cases |
| `secaudit` | Security audits (OWASP Top 10) |
| `docgen` | Documentation generation |
| `tracer` | Static call-flow analysis |

**Tool Architecture:**

```
BaseTool (shared/base_tool.py)
├── Conversation memory integration
├── File reading and token budgeting
├── Model selection and provider routing
└── Response formatting

SimpleTool (simple/base.py)
├── Single-turn model calls
├── Automatic schema generation
└── Used by: chat, challenge

WorkflowTool (workflow/base.py)
├── Multi-step investigation + expert analysis
├── Step tracking (step_number, findings, confidence)
├── CLI-guided investigation phases
└── Used by: codereview, consensus, debug, planner
```

### B. Providers

Abstract provider pattern - each AI backend implements `ModelProvider`:

```python
class ModelProvider(ABC):
    MODEL_CAPABILITIES: dict[str, ModelCapabilities]

    def generate_content(prompt, model_name, ...) -> ModelResponse
    def list_models() -> list[str]
    def get_capabilities(model_name) -> ModelCapabilities
```

**Concrete Providers:**

| Provider | Backend |
|----------|---------|
| `GeminiModelProvider` | Google Gemini API |
| `OpenAIModelProvider` | OpenAI GPT models |
| `AzureOpenAIProvider` | Azure-hosted OpenAI |
| `XAIModelProvider` | X.AI Grok |
| `CustomProvider` | Ollama, vLLM, LM Studio |
| `OpenRouterProvider` | Multi-model aggregator |

**ModelProviderRegistry:**

- Singleton pattern for provider management
- Lazy initialization (only create if API key exists)
- Provider priority ordering for model selection
- Caching of initialized providers

### C. clink: CLI-to-CLI Bridging

Sophisticated system for spawning isolated CLI subagents:

```
┌─────────────────┐
│  Current CLI    │  (e.g., Claude Code)
└────────┬────────┘
         │
      clink tool
         │
    ┌────▼─────────────────────────┐
    │ CLinkRegistry                 │
    │ (conf/cli_clients/*.json)     │
    └────┬──────────────────────────┘
         │
    ┌────▼───────────────────┐
    │ Isolated subprocess CLI │
    │ (fresh context window)  │
    └─────────────────────────┘
```

**Key Features:**

- **Agents** (`clink/agents/`): Claude, Codex, Gemini implementations
- **Parsers** (`clink/parsers/`): Extract structured output from each CLI
- **Role Presets**: Predefined system prompts (planner, codereviewer, default)
- **Response Extraction**: `<SUMMARY>...</SUMMARY>` tags for clean output

**CLI Config Example** (`conf/cli_clients/gemini.json`):

```json
{
  "name": "gemini",
  "command": ["gemini", "code"],
  "roles": {
    "default": { "system_prompt": "..." },
    "planner": { "system_prompt": "..." },
    "codereviewer": { "system_prompt": "..." }
  }
}
```

### D. Conversation Memory

Implements **context revival** - remembering conversations across resets:

```python
ConversationThread:
  - continuation_id: str (UUID)
  - turns: list[ConversationTurn]
  - metadata: {tool_name, timestamp, model, etc}

ConversationTurn:
  - user_message: str
  - assistant_response: str
  - file_references: list[str]
  - metadata: {tool, model, tokens, ...}
```

**Key Operations:**

- `create_thread()` - Start new conversation
- `get_thread(continuation_id)` - Retrieve previous thread
- `add_turn()` - Record interaction
- `reconstruct_thread_context()` - Inject previous turns into new prompts

### E. System Prompts

Rich prompt templates for each tool in `systemprompts/`:

- `CHAT_PROMPT` - Conversational development partner
- `CODEREVIEW_PROMPT` - Multi-pass code review methodology
- `CONSENSUS_PROMPT` - Structured debate facilitator
- `DEBUG_PROMPT` - Systematic root cause analysis
- Model-specific thinking mode instructions

---

## 6. File Structure

```
pal-mcp-server/
├── server.py                 # MCP server core - tool registry, request routing
├── config.py                 # Configuration constants and defaults
├── tools/                    # Tool implementations
│   ├── chat.py, clink.py, consensus.py, codereview.py, debug.py, ...
│   ├── shared/               # Shared tool infrastructure
│   │   ├── base_tool.py      # BaseTool abstract class
│   │   └── base_models.py    # Pydantic models
│   ├── simple/               # SimpleTool base classes
│   │   └── base.py
│   └── workflow/             # WorkflowTool base classes
│       └── base.py
├── providers/                # Model provider implementations
│   ├── base.py, gemini.py, openai.py, azure_openai.py, ...
│   ├── registry.py           # ModelProviderRegistry (singleton)
│   └── shared/               # Provider utilities
├── clink/                    # CLI-to-CLI bridging system
│   ├── registry.py           # CLI configuration loader
│   ├── agents/               # CLI agent implementations
│   └── parsers/              # Response parsing
├── utils/                    # Shared utilities
│   ├── conversation_memory.py
│   ├── file_utils.py
│   └── token_utils.py
├── systemprompts/            # Tool-specific prompts
├── conf/                     # Model registry configurations
│   ├── *_models.json         # Model definitions per provider
│   └── cli_clients/          # CLI client definitions
├── tests/                    # Test suite with VCR cassettes
└── docs/                     # Documentation
```

---

## 7. Interesting Patterns & Design Decisions

### Conversation-Aware File Processing

- Tools transparently access conversation history via `continuation_id`
- Files from previous turns are automatically included
- Prevents context loss when switching tools

### Dual-Layer Tool Architecture

- **SimpleTool**: Lightweight single-turn (chat, challenge)
- **WorkflowTool**: Multi-step investigation + expert analysis (codereview, consensus)
- Both inherit common functionality from BaseTool

### Workflow Pattern

Tools guide the CLI through investigation phases:

```
Step 1: CLI analyzes file X
Step 2: Tool: "Check file Y for related code"
Step 3: CLI: "Found issues in file Y"
Step 4: Tool: "Consulting expert model..."
Step 5: Expert analysis returned
```

### Token-Aware Processing

- Automatic file expansion/truncation based on model token limits
- Graceful degradation when approaching limits
- `estimate_tokens()` utility calculates prompt size upfront

### Model Auto-Selection

When `DEFAULT_MODEL="auto"`, tools pick optimal model based on:

- Task category (analytical vs creative vs balanced)
- Model capabilities (thinking, vision, context window)
- Provider priority order
- Effectiveness ranking formula

### Provider Priority with Namespacing

```python
PROVIDER_PRIORITY_ORDER = [
    GOOGLE,      # Native APIs first
    OPENAI,
    AZURE,
    XAI,
    DIAL,
    CUSTOM,      # Local models
    OPENROUTER,  # Catch-all
]
```

Prevents model name collisions and ensures deterministic routing.

### Logging Strategy

```
logs/mcp_server.log    # Everything (20MB max, 5 backups)
logs/mcp_activity.log  # Tool calls only (10MB max, 2 backups)
```

Size-based rotation prevents unbounded growth.

---

## 8. Configuration System

Key configuration constants from `config.py`:

```python
# Version
__version__ = "9.8.2"

# Model defaults
DEFAULT_MODEL = "auto"  # Claude picks best model per task

# Temperature settings
TEMPERATURE_ANALYTICAL = 1.0   # Code review, debugging
TEMPERATURE_BALANCED = 1.0     # General chat
TEMPERATURE_CREATIVE = 1.0     # Architecture, brainstorming

# MCP transport limits
MCP_PROMPT_SIZE_LIMIT = 25_000  # Chars for MCP transport
MAX_MCP_OUTPUT_TOKENS = 100_000

# Consensus settings
DEFAULT_CONSENSUS_TIMEOUT = 120.0
DEFAULT_CONSENSUS_MAX_INSTANCES_PER_COMBINATION = 2
```

---

## 9. Comparison with Glee

| Aspect | PAL MCP | Glee |
|--------|---------|------|
| **Focus** | Multi-model orchestration via MCP tools | Code review orchestration with memory |
| **Architecture** | Monolithic MCP server with all tools | Lightweight CLI + MCP server |
| **Tools** | 18 specialized tools (chat, codereview, consensus, etc.) | Review, memory, config tools |
| **Model Support** | 7 provider backends (Gemini, OpenAI, Azure, etc.) | Relies on external CLIs (Claude, Codex, Gemini) |
| **CLI Bridging** | clink system spawns subagent CLIs | Direct CLI invocation via subprocess |
| **Memory** | ConversationMemory for context revival | LanceDB + DuckDB for persistent memory |
| **Session Hooks** | None | SessionStart/SessionEnd hooks for context injection |
| **Complexity** | High (18 tools, 7 providers, clink system) | Low (focused on review workflow) |

### Key Takeaways for Glee

1. **Workflow Pattern**: PAL's WorkflowTool concept (multi-step investigation + expert analysis) could enhance Glee's review workflow
2. **Conversation Memory**: The `continuation_id` pattern for context revival is worth considering
3. **Tool Filtering**: `DISABLED_TOOLS` pattern is simple and effective
4. **Prompt Organization**: Dedicated `systemprompts/` directory keeps prompts maintainable
5. **clink Architecture**: The CLI bridging pattern is similar to Glee's agent invocation but more sophisticated

---

## 10. Notable Features

- **Vision Support**: Multiple models support image analysis
- **Extended Thinking**: Models like O1/O3 support thinking tokens for deep reasoning
- **Streaming**: Real-time response streaming where supported
- **Large Prompt Bypass**: Files can be uploaded to bypass MCP's 25K char limit
- **Model Aliases**: "pro", "flash", "gpt5" automatically resolve to latest versions
- **Stance-Steering**: Consensus tool can request "for", "against", or "neutral" perspectives
- **Context Revival**: Continue conversations even after AI context window resets

---

## References

- Repository: https://github.com/fahad/pal-mcp-server
- License: MIT/Apache 2.0
- Python: 3.9+
