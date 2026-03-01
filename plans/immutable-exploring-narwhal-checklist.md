# FARS 10 项问题修复 — 执行检查清单

## 批次 1：简单修复
- [x] Issue 3: PlanningAgent prompts.py `structured_insights.json` → `papers_analyzed.json`
- [x] Issue 4: WritingAgent prompts.py 删除 `run_python` 引用 (prompt + tools.py + agent.py)
- [x] Issue 5: base_agent.py `state["error"]` → `state["error_log"]`

## 批次 2：指标计算修复
- [x] Issue 1: metrics.py Sortino ratio 双重年化 — 移除 `* np.sqrt(252)` 于 downside std
- [x] Issue 2: backtest_engine.py 假指标替换:
  - [x] 添加 TimeReturn analyzer
  - [x] 提取日收益率序列
  - [x] 计算真实 CAGR/Volatility/Sortino/Calmar

## 批次 3：架构优化
- [x] Issue 7: 新建 `agents/common_tools.py` (4 schema + 4 executor + get_common_tools)
- [x] Issue 7: ideation/tools.py 删除重复代码，导入 common_tools
- [x] Issue 7: planning/tools.py 删除重复代码，导入 common_tools
- [x] Issue 7: experiment/tools.py 删除重复代码，导入 common_tools
- [x] Issue 7: writing/tools.py 删除重复代码，导入 common_tools
- [x] Issue 6: 删除 config/multi_llm_config.py
- [x] Issue 6: 删除 config/llm_config_oauth.py
- [x] Issue 6: 删除 config/auth_config.py
- [x] Issue 6: 删除 scripts/setup_oauth.py
- [x] Issue 6: 删除 scripts/test_auth.py

## 批次 4：清理和增强
- [x] Issue 8: 删除 core/ 死代码 (5 文件)
- [x] Issue 8: 删除依赖已删模块的 tests/scripts (4 文件)
- [x] Issue 8: ideation/agent.py 删除 `core.document_memory_manager` 注释
- [x] Issue 9: base_agent.py 添加 token 计数器 (循环前/每轮/循环后)
- [x] Issue 10: sandbox.py 增强黑名单 + 元字符检测 + shell=False + shlex.split + FileNotFoundError

## 文档更新
- [x] agents/CLAUDE.md: 添加 common_tools.py 条目 + 更新 writing 工具数
- [x] agents/writing/CLAUDE.md: 工具数 6→5, 通用工具说明
- [x] agents/experiment/CLAUDE.md: sandbox 安全增强说明, 通用工具说明
- [x] agents/ideation/CLAUDE.md: 通用工具说明
- [x] agents/planning/CLAUDE.md: 通用工具说明 + prompt 修正
- [x] config/CLAUDE.md: 移除 3 个文件条目, 添加已删除段
- [x] core/CLAUDE.md: 移除 5 个文件条目, 添加已删除段
- [x] tools/CLAUDE.md: backtest_engine 描述更新

## 验证
- [x] AST 语法检查通过 (所有 13 个修改文件)
- [x] writing/agent.py include_python 参数已清理

最后执行日期: 2026-03-01
