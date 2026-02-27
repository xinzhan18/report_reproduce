"""
LLM Configuration with OAuth Support
支持API Key和OAuth认证的LLM配置

Usage Examples:

1. API Key (default):
   llm = get_llm()  # Uses ANTHROPIC_API_KEY from .env

2. OAuth (Anthropic):
   llm = get_llm(auth_method="oauth", provider="anthropic")

3. OAuth (OpenAI):
   llm = get_llm(auth_method="oauth", provider="openai")

4. Switch providers:
   llm = get_llm(provider="openai")  # Uses OpenAI with API key
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - os, typing, dotenv.load_dotenv, anthropic.Anthropic, config.auth_config
# OUTPUT: 对外提供 - UnifiedLLMConfig类, get_llm函数, get_llm_config_instance函数, setup_oauth_interactive函数
# POSITION: 系统地位 - [Config/LLM Layer] - OAuth认证LLM配置,统一API Key和OAuth两种认证方式
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import os
from typing import Optional, Literal, Union
from dotenv import load_dotenv
from anthropic import Anthropic
from config.auth_config import (
    get_auth_config,
    AuthProvider,
    AuthMethod
)

# Load environment variables
load_dotenv()

# Model type
ModelType = Literal["sonnet", "opus", "haiku", "gpt-4", "gpt-3.5-turbo"]

# Provider-specific model IDs
ANTHROPIC_MODELS = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku": "claude-haiku-4-5-20251001",
}

OPENAI_MODELS = {
    "gpt-4": "gpt-4-turbo-preview",
    "gpt-3.5-turbo": "gpt-3.5-turbo",
}


class UnifiedLLMConfig:
    """
    Unified LLM configuration supporting multiple providers and authentication methods.
    """

    def __init__(
        self,
        provider: AuthProvider = "anthropic",
        auth_method: AuthMethod = "api_key",
        model_type: Optional[ModelType] = None
    ):
        """
        Initialize LLM configuration with authentication.

        Args:
            provider: LLM provider (anthropic, openai, custom)
            auth_method: Authentication method (api_key, oauth, bearer_token)
            model_type: Model type to use (provider-specific)
        """
        self.provider = provider
        self.auth_method = auth_method
        self.auth_config = get_auth_config(provider=provider, auth_method=auth_method)

        # Determine default model type based on provider
        if model_type is None:
            model_type = "sonnet" if provider == "anthropic" else "gpt-4"
        self.model_type = model_type

        # Initialize client
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the LLM client based on provider"""
        if self.provider == "anthropic":
            client_kwargs = self.auth_config.get_client_kwargs()
            self._client = Anthropic(**client_kwargs)

        elif self.provider == "openai":
            try:
                from openai import OpenAI
                client_kwargs = self.auth_config.get_client_kwargs()
                self._client = OpenAI(**client_kwargs)
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. Install with: pip install openai"
                )

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def get_client(self) -> Union[Anthropic, 'OpenAI']:
        """
        Get the LLM client instance.

        Returns:
            Client instance (Anthropic or OpenAI)
        """
        return self._client

    def get_model_id(self) -> str:
        """
        Get the model ID for API calls.

        Returns:
            Model ID string
        """
        if self.provider == "anthropic":
            return ANTHROPIC_MODELS.get(self.model_type, ANTHROPIC_MODELS["sonnet"])
        elif self.provider == "openai":
            return OPENAI_MODELS.get(self.model_type, OPENAI_MODELS["gpt-4"])
        else:
            return self.model_type

    def call(
        self,
        messages: list,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ):
        """
        Unified API call across providers.

        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: System prompt (for providers that support it)
            **kwargs: Additional provider-specific parameters

        Returns:
            Response from the LLM
        """
        if self.provider == "anthropic":
            response = self._client.messages.create(
                model=self.get_model_id(),
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=messages,
                **kwargs
            )
            return response

        elif self.provider == "openai":
            # OpenAI uses system message differently
            openai_messages = []
            if system:
                openai_messages.append({"role": "system", "content": system})
            openai_messages.extend(messages)

            response = self._client.chat.completions.create(
                model=self.get_model_id(),
                max_tokens=max_tokens,
                temperature=temperature,
                messages=openai_messages,
                **kwargs
            )
            return response

        else:
            raise ValueError(f"Unsupported provider: {self.provider}")


# Global config instance
_llm_config: Optional[UnifiedLLMConfig] = None


def get_llm(
    provider: AuthProvider = "anthropic",
    auth_method: AuthMethod = "api_key",
    model_type: Optional[ModelType] = None
) -> Union[Anthropic, 'OpenAI']:
    """
    Get LLM client with specified authentication.

    Args:
        provider: LLM provider (anthropic, openai, custom)
        auth_method: Authentication method (api_key, oauth, bearer_token)
        model_type: Model type to use

    Returns:
        LLM client instance

    Examples:
        # Anthropic with API key (default)
        llm = get_llm()

        # Anthropic with OAuth
        llm = get_llm(auth_method="oauth")

        # OpenAI with API key
        llm = get_llm(provider="openai")

        # OpenAI with OAuth
        llm = get_llm(provider="openai", auth_method="oauth")
    """
    global _llm_config

    # Create new config if parameters changed
    if (
        _llm_config is None
        or _llm_config.provider != provider
        or _llm_config.auth_method != auth_method
        or (model_type and _llm_config.model_type != model_type)
    ):
        _llm_config = UnifiedLLMConfig(
            provider=provider,
            auth_method=auth_method,
            model_type=model_type
        )

    return _llm_config.get_client()


def get_llm_config_instance(
    provider: AuthProvider = "anthropic",
    auth_method: AuthMethod = "api_key",
    model_type: Optional[ModelType] = None
) -> UnifiedLLMConfig:
    """
    Get the UnifiedLLMConfig instance (for advanced usage).

    Args:
        provider: LLM provider
        auth_method: Authentication method
        model_type: Model type

    Returns:
        UnifiedLLMConfig instance
    """
    global _llm_config

    if (
        _llm_config is None
        or _llm_config.provider != provider
        or _llm_config.auth_method != auth_method
        or (model_type and _llm_config.model_type != model_type)
    ):
        _llm_config = UnifiedLLMConfig(
            provider=provider,
            auth_method=auth_method,
            model_type=model_type
        )

    return _llm_config


def setup_oauth_interactive(provider: AuthProvider = "anthropic"):
    """
    Interactive OAuth setup.

    This function will guide you through the OAuth authentication process.

    Args:
        provider: Provider to authenticate with (anthropic, openai)

    Example:
        >>> setup_oauth_interactive("openai")
        # Follow the prompts to complete OAuth flow
    """
    print(f"\n{'='*70}")
    print(f"Setting up OAuth for {provider.upper()}")
    print(f"{'='*70}\n")

    config = UnifiedLLMConfig(provider=provider, auth_method="oauth")
    print(f"\n✓ OAuth setup complete for {provider}")
    print(f"Token cached at: data/auth/{provider}_oauth_token.json")
    print(f"\nYou can now use: get_llm(provider='{provider}', auth_method='oauth')")

    return config.get_client()
