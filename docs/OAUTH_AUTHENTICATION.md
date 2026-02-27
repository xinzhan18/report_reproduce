# OAuth认证指南 / OAuth Authentication Guide

## 概述

系统现在支持**多种认证方式**：

✅ **API Key** (默认) - 简单直接
✅ **OAuth 2.0** - 更安全，支持token刷新
✅ **Bearer Token** - 自定义token认证

支持的Provider：
- **Anthropic (Claude)** - API Key (主要), OAuth (未来支持)
- **OpenAI (GPT)** - API Key, OAuth
- **Custom** - 自定义provider

---

## 快速开始

### 方式1：API Key（推荐，最简单）

**配置 `.env` 文件**：

```bash
# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-api03-xxx

# OpenAI (GPT)
OPENAI_API_KEY=sk-xxx

# 选择使用哪个provider
DEFAULT_LLM_PROVIDER=anthropic  # 或 openai
```

**使用**：

```python
from config.llm_config_oauth import get_llm

# 使用Anthropic (默认)
llm = get_llm()

# 使用OpenAI
llm = get_llm(provider="openai")
```

---

### 方式2：OAuth 2.0（更安全）

#### OpenAI OAuth设置

**1. 在OpenAI平台创建OAuth应用**：
- 访问 https://platform.openai.com/
- 进入 Settings → OAuth Apps
- 创建新应用，获取 Client ID 和 Client Secret

**2. 配置 `.env` 文件**：

```bash
# OpenAI OAuth credentials
OPENAI_CLIENT_ID=your_client_id_here
OPENAI_CLIENT_SECRET=your_client_secret_here
OPENAI_REDIRECT_URI=http://localhost:8080/callback

# 可选：已有的access token
# OPENAI_ACCESS_TOKEN=your_token_here
```

**3. 运行OAuth设置脚本**：

```bash
python scripts/setup_oauth.py --provider openai
```

或在代码中：

```python
from config.llm_config_oauth import setup_oauth_interactive

# 会打开浏览器完成OAuth流程
client = setup_oauth_interactive("openai")
```

**4. 使用OAuth认证**：

```python
from config.llm_config_oauth import get_llm

# 使用缓存的OAuth token
llm = get_llm(provider="openai", auth_method="oauth")
```

#### Anthropic OAuth说明

**注意**：Anthropic当前**主要使用API Key**，OAuth支持有限。

如果未来支持OAuth，配置方式类似：

```bash
# .env
ANTHROPIC_CLIENT_ID=your_client_id
ANTHROPIC_CLIENT_SECRET=your_client_secret
```

当前建议：**使用API Key认证**

---

## 完整使用示例

### 示例1：切换Provider

```python
from config.llm_config_oauth import get_llm

# 使用Anthropic Claude
claude = get_llm(provider="anthropic", model_type="sonnet")
response = claude.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Hello!"}]
)

# 切换到OpenAI GPT
gpt = get_llm(provider="openai", model_type="gpt-4")
response = gpt.chat.completions.create(
    model="gpt-4-turbo-preview",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### 示例2：统一接口调用

```python
from config.llm_config_oauth import get_llm_config_instance

# 获取配置实例
config = get_llm_config_instance(provider="anthropic", model_type="sonnet")

# 使用统一接口（自动处理provider差异）
response = config.call(
    messages=[{"role": "user", "content": "Explain quantum computing"}],
    max_tokens=2000,
    temperature=0.7,
    system="You are a helpful physics tutor"
)

# 无论provider是什么，接口一致
```

### 示例3：在Agent中使用不同Provider

修改 `agents/ideation_agent.py`：

```python
# 原来
from config.llm_config import get_llm

# 现在可以选择provider
from config.llm_config_oauth import get_llm

def __init__(self, ...):
    # 默认使用Anthropic
    self.llm = get_llm(provider="anthropic")

    # 或使用环境变量控制
    provider = os.getenv("IDEATION_PROVIDER", "anthropic")
    self.llm = get_llm(provider=provider)

    # 或使用OAuth
    self.llm = get_llm(provider="openai", auth_method="oauth")
```

### 示例4：混合使用多个Provider

```python
from config.llm_config_oauth import get_llm

# Ideation用Claude (擅长创造性思维)
ideation_llm = get_llm(provider="anthropic", model_type="sonnet")

# Planning用GPT-4 (擅长结构化规划)
planning_llm = get_llm(provider="openai", model_type="gpt-4")

# Experiment用Haiku (速度快，成本低)
experiment_llm = get_llm(provider="anthropic", model_type="haiku")
```

---

## OAuth Token管理

### Token缓存位置

```
data/auth/
├── anthropic_oauth_token.json
└── openai_oauth_token.json
```

### Token结构

```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "refresh_xxx",
  "expires_at": "2026-02-28T14:30:00",
  "token_type": "Bearer",
  "scope": "openai.api"
}
```

### Token自动刷新

系统会自动检测token过期并刷新：

```python
from config.auth_config import get_auth_config

config = get_auth_config(provider="openai", auth_method="oauth")

# 自动处理过期token
token = config.get_oauth_token()  # 如果过期，会自动刷新
```

### 手动刷新Token

```python
from config.auth_config import get_auth_config

config = get_auth_config(provider="openai", auth_method="oauth")
config._refresh_token()  # 强制刷新
```

### 清除Token（重新认证）

```bash
# 删除缓存的token
rm data/auth/openai_oauth_token.json

# 下次调用会触发新的OAuth流程
```

---

## 环境变量配置

完整的 `.env` 配置示例：

```bash
# ==================== LLM Provider选择 ====================
DEFAULT_LLM_PROVIDER=anthropic  # anthropic, openai, custom

# ==================== Anthropic (Claude) ====================
# API Key认证 (推荐)
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# OAuth认证 (未来支持)
# ANTHROPIC_CLIENT_ID=
# ANTHROPIC_CLIENT_SECRET=

# ==================== OpenAI (GPT) ====================
# API Key认证
OPENAI_API_KEY=sk-xxxxx

# OAuth认证
OPENAI_CLIENT_ID=your_openai_client_id
OPENAI_CLIENT_SECRET=your_openai_client_secret
OPENAI_REDIRECT_URI=http://localhost:8080/callback

# ==================== Per-Agent配置 ====================
# 可以为每个agent单独配置provider

# Ideation Agent
IDEATION_PROVIDER=anthropic  # 或 openai
IDEATION_AUTH_METHOD=api_key  # 或 oauth
IDEATION_MODEL=sonnet

# Planning Agent
PLANNING_PROVIDER=openai
PLANNING_AUTH_METHOD=oauth
PLANNING_MODEL=gpt-4

# Experiment Agent
EXPERIMENT_PROVIDER=anthropic
EXPERIMENT_AUTH_METHOD=api_key
EXPERIMENT_MODEL=haiku

# Writing Agent
WRITING_PROVIDER=anthropic
WRITING_AUTH_METHOD=api_key
WRITING_MODEL=sonnet

# ==================== Custom Provider ====================
CUSTOM_API_KEY=your_custom_key
CUSTOM_API_ENDPOINT=https://api.custom.com/v1
CUSTOM_BEARER_TOKEN=your_bearer_token
```

---

## OAuth设置脚本

创建 `scripts/setup_oauth.py`：

```python
#!/usr/bin/env python3
"""
Interactive OAuth setup script
"""

import argparse
from config.llm_config_oauth import setup_oauth_interactive


def main():
    parser = argparse.ArgumentParser(description="Setup OAuth authentication")
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default="openai",
        help="LLM provider to authenticate with"
    )

    args = parser.parse_args()

    print(f"\nStarting OAuth setup for {args.provider.upper()}...\n")

    try:
        client = setup_oauth_interactive(args.provider)
        print(f"\n✓ Success! OAuth configured for {args.provider}")
        print(f"You can now use: get_llm(provider='{args.provider}', auth_method='oauth')")

    except Exception as e:
        print(f"\n✗ OAuth setup failed: {e}")
        print("\nPlease check:")
        print(f"1. {args.provider.upper()}_CLIENT_ID is set in .env")
        print(f"2. {args.provider.upper()}_CLIENT_SECRET is set in .env")
        print(f"3. You have network access to {args.provider} OAuth endpoints")


if __name__ == "__main__":
    main()
```

**使用**：

```bash
# OpenAI OAuth
python scripts/setup_oauth.py --provider openai

# Anthropic OAuth (如果支持)
python scripts/setup_oauth.py --provider anthropic
```

---

## 安全最佳实践

### 1. 不要提交API Key到Git

```bash
# .gitignore 应包含
.env
data/auth/*.json
```

### 2. 使用环境变量

```bash
# 好 ✓
ANTHROPIC_API_KEY=sk-ant-xxx

# 不好 ✗ (硬编码在代码中)
api_key = "sk-ant-xxx"
```

### 3. 定期轮换API Key

建议每3-6个月更换一次API key。

### 4. OAuth Token安全

- Token文件设置正确的权限：
  ```bash
  chmod 600 data/auth/*.json
  ```
- 不要在日志中输出token
- 定期检查token过期时间

### 5. 使用不同的Key隔离环境

```bash
# 开发环境
ANTHROPIC_API_KEY_DEV=sk-ant-dev-xxx

# 生产环境
ANTHROPIC_API_KEY_PROD=sk-ant-prod-xxx
```

---

## 故障排查

### 问题1：OAuth认证失败

**症状**：`OAuth token not available`

**解决**：
1. 检查 `.env` 中 `CLIENT_ID` 和 `CLIENT_SECRET` 是否正确
2. 检查 `REDIRECT_URI` 是否与OAuth应用配置一致
3. 清除缓存token：`rm data/auth/openai_oauth_token.json`
4. 重新运行 `setup_oauth.py`

### 问题2：API Key无效

**症状**：`Invalid API key`

**解决**：
1. 确认 `.env` 文件已加载：`python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('ANTHROPIC_API_KEY'))"`
2. 验证key格式：
   - Anthropic: `sk-ant-api03-xxx`
   - OpenAI: `sk-xxx`
3. 检查key是否过期或被吊销
4. 在对应平台重新生成key

### 问题3：Token自动刷新失败

**症状**：Token过期后无法自动刷新

**解决**：
1. 检查refresh_token是否存在
2. 手动触发刷新：
   ```python
   from config.auth_config import get_auth_config
   config = get_auth_config(provider="openai", auth_method="oauth")
   config._refresh_token()
   ```
3. 如果失败，重新认证：`rm data/auth/*.json && python scripts/setup_oauth.py`

### 问题4：切换provider时认证错误

**症状**：切换provider后使用了错误的credentials

**解决**：
显式指定provider：
```python
# 清楚指定
llm = get_llm(provider="openai", auth_method="oauth")

# 而不是依赖默认值
llm = get_llm()  # 可能使用错误的provider
```

---

## API对比

### Anthropic vs OpenAI

| 特性 | Anthropic (Claude) | OpenAI (GPT) |
|-----|-------------------|--------------|
| **认证方式** | API Key (主要) | API Key, OAuth |
| **OAuth支持** | 有限 | 完整支持 |
| **Token刷新** | N/A | 支持 |
| **API风格** | messages.create() | chat.completions.create() |
| **System Prompt** | 独立参数 | 在messages数组中 |

### 统一接口的优势

使用 `UnifiedLLMConfig.call()` 可以屏蔽差异：

```python
from config.llm_config_oauth import get_llm_config_instance

# 不管provider是什么，接口一致
config = get_llm_config_instance(provider="anthropic")  # 或 "openai"

response = config.call(
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=1000,
    temperature=0.7,
    system="You are helpful"  # 自动适配不同provider
)
```

---

## 总结

### 推荐配置

**简单项目**：
```python
# 使用API Key，简单直接
llm = get_llm(provider="anthropic")
```

**企业项目**：
```python
# 使用OAuth，更安全
llm = get_llm(provider="openai", auth_method="oauth")
```

**混合使用**：
```python
# 不同agent使用不同provider
ideation = get_llm(provider="anthropic", model_type="sonnet")
planning = get_llm(provider="openai", model_type="gpt-4")
```

### 下一步

1. **配置 `.env`** - 添加你的API keys或OAuth credentials
2. **测试认证** - 运行 `python scripts/test_auth.py`
3. **选择provider** - 根据需求选择Anthropic或OpenAI
4. **可选：设置OAuth** - 如果需要更安全的认证，运行 `scripts/setup_oauth.py`

---

**需要帮助？**
- Anthropic API文档: https://docs.anthropic.com/
- OpenAI API文档: https://platform.openai.com/docs/
- OAuth 2.0规范: https://oauth.net/2/
