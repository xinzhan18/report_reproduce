# Upgrade Guide - Enhanced Features

本文档说明了新增的工程化改进功能。

## 🎯 新增功能概览

### 1. **多API Key支持**
每个agent可以使用不同的API key和LLM模型。

### 2. **增强数据持久化**
- 完整的数据库schema（SQLite）
- 文档阅读历史追踪
- 引用自动管理

### 3. **PDF阅读支持**
- 自动下载arXiv PDF
- 文本提取和分析
- 内容搜索

### 4. **迭代记忆系统**
- 记录每轮发现、问题、改进
- 跨项目学习
- 智能迭代决策

### 5. **引用管理系统**
- 自动生成引用
- 多种引用格式（APA, IEEE, Chicago）
- BibTeX导出

## 📚 数据库Schema

新增数据库表：

```sql
- papers              # 所有查看过的论文
- citations           # 引用记录
- projects            # 研究项目
- iterations          # 迭代历史
- memories            # 跨项目记忆
- agent_executions    # Agent执行日志
- document_access_log # 文档访问日志
```

## 🔑 配置多API Key

### 方法1：环境变量

```bash
# 每个agent独立配置
IDEATION_API_KEY=sk-ant-xxx
PLANNING_API_KEY=sk-ant-yyy
EXPERIMENT_API_KEY=sk-ant-zzz
WRITING_API_KEY=sk-ant-www
```

### 方法2：JSON配置文件

创建 `config/llm_keys.json`:

```json
{
  "ideation": {
    "provider": "anthropic",
    "api_key": "your_key",
    "model_id": "claude-sonnet-4-5-20250929",
    "temperature": 0.7
  },
  "experiment": {
    "provider": "openai",
    "api_key": "your_openai_key",
    "model_id": "gpt-4-turbo-preview",
    "temperature": 0.2
  }
}
```

## 📖 使用PDF阅读功能

```python
from tools.pdf_reader import PDFReader

# 初始化PDF阅读器
pdf_reader = PDFReader()

# 下载并分析PDF
arxiv_id = "2301.12345"
summary = pdf_reader.get_paper_summary(arxiv_id)

print(f"Has PDF: {summary['has_pdf']}")
print(f"Sections: {summary['sections'].keys()}")

# 搜索PDF内容
results = pdf_reader.search_pdf_content(
    arxiv_id,
    search_terms=["momentum", "sharpe ratio"]
)
```

## 📝 使用引用管理

```python
from tools.citation_manager import CitationManager

# 创建引用管理器
citations = CitationManager(
    project_id="my_project",
    citation_style="APA"  # 或 IEEE, Chicago, Harvard
)

# 添加引用
cite_key = citations.cite_paper(
    arxiv_id="2301.12345",
    context="This approach was inspired by..."
)

# 生成参考文献列表
bibliography = citations.generate_bibliography()

# 导出BibTeX
bibtex = citations.export_bibtex()
```

## 🔄 使用迭代记忆

```python
from core.iteration_memory import IterationMemory, IterationAnalyzer

# 初始化迭代记忆
memory = IterationMemory(project_id="my_project")

# 开始新迭代
iteration_id = memory.start_iteration(
    iteration_number=1,
    agent_name="experiment"
)

# 记录发现
memory.record_finding(
    "Strategy performs well in trending markets",
    importance=0.9,
    tags=["momentum", "trend"]
)

# 记录问题
memory.record_issue(
    "High drawdown during market reversals",
    severity="high",
    tags=["risk", "drawdown"]
)

# 记录改进建议
memory.record_improvement(
    "Add volatility filter to reduce whipsaws",
    category="methodology",
    tags=["filter", "risk_management"]
)

# 完成迭代
memory.complete_iteration(
    iteration_id=iteration_id,
    status="success",
    findings=["Finding 1", "Finding 2"],
    issues=["Issue 1"],
    improvements=["Improvement 1"],
    metrics={"sharpe_ratio": 1.2}
)

# 获取历史
previous_findings = memory.get_previous_findings()
summary = memory.get_iteration_summary()

# 决定是否继续迭代
should_continue, reason = memory.should_continue_iterating()
```

## 💾 数据库查询示例

```python
from core.database import get_database

db = get_database()

# 查看所有项目
projects = db.conn.execute("SELECT * FROM projects").fetchall()

# 查看某个项目的所有引用
citations = db.get_citations("project_id_here")

# 查看迭代历史
iterations = db.get_iteration_history("project_id_here")

# 查看记忆/学习
memories = db.get_relevant_memories(memory_type="improvement", limit=10)

# 检查文档是否已读
has_read = db.has_paper_been_read("2301.12345", "project_id")
```

## 🎨 新的工作流程

### 完整工作流with新功能:

```python
from core.pipeline import run_research_pipeline
from core.database import get_database
from tools.citation_manager import CitationManager
from tools.pdf_reader import PDFReader
from core.iteration_memory import IterationMemory

# 1. 运行研究流程
result = run_research_pipeline("momentum strategies")

project_id = result["project_id"]

# 2. 检查引用
db = get_database()
citations = db.get_citations(project_id)
print(f"Total citations: {len(citations)}")

# 3. 生成完整参考文献
citation_mgr = CitationManager(project_id, citation_style="APA")
bibliography = citation_mgr.generate_bibliography()

# 4. 查看迭代历史
memory = IterationMemory(project_id)
summary = memory.get_iteration_summary()
print(summary)

# 5. 下载所有引用的PDF
pdf_reader = PDFReader()
for citation in citations:
    arxiv_id = citation["arxiv_id"]
    pdf_reader.download_pdf(arxiv_id)
```

## 📊 监控和统计

```python
from config.multi_llm_config import get_llm_manager
from core.database import get_database

# LLM配置统计
llm_mgr = get_llm_manager()
stats = llm_mgr.get_statistics()
print(f"Configured agents: {stats['agents']}")
print(f"Providers: {stats['providers']}")

# 数据库统计
db = get_database()

# 总论文数
total_papers = db.conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]

# 总引用数
total_citations = db.conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0]

# 总记忆数
total_memories = db.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

print(f"Papers in database: {total_papers}")
print(f"Total citations: {total_citations}")
print(f"Memories stored: {total_memories}")
```

## 🔧 依赖更新

新增依赖项需要安装：

```bash
pip install PyPDF2  # PDF读取
```

在 `requirements.txt` 中已包含。

## 🚀 迁移现有项目

如果您有使用旧版本创建的项目：

1. **备份数据**：
```bash
cp -r outputs outputs_backup
```

2. **运行数据库初始化**：
```python
from core.database import get_database
db = get_database()  # 自动创建所有表
```

3. **可选：导入旧项目数据**：
```python
# 手动导入旧项目的论文和引用到新数据库
```

## ⚙️ 配置选项

### .env 新增选项:

```bash
# 引用格式
CITATION_STYLE=APA

# PDF缓存
PDF_CACHE_ENABLED=true
PDF_AUTO_DOWNLOAD=true

# 迭代设置
MAX_ITERATIONS=5
IMPROVEMENT_THRESHOLD=0.05

# 记忆保留期
MEMORY_RETENTION_DAYS=365
```

## 🎯 最佳实践

### 1. API Key管理
- 为不同agent使用不同key以分散负载
- 使用较便宜的模型（Haiku）处理简单任务
- 监控各agent的API使用量

### 2. PDF缓存
- 定期清理旧PDF（`pdf_reader.clean_cache(older_than_days=90)`）
- 大项目考虑外部存储

### 3. 迭代管理
- 设置合理的 `MAX_ITERATIONS`
- 每次迭代记录详细的findings和improvements
- 使用 `should_continue_iterating()` 自动决策

### 4. 引用管理
- 及时记录引用（在阅读论文时）
- 定期验证引用（`citations.validate_citations()`）
- 导出BibTeX备份

## 📖 更多示例

查看 `examples/` 目录获取更多使用示例：
- `examples/multi_api_keys.py` - 多API key配置
- `examples/pdf_analysis.py` - PDF分析工作流
- `examples/iteration_learning.py` - 迭代学习示例
- `examples/citation_workflow.py` - 引用管理工作流

## ❓ 常见问题

**Q: 是否必须为每个agent配置独立API key？**
A: 不是必须的。如果只设置 `ANTHROPIC_API_KEY`，所有agent会共享。独立配置是可选的优化。

**Q: PDF下载失败怎么办？**
A: 系统会继续使用论文的abstract。可以稍后手动下载或禁用 `PDF_AUTO_DOWNLOAD`。

**Q: 数据库会变得很大吗？**
A: 主要存储元数据。定期清理旧项目和PDF缓存可控制大小。

**Q: 如何导出所有数据？**
A: 数据库是标准SQLite，可以用任何SQLite工具导出。引用可导出为BibTeX。

---

**升级完成！** 现在您的系统具有完整的工程化能力。
