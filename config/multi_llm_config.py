"""
Enhanced multi-LLM configuration system.

Supports multiple API keys per agent and multiple LLM providers.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - os, typing, dotenv.load_dotenv, anthropic.Anthropic, json, pathlib.Path
# OUTPUT: 对外提供 - LLMConfiguration类, MultiLLMConfigManager类, get_llm_manager函数, get_agent_llm函数, get_agent_model_params函数
# POSITION: 系统地位 - [Config/LLM Layer] - 多模型配置管理器,支持为不同Agent分配不同LLM和API Key
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import os
from typing import Optional, Dict, Any, Literal
from dotenv import load_dotenv
from anthropic import Anthropic
import json
from pathlib import Path

# Load environment variables
load_dotenv()


LLMProvider = Literal["anthropic", "openai", "azure", "google"]
ModelType = Literal["sonnet", "opus", "haiku", "gpt4", "gpt35"]


class LLMConfiguration:
    """
    Configuration for a single LLM instance.
    """

    def __init__(
        self,
        provider: LLMProvider,
        api_key: str,
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        additional_params: Optional[Dict[str, Any]] = None
    ):
        self.provider = provider
        self.api_key = api_key
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.additional_params = additional_params or {}


class MultiLLMConfigManager:
    """
    Manages multiple LLM configurations for different agents.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize multi-LLM configuration manager.

        Args:
            config_path: Path to configuration file (default: config/llm_keys.json)
        """
        self.config_path = config_path or Path("config/llm_keys.json")
        self.configs: Dict[str, LLMConfiguration] = {}
        self.clients: Dict[str, Any] = {}

        # Load configurations
        self._load_configs()

    def _load_configs(self):
        """Load LLM configurations from file and environment."""
        # Load from JSON config if exists
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
                self._parse_config_data(config_data)

        # Load from environment variables (higher priority)
        self._load_from_env()

        # Set defaults if nothing configured
        if not self.configs:
            self._set_defaults()

    def _parse_config_data(self, config_data: Dict[str, Any]):
        """Parse configuration data from JSON."""
        for agent_name, agent_config in config_data.items():
            provider = agent_config.get("provider", "anthropic")
            api_key = agent_config.get("api_key", "")
            model_id = agent_config.get("model_id", "")
            temperature = agent_config.get("temperature", 0.7)
            max_tokens = agent_config.get("max_tokens", 4000)

            self.configs[agent_name] = LLMConfiguration(
                provider=provider,
                api_key=api_key,
                model_id=model_id,
                temperature=temperature,
                max_tokens=max_tokens
            )

    def _load_from_env(self):
        """Load configurations from environment variables."""
        # Format: AGENT_NAME_LLM_PROVIDER, AGENT_NAME_API_KEY, AGENT_NAME_MODEL
        agents = ["ideation", "planning", "experiment", "writing"]

        for agent in agents:
            env_prefix = agent.upper()

            provider = os.getenv(f"{env_prefix}_LLM_PROVIDER", "anthropic")
            api_key = os.getenv(f"{env_prefix}_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            model_id = os.getenv(f"{env_prefix}_MODEL_ID")
            temperature = float(os.getenv(f"{env_prefix}_TEMPERATURE", "0.7"))
            max_tokens = int(os.getenv(f"{env_prefix}_MAX_TOKENS", "4000"))

            if api_key:
                # Determine model ID based on provider
                if not model_id:
                    model_id = self._get_default_model(provider)

                self.configs[agent] = LLMConfiguration(
                    provider=provider,
                    api_key=api_key,
                    model_id=model_id,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

    def _set_defaults(self):
        """Set default configurations using ANTHROPIC_API_KEY."""
        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError(
                "No LLM API keys configured. Set ANTHROPIC_API_KEY or individual "
                "agent keys (IDEATION_API_KEY, etc.)"
            )

        # Default: all agents use same Anthropic key with different models
        default_configs = {
            "ideation": ("sonnet", 0.7, 4000),
            "planning": ("sonnet", 0.3, 3000),
            "experiment": ("sonnet", 0.2, 4000),
            "writing": ("sonnet", 0.4, 4000),
        }

        for agent, (model_type, temp, tokens) in default_configs.items():
            self.configs[agent] = LLMConfiguration(
                provider="anthropic",
                api_key=api_key,
                model_id=self._get_anthropic_model_id(model_type),
                temperature=temp,
                max_tokens=tokens
            )

    def _get_default_model(self, provider: str) -> str:
        """Get default model ID for provider."""
        defaults = {
            "anthropic": "claude-sonnet-4-5-20250929",
            "openai": "gpt-4-turbo-preview",
            "azure": "gpt-4",
            "google": "gemini-pro"
        }
        return defaults.get(provider, "claude-sonnet-4-5-20250929")

    def _get_anthropic_model_id(self, model_type: str) -> str:
        """Get Anthropic model ID."""
        models = {
            "opus": "claude-opus-4-6",
            "sonnet": "claude-sonnet-4-5-20250929",
            "haiku": "claude-haiku-4-5-20251001",
        }
        return models.get(model_type, models["sonnet"])

    def get_client(self, agent_name: str) -> Any:
        """
        Get LLM client for specified agent.

        Args:
            agent_name: Name of agent (ideation, planning, experiment, writing)

        Returns:
            LLM client instance
        """
        if agent_name not in self.clients:
            config = self.configs.get(agent_name)

            if not config:
                raise ValueError(f"No configuration found for agent: {agent_name}")

            # Create client based on provider
            if config.provider == "anthropic":
                self.clients[agent_name] = Anthropic(api_key=config.api_key)

            elif config.provider == "openai":
                try:
                    from openai import OpenAI
                    self.clients[agent_name] = OpenAI(api_key=config.api_key)
                except ImportError:
                    raise ImportError("OpenAI package not installed. Run: pip install openai")

            elif config.provider == "azure":
                try:
                    from openai import AzureOpenAI
                    endpoint = config.additional_params.get("endpoint")
                    self.clients[agent_name] = AzureOpenAI(
                        api_key=config.api_key,
                        azure_endpoint=endpoint
                    )
                except ImportError:
                    raise ImportError("OpenAI package not installed. Run: pip install openai")

            else:
                raise ValueError(f"Unsupported provider: {config.provider}")

        return self.clients[agent_name]

    def get_config(self, agent_name: str) -> LLMConfiguration:
        """
        Get configuration for agent.

        Args:
            agent_name: Agent name

        Returns:
            LLM configuration
        """
        if agent_name not in self.configs:
            raise ValueError(f"No configuration for agent: {agent_name}")

        return self.configs[agent_name]

    def get_model_params(self, agent_name: str) -> Dict[str, Any]:
        """
        Get model parameters for API calls.

        Args:
            agent_name: Agent name

        Returns:
            Dictionary with model, temperature, max_tokens
        """
        config = self.get_config(agent_name)

        return {
            "model": config.model_id,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }

    def set_agent_config(
        self,
        agent_name: str,
        provider: LLMProvider,
        api_key: str,
        model_id: str,
        temperature: float = 0.7,
        max_tokens: int = 4000
    ):
        """
        Set configuration for an agent.

        Args:
            agent_name: Agent name
            provider: LLM provider
            api_key: API key
            model_id: Model identifier
            temperature: Temperature parameter
            max_tokens: Maximum tokens
        """
        self.configs[agent_name] = LLMConfiguration(
            provider=provider,
            api_key=api_key,
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Clear cached client
        if agent_name in self.clients:
            del self.clients[agent_name]

    def save_config(self):
        """Save current configuration to file."""
        config_data = {}

        for agent_name, config in self.configs.items():
            config_data[agent_name] = {
                "provider": config.provider,
                "api_key": config.api_key,  # Note: In production, encrypt this
                "model_id": config.model_id,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens
            }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            json.dump(config_data, f, indent=2)

    def list_agents(self) -> List[str]:
        """Get list of configured agents."""
        return list(self.configs.keys())

    def get_statistics(self) -> Dict[str, Any]:
        """Get configuration statistics."""
        provider_counts = {}

        for config in self.configs.values():
            provider_counts[config.provider] = provider_counts.get(config.provider, 0) + 1

        return {
            "total_agents": len(self.configs),
            "providers": provider_counts,
            "agents": list(self.configs.keys())
        }


# Global configuration manager
_config_manager: Optional[MultiLLMConfigManager] = None


def get_llm_manager() -> MultiLLMConfigManager:
    """Get or create global LLM configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = MultiLLMConfigManager()
    return _config_manager


def get_agent_llm(agent_name: str) -> Any:
    """
    Get LLM client for an agent.

    Args:
        agent_name: Agent name

    Returns:
        LLM client
    """
    manager = get_llm_manager()
    return manager.get_client(agent_name)


def get_agent_model_params(agent_name: str) -> Dict[str, Any]:
    """
    Get model parameters for an agent.

    Args:
        agent_name: Agent name

    Returns:
        Model parameters dict
    """
    manager = get_llm_manager()
    return manager.get_model_params(agent_name)
