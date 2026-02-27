# agents/utils/ - Agent工具层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 为Agent提供通用工具函数,包括JSON解析和Prompt构建
2. **依赖**: json (标准库), typing (类型系统), 无外部核心依赖
3. **输出**: JSONParser (JSON提取和验证), PromptBuilder (Prompt模板构建),被所有Agent使用

## 文件清单

### json_parser.py
- **角色**: JSON解析工具 (Parser & Validator)
- **功能**: 从LLM输出中提取JSON,处理markdown代码块、验证schema、错误恢复

### prompt_builder.py
- **角色**: Prompt构建工具 (Template Builder)
- **功能**: 构建结构化的Agent Prompt,支持模板变量替换、上下文注入、格式化

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出工具类,提供统一的包接口

## 更新历史

- 2026-02-27: 创建此文档,记录当前架构
