# scheduler/ - 调度自动化层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 实现系统的自动化调度,包括定时论文扫描和Pipeline执行
2. **依赖**: core/pipeline (Pipeline编排器), tools/paper_fetcher (论文获取), schedule库 (定时任务)
3. **输出**: DailyScanner (每日文献扫描器), PipelineRunner (Pipeline执行器),实现完全自动化的研究流程

## 文件清单

### daily_scan.py
- **角色**: 每日扫描器 (Daily Scanner)
- **功能**: 定时扫描arXiv新论文,识别研究机会,自动触发Pipeline执行

### pipeline_runner.py
- **角色**: Pipeline执行器 (Pipeline Runner)
- **功能**: 管理Pipeline的启动、监控、重试、日志记录,支持批量项目执行

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出调度类,提供统一的包接口

## 更新历史

- 2026-02-27: 创建此文档,记录当前架构
