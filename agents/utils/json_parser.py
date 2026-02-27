"""
JSON parsing utilities

Provides robust JSON extraction and parsing from LLM responses.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - json (JSON解析), re (正则表达式),
#                   typing (类型系统), logging (日志)
# OUTPUT: 对外提供 - extract_json()函数,从LLM响应文本中提取JSON,
#                   支持多种格式(代码块、原始JSON等)
# POSITION: 系统地位 - Agent/Utils (智能体层-工具)
#                     LLM输出解析工具,被所有Agent使用
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import json
import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("json_parser")


def extract_json(text: str) -> Dict:
    """
    Extract JSON from text that may contain markdown or other formatting.

    Tries multiple strategies:
    1. JSON in code blocks (```json ... ```)
    2. Raw JSON objects ({ ... })
    3. Direct parsing

    Args:
        text: Text containing JSON

    Returns:
        Parsed JSON dict

    Raises:
        ValueError if JSON cannot be extracted
    """
    # Strategy 1: Find JSON in code blocks
    json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        json_text = json_match.group(1)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    # Strategy 2: Find raw JSON object
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        json_text = json_match.group(0)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

    # Strategy 3: Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to extract JSON: {e}")
        logger.error(f"Text: {text[:500]}...")
        raise ValueError(f"Could not extract valid JSON from text: {e}")


def parse_json_safely(
    text: str,
    default: Optional[Dict] = None
) -> Dict:
    """
    Parse JSON with fallback to default value.

    Args:
        text: Text to parse
        default: Default value if parsing fails (default: empty dict)

    Returns:
        Parsed JSON or default value
    """
    if default is None:
        default = {}

    try:
        return extract_json(text)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"JSON parsing failed, using default: {e}")
        return default


def validate_json_schema(
    data: Dict,
    required_keys: list[str]
) -> bool:
    """
    Validate that JSON contains required keys.

    Args:
        data: JSON dict to validate
        required_keys: List of required key names

    Returns:
        True if all keys present, False otherwise
    """
    return all(key in data for key in required_keys)


def extract_json_field(
    data: Dict,
    field_path: str,
    default: Any = None
) -> Any:
    """
    Extract field from nested JSON using dot notation.

    Examples:
        extract_json_field(data, "rankings.0.score")
        extract_json_field(data, "metadata.author")

    Args:
        data: JSON dict
        field_path: Dot-separated path to field
        default: Default value if field not found

    Returns:
        Field value or default
    """
    parts = field_path.split('.')
    current = data

    for part in parts:
        try:
            # Handle array indices
            if part.isdigit():
                current = current[int(part)]
            else:
                current = current[part]
        except (KeyError, IndexError, TypeError):
            return default

    return current
