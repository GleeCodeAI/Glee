"""Codex (OpenAI) OAuth authentication using PKCE flow.

Based on OpenAI's Codex CLI authentication:
- Uses Authorization Code flow with PKCE
- Client ID: app_EMoamEEZ73f0CkXaXp7hrann
- Issuer: https://auth.openai.com
- Runs local HTTP server for OAuth callback
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import http.server
import secrets
import socketserver
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    pass

# OpenAI OAuth configuration (from opencode/codex)
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
ISSUER = "https://auth.openai.com"
CALLBACK_PORT = 1455
CALLBACK_PATH = "/auth/callback"
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"

# OAuth endpoints
AUTHORIZE_URL = f"{ISSUER}/oauth/authorize"
TOKEN_URL = f"{ISSUER}/oauth/token"


@dataclass
class PKCECodes:
    """PKCE verifier and challenge."""

    verifier: str
    challenge: str


@dataclass
class TokenResponse:
    """OAuth token response."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


def generate_pkce() -> PKCECodes:
    """Generate PKCE verifier and challenge.

    The verifier is a random string, and the challenge is the
    base64url-encoded SHA256 hash of the verifier.
    """
    # Generate random verifier (43-128 characters)
    verifier = secrets.token_urlsafe(32)

    # Create challenge: base64url(sha256(verifier))
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    return PKCECodes(verifier=verifier, challenge=challenge)


def build_authorize_url(pkce: PKCECodes, state: str) -> str:
    """Build the authorization URL for the OAuth flow."""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email offline_access",
        "code_challenge": pkce.challenge,
        "code_challenge_method": "S256",
        "state": state,
        # Required for Codex OAuth flow
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": "codex_cli_rs",
    }
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


async def exchange_code_for_tokens(code: str, pkce: PKCECodes) -> TokenResponse:
    """Exchange authorization code for access and refresh tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "code_verifier": pkce.verifier,
            },
        )
        response.raise_for_status()
        data = response.json()

        return TokenResponse(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expires_in=data.get("expires_in", 3600),
            token_type=data.get("token_type", "Bearer"),
        )


async def refresh_access_token(refresh_token: str) -> TokenResponse:
    """Refresh the access token using the refresh token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": CLIENT_ID,
            },
        )
        response.raise_for_status()
        data = response.json()

        return TokenResponse(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token),
            expires_in=data.get("expires_in", 3600),
            token_type=data.get("token_type", "Bearer"),
        )


def extract_account_id(access_token: str) -> str | None:
    """Extract account ID from JWT access token claims.

    The account ID can be in various claim locations:
    - chatgpt_account_id (root)
    - https://api.openai.com/auth.chatgpt_account_id (nested)
    - organizations[0].id (fallback)
    """
    try:
        # JWT is base64url encoded: header.payload.signature
        parts = access_token.split(".")
        if len(parts) != 3:
            return None

        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding

        import json

        claims = json.loads(base64.urlsafe_b64decode(payload))

        # Try various claim locations
        if "chatgpt_account_id" in claims:
            return claims["chatgpt_account_id"]

        if "https://api.openai.com/auth" in claims:
            auth_claims = claims["https://api.openai.com/auth"]
            if "chatgpt_account_id" in auth_claims:
                return auth_claims["chatgpt_account_id"]

        if "organizations" in claims and claims["organizations"]:
            return claims["organizations"][0].get("id")

        return None
    except Exception:
        return None


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    # Class variables to store result
    auth_code: str | None = None
    error: str | None = None
    state: str | None = None
    received_state: str | None = None

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Suppress default logging."""
        del format, args  # Unused

    def do_GET(self) -> None:
        """Handle GET request (OAuth callback)."""
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return

        # Parse query parameters
        params = urllib.parse.parse_qs(parsed.query)

        # Check for error
        if "error" in params:
            OAuthCallbackHandler.error = params["error"][0]
            self._send_error_response(params.get("error_description", ["Unknown error"])[0])
            return

        # Get authorization code
        if "code" not in params:
            OAuthCallbackHandler.error = "No authorization code received"
            self._send_error_response("No authorization code received")
            return

        # Verify state
        OAuthCallbackHandler.received_state = params.get("state", [None])[0]
        if OAuthCallbackHandler.received_state != OAuthCallbackHandler.state:
            OAuthCallbackHandler.error = "State mismatch - possible CSRF attack"
            self._send_error_response("State mismatch")
            return

        OAuthCallbackHandler.auth_code = params["code"][0]
        self._send_success_response()

    def _send_success_response(self) -> None:
        """Send success HTML response."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Glee - Authentication Successful</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif;
               display: flex; justify-content: center; align-items: center;
               height: 100vh; margin: 0; background: #f5f5f5; }
        .container { text-align: center; padding: 40px; background: white;
                     border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #10a37f; margin-bottom: 10px; }
        p { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Authentication Successful!</h1>
        <p>You can close this window and return to the terminal.</p>
    </div>
</body>
</html>
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_error_response(self, message: str) -> None:
        """Send error HTML response."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Glee - Authentication Failed</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif;
               display: flex; justify-content: center; align-items: center;
               height: 100vh; margin: 0; background: #f5f5f5; }}
        .container {{ text-align: center; padding: 40px; background: white;
                     border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #e74c3c; margin-bottom: 10px; }}
        p {{ color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Authentication Failed</h1>
        <p>{message}</p>
        <p>Please try again.</p>
    </div>
</body>
</html>
"""
        self.send_response(400)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())


class OAuthCallbackServer:
    """Local HTTP server for OAuth callback."""

    def __init__(self, state: str):
        """Initialize with expected state for CSRF protection."""
        self.state = state
        self.server: socketserver.TCPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the callback server in a background thread."""
        # Set expected state
        OAuthCallbackHandler.state = self.state
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.error = None
        OAuthCallbackHandler.received_state = None

        # Allow port reuse
        socketserver.TCPServer.allow_reuse_address = True

        # Bind to localhost only (127.0.0.1)
        self.server = socketserver.TCPServer(("127.0.0.1", CALLBACK_PORT), OAuthCallbackHandler)
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self) -> None:
        """Serve requests until we get the callback."""
        if self.server:
            # Keep serving until we get the auth code or error
            while not OAuthCallbackHandler.auth_code and not OAuthCallbackHandler.error:
                self.server.handle_request()

    def wait_for_callback(self, timeout: float = 300) -> tuple[str | None, str | None]:
        """Wait for the OAuth callback.

        Returns:
            Tuple of (auth_code, error)
        """
        start = time.time()
        while time.time() - start < timeout:
            if OAuthCallbackHandler.auth_code or OAuthCallbackHandler.error:
                break
            time.sleep(0.1)

        return OAuthCallbackHandler.auth_code, OAuthCallbackHandler.error

    def stop(self) -> None:
        """Stop the callback server."""
        if self.server:
            try:
                self.server.server_close()
            except Exception:
                pass
            self.server = None


async def authenticate() -> tuple[TokenResponse | None, str | None]:
    """Run the full OAuth PKCE flow for Codex.

    Returns:
        Tuple of (TokenResponse, None) on success, or (None, error_message) on failure
    """
    # Generate PKCE codes
    pkce = generate_pkce()

    # Generate state for CSRF protection (hex like opencode)
    state = secrets.token_hex(16)

    # Build authorization URL
    auth_url = build_authorize_url(pkce, state)

    # Start callback server
    callback_server = OAuthCallbackServer(state)
    callback_server.start()

    try:
        # Open browser for user authentication
        print(f"\nOpening browser for authentication...")
        print(f"If the browser doesn't open, visit:\n{auth_url}\n")
        webbrowser.open(auth_url)

        # Wait for callback
        print("Waiting for authentication...")
        auth_code, error = callback_server.wait_for_callback(timeout=300)

        if error:
            return None, f"Authentication failed: {error}"

        if not auth_code:
            return None, "Authentication timed out (5 minutes)"

        # Exchange code for tokens
        print("Exchanging code for tokens...")
        tokens = await exchange_code_for_tokens(auth_code, pkce)

        return tokens, None

    except httpx.HTTPStatusError as e:
        return None, f"Token exchange failed: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return None, f"Authentication failed: {e}"
    finally:
        callback_server.stop()


def authenticate_sync() -> tuple[TokenResponse | None, str | None]:
    """Synchronous wrapper for authenticate()."""
    return asyncio.run(authenticate())
