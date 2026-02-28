# market_data/ - 数据层模块

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 提供统一的多市场金融数据获取接口（美股/港股/A股/加密货币）
2. **依赖**: yfinance (美股/港股), akshare (A股, 可选), ccxt (加密货币, 可选), pandas
3. **输出**: DataFetcher 路由器 + DataSource 抽象基类，被 ExperimentAgent 调用

## 架构模式

Strategy Pattern: DataSource 抽象基类定义统一接口，各数据源实现具体逻辑。
DataFetcher 路由器根据 market 类型分发到对应 DataSource。
可选依赖（akshare、ccxt）import 失败时 graceful skip。

```
DataSource (ABC)  ← base.py
  ├─ YFinanceSource  ← yfinance_source.py (us_equity, hk_equity)
  ├─ AkShareSource   ← akshare_source.py  (cn_equity, 需 pip install akshare)
  └─ CCXTSource      ← ccxt_source.py     (crypto, 需 pip install ccxt)

DataFetcher  ← fetcher.py
  └─ fetch(data_config) → Dict[str, DataFrame]  ← ExperimentAgent 唯一入口
```

## 文件清单

### base.py
- **角色**: 数据源抽象基类
- **功能**: 定义 DataSource ABC，统一 fetch() 和 available_markets() 接口

### yfinance_source.py
- **角色**: 美股/港股数据源
- **功能**: 使用 yfinance 库获取 Yahoo Finance OHLCV 数据

### akshare_source.py
- **角色**: A 股数据源
- **功能**: 使用 akshare 库获取 A 股前复权 OHLCV 数据（需安装 akshare）

### ccxt_source.py
- **角色**: 加密货币数据源
- **功能**: 使用 ccxt 库从交易所获取加密货币 OHLCV 数据（需安装 ccxt）

### fetcher.py
- **角色**: DataFetcher 路由器
- **功能**: 根据 data_config.market 分发到对应 DataSource，提供 fetch() 和 fetch_single_symbol() 方法

### __init__.py
- **角色**: 模块初始化
- **功能**: 导出 DataFetcher 和 DataSource

## 更新历史

- 2026-03-01: 创建模块，从 tools/data_fetcher.py 迁移并扩展为多市场数据层
