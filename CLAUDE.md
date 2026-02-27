# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**Research Automation Agent System (FARS)** - A fully automated research system for quantitative finance that orchestrates the entire research lifecycle using a multi-agent collaboration architecture powered by Claude AI (Anthropic API).

This system automates quantitative finance research from literature review through experiment execution to report generation using four specialized AI agents working in a pipeline.

## System Architecture

### Core Components

1. **Four Specialized Agents** (`agents/`)
   - **IdeationAgent**: Literature scanning, gap analysis, hypothesis generation
   - **PlanningAgent**: Experiment design and methodology planning
   - **ExperimentAgent**: Strategy code generation and backtest execution
   - **WritingAgent**: Research report generation and documentation

2. **LangGraph Pipeline** (`core/pipeline.py`)
   - Orchestrates agent workflow with state management
   - Implements checkpointing and resume capability
   - Conditional routing for error handling and retries

3. **State Management** (`core/state.py`)
   - `ResearchState`: TypedDict flowing through all agents
   - Persistent checkpointing using SQLite (LangGraph)
   - Tracks all outputs and metadata

4. **Tools & Utilities** (`tools/`)
   - `PaperFetcher`: arXiv API wrapper for academic papers
   - `FinancialDataFetcher`: yfinance integration for market data
   - `BacktestEngine`: Backtrader wrapper for strategy testing
   - `FileManager`: File I/O and project organization

5. **Scheduler & Automation** (`scheduler/`)
   - `DailyScanner`: Automated paper scanning and research initiation
   - `PipelineRunner`: Project execution and monitoring

## Technology Stack

- **Language**: Python 3.10+
- **LLM Framework**: LangGraph + Anthropic SDK
- **AI Models**: Claude 4.5 Sonnet (complex tasks), Claude 4.5 Haiku (simple tasks)
- **Backtesting**: Backtrader
- **Data Sources**: yfinance (Yahoo Finance), arXiv API
- **Storage**: SQLite for checkpointing, JSON for outputs
- **Testing**: pytest

## Repository Structure

```
report_reproduce/
├── agents/              # Four core agents
├── config/              # Configuration files
├── core/                # State management & pipeline
├── tools/               # Utility tools
├── scheduler/           # Automation & scheduling
├── data/                # Data storage (literature, checkpoints)
├── outputs/             # Research project outputs
└── tests/               # Test suite
```

## Development Workflow

### Running the System

1. **Setup Environment**:
```bash
pip install -r requirements.txt
cp .env.example .env
# Add ANTHROPIC_API_KEY to .env
```

2. **Run a Research Project**:
```bash
python -m core.pipeline "momentum strategies in equity markets"
```

3. **Run Daily Scanner**:
```bash
python -m scheduler.daily_scan --mode once
```

### Adding New Features

**Adding a New Agent**:
1. Create class in `agents/` inheriting agent pattern
2. Implement `__call__(state: ResearchState) -> ResearchState`
3. Add node to pipeline in `core/pipeline.py`
4. Update `config/agent_config.py` with settings

**Adding Data Sources**:
1. Extend `tools/data_fetcher.py` with new fetcher methods
2. Update `config/data_sources.py` with API configs
3. Add API key to `.env.example`

**Adding Backtest Engines**:
1. Create wrapper in `tools/` following `BacktestEngine` pattern
2. Implement standardized result format (`BacktestResults`)
3. Update `ExperimentAgent` to support new engine

## Key Design Patterns

### Agent Pattern
All agents follow this structure:
```python
class Agent:
    def __init__(self, llm, tools...):
        self.llm = llm
        self.config = get_agent_config("agent_name")

    def __call__(self, state: ResearchState) -> ResearchState:
        # 1. Update status
        state["status"] = "agent_stage"

        # 2. Process inputs
        result = self.process(state)

        # 3. Update state with outputs
        state["output_field"] = result

        # 4. Save artifacts to file system
        self.file_manager.save_text(...)

        return state
```

### State Flow
```
create_initial_state()
  → IdeationAgent (papers, hypothesis)
  → PlanningAgent (experiment_plan, methodology)
  → ExperimentAgent (code, results)
  → WritingAgent (report)
  → completed
```

### Persistence
- LangGraph SQLite checkpointer saves state after each agent
- File system stores all artifacts in `outputs/{project_id}/`
- Can resume any project from last checkpoint

## Configuration

### Agent Settings (`config/agent_config.py`)
```python
AGENT_CONFIG = {
    "ideation": {
        "model": "sonnet",
        "temperature": 0.7,
        "focus_categories": ["q-fin.RM", "q-fin.PM", ...],
        "keywords": ["momentum", "mean reversion", ...]
    },
    # ... other agents
}
```

### LLM Models (`config/llm_config.py`)
- **Sonnet** (default): Complex reasoning, planning, code generation
- **Haiku**: Simple tasks, cost optimization
- **Opus**: Reserved for most challenging tasks (optional)

## Testing

Run tests:
```bash
# All tests
pytest tests/

# Specific tests
pytest tests/test_agents.py
pytest tests/test_pipeline.py

# With coverage
pytest --cov=. tests/
```

## Important Notes

### API Usage
- **Anthropic API**: Required for all agents (set `ANTHROPIC_API_KEY`)
- **arXiv API**: Free, rate limited (1 req/sec)
- **yfinance**: Free, conservative rate limiting implemented

### Compute Requirements
- **CPU-only**: No GPU required (quantitative backtesting, not ML training)
- **Memory**: ~2GB for typical research project
- **Storage**: ~100MB per project (papers, results, reports)

### Limitations
- **Domain**: Quantitative finance only (no general research yet)
- **Data**: Public data sources only (Yahoo Finance)
- **Review**: Human review required before publication
- **Execution**: No live trading integration

## Common Development Tasks

### Debugging a Failed Pipeline
```python
from scheduler.pipeline_runner import PipelineRunner

runner = PipelineRunner()
# Resume from checkpoint to continue
result = runner.resume_project("2026-02-27_project_id")
```

### Inspecting Project Outputs
```
outputs/{project_id}/
├── literature/          # Papers, hypothesis
├── experiments/         # Strategy code, results
└── reports/             # Final report
```

### Modifying Prompts
Agent prompts are in each agent's implementation:
- `agents/ideation_agent.py`: Literature analysis prompts
- `agents/planning_agent.py`: Experiment design prompts
- `agents/experiment_agent.py`: Code generation prompts
- `agents/writing_agent.py`: Report writing prompts

### Adjusting Success Criteria
Edit `config/agent_config.py`:
```python
"experiment": {
    "validation_metrics": {
        "min_sharpe_ratio": 0.5,
        "min_trades": 10,
        "max_drawdown_threshold": 0.5
    }
}
```

## Error Handling

The pipeline includes:
- **Retry Logic**: Failed experiments retry up to 2 times
- **Conditional Routing**: Routes to error handler on failures
- **Checkpointing**: Can resume from any point
- **Logging**: All execution logs saved to project directory

## Future Enhancements

High-priority items:
1. Multi-engine backtesting comparison
2. Walk-forward optimization
3. Portfolio-level strategies
4. Real-time monitoring dashboard
5. Background execution with multiprocessing

## Contributing Guidelines

1. Follow existing agent patterns
2. Add tests for new functionality
3. Update configuration files
4. Document new features in README
5. Maintain backward compatibility

## Performance Considerations

- **LLM Calls**: Each agent makes 2-5 API calls (optimize with caching if needed)
- **Backtesting**: Typically 10-60 seconds for 5-10 years of daily data
- **Full Pipeline**: 5-15 minutes per research project (end-to-end)
- **Cost**: ~$0.50-2.00 per project (Claude API costs)

## Security & Privacy

- **API Keys**: Store in `.env`, never commit
- **Data**: All project data stored locally
- **Papers**: Cached locally, respect arXiv ToS
- **Reports**: Not automatically published (human review required)

---

**For questions or issues**: Review code comments, check test files, or consult the main README.md
