"""Auth storage for Glee credentials.

Stores credentials in separate files under ~/.glee/auth/:

```
~/.glee/auth/
  codex-oauth.yml      # OAuth credentials for Codex
  copilot-oauth.yml    # OAuth credentials for GitHub Copilot
  claude-api-key.yml   # API key for Claude
  gemini-api-key.yml   # API key for Gemini
  custom/              # Custom OpenAI-compatible providers
    openrouter.yml
    ollama.yml
    together.yml
```

Custom provider config:

```yaml
# openrouter.yml
type: openai-compatible
base_url: https://openrouter.ai/api/v1
api_key: sk-or-xxx
models:
  - alias: claude-sonnet
    name: anthropic/claude-3.5-sonnet
  - alias: gpt-4o
    name: openai/gpt-4o
```

Resolution order:
1. Environment variable (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
2. Project .glee/auth/{provider}-*.yml
3. Global ~/.glee/auth/{provider}-*.yml
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml


# SDK types
SDK_TYPE = Literal["openai", "anthropic", "google"]

# OAuth providers (login via browser)
OAUTH_PROVIDERS = {
    "codex": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
}

# Environment variable fallbacks
ENV_VAR_MAP = {
    "codex": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}

# Popular OpenAI-compatible endpoints (for quick setup)
OPENAI_ENDPOINTS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "together": "https://api.together.xyz/v1",
    "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "z.ai": "https://api.z.ai/v1",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}

# Supported built-in providers (backwards compat)
PROVIDERS = ["codex", "gemini", "claude"]


@dataclass
class OAuthCredentials:
    """OAuth credentials."""

    method: Literal["oauth"] = "oauth"
    access_token: str = ""
    refresh_token: str = ""
    expires_at: int = 0  # Unix timestamp
    account_id: str | None = None

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires_at == 0:
            return False  # No expiry (e.g., Copilot)
        return time.time() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML storage."""
        d: dict[str, Any] = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }
        if self.account_id:
            d["account_id"] = self.account_id
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OAuthCredentials:
        """Create from dictionary."""
        return cls(
            method="oauth",
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            expires_at=data.get("expires_at", 0),
            account_id=data.get("account_id"),
        )


@dataclass
class APIKeyCredentials:
    """API key credentials."""

    method: Literal["api_key"] = "api_key"
    api_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML storage."""
        return {
            "api_key": self.api_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> APIKeyCredentials:
        """Create from dictionary."""
        return cls(
            method="api_key",
            api_key=data.get("api_key", ""),
        )


# Union type for credentials
Credentials = OAuthCredentials | APIKeyCredentials


@dataclass
class ModelMapping:
    """Maps an upstream model name to a local alias."""

    alias: str  # The name you use (e.g., "claude-sonnet")
    name: str  # The actual model name (e.g., "anthropic/claude-3.5-sonnet")

    def to_dict(self) -> dict[str, str]:
        return {"alias": self.alias, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelMapping:
        return cls(alias=data.get("alias", ""), name=data.get("name", ""))


@dataclass
class CustomProvider:
    """Custom OpenAI-compatible provider configuration.

    Supports providers like OpenRouter, z.ai, Ollama, Together.ai, etc.
    """

    name: str  # Provider name (e.g., "openrouter")
    type: Literal["openai-compatible", "claude-compatible", "gemini-compatible"] = "openai-compatible"
    base_url: str = ""  # API base URL (e.g., "https://openrouter.ai/api/v1")
    api_key: str = ""  # API key
    models: list[ModelMapping] | None = None  # Model aliases
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for YAML storage."""
        d: dict[str, Any] = {
            "type": self.type,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "enabled": self.enabled,
        }
        if self.models:
            d["models"] = [m.to_dict() for m in self.models]
        return d

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> CustomProvider:
        """Create from dictionary."""
        models = None
        if "models" in data:
            models = [ModelMapping.from_dict(m) for m in data["models"]]

        return cls(
            name=name,
            type=data.get("type", "openai-compatible"),
            base_url=data.get("base_url", ""),
            api_key=data.get("api_key", ""),
            models=models,
            enabled=data.get("enabled", True),
        )

    def get_model_name(self, alias: str) -> str:
        """Get the actual model name for an alias."""
        if self.models:
            for m in self.models:
                if m.alias == alias:
                    return m.name
        return alias  # Return as-is if no mapping found


class AuthStorage:
    """Manage auth storage in YAML files.

    Each provider has its own file under the auth directory:
    - {auth_dir}/codex-oauth.yml
    - {auth_dir}/claude-api-key.yml
    """

    def __init__(self, auth_dir: Path | str):
        """Initialize with path to auth directory."""
        self.auth_dir = Path(auth_dir).expanduser()

    def _ensure_dir(self) -> None:
        """Ensure the auth directory exists with secure permissions."""
        self.auth_dir.mkdir(parents=True, exist_ok=True)
        # Set directory permissions to 700 (owner only)
        os.chmod(self.auth_dir, 0o700)

    def _get_file_path(self, provider: str, method: str) -> Path:
        """Get the file path for a provider's credentials."""
        return self.auth_dir / f"{provider}-{method}.yml"

    def _read_file(self, path: Path) -> dict[str, Any]:
        """Read a credential file."""
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                result = yaml.safe_load(f)
                if isinstance(result, dict):
                    return cast(dict[str, Any], result)
                return {}
        except Exception:
            return {}

    def _write_file(self, path: Path, data: dict[str, Any]) -> None:
        """Write to a credential file with secure permissions."""
        self._ensure_dir()
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
        # Set file permissions to 600 (owner read/write only)
        os.chmod(path, 0o600)

    def get(self, provider: str) -> Credentials | None:
        """Get credentials for a provider."""
        # Try OAuth first
        oauth_path = self._get_file_path(provider, "oauth")
        if oauth_path.exists():
            data = self._read_file(oauth_path)
            if data:
                return OAuthCredentials.from_dict(data)

        # Then try API key
        api_key_path = self._get_file_path(provider, "api-key")
        if api_key_path.exists():
            data = self._read_file(api_key_path)
            if data:
                return APIKeyCredentials.from_dict(data)

        return None

    def save(self, provider: str, credentials: Credentials) -> None:
        """Save credentials for a provider."""
        if isinstance(credentials, OAuthCredentials):
            method = "oauth"
        else:
            method = "api-key"

        path = self._get_file_path(provider, method)
        self._write_file(path, credentials.to_dict())

    def delete(self, provider: str) -> bool:
        """Delete credentials for a provider. Returns True if deleted."""
        deleted = False

        # Delete OAuth file if exists
        oauth_path = self._get_file_path(provider, "oauth")
        if oauth_path.exists():
            oauth_path.unlink()
            deleted = True

        # Delete API key file if exists
        api_key_path = self._get_file_path(provider, "api-key")
        if api_key_path.exists():
            api_key_path.unlink()
            deleted = True

        return deleted

    def list_providers(self) -> list[str]:
        """List all providers with saved credentials."""
        providers: set[str] = set()
        if not self.auth_dir.exists():
            return []

        for path in self.auth_dir.glob("*-oauth.yml"):
            provider = path.stem.rsplit("-oauth", 1)[0]
            providers.add(provider)

        for path in self.auth_dir.glob("*-api-key.yml"):
            provider = path.stem.rsplit("-api-key", 1)[0]
            providers.add(provider)

        return sorted(providers)


def _get_global_storage() -> AuthStorage:
    """Get the global auth storage (~/.glee/auth/)."""
    return AuthStorage(Path.home() / ".glee" / "auth")


def _get_project_storage() -> AuthStorage | None:
    """Get the project auth storage (.glee/auth/) if it exists."""
    project_path = Path.cwd() / ".glee" / "auth"
    if project_path.exists():
        return AuthStorage(project_path)
    return None


def get_credentials(provider: str) -> Credentials | None:
    """Get credentials for a provider with resolution order.

    Resolution order:
    1. Environment variable
    2. Project .glee/auth.yml
    3. Global ~/.glee/auth.yml
    """
    # 1. Check environment variable
    env_var = ENV_VAR_MAP.get(provider)
    if env_var:
        value = os.environ.get(env_var)
        if value:
            return APIKeyCredentials(api_key=value)

    # 2. Check project storage
    project_storage = _get_project_storage()
    if project_storage:
        creds = project_storage.get(provider)
        if creds:
            return creds

    # 3. Check global storage
    global_storage = _get_global_storage()
    return global_storage.get(provider)


def save_credentials(
    provider: str, credentials: Credentials, *, project: bool = False
) -> None:
    """Save credentials for a provider.

    Args:
        provider: Provider name (codex, copilot, claude, gemini)
        credentials: Credentials to save
        project: If True, save to project .glee/auth/ instead of global
    """
    if project:
        storage = AuthStorage(Path.cwd() / ".glee" / "auth")
    else:
        storage = _get_global_storage()
    storage.save(provider, credentials)


def delete_credentials(provider: str, *, project: bool = False) -> bool:
    """Delete credentials for a provider.

    Args:
        provider: Provider name
        project: If True, delete from project storage

    Returns:
        True if credentials were deleted
    """
    if project:
        storage = AuthStorage(Path.cwd() / ".glee" / "auth")
    else:
        storage = _get_global_storage()
    return storage.delete(provider)


def list_providers() -> dict[str, dict[str, Any]]:
    """List all configured providers with their status.

    Returns:
        Dict mapping provider name to status info
    """
    result: dict[str, dict[str, Any]] = {}

    for provider in PROVIDERS:
        creds = get_credentials(provider)
        if creds is None:
            result[provider] = {"configured": False}
        elif isinstance(creds, OAuthCredentials):
            result[provider] = {
                "configured": True,
                "method": "oauth",
                "expired": creds.is_expired(),
                "account_id": creds.account_id,
            }
        else:
            result[provider] = {
                "configured": True,
                "method": "api_key",
                "masked_key": creds.api_key[:8] + "..." if len(creds.api_key) > 8 else "***",
            }

    return result


# =============================================================================
# Custom Provider Management
# =============================================================================

def _get_custom_dir(*, project: bool = False) -> Path:
    """Get the custom providers directory."""
    if project:
        return Path.cwd() / ".glee" / "auth" / "custom"
    return Path.home() / ".glee" / "auth" / "custom"


def get_custom_provider(name: str) -> CustomProvider | None:
    """Get a custom provider by name.

    Checks project-local first, then global.
    """
    # Check project-local
    project_path = _get_custom_dir(project=True) / f"{name}.yml"
    if project_path.exists():
        try:
            with open(project_path) as f:
                raw = yaml.safe_load(f)
                if isinstance(raw, dict):
                    return CustomProvider.from_dict(name, cast(dict[str, Any], raw))
        except Exception:
            pass

    # Check global
    global_path = _get_custom_dir(project=False) / f"{name}.yml"
    if global_path.exists():
        try:
            with open(global_path) as f:
                raw = yaml.safe_load(f)
                if isinstance(raw, dict):
                    return CustomProvider.from_dict(name, cast(dict[str, Any], raw))
        except Exception:
            pass

    return None


def save_custom_provider(provider: CustomProvider, *, project: bool = False) -> None:
    """Save a custom provider configuration."""
    custom_dir = _get_custom_dir(project=project)
    custom_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(custom_dir.parent, 0o700)

    path = custom_dir / f"{provider.name}.yml"
    with open(path, "w") as f:
        yaml.dump(provider.to_dict(), f, default_flow_style=False)
    os.chmod(path, 0o600)


def delete_custom_provider(name: str, *, project: bool = False) -> bool:
    """Delete a custom provider. Returns True if deleted."""
    path = _get_custom_dir(project=project) / f"{name}.yml"
    if path.exists():
        path.unlink()
        return True
    return False


def list_custom_providers() -> list[CustomProvider]:
    """List all custom providers (project + global)."""
    providers: dict[str, CustomProvider] = {}

    # Load global providers first
    global_dir = _get_custom_dir(project=False)
    if global_dir.exists():
        for path in global_dir.glob("*.yml"):
            name = path.stem
            try:
                with open(path) as f:
                    raw = yaml.safe_load(f)
                    if isinstance(raw, dict):
                        providers[name] = CustomProvider.from_dict(name, cast(dict[str, Any], raw))
            except Exception:
                pass

    # Project providers override global
    project_dir = _get_custom_dir(project=True)
    if project_dir.exists():
        for path in project_dir.glob("*.yml"):
            name = path.stem
            try:
                with open(path) as f:
                    raw = yaml.safe_load(f)
                    if isinstance(raw, dict):
                        providers[name] = CustomProvider.from_dict(name, cast(dict[str, Any], raw))
            except Exception:
                pass

    return sorted(providers.values(), key=lambda p: p.name)


# Pre-configured custom provider templates
CUSTOM_PROVIDER_TEMPLATES = {
    "openrouter": CustomProvider(
        name="openrouter",
        type="openai-compatible",
        base_url="https://openrouter.ai/api/v1",
        api_key="",
        models=[
            ModelMapping(alias="claude-sonnet", name="anthropic/claude-3.5-sonnet"),
            ModelMapping(alias="gpt-4o", name="openai/gpt-4o"),
            ModelMapping(alias="llama-70b", name="meta-llama/llama-3.1-70b-instruct"),
        ],
    ),
    "together": CustomProvider(
        name="together",
        type="openai-compatible",
        base_url="https://api.together.xyz/v1",
        api_key="",
        models=[
            ModelMapping(alias="llama-70b", name="meta-llama/Llama-3.3-70B-Instruct-Turbo"),
            ModelMapping(alias="qwen-72b", name="Qwen/Qwen2.5-72B-Instruct-Turbo"),
        ],
    ),
    "ollama": CustomProvider(
        name="ollama",
        type="openai-compatible",
        base_url="http://localhost:11434/v1",
        api_key="ollama",  # Ollama doesn't require a real key
        models=[
            ModelMapping(alias="llama", name="llama3.2"),
            ModelMapping(alias="qwen", name="qwen2.5-coder"),
        ],
    ),
    "z.ai": CustomProvider(
        name="z.ai",
        type="openai-compatible",
        base_url="https://api.z.ai/v1",
        api_key="",
    ),
    "groq": CustomProvider(
        name="groq",
        type="openai-compatible",
        base_url="https://api.groq.com/openai/v1",
        api_key="",
        models=[
            ModelMapping(alias="llama-70b", name="llama-3.3-70b-versatile"),
            ModelMapping(alias="mixtral", name="mixtral-8x7b-32768"),
        ],
    ),
    "mistral": CustomProvider(
        name="mistral",
        type="openai-compatible",
        base_url="https://api.mistral.ai/v1",
        api_key="",
        models=[
            ModelMapping(alias="mistral-large", name="mistral-large-latest"),
            ModelMapping(alias="codestral", name="codestral-latest"),
        ],
    ),
    "deepseek": CustomProvider(
        name="deepseek",
        type="openai-compatible",
        base_url="https://api.deepseek.com/v1",
        api_key="",
        models=[
            ModelMapping(alias="deepseek-chat", name="deepseek-chat"),
            ModelMapping(alias="deepseek-coder", name="deepseek-coder"),
        ],
    ),
    "lmstudio": CustomProvider(
        name="lmstudio",
        type="openai-compatible",
        base_url="http://localhost:1234/v1",
        api_key="lm-studio",  # LM Studio doesn't require a real key
    ),
}
