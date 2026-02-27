# Research Automation Agent System (FARS)

A fully automated research system for quantitative finance that orchestrates the entire research lifecycle—from literature review to experiment execution to report generation—using a multi-agent collaboration architecture powered by Claude AI.

## Overview

This system automates quantitative finance research through four specialized AI agents:

1. **Ideation Agent** (构思智能体) - Literature scanning, gap analysis, and hypothesis generation
2. **Planning Agent** (规划智能体) - Experiment design and methodology planning
3. **Experiment Agent** (实验智能体) - Strategy code generation and backtest execution
4. **Writing Agent** (报告智能体) - Research report generation and documentation

### Key Features

- 🤖 **Fully Automated Pipeline**: End-to-end automation from paper discovery to report generation
- 📚 **Literature Intelligence**: Automatic scanning of arXiv, SSRN, and other academic sources
- 📊 **Quantitative Backtesting**: Integrated backtesting engine using Backtrader
- 🔄 **State Persistence**: LangGraph-powered checkpointing for resume capability
- 📅 **Scheduled Scanning**: Daily automated paper scanning and research initiation
- 📝 **Academic Reports**: Generates publication-ready research reports

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Research Pipeline                          │
│                                                               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐│
│  │Ideation  │───▶│Planning  │───▶│Experiment│───▶│Writing ││
│  │Agent     │    │Agent     │    │Agent     │    │Agent   ││
│  └──────────┘    └──────────┘    └──────────┘    └────────┘│
│       │               │                 │              │     │
│       ▼               ▼                 ▼              ▼     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │        Shared File System (Persistence Layer)         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

#### Ideation Agent
- Scans arXiv (q-fin, stat.ML, cs.LG categories) daily
- Analyzes literature and identifies trends
- Discovers research gaps in quantitative finance
- Generates testable hypotheses

#### Planning Agent
- Transforms hypotheses into executable experiment plans
- Designs methodology and approach
- Specifies data requirements and success criteria
- Validates feasibility

#### Experiment Agent
- Generates Python strategy code from plans
- Executes backtests on historical financial data
- Calculates performance metrics (Sharpe, returns, drawdown, etc.)
- Validates results against success criteria

#### Writing Agent
- Integrates outputs from all previous agents
- Generates structured academic reports
- Formats for review and audit
- Creates comprehensive documentation

## Installation

### Prerequisites

- Python 3.10 or higher
- Anthropic API key (Claude 4.5/4.6)
- Internet connection for data fetching

### Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd report_reproduce
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

Note: `ta-lib` may require additional system dependencies. On Windows, download the wheel from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib).

3. **Configure environment variables**:
```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=your_api_key_here
```

4. **Verify installation**:
```bash
python -m pytest tests/
```

## Usage

### Running a Single Research Project

```python
from core.pipeline import run_research_pipeline

# Run complete research pipeline
result = run_research_pipeline(
    research_direction="momentum strategies in equity markets"
)

print(f"Status: {result['status']}")
print(f"Report: {result['report_path']}")
```

### Command Line Usage

```bash
# Run research pipeline
python -m core.pipeline "momentum strategies in quantitative finance"

# Run daily scanner once
python -m scheduler.daily_scan --mode once

# Start daily scheduler (scans at 8 AM daily)
python -m scheduler.daily_scan --mode daily --time 08:00

# Run scanner every 12 hours
python -m scheduler.daily_scan --mode interval --interval 12
```

### Using Pipeline Runner

```python
from scheduler.pipeline_runner import PipelineRunner

runner = PipelineRunner()

# Run a project
result = runner.run_project(
    research_direction="factor models in emerging markets"
)

# List all projects
projects = runner.list_projects()

# Resume a project from checkpoint
result = runner.resume_project(project_id="2026-02-27_momentum_strategies")

# Get statistics
stats = runner.get_statistics()
print(f"Success rate: {stats['success_rate']:.1f}%")
```

## Project Structure

```
report_reproduce/
├── agents/                    # Core agents
│   ├── ideation_agent.py     # Literature review & hypothesis
│   ├── planning_agent.py     # Experiment design
│   ├── experiment_agent.py   # Backtest execution
│   └── writing_agent.py      # Report generation
├── config/                    # Configuration
│   ├── agent_config.py       # Agent settings
│   ├── llm_config.py         # Claude API config
│   └── data_sources.py       # Data source configs
├── core/                      # Core system
│   ├── state.py              # State definitions
│   ├── persistence.py        # Checkpointing
│   └── pipeline.py           # Pipeline orchestration
├── tools/                     # Utility tools
│   ├── paper_fetcher.py      # arXiv API wrapper
│   ├── file_manager.py       # File operations
│   ├── data_fetcher.py       # Financial data (yfinance)
│   └── backtest_engine.py    # Backtrader wrapper
├── scheduler/                 # Automation
│   ├── daily_scan.py         # Daily paper scanner
│   └── pipeline_runner.py    # Pipeline manager
├── data/                      # Data storage
│   ├── literature/           # Cached papers
│   └── checkpoints/          # State checkpoints
├── outputs/                   # Research outputs
│   └── {project_id}/         # Per-project outputs
├── tests/                     # Test suite
├── requirements.txt
├── README.md
└── CLAUDE.md                 # Development guide
```

## Configuration

### Agent Configuration

Edit `config/agent_config.py` to customize agent behavior:

```python
AGENT_CONFIG = {
    "ideation": {
        "model": "sonnet",          # Claude model
        "temperature": 0.7,         # Creativity level
        "focus_categories": [...],  # arXiv categories
        "keywords": [...],          # Search keywords
    },
    # ... other agents
}
```

### Data Sources

Configure in `config/data_sources.py`:

```python
FINANCIAL_DATA_CONFIG = {
    "primary_source": "yfinance",
    # Add API keys for premium data sources
}
```

## Performance Metrics

The system calculates comprehensive backtesting metrics:

- **Returns**: Total return, CAGR, annualized return
- **Risk**: Volatility, max drawdown, VaR, CVaR
- **Risk-Adjusted**: Sharpe ratio, Sortino ratio, Calmar ratio
- **Trade Statistics**: Win rate, profit factor, trade duration
- **Robustness**: Out-of-sample performance

## Output Structure

Each research project creates:

```
outputs/{project_id}/
├── literature/
│   ├── papers_analyzed.json      # Paper metadata
│   ├── literature_summary.md     # Literature review
│   └── hypothesis.md             # Research hypothesis
├── experiments/
│   ├── experiment_plan_v1.json   # Experiment design
│   ├── strategy.py               # Generated strategy code
│   ├── backtest_results.json     # Performance metrics
│   └── execution_logs.txt        # Execution logs
└── reports/
    ├── final_report.md           # Main report (Markdown)
    └── final_report_formatted.md # HTML-friendly version
```

## Strategy Types Supported

The system can generate and test various quantitative strategies:

1. **Momentum Strategies**: Trend following, moving average crossovers
2. **Mean Reversion**: Pairs trading, statistical arbitrage
3. **Factor Models**: Value, momentum, quality factors
4. **Technical Indicators**: RSI, MACD, Bollinger Bands
5. **Risk Parity**: Portfolio allocation strategies

## Limitations

- **Domain**: Currently focused on quantitative finance research
- **Compute**: Designed for CPU-only environments (no ML training)
- **Data**: Limited to publicly available financial data (Yahoo Finance, etc.)
- **Review**: Human review required before publication
- **Execution**: No live trading integration

## Development

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_agents.py

# Run with coverage
pytest --cov=. tests/
```

### Adding New Agents

1. Create agent class in `agents/` directory
2. Implement `__call__(state: ResearchState) -> ResearchState`
3. Add to pipeline in `core/pipeline.py`
4. Update configuration in `config/agent_config.py`

### Extending Data Sources

Add new data sources in `tools/data_fetcher.py`:

```python
class FinancialDataFetcher:
    def fetch_from_new_source(self, symbol):
        # Implementation
        pass
```

## Troubleshooting

### Common Issues

**1. API Rate Limits**
- arXiv: Max 1 request/second (handled automatically)
- yfinance: Conservative rate limiting implemented

**2. Missing Data**
- Verify symbol exists and has historical data
- Check date range is valid

**3. Strategy Execution Errors**
- Review `execution_logs.txt` in project directory
- Check strategy code in `experiments/strategy.py`

**4. LLM API Errors**
- Verify ANTHROPIC_API_KEY is set
- Check API quota and limits

## Roadmap

- [ ] Multi-backtesting engine comparison (VectorBT, Zipline)
- [ ] Walk-forward optimization
- [ ] Monte Carlo simulation for robustness
- [ ] Portfolio-level backtesting
- [ ] Real-time monitoring dashboard
- [ ] Integration with broker APIs for paper trading

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

[Specify License]

## Citation

If you use this system in your research, please cite:

```bibtex
@software{research_automation_2026,
  title={Research Automation Agent System for Quantitative Finance},
  author={[Your Name]},
  year={2026},
  url={[Repository URL]}
}
```

## Contact

For questions or support, please open an issue on GitHub.

---

**Disclaimer**: This system is for research purposes only. Generated strategies should be thoroughly validated before any real-world application. Past performance does not guarantee future results.
