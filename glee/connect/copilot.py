"""GitHub Copilot OAuth authentication using Device Flow.

Based on OpenCode's Copilot plugin:
- Uses Device Authorization Grant (RFC 8628)
- Client ID: Ov23lix9NqDZRRaZy0yK
- User visits github.com/login/device and enters code
- Polls for access token until user completes auth
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

# GitHub Copilot OAuth configuration
CLIENT_ID = "Ov23lix9NqDZRRaZy0yK"
DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_AGENT = "glee/1.0 (https://GleeCode.ai)"


@dataclass
class DeviceCodeResponse:
    """Response from device code request."""

    device_code: str
    user_code: str
    verification_uri: str
    interval: int  # Polling interval in seconds


@dataclass
class TokenResponse:
    """OAuth token response."""

    access_token: str


async def request_device_code() -> DeviceCodeResponse:
    """Request a device code from GitHub."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            DEVICE_CODE_URL,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            json={
                "client_id": CLIENT_ID,
                "scope": "read:user",
            },
        )
        if not response.is_success:
            error_text = response.text
            raise Exception(f"GitHub API error {response.status_code}: {error_text}")

        data = response.json()

        return DeviceCodeResponse(
            device_code=data["device_code"],
            user_code=data["user_code"],
            verification_uri=data["verification_uri"],
            interval=data.get("interval", 5),
        )


async def poll_for_token(device_code: str, interval: int, timeout: float = 300) -> TokenResponse | None:
    """Poll GitHub for access token until user completes auth or timeout."""
    start = time.time()

    async with httpx.AsyncClient() as client:
        while time.time() - start < timeout:
            response = await client.post(
                ACCESS_TOKEN_URL,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                },
                json={
                    "client_id": CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )

            if not response.is_success:
                return None

            data = response.json()

            if "access_token" in data:
                return TokenResponse(access_token=data["access_token"])

            error = data.get("error")
            if error == "authorization_pending":
                # User hasn't completed auth yet, keep polling
                await asyncio.sleep(interval)
                continue
            elif error == "slow_down":
                # Need to slow down polling
                interval += 5
                await asyncio.sleep(interval)
                continue
            elif error == "expired_token":
                # Device code expired
                return None
            elif error == "access_denied":
                # User denied access
                return None
            elif error:
                # Unknown error
                return None

            await asyncio.sleep(interval)

    return None  # Timeout


import asyncio
import webbrowser


async def authenticate() -> tuple[TokenResponse | None, str | None]:
    """Run the full OAuth Device Flow for GitHub Copilot.

    Returns:
        Tuple of (TokenResponse, None) on success, or (None, error_message) on failure
    """
    try:
        # Request device code
        device = await request_device_code()

        # Build URL with pre-filled code
        auth_url = f"{device.verification_uri}?user_code={device.user_code}"

        print(f"\nOpening browser for authentication...")
        print(f"Code: {device.user_code}")
        print(f"If browser doesn't open, visit: {auth_url}\n")

        webbrowser.open(auth_url)

        print("Waiting for authorization...")

        # Poll for token
        token = await poll_for_token(device.device_code, device.interval)

        if not token:
            return None, "Authorization failed or timed out"

        return token, None

    except httpx.HTTPStatusError as e:
        return None, f"HTTP error: {e.response.status_code}"
    except Exception as e:
        return None, f"Error: {e}"


def authenticate_sync() -> tuple[TokenResponse | None, str | None]:
    """Synchronous wrapper for authenticate()."""
    return asyncio.run(authenticate())
