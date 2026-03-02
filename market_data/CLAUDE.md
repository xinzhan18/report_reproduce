# market_data/ - 本地面板数据加载模块

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 从本地 CSV 文件加载量价面板数据（A 股 + 加密货币）
2. **依赖**: pandas, pathlib, json, logging
3. **输出**: LocalDataLoader 类，被 ExperimentAgent 调用

## 架构模式

```
LocalDataLoader  ← local_data_loader.py
  └─ load(data_config) → Dict[str, DataFrame]  ← ExperimentAgent 唯一入口

数据目录结构:
  data/market/a_shares/000001.SZ.csv
  data/market/crypto/BTCUSDT.csv
```

## 文件清单

### local_data_loader.py
- **角色**: 本地面板数据加载器
- **功能**: 从 data/market/{market}/ 目录加载 CSV 文件，支持 universe 过滤和日期范围过滤

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出 LocalDataLoader

## 已删除文件

- `base.py` → 删除 (DataSource ABC 不再需要)
- `yfinance_source.py` → 删除 (远程数据获取，改为本地加载)
- `akshare_source.py` → 删除 (远程数据获取，改为本地加载)
- `ccxt_source.py` → 删除 (远程数据获取，改为本地加载)
- `fetcher.py` → 删除 (被 LocalDataLoader 替代)

## 更新历史

- 2026-03-02: 因子研究改造：删除全部远程数据源 + DataFetcher，新建 LocalDataLoader 本地面板数据加载器
- 2026-03-01: 创建模块，从 tools/data_fetcher.py 迁移并扩展为多市场数据层
