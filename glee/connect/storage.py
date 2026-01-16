"""Connection storage for Glee.

Single file storage: ~/.config/glee/connections.yml

```yaml
- id: a1b2c3d4e5
  label: codex
  type: oauth
  sdk: openai
  vendor: openai
  refresh: "..."
  access: "..."
  expires: 1736956800000
  account_id: "org-abc123"

- id: f6g7h8i9j0
  label: anthropic
  type: api
  sdk: anthropic
  vendor: anthropic
  key: "sk-ant-..."

- id: k1l2m3n4o5
  label: openrouter
  type: api
  sdk: openai
  vendor: openrouter
  base_url: "https://openrouter.ai/api/v1"
  key: "sk-or-..."
```
"""

from __future__ import annotations

import os
import secrets
import string
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

# SDK types
SDK = Literal["openai", "anthropic", "vertex", "bedrock"]

# Common vendors with known base URLs (for OpenAI SDK)
VENDOR_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "together": "https://api.together.xyz/v1",
    "groq": "https://api.groq.com/openai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}


def generate_id() -> str:
    """Generate a random alphanumeric ID."""
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(10))


@dataclass
class OAuthCredential:
    """OAuth credential (e.g., Codex, Gemini)."""

    id: str
    label: str
    sdk: SDK
    vendor: str
    refresh: str = ""
    access: str = ""
    expires: int = 0  # Unix timestamp (milliseconds)
    account_id: str | None = None
    type: Literal["oauth"] = field(default="oauth", repr=False)

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires == 0:
            return False
        return time.time() * 1000 > self.expires

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "type": "oauth",
            "sdk": self.sdk,
            "vendor": self.vendor,
            "refresh": self.refresh,
            "access": self.access,
            "expires": self.expires,
        }
        if self.account_id:
            d["account_id"] = self.account_id
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OAuthCredential:
        return cls(
            id=data.get("id", generate_id()),
            label=data.get("label", ""),
            sdk=data.get("sdk", "openai"),
            vendor=data.get("vendor", ""),
            refresh=data.get("refresh", ""),
            access=data.get("access", ""),
            expires=data.get("expires", 0),
            account_id=data.get("account_id"),
        )


@dataclass
class APICredential:
    """API key credential (e.g., Claude, OpenRouter)."""

    id: str
    label: str
    sdk: SDK
    vendor: str
    key: str = ""
    base_url: str | None = None
    type: Literal["api"] = field(default="api", repr=False)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "label": self.label,
            "type": "api",
            "sdk": self.sdk,
            "vendor": self.vendor,
            "key": self.key,
        }
        if self.base_url:
            d["base_url"] = self.base_url
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> APICredential:
        return cls(
            id=data.get("id", generate_id()),
            label=data.get("label", ""),
            sdk=data.get("sdk", "openai"),
            vendor=data.get("vendor", ""),
            key=data.get("key", ""),
            base_url=data.get("base_url"),
        )


# Union type
Credential = OAuthCredential | APICredential

# Storage path
CONNECTIONS_PATH = Path.home() / ".config" / "glee" / "connections.yml"


class ConnectionStorage:
    """Storage for Glee connections (~/.config/glee/connections.yml)."""

    path: Path = CONNECTIONS_PATH

    @classmethod
    def all(cls) -> list[Credential]:
        """Get all connections."""
        result: list[Credential] = []
        for entry in cls.read():
            cred = cls.parse(entry)
            if cred:
                result.append(cred)
        return result

    @classmethod
    def get(cls, id: str) -> Credential | None:
        """Get connection by ID."""
        for cred in cls.all():
            if cred.id == id:
                return cred
        return None

    @classmethod
    def find(cls, vendor: str, type: Literal["oauth", "api"] | None = None) -> list[Credential]:
        """Find connections by vendor and optionally type."""
        result: list[Credential] = []
        for cred in cls.all():
            if cred.vendor == vendor:
                if type is None or cred.type == type:
                    result.append(cred)
        return result

    @classmethod
    def find_one(cls, vendor: str, type: Literal["oauth", "api"] | None = None) -> Credential | None:
        """Find first connection matching vendor and optionally type."""
        matches = cls.find(vendor, type)
        return matches[0] if matches else None

    @classmethod
    def add(cls, credential: Credential) -> Credential:
        """Add a new connection. Generates ID if not set."""
        if not credential.id:
            credential.id = generate_id()

        data = cls.read()
        data.append(credential.to_dict())
        cls.write(data)
        return credential

    @classmethod
    def remove(cls, id: str) -> bool:
        """Remove connection by ID."""
        data = cls.read()
        original_len = len(data)
        data = [d for d in data if d.get("id") != id]
        if len(data) < original_len:
            cls.write(data)
            return True
        return False

    @classmethod
    def update(cls, id: str, credential: Credential) -> bool:
        """Update connection by ID."""
        data = cls.read()
        for i, entry in enumerate(data):
            if entry.get("id") == id:
                credential.id = id  # Preserve ID
                data[i] = credential.to_dict()
                cls.write(data)
                return True
        return False

    @classmethod
    def read(cls) -> list[dict[str, Any]]:
        """Read all connections from file."""
        if not cls.path.exists():
            return []
        try:
            with open(cls.path) as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, list) else []  # type: ignore[return-value]
        except Exception:
            return []

    @classmethod
    def write(cls, data: list[dict[str, Any]]) -> None:
        """Write connections to file."""
        cls.path.parent.mkdir(parents=True, exist_ok=True)
        with open(cls.path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        os.chmod(cls.path, 0o600)

    @staticmethod
    def parse(data: dict[str, Any]) -> Credential | None:
        """Parse a dict into the appropriate credential type."""
        cred_type = data.get("type")
        if cred_type == "oauth":
            return OAuthCredential.from_dict(data)
        elif cred_type == "api":
            return APICredential.from_dict(data)
        return None
