# tools/ - 工具库层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 提供外部数据获取、文件管理、回测执行等工具能力
2. **依赖**: arxiv SDK (论文检索), yfinance (金融数据), backtrader (回测框架), PyPDF2 (PDF解析)
3. **输出**: PaperFetcher, DataFetcher, BacktestEngine, FileManager等工具类,被Agent层调用

## 文件清单

### paper_fetcher.py
- **角色**: 论文获取工具 (Paper Retrieval)
- **功能**: 从arXiv检索学术论文,支持关键词搜索、ID查询、相关性过滤

### data_fetcher.py
- **角色**: 金融数据获取工具 (Financial Data Fetcher)
- **功能**: 从Yahoo Finance获取股票/指数数据,支持历史数据、实时行情

### backtest_engine.py
- **角色**: 回测引擎 (Backtesting Engine)
- **功能**: 使用Backtrader执行策略回测,计算收益率、夏普比率等指标

### file_manager.py
- **角色**: 文件管理器 (File Manager)
- **功能**: 统一管理项目文件的读写、目录结构、路径解析

### pdf_reader.py
- **角色**: PDF阅读器 (PDF Parser)
- **功能**: 解析PDF论文内容,提取文本、元数据、引用信息

### citation_manager.py
- **角色**: 引用管理器 (Citation Manager)
- **功能**: 管理论文引用关系,生成引用格式(BibTeX/APA),构建引用网络

### smart_literature_access.py
- **角色**: 智能文献访问 (Smart Literature Access)
- **功能**: 智能路由文献访问方式,优先使用本地缓存,按需下载,支持多源检索

### domain_classifier.py
- **角色**: 领域分类器 (Domain Classifier)
- **功能**: 对论文进行领域分类,识别研究主题,支持多标签分类

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出所有工具类,提供统一的包接口

## 更新历史

- 2026-02-27: 创建此文档,记录当前架构
