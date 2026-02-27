"""
LLM configuration for Claude API integration.

Supports both Sonnet (complex reasoning) and Haiku (simple tasks) models.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - os (环境变量), dotenv (环境变量加载),
#                   anthropic SDK (Anthropic API客户端),
#                   typing (类型系统)
# OUTPUT: 对外提供 - LLMConfig类 (LLM配置管理器),
#                   MODEL_IDS字典 (模型ID映射),
#                   ModelType类型 (模型类型定义),
#                   get_model_id()函数 (获取模型ID)
# POSITION: 系统地位 - Config/LLM (配置层-LLM配置)
#                     所有Agent的LLM调用基础,定义模型选择和API认证
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import os
from typing import Optional, Literal
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()


# Model configurations
ModelType = Literal["sonnet", "opus", "haiku"]

MODEL_IDS = {
    "opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku": "claude-haiku-4-5-20251001",
}

# Default model for each use case
DEFAULT_MODEL = "sonnet"  # For complex reasoning tasks
SIMPLE_TASK_MODEL = "haiku"  # For simple, fast tasks


class LLMConfig:
    """
    Configuration manager for Claude API.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM configuration.

        Args:
            api_key: Anthropic API key. If not provided, reads from ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = Anthropic(api_key=self.api_key)

    def get_client(self) -> Anthropic:
        """Get the Anthropic client instance."""
        return self.client

    @staticmethod
    def get_model_id(model_type: ModelType = "sonnet") -> str:
        """
        Get the model ID for a given model type.

        Args:
            model_type: Type of model (sonnet, opus, or haiku)

        Returns:
            Full model ID string
        """
        return MODEL_IDS.get(model_type, MODEL_IDS["sonnet"])


# Global LLM config instance
_llm_config: Optional[LLMConfig] = None


def get_llm_config() -> LLMConfig:
    """
    Get or create the global LLM configuration instance.

    Returns:
        LLMConfig instance
    """
    global _llm_config
    if _llm_config is None:
        _llm_config = LLMConfig()
    return _llm_config


def get_llm(model_type: ModelType = "sonnet") -> Anthropic:
    """
    Get Claude LLM client for complex reasoning tasks.

    Args:
        model_type: Type of model to use (default: sonnet)

    Returns:
        Anthropic client instance
    """
    config = get_llm_config()
    return config.get_client()


def get_haiku_llm() -> Anthropic:
    """
    Get Claude Haiku LLM client for simple, fast tasks.

    Returns:
        Anthropic client instance configured for Haiku
    """
    return get_llm("haiku")


def get_model_name(model_type: ModelType = "sonnet") -> str:
    """
    Get the full model name for API calls.

    Args:
        model_type: Type of model (sonnet, opus, or haiku)

    Returns:
        Model ID string for API calls
    """
    return LLMConfig.get_model_id(model_type)


# Context window sizes
CONTEXT_WINDOWS = {
    "opus": 200_000,
    "sonnet": 200_000,
    "haiku": 200_000,
}


def get_context_window(model_type: ModelType = "sonnet") -> int:
    """
    Get the context window size for a model type.

    Args:
        model_type: Type of model

    Returns:
        Context window size in tokens
    """
    return CONTEXT_WINDOWS.get(model_type, 200_000)
