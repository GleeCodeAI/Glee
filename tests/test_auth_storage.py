"""Tests for auth storage module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from glee.auth import storage


@pytest.fixture
def temp_auth_file():
    """Create a temporary auth file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        temp_path = Path(f.name)

    # Patch the auth path to use temp file
    with patch.object(storage, "_get_auth_path", return_value=temp_path):
        yield temp_path

    # Cleanup
    if temp_path.exists():
        os.unlink(temp_path)


class TestAPICredential:
    """Tests for APICredential dataclass."""

    def test_create_api_credential(self):
        cred = storage.APICredential(
            id="test123",
            label="my-openrouter",
            sdk="openai",
            vendor="openrouter",
            key="sk-or-xxx",
            base_url="https://openrouter.ai/api/v1",
        )
        assert cred.id == "test123"
        assert cred.label == "my-openrouter"
        assert cred.sdk == "openai"
        assert cred.vendor == "openrouter"
        assert cred.key == "sk-or-xxx"
        assert cred.base_url == "https://openrouter.ai/api/v1"
        assert cred.type == "api"

    def test_to_dict(self):
        cred = storage.APICredential(
            id="test123",
            label="anthropic",
            sdk="anthropic",
            vendor="anthropic",
            key="sk-ant-xxx",
        )
        d = cred.to_dict()
        assert d["id"] == "test123"
        assert d["label"] == "anthropic"
        assert d["type"] == "api"
        assert d["sdk"] == "anthropic"
        assert d["vendor"] == "anthropic"
        assert d["key"] == "sk-ant-xxx"
        assert "base_url" not in d  # None values not included

    def test_from_dict(self):
        data = {
            "id": "abc123",
            "label": "groq",
            "type": "api",
            "sdk": "openai",
            "vendor": "groq",
            "key": "gsk-xxx",
            "base_url": "https://api.groq.com/openai/v1",
        }
        cred = storage.APICredential.from_dict(data)
        assert cred.id == "abc123"
        assert cred.label == "groq"
        assert cred.vendor == "groq"
        assert cred.key == "gsk-xxx"
        assert cred.base_url == "https://api.groq.com/openai/v1"


class TestOAuthCredential:
    """Tests for OAuthCredential dataclass."""

    def test_create_oauth_credential(self):
        cred = storage.OAuthCredential(
            id="oauth123",
            label="codex",
            sdk="openai",
            vendor="openai",
            refresh="refresh-token",
            access="access-token",
            expires=1736956800000,
            account_id="org-abc",
        )
        assert cred.id == "oauth123"
        assert cred.label == "codex"
        assert cred.sdk == "openai"
        assert cred.vendor == "openai"
        assert cred.refresh == "refresh-token"
        assert cred.access == "access-token"
        assert cred.expires == 1736956800000
        assert cred.account_id == "org-abc"
        assert cred.type == "oauth"

    def test_is_expired_not_expired(self):
        import time

        future_time = int((time.time() + 3600) * 1000)  # 1 hour from now
        cred = storage.OAuthCredential(
            id="test",
            label="codex",
            sdk="openai",
            vendor="openai",
            expires=future_time,
        )
        assert not cred.is_expired()

    def test_is_expired_expired(self):
        past_time = 1000  # Way in the past
        cred = storage.OAuthCredential(
            id="test",
            label="codex",
            sdk="openai",
            vendor="openai",
            expires=past_time,
        )
        assert cred.is_expired()

    def test_is_expired_zero_never_expires(self):
        cred = storage.OAuthCredential(
            id="test",
            label="copilot",
            sdk="openai",
            vendor="github",
            expires=0,
        )
        assert not cred.is_expired()

    def test_to_dict(self):
        cred = storage.OAuthCredential(
            id="oauth123",
            label="codex",
            sdk="openai",
            vendor="openai",
            refresh="refresh-token",
            access="access-token",
            expires=1736956800000,
            account_id="org-abc",
        )
        d = cred.to_dict()
        assert d["id"] == "oauth123"
        assert d["type"] == "oauth"
        assert d["refresh"] == "refresh-token"
        assert d["account_id"] == "org-abc"

    def test_from_dict(self):
        data = {
            "id": "oauth456",
            "label": "copilot",
            "type": "oauth",
            "sdk": "openai",
            "vendor": "github",
            "refresh": "token",
            "access": "token",
            "expires": 0,
        }
        cred = storage.OAuthCredential.from_dict(data)
        assert cred.id == "oauth456"
        assert cred.label == "copilot"
        assert cred.vendor == "github"


class TestStorageFunctions:
    """Tests for storage CRUD functions."""

    def test_add_and_get(self, temp_auth_file):
        cred = storage.APICredential(
            id="",
            label="test-api",
            sdk="openai",
            vendor="openrouter",
            key="test-key",
        )
        added = storage.add(cred)
        assert added.id  # ID should be generated

        retrieved = storage.get(added.id)
        assert retrieved is not None
        assert retrieved.label == "test-api"
        assert retrieved.key == "test-key"

    def test_all_empty(self, temp_auth_file):
        creds = storage.all()
        assert creds == []

    def test_all_multiple(self, temp_auth_file):
        storage.add(storage.APICredential(
            id="", label="cred1", sdk="openai", vendor="openrouter", key="key1"
        ))
        storage.add(storage.APICredential(
            id="", label="cred2", sdk="anthropic", vendor="anthropic", key="key2"
        ))
        storage.add(storage.OAuthCredential(
            id="", label="cred3", sdk="openai", vendor="openai"
        ))

        creds = storage.all()
        assert len(creds) == 3

    def test_find_by_vendor(self, temp_auth_file):
        storage.add(storage.APICredential(
            id="", label="or1", sdk="openai", vendor="openrouter", key="key1"
        ))
        storage.add(storage.APICredential(
            id="", label="or2", sdk="openai", vendor="openrouter", key="key2"
        ))
        storage.add(storage.APICredential(
            id="", label="ant", sdk="anthropic", vendor="anthropic", key="key3"
        ))

        openrouter_creds = storage.find(vendor="openrouter")
        assert len(openrouter_creds) == 2

        anthropic_creds = storage.find(vendor="anthropic")
        assert len(anthropic_creds) == 1

    def test_find_by_vendor_and_type(self, temp_auth_file):
        storage.add(storage.APICredential(
            id="", label="api", sdk="openai", vendor="openai", key="key1"
        ))
        storage.add(storage.OAuthCredential(
            id="", label="oauth", sdk="openai", vendor="openai"
        ))

        api_creds = storage.find(vendor="openai", type="api")
        assert len(api_creds) == 1
        assert api_creds[0].label == "api"

        oauth_creds = storage.find(vendor="openai", type="oauth")
        assert len(oauth_creds) == 1
        assert oauth_creds[0].label == "oauth"

    def test_find_one(self, temp_auth_file):
        storage.add(storage.APICredential(
            id="", label="test", sdk="openai", vendor="groq", key="key1"
        ))

        cred = storage.find_one(vendor="groq")
        assert cred is not None
        assert cred.label == "test"

        no_cred = storage.find_one(vendor="nonexistent")
        assert no_cred is None

    def test_remove(self, temp_auth_file):
        added = storage.add(storage.APICredential(
            id="", label="to-remove", sdk="openai", vendor="test", key="key"
        ))

        assert storage.get(added.id) is not None
        assert storage.remove(added.id) is True
        assert storage.get(added.id) is None

    def test_remove_nonexistent(self, temp_auth_file):
        assert storage.remove("nonexistent-id") is False

    def test_update(self, temp_auth_file):
        added = storage.add(storage.APICredential(
            id="", label="original", sdk="openai", vendor="test", key="old-key"
        ))

        updated_cred = storage.APICredential(
            id=added.id,
            label="updated",
            sdk="openai",
            vendor="test",
            key="new-key",
        )
        assert storage.update(added.id, updated_cred) is True

        retrieved = storage.get(added.id)
        assert retrieved is not None
        assert retrieved.label == "updated"
        assert retrieved.key == "new-key"

    def test_update_nonexistent(self, temp_auth_file):
        cred = storage.APICredential(
            id="fake", label="test", sdk="openai", vendor="test", key="key"
        )
        assert storage.update("nonexistent", cred) is False


class TestGenerateId:
    """Tests for ID generation."""

    def test_generate_id_length(self):
        id1 = storage._generate_id()
        assert len(id1) == 10

    def test_generate_id_alphanumeric(self):
        id1 = storage._generate_id()
        assert id1.isalnum()
        assert id1.islower() or id1.replace("0123456789", "").islower()

    def test_generate_id_unique(self):
        ids = [storage._generate_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique


class TestVendorUrls:
    """Tests for vendor URL constants."""

    def test_known_vendors(self):
        assert "openai" in storage.VENDOR_URLS
        assert "openrouter" in storage.VENDOR_URLS
        assert "groq" in storage.VENDOR_URLS
        assert "anthropic" not in storage.VENDOR_URLS  # Anthropic uses its own SDK

    def test_vendor_urls_format(self):
        for vendor, url in storage.VENDOR_URLS.items():
            assert url.startswith("http")
            assert "/v1" in url or vendor in ("ollama", "lmstudio")
