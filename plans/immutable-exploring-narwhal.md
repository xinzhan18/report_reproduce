# 量化因子研究 Pipeline 改造方案

## Context

当前 FARS 系统面向**交易策略研究**（momentum/mean-reversion → backtest → Sharpe/MaxDD）。
用户需要将其转型为**量化因子研究**系统：从论文中提取因子构造逻辑 → 实现因子计算代码 → 调用因子评估框架验证。

**核心简化点**：
- 场景聚焦：量化因子挖掘（A股 + 加密货币）
- 评估框架：用户提供 Python 库函数（类似 alphalens），ExperimentAgent 在 sandbox 中调用
- 数据来源：本地量价数据（格式待定，需设计接口）
- 保持 4 Agent 架构（Ideation → Planning → Experiment → Writing）

---

## 修改文件清单

### 新建 (1 文件)
| 文件 | 用途 |
|------|------|
| `market_data/local_data_loader.py` | 本地面板数据加载器（替代远程 DataFetcher） |

### 删除 (5 文件)
| 文件 | 原因 |
|------|------|
| `market_data/yfinance_source.py` | 远程数据获取，不再需要 |
| `market_data/akshare_source.py` | 远程数据获取，不再需要 |
| `market_data/ccxt_source.py` | 远程数据获取，不再需要 |
| `market_data/fetcher.py` | 被 LocalDataLoader 替代 |
| `market_data/base.py` | DataSource ABC 不再需要 |

### 修改 (15 文件)
| # | 文件 | 改动 |
|---|------|------|
| 1 | `core/state.py` | `ExperimentPlan`→`FactorPlan`, `BacktestResults`→`FactorResults` |
| 2 | `core/pipeline.py` | `DataFetcher`→`LocalDataLoader`, 更新 main() 输出 |
| 3 | `config/agent_config.py` | keywords 改为因子相关, validation_metrics 改为 IC/ICIR |
| 4 | `market_data/__init__.py` | 导出 `LocalDataLoader` |
| 5 | `agents/experiment/metrics.py` | `compute_metrics`→`evaluate_factor`（因子评估函数） |
| 6 | `agents/experiment/sandbox.py` | `inject_data` 支持面板数据, `inject_helpers` 注入 evaluate_factor |
| 7 | `agents/experiment/agent.py` | 全面替换：BacktestResults→FactorResults, 指标/分析/回写逻辑 |
| 8 | `agents/experiment/prompts.py` | 完整重写：因子计算+评估 workflow |
| 9 | `agents/experiment/tools.py` | submit_result schema 改为因子指标 |
| 10 | `agents/ideation/prompts.py` | 完整重写：因子构造逻辑提取 |
| 11 | `agents/ideation/agent.py` | `_build_ideation_markdown` 措辞微调 |
| 12 | `agents/planning/prompts.py` | 完整重写：因子测试方案设计 |
| 13 | `agents/planning/agent.py` | `_on_submit_result` 映射到 FactorPlan, `_build_plan_markdown` 更新 |
| 14 | `agents/writing/prompts.py` | 完整重写：因子研究报告格式 |
| 15 | `agents/writing/agent.py` | `_build_state_summary` 改为因子指标 |

---

## 核心设计

### 1. 数据类型 (`core/state.py`)

```python
class FactorPlan(TypedDict):
    objective: str
    factor_description: str       # 因子衡量什么
    factor_formula: str           # 公式或伪代码
    data_requirements: List[str]
    implementation_steps: List[str]
    test_universe: str            # "a_shares" | "crypto"
    test_period: str              # "2018-01-01 to 2024-12-31"
    rebalance_frequency: str      # "daily" | "weekly" | "monthly"
    success_criteria: Dict[str, float]  # {"ic_mean": 0.03, "icir": 0.5}
    risk_factors: List[str]
    estimated_runtime: str

class FactorResults(TypedDict):
    ic_mean: float              # Mean IC
    ic_std: float               # IC 标准差
    icir: float                 # IC / IC_std
    rank_ic_mean: float         # Mean Rank IC
    rank_icir: float            # Rank ICIR
    turnover_mean: float        # 平均换手率
    long_short_return: float    # 多空年化收益
    top_group_return: float     # 顶层分组年化收益
    bottom_group_return: float  # 底层分组年化收益
    monotonicity_score: float   # 分层单调性 (0-1)
    factor_coverage: float      # 因子覆盖率
```

ResearchState: `experiment_plan: FactorPlan`, `results_data: FactorResults`。其余不变。

### 2. 本地数据加载 (`market_data/local_data_loader.py`)

```python
class LocalDataLoader:
    """本地面板数据加载器。

    目录结构:
        data/market/a_shares/000001.SZ.csv
        data/market/a_shares/000002.SZ.csv
        data/market/crypto/BTCUSDT.csv

    CSV 格式: date,open,high,low,close,volume (DatetimeIndex)
    """
    def __init__(self, data_dir: str = "data/market"):
        ...

    def load(self, data_config: dict) -> dict[str, pd.DataFrame]:
        """根据 data_config 加载数据。

        data_config: {
            "market": "a_shares" | "crypto",
            "universe": "all" | ["000001.SZ", ...],
            "start_date": "2018-01-01",  # optional
            "end_date": "2024-12-31",    # optional
        }
        Returns: {symbol: DataFrame(date, OHLCV)}
        """
```

### 3. 因子评估函数 (`agents/experiment/metrics.py`)

替换 `compute_metrics` 为 `evaluate_factor`：

```python
def evaluate_factor(
    factor_values: pd.DataFrame,  # index=date, columns=symbols
    price_data: pd.DataFrame,     # index=date, columns=symbols (close)
    n_groups: int = 5,
    holding_period: int = 1,
) -> dict:
    """因子评估接口。返回 ic_mean/icir/rank_ic_mean/... 等指标。

    用户后续可替换函数体为自己的评估库。接口签名和返回 key 保持不变。
    """
```

提供一个基础的 IC 计算占位实现，用户后续替换为自己的评估库。

### 4. Sandbox 改造 (`agents/experiment/sandbox.py`)

**`inject_data`**：写入 per-symbol CSV + `data/panel.csv`（stacked format，含 symbol 列）+ manifest（含 total_symbols、columns）

**`inject_helpers`**：注入 `evaluate_factor.py`（替代 `compute_metrics.py`）

### 5. ExperimentAgent 关键改动

- `data_fetcher` → `data_loader` (LocalDataLoader)
- 必需指标：`["ic_mean", "icir"]`（替代 sharpe/drawdown/trades）
- `_map_to_backtest_results` → `_map_to_factor_results`
- `_analyze_results` prompt：评估因子质量（IC 水平、ICIR、单调性、换手率）
- verdict: "success"（IC/ICIR 达标）/ "revise_plan"（有改进方向）/ "accept_partial"
- `_check_success_criteria`：ic_mean >= threshold, icir >= threshold, turnover_mean <= threshold
- 产出文件名：`strategy.py` → `factor_code.py`, `backtest_results.json` → `factor_results.json`
- `_collect_code_from_sandbox`：排除 `evaluate_factor.py`（替代排除 `compute_metrics.py`）

### 6. Prompt 全面重写（4 个 Agent）

**IdeationAgent prompt**：
- 搜索方向：quantitative factors, alpha factors, cross-sectional predictors, factor zoo, anomalies
- 输出：因子构造逻辑、经济学直觉、适用市场
- hypothesis 格式：因子预测能力假设

**PlanningAgent prompt**：
- 读取 `literature/ideation.md` 中的因子假设
- 设计：因子公式、测试 universe、测试期间、再平衡频率
- success_criteria：IC/ICIR 阈值
- submit_result 格式新增 `factor_description`, `factor_formula`, `test_universe`, `test_period`, `rebalance_frequency`

**ExperimentAgent prompt**：
- workspace 中有 `evaluate_factor.py` 和 `data/panel.csv`
- 任务：加载数据 → 计算截面因子值 → 调用 evaluate_factor → 提交结果
- 数据加载 pattern：读 manifest → 构建 price_data matrix → 计算因子

**WritingAgent prompt**：
- 报告结构：Abstract → Introduction → Literature Review → Factor Construction → Evaluation Results → Discussion → Conclusion
- 上游文件：`ideation.md`, `plan.md`, `experiment.md`, `factor_results.json`, `factor_code.py`

### 7. Agent Config 更新 (`config/agent_config.py`)

```python
"ideation": {
    "keywords": [
        "quantitative factors", "alpha factors", "cross-sectional predictors",
        "factor investing", "anomalies", "factor zoo",
        "momentum factor", "value factor", "quality factor",
        "high-frequency factors", "machine learning factors",
        "cryptocurrency factors", "A-share factors",
    ],
    ...
}

"experiment": {
    "validation_metrics": {
        "min_ic_mean": 0.02,
        "min_icir": 0.3,
        "max_turnover": 0.8,
        "min_coverage": 0.5,
    },
    ...
}
```

---

## 实施顺序

```
Phase 1: 基础设施（无 Agent 依赖）
  [x] 1. core/state.py          → FactorPlan + FactorResults
  [x] 2. market_data/            → 删除 5 文件 + 新建 LocalDataLoader + 更新 __init__
  [x] 3. agents/experiment/metrics.py → evaluate_factor
  [x] 4. config/agent_config.py  → 因子关键词 + 因子验证阈值

Phase 2: ExperimentAgent（最复杂）
  [x] 5. agents/experiment/sandbox.py  → 面板数据注入 + evaluate_factor 注入
  [x] 6. agents/experiment/prompts.py  → 完整重写
  [x] 7. agents/experiment/tools.py    → submit_result schema
  [x] 8. agents/experiment/agent.py    → 全面替换

Phase 3: Pipeline + 上游 Agent
  [x] 9. core/pipeline.py              → DataFetcher → LocalDataLoader
  [x] 10. agents/ideation/prompts.py   → 因子研究 prompt
  [x] 11. agents/ideation/agent.py     → 微调
  [x] 12. agents/planning/prompts.py   → 因子规划 prompt
  [x] 13. agents/planning/agent.py     → FactorPlan 映射

Phase 4: Writing + 文档
  [x] 14. agents/writing/prompts.py    → 因子报告 prompt
  [x] 15. agents/writing/agent.py      → 因子指标摘要
  [x] 16. 文档更新（所有 CLAUDE.md + 文件头）
  [x] 17. AST 语法验证通过（18 文件）
```

---

## 验证

1. **AST 语法检查**：所有修改 .py 文件 `ast.parse()` 通过
2. **类型兼容**：`create_initial_state()` 正确初始化 FactorPlan/FactorResults
3. **数据加载**：创建 2 个 symbol 测试数据 → LocalDataLoader.load() 返回正确 dict
4. **Sandbox 注入**：验证 sandbox 中存在 `evaluate_factor.py` + `data/panel.csv` + per-symbol CSV
5. **评估函数**：用随机数据调用 `evaluate_factor()` → 返回包含所有必需 key 的 dict
6. **Pipeline 路由**：feedback.verdict="revise_plan" + iteration=0 → 路由到 "planning"
7. **端到端**：用测试数据跑完整 pipeline，验证各 .md 文件产出和因子指标
