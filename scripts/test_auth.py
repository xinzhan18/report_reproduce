#!/usr/bin/env python3
"""
Test authentication configuration
测试认证配置
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - sys, os, pathlib.Path, importlib.util
# OUTPUT: 对外提供 - test_api_key_auth/test_oauth_auth函数, main函数(命令行入口)
# POSITION: 系统地位 - [Scripts/Testing Layer] - 认证测试脚本,验证API Key和OAuth配置是否正确
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Direct imports
import importlib.util

# Load auth config
auth_spec = importlib.util.spec_from_file_location(
    "auth_config",
    project_root / "config" / "auth_config.py"
)
auth_module = importlib.util.module_from_spec(auth_spec)
auth_spec.loader.exec_module(auth_module)

get_auth_config = auth_module.get_auth_config


def test_api_key_auth(provider: str):
    """Test API key authentication"""
    print(f"\n{'='*70}")
    print(f"Testing {provider.upper()} API Key Authentication")
    print(f"{'='*70}\n")

    try:
        config = get_auth_config(provider=provider, auth_method="api_key")
        api_key = config.get_api_key()

        if api_key:
            # Mask the key for security
            masked_key = api_key[:8] + "..." + api_key[-4:]
            print(f"[SUCCESS] API Key found: {masked_key}")
            print(f"[SUCCESS] {provider.upper()} API key authentication working!")
            return True
        else:
            print(f"[ERROR] No API key found")
            return False

    except ValueError as e:
        print(f"[ERROR] {e}")
        print(f"\nTo fix:")
        if provider == "anthropic":
            print(f"  Add to .env: ANTHROPIC_API_KEY=sk-ant-xxx")
        elif provider == "openai":
            print(f"  Add to .env: OPENAI_API_KEY=sk-xxx")
        return False

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


def test_oauth_auth(provider: str):
    """Test OAuth authentication"""
    print(f"\n{'='*70}")
    print(f"Testing {provider.upper()} OAuth Authentication")
    print(f"{'='*70}\n")

    token_file = project_root / "data" / "auth" / f"{provider}_oauth_token.json"

    if not token_file.exists():
        print(f"[INFO] No cached OAuth token found")
        print(f"  Token file: {token_file}")
        print(f"\nTo setup OAuth:")
        print(f"  python scripts/setup_oauth.py --provider {provider}")
        return False

    try:
        config = get_auth_config(provider=provider, auth_method="oauth")
        token = config.get_oauth_token()

        if token:
            masked_token = token[:12] + "..." + token[-4:]
            print(f"[SUCCESS] OAuth token found: {masked_token}")
            print(f"[SUCCESS] {provider.upper()} OAuth authentication working!")

            # Check expiration
            if config._oauth_token and config._oauth_token.expires_at:
                expires = config._oauth_token.expires_at
                print(f"[INFO] Token expires at: {expires}")

                if config._oauth_token.is_expired():
                    print(f"[WARNING] Token is expired, will be refreshed on next use")
                else:
                    print(f"[INFO] Token is valid")

            return True
        else:
            print(f"[ERROR] Failed to get OAuth token")
            return False

    except Exception as e:
        print(f"[ERROR] OAuth test failed: {e}")
        return False


def test_headers(provider: str, auth_method: str):
    """Test authentication headers generation"""
    print(f"\n{'='*70}")
    print(f"Testing Headers Generation ({provider}, {auth_method})")
    print(f"{'='*70}\n")

    try:
        config = get_auth_config(provider=provider, auth_method=auth_method)
        headers = config.get_headers()

        print(f"Generated headers:")
        for key, value in headers.items():
            # Mask sensitive values
            if key.lower() in ["authorization", "x-api-key"]:
                masked_value = value[:15] + "..." + value[-4:] if len(value) > 20 else "***"
                print(f"  {key}: {masked_value}")
            else:
                print(f"  {key}: {value}")

        print(f"\n[SUCCESS] Headers generated successfully")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to generate headers: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("Authentication Configuration Test")
    print("="*70)

    # Check .env file
    env_file = project_root / ".env"
    if not env_file.exists():
        print(f"\n[WARNING] .env file not found at: {env_file}")
        print(f"[INFO] Copy .env.example to .env and configure your API keys")

    # Test Anthropic
    print("\n" + "="*70)
    print("ANTHROPIC (Claude) TESTS")
    print("="*70)

    anthropic_api_ok = test_api_key_auth("anthropic")
    anthropic_oauth_ok = test_oauth_auth("anthropic")

    if anthropic_api_ok:
        test_headers("anthropic", "api_key")

    # Test OpenAI
    print("\n" + "="*70)
    print("OPENAI (GPT) TESTS")
    print("="*70)

    openai_api_ok = test_api_key_auth("openai")
    openai_oauth_ok = test_oauth_auth("openai")

    if openai_api_ok:
        test_headers("openai", "api_key")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70 + "\n")

    results = {
        "Anthropic API Key": anthropic_api_ok,
        "Anthropic OAuth": anthropic_oauth_ok,
        "OpenAI API Key": openai_api_ok,
        "OpenAI OAuth": openai_oauth_ok
    }

    for test_name, status in results.items():
        status_icon = "[OK]" if status else "[--]"
        print(f"{status_icon} {test_name}")

    print()

    # Recommendations
    print("Recommendations:")
    if not anthropic_api_ok:
        print("  - Add ANTHROPIC_API_KEY to .env for Claude API access")
    if not openai_api_ok:
        print("  - Add OPENAI_API_KEY to .env for OpenAI API access")
    if not openai_oauth_ok:
        print("  - Run 'python scripts/setup_oauth.py --provider openai' for OAuth")

    print()


if __name__ == "__main__":
    main()
