"""
OAuth and Authentication Configuration
支持多种认证方式：API Key, OAuth 2.0, Custom Token

Supports:
- Anthropic API Key (default)
- OpenAI API Key
- OAuth 2.0 for Anthropic (if available)
- OAuth 2.0 for OpenAI
- Custom authentication providers
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - os, json, time, typing, pathlib.Path, dotenv.load_dotenv, dataclasses.dataclass, datetime
# OUTPUT: 对外提供 - OAuthToken类, AuthConfig类, get_auth_config函数, get_api_key函数, setup_oauth函数
# POSITION: 系统地位 - [Config/Security Layer] - API认证配置中心,支持API Key/OAuth/Bearer Token多种认证方式
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import os
import json
import time
from typing import Optional, Dict, Any, Literal
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()


AuthProvider = Literal["anthropic", "openai", "custom"]
AuthMethod = Literal["api_key", "oauth", "bearer_token"]


@dataclass
class OAuthToken:
    """OAuth token container"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"
    scope: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if token is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "token_type": self.token_type,
            "scope": self.scope
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OAuthToken':
        """Load from dictionary"""
        expires_at = None
        if data.get("expires_at"):
            expires_at = datetime.fromisoformat(data["expires_at"])

        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope")
        )


class AuthConfig:
    """
    Unified authentication configuration supporting multiple providers and methods
    """

    def __init__(
        self,
        provider: AuthProvider = "anthropic",
        auth_method: AuthMethod = "api_key",
        token_cache_dir: str = "data/auth"
    ):
        """
        Initialize authentication configuration.

        Args:
            provider: Authentication provider (anthropic, openai, custom)
            auth_method: Authentication method (api_key, oauth, bearer_token)
            token_cache_dir: Directory to cache OAuth tokens
        """
        self.provider = provider
        self.auth_method = auth_method
        self.token_cache_dir = Path(token_cache_dir)
        self.token_cache_dir.mkdir(parents=True, exist_ok=True)

        self._oauth_token: Optional[OAuthToken] = None
        self._load_cached_token()

    def _load_cached_token(self):
        """Load cached OAuth token if exists"""
        token_file = self.token_cache_dir / f"{self.provider}_oauth_token.json"
        if token_file.exists():
            try:
                with open(token_file, 'r') as f:
                    data = json.load(f)
                    self._oauth_token = OAuthToken.from_dict(data)

                    # Check if expired
                    if self._oauth_token.is_expired():
                        print(f"⚠️  Cached OAuth token expired, will refresh")
                        self._refresh_token()
            except Exception as e:
                print(f"⚠️  Failed to load cached token: {e}")

    def _save_token(self, token: OAuthToken):
        """Save OAuth token to cache"""
        token_file = self.token_cache_dir / f"{self.provider}_oauth_token.json"
        try:
            with open(token_file, 'w') as f:
                json.dump(token.to_dict(), f, indent=2)
            self._oauth_token = token
        except Exception as e:
            print(f"⚠️  Failed to save token: {e}")

    def get_api_key(self) -> str:
        """
        Get API key for direct API key authentication.

        Returns:
            API key string

        Raises:
            ValueError: If API key not found
        """
        if self.provider == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                raise ValueError(
                    "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable."
                )
            return key

        elif self.provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable."
                )
            return key

        else:
            key = os.getenv("CUSTOM_API_KEY")
            if not key:
                raise ValueError(
                    "Custom API key not found. Set CUSTOM_API_KEY environment variable."
                )
            return key

    def get_oauth_token(self) -> str:
        """
        Get OAuth access token (refreshing if necessary).

        Returns:
            Access token string

        Raises:
            ValueError: If OAuth not configured or token unavailable
        """
        if self._oauth_token is None:
            # Try to initiate OAuth flow
            self._initiate_oauth_flow()

        if self._oauth_token is None:
            raise ValueError("OAuth token not available. Please authenticate first.")

        # Refresh if expired
        if self._oauth_token.is_expired():
            self._refresh_token()

        return self._oauth_token.access_token

    def _initiate_oauth_flow(self):
        """
        Initiate OAuth 2.0 authorization flow.

        This is a placeholder - actual implementation depends on provider.
        """
        print(f"\n{'='*70}")
        print(f"OAuth Authentication Required for {self.provider.upper()}")
        print(f"{'='*70}\n")

        if self.provider == "anthropic":
            self._anthropic_oauth_flow()
        elif self.provider == "openai":
            self._openai_oauth_flow()
        else:
            self._custom_oauth_flow()

    def _anthropic_oauth_flow(self):
        """
        Anthropic OAuth flow (if supported).

        Note: As of 2026-02, Anthropic primarily uses API keys.
        This is a placeholder for future OAuth support.
        """
        print("⚠️  Anthropic OAuth not yet supported by Anthropic API.")
        print("Using API key authentication instead.")
        print("\nPlease ensure ANTHROPIC_API_KEY is set in your .env file.")
        print("\nTo get your API key:")
        print("1. Go to https://console.anthropic.com/")
        print("2. Navigate to 'API Keys'")
        print("3. Create a new key or copy existing one")
        print("4. Add to .env: ANTHROPIC_API_KEY=your_key_here\n")

        # Fallback to API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            # Treat as bearer token
            self._oauth_token = OAuthToken(
                access_token=api_key,
                token_type="X-API-Key"  # Anthropic uses X-API-Key header
            )
            print("✓ Using API key as authentication token")
        else:
            raise ValueError("Anthropic API key not found")

    def _openai_oauth_flow(self):
        """
        OpenAI OAuth flow.

        OpenAI supports OAuth for certain applications.
        """
        print("Initiating OpenAI OAuth flow...")
        print("\nOpenAI OAuth Configuration:")
        print("1. CLIENT_ID: Set OPENAI_CLIENT_ID in .env")
        print("2. CLIENT_SECRET: Set OPENAI_CLIENT_SECRET in .env")
        print("3. REDIRECT_URI: Set OPENAI_REDIRECT_URI in .env")

        client_id = os.getenv("OPENAI_CLIENT_ID")
        client_secret = os.getenv("OPENAI_CLIENT_SECRET")
        redirect_uri = os.getenv("OPENAI_REDIRECT_URI", "http://localhost:8080/callback")

        if not client_id or not client_secret:
            print("\n⚠️  OpenAI OAuth credentials not configured.")
            print("Falling back to API key authentication.")

            # Fallback to API key
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._oauth_token = OAuthToken(
                    access_token=api_key,
                    token_type="Bearer"
                )
                print("✓ Using API key as authentication token")
            else:
                raise ValueError("OpenAI authentication not configured")
            return

        # Actual OAuth flow (requires HTTP server and browser interaction)
        print(f"\nAuthorization URL:")
        auth_url = (
            f"https://platform.openai.com/oauth/authorize?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=openai.api"
        )
        print(auth_url)
        print("\n1. Open this URL in your browser")
        print("2. Authorize the application")
        print("3. Copy the authorization code from the redirect URL")

        auth_code = input("\nEnter authorization code: ").strip()

        if auth_code:
            # Exchange code for token
            self._exchange_openai_code(auth_code, client_id, client_secret, redirect_uri)
        else:
            print("⚠️  No authorization code provided")

    def _exchange_openai_code(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ):
        """Exchange authorization code for access token"""
        try:
            import requests

            response = requests.post(
                "https://platform.openai.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri
                }
            )

            if response.status_code == 200:
                data = response.json()
                expires_in = data.get("expires_in", 3600)
                expires_at = datetime.now() + timedelta(seconds=expires_in)

                token = OAuthToken(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    expires_at=expires_at,
                    token_type=data.get("token_type", "Bearer"),
                    scope=data.get("scope")
                )

                self._save_token(token)
                print("✓ OAuth token obtained successfully")
            else:
                print(f"⚠️  Token exchange failed: {response.text}")

        except ImportError:
            print("⚠️  'requests' library required for OAuth. Install: pip install requests")
        except Exception as e:
            print(f"⚠️  OAuth flow failed: {e}")

    def _custom_oauth_flow(self):
        """Custom OAuth flow for other providers"""
        print("Custom OAuth flow not implemented.")
        print("Please configure authentication manually.")

    def _refresh_token(self):
        """Refresh OAuth token using refresh token"""
        if not self._oauth_token or not self._oauth_token.refresh_token:
            print("⚠️  No refresh token available, re-authentication required")
            self._initiate_oauth_flow()
            return

        print("Refreshing OAuth token...")

        if self.provider == "openai":
            self._refresh_openai_token()
        else:
            print("Token refresh not implemented for this provider")

    def _refresh_openai_token(self):
        """Refresh OpenAI OAuth token"""
        try:
            import requests

            client_id = os.getenv("OPENAI_CLIENT_ID")
            client_secret = os.getenv("OPENAI_CLIENT_SECRET")

            response = requests.post(
                "https://platform.openai.com/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._oauth_token.refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret
                }
            )

            if response.status_code == 200:
                data = response.json()
                expires_in = data.get("expires_in", 3600)
                expires_at = datetime.now() + timedelta(seconds=expires_in)

                token = OAuthToken(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", self._oauth_token.refresh_token),
                    expires_at=expires_at,
                    token_type=data.get("token_type", "Bearer")
                )

                self._save_token(token)
                print("✓ Token refreshed successfully")
            else:
                print(f"⚠️  Token refresh failed: {response.text}")
                self._initiate_oauth_flow()

        except Exception as e:
            print(f"⚠️  Token refresh failed: {e}")
            self._initiate_oauth_flow()

    def get_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.

        Returns:
            Dictionary of HTTP headers
        """
        headers = {}

        if self.auth_method == "api_key":
            if self.provider == "anthropic":
                headers["x-api-key"] = self.get_api_key()
                headers["anthropic-version"] = "2023-06-01"
            elif self.provider == "openai":
                headers["Authorization"] = f"Bearer {self.get_api_key()}"
            else:
                headers["Authorization"] = f"Bearer {self.get_api_key()}"

        elif self.auth_method == "oauth":
            token = self.get_oauth_token()
            headers["Authorization"] = f"Bearer {token}"

        elif self.auth_method == "bearer_token":
            token = os.getenv("CUSTOM_BEARER_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        return headers

    def get_client_kwargs(self) -> Dict[str, Any]:
        """
        Get keyword arguments for LLM client initialization.

        Returns:
            Dictionary of client initialization parameters
        """
        if self.auth_method == "api_key":
            return {"api_key": self.get_api_key()}
        elif self.auth_method == "oauth":
            return {"api_key": self.get_oauth_token()}
        else:
            return {}


# Global auth config instance
_auth_config: Optional[AuthConfig] = None


def get_auth_config(
    provider: AuthProvider = "anthropic",
    auth_method: AuthMethod = "api_key"
) -> AuthConfig:
    """
    Get or create authentication configuration.

    Args:
        provider: Authentication provider
        auth_method: Authentication method

    Returns:
        AuthConfig instance
    """
    global _auth_config

    # Check if we need to create new config
    if _auth_config is None or _auth_config.provider != provider or _auth_config.auth_method != auth_method:
        _auth_config = AuthConfig(provider=provider, auth_method=auth_method)

    return _auth_config


def get_api_key(provider: AuthProvider = "anthropic") -> str:
    """
    Convenience function to get API key.

    Args:
        provider: Provider name

    Returns:
        API key string
    """
    config = get_auth_config(provider=provider, auth_method="api_key")
    return config.get_api_key()


def setup_oauth(provider: AuthProvider = "anthropic") -> AuthConfig:
    """
    Setup OAuth authentication (interactive).

    Args:
        provider: Provider to authenticate with

    Returns:
        AuthConfig instance with OAuth configured
    """
    config = AuthConfig(provider=provider, auth_method="oauth")
    # This will trigger interactive OAuth flow if needed
    config.get_oauth_token()
    return config
