#!/usr/bin/env python3
"""
Interactive OAuth setup script
交互式OAuth设置脚本
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - sys, argparse, pathlib.Path, importlib.util
# OUTPUT: 对外提供 - main函数(命令行入口)
# POSITION: 系统地位 - [Scripts/Setup Layer] - OAuth交互式设置脚本,引导用户完成OAuth认证配置
#
# 注意:当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Direct import to avoid dependencies
import importlib.util

spec = importlib.util.spec_from_file_location(
    "llm_config_oauth",
    project_root / "config" / "llm_config_oauth.py"
)
llm_config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llm_config_module)

setup_oauth_interactive = llm_config_module.setup_oauth_interactive


def main():
    parser = argparse.ArgumentParser(
        description="Setup OAuth authentication for LLM providers"
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default="openai",
        help="LLM provider to authenticate with (default: openai)"
    )

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"OAuth Setup for {args.provider.upper()}")
    print(f"{'='*70}\n")

    print(f"Starting OAuth setup for {args.provider}...")
    print(f"This will guide you through the authentication process.\n")

    try:
        client = setup_oauth_interactive(args.provider)

        print(f"\n{'='*70}")
        print(f"[SUCCESS] OAuth configured for {args.provider}!")
        print(f"{'='*70}\n")

        print(f"Usage in code:")
        print(f"  from config.llm_config_oauth import get_llm")
        print(f"  llm = get_llm(provider='{args.provider}', auth_method='oauth')")
        print()
        print(f"Token cached at:")
        print(f"  data/auth/{args.provider}_oauth_token.json")
        print()

    except KeyboardInterrupt:
        print("\n\n[CANCELLED] OAuth setup cancelled by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n{'='*70}")
        print(f"[ERROR] OAuth setup failed")
        print(f"{'='*70}\n")

        print(f"Error: {e}\n")
        print(f"Troubleshooting:")
        print(f"1. Check .env file for required variables:")

        if args.provider == "openai":
            print(f"   - OPENAI_CLIENT_ID")
            print(f"   - OPENAI_CLIENT_SECRET")
            print(f"   - OPENAI_REDIRECT_URI (optional)")
        elif args.provider == "anthropic":
            print(f"   - ANTHROPIC_CLIENT_ID")
            print(f"   - ANTHROPIC_CLIENT_SECRET")

        print(f"2. Verify OAuth app is configured correctly in provider console")
        print(f"3. Check network connectivity")
        print()

        sys.exit(1)


if __name__ == "__main__":
    main()
