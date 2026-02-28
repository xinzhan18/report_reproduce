"""
LLM 调用模块 - 无状态函数式接口

提供 call_llm / call_llm_json / extract_json 三个函数，
替代原 LLMService 类和 json_parser 模块。
"""

# INPUT:  config.llm_config (模型名称解析), anthropic SDK, json, re, time, logging
# OUTPUT: call_llm(), call_llm_json(), extract_json()
# POSITION: Agent层 LLM 调用工具

import json
import re
import time
import logging

from config.llm_config import get_model_name

logger = logging.getLogger("agents.llm")


def call_llm(
    client,
    prompt: str,
    system_prompt: str = "",
    model: str = "sonnet",
    max_tokens: int = 4000,
    temperature: float = 0.7,
    max_retries: int = 3,
) -> str:
    """调用 LLM 并返回文本，自动重试。"""
    model_id = get_model_name(model)
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"All {max_retries} attempts exhausted")

    raise last_error


def extract_json(text: str) -> dict:
    """从 LLM 响应中提取 JSON。策略: code block → raw {} → 直接 parse。"""
    # Strategy 1: ```json ... ```
    m = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 2: raw { ... }
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 3: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to extract JSON: {e}")
        raise ValueError(f"Could not extract valid JSON from text: {e}")


def call_llm_json(
    client,
    prompt: str,
    system_prompt: str = "",
    model: str = "sonnet",
    max_tokens: int = 4000,
    temperature: float = 0.7,
    max_retries: int = 3,
) -> dict:
    """调用 LLM 并解析返回的 JSON。"""
    text = call_llm(client, prompt, system_prompt, model, max_tokens, temperature, max_retries)
    return extract_json(text)
