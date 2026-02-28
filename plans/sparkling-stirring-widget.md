# IdeationAgent 深度文献分析重构计划

## Context

当前 IdeationAgent 的文献分析**只读摘要前300字符**，让 LLM 凭摘要"猜测"研究缺口和假设。这本质上是浅层扫描，无法理解论文的方法论细节、实验设计和具体结论。

与此同时，代码库中已有完整的深度分析基础设施却从未被使用：
- `PDFReader` (下载/提取全文/章节分割) — 从未调用
- `DocumentMemoryManager` (分析缓存) — 从未调用
- `LiteratureAccessManager` — 构造了但从未使用
- `RankedPaper/StructuredInsights/ResearchGap/Hypothesis/ResearchSynthesis` 等数据结构 — 定义了但从未使用
- 知识图谱查询结果 — 只打日志不注入 prompt

**目标**: 重构为三阶段深度分析流水线，利用已有工具和数据结构。

---

## 修改文件清单

| 文件 | 改动 | 说明 |
|------|------|------|
| `agents/ideation_agent.py` | **重写** | 实现三阶段流水线 |
| `agents/llm.py` | 小改 | `extract_json` 支持 JSON 数组 `[...]` |
| `config/agent_config.py` | 小改 | 添加深度分析配置项 |
| `core/pipeline.py` | 小改 | 传入 `pdf_reader` 参数 |

不需要修改的文件（直接复用）：
- `tools/pdf_reader.py` — 直接调用
- `core/document_memory_manager.py` — 直接调用
- `core/state.py` — 数据结构已定义，直接 import

---

## 三阶段流水线设计

### Stage 1: 快速扫描与排序

```
scan_papers() (不变)
    → List[PaperMetadata]
        ↓
rank_papers() (新方法)
    → LLM 读每篇的完整 abstract + 知识图谱上下文
    → 输出 JSON: 每篇 relevance_score + should_analyze_deep
    → List[RankedPaper]
    → 选出 top 5 篇进入 Stage 2
```

### Stage 2: 深度阅读

对每篇 `should_analyze_deep=True` 的论文：

```
检查 DocumentMemoryManager 缓存
    → 命中: 直接恢复 StructuredInsights
    → 未命中:
        PDFReader.download_pdf(arxiv_id)
        PDFReader.extract_text(pdf_path)
        PDFReader.extract_sections(text)  # intro/methodology/results/conclusion
        LLM 深度分析各 section → StructuredInsights
        DocumentMemoryManager.save_analysis_results() 写缓存
```

**降级**: PDF 下载/解析失败时，退化为 abstract-only 分析（构造精简版 StructuredInsights）

### Stage 3: 跨论文综合

```
synthesize_literature()
    输入: 所有 StructuredInsights + 未深度分析论文的摘要 + 知识图谱上下文
    LLM 跨论文综合分析 → ResearchSynthesis
        ↓
identify_research_gaps()
    输入: ResearchSynthesis + StructuredInsights
    LLM 生成结构化缺口 → List[ResearchGap] (有 evidence 引用具体论文)
        ↓
generate_hypothesis()
    输入: ResearchGap列表 + ResearchSynthesis + 知识图谱上下文
    LLM 生成可回测假设 → Hypothesis (有 feasibility_score/novelty_score)
```

---

## 具体实现步骤

### Step 1: 修改 `agents/llm.py`

`extract_json` 第69行 Strategy 2 改为同时匹配 `{}` 和 `[]`：

```python
# Strategy 2: raw { ... } 或 [ ... ]
m = re.search(r'[\{\[].*[\}\]]', text, re.DOTALL)
```

### Step 2: 修改 `config/agent_config.py`

`AGENT_CONFIG["ideation"]` 添加：

```python
"deep_analysis_count": 5,       # 深度分析论文数量上限
"fallback_to_abstract": True,   # PDF 失败时退化为摘要分析
```

### Step 3: 修改 `core/pipeline.py`

第56-71行，创建 `PDFReader` 并传入 IdeationAgent：

```python
from tools.pdf_reader import PDFReader
...
pdf_reader = PDFReader()
ideation_agent = IdeationAgent(llm, paper_fetcher, file_manager, pdf_reader=pdf_reader)
```

### Step 4: 重写 `agents/ideation_agent.py`

#### 4.1 新增 imports
```python
from dataclasses import asdict
from tools.pdf_reader import PDFReader
from core.document_memory_manager import get_document_memory_manager
from core.state import (
    ResearchState, PaperMetadata,
    RankedPaper, StructuredInsights,
    ResearchGap, Hypothesis, ResearchSynthesis,
)
```

#### 4.2 `__init__` 改动
- 接收 `pdf_reader` 参数 (通过 kwargs)
- 创建 `self.doc_memory = get_document_memory_manager()`
- 删除 `self.literature_access`（死代码）

#### 4.3 新增 `_build_kg_context()` 私有方法
- 查询知识图谱，格式化为 Markdown 段落
- 返回 str，注入到后续所有 LLM prompt 中

#### 4.4 新增 `rank_papers()` — Stage 1
- LLM 评估每篇论文相关性 (读完整 abstract)
- 输出 `List[RankedPaper]`
- 降级: JSON 解析失败时取前 N 篇

#### 4.5 新增 `deep_analyze_paper()` — Stage 2 单篇
- 缓存检查 → PDF 下载 → 全文提取 → 章节分割 → LLM 分析
- 输出 `StructuredInsights`
- 降级: PDF 失败时用 abstract 构造精简版

#### 4.6 新增 `deep_analyze_papers()` — Stage 2 批量
- 遍历 `should_analyze_deep=True` 的论文
- 逐篇调用 `deep_analyze_paper()`

#### 4.7 新增 `synthesize_literature()` — Stage 3
- 输入所有 StructuredInsights + 未深度分析论文摘要
- LLM 综合分析 → `ResearchSynthesis`

#### 4.8 重写 `identify_research_gaps()` — Stage 3
- 输入 `ResearchSynthesis` + `StructuredInsights`
- 输出 `List[ResearchGap]`（有 evidence 引用论文）

#### 4.9 重写 `generate_hypothesis()` — Stage 3
- 输入 `List[ResearchGap]` + `ResearchSynthesis`
- 输出 `Hypothesis` dataclass

#### 4.10 重写 `_execute()` 主流程
- Stage 1 → Stage 2 → Stage 3
- state 写入保持兼容（`literature_summary: str`, `research_gaps: List[str]`, `hypothesis: str`）

#### 4.11 更新 `_generate_execution_summary()`
- 加入深度分析论文数量等指标

### Step 5: 更新文档
- `agents/ideation_agent.py` 文件头注释
- `agents/CLAUDE.md` 更新 IdeationAgent 描述
- `config/agent_config.py` 文件头注释

---

## 产出文件

| 文件 | 路径 | 新增/更新 |
|------|------|----------|
| `papers_analyzed.json` | `literature/` | 不变 |
| `ranked_papers.json` | `literature/` | **新增** |
| `structured_insights.json` | `literature/` | **新增** |
| `literature_summary.md` | `literature/` | 内容更丰富 |
| `research_synthesis.json` | `literature/` | **新增** |
| `hypothesis.md` | `literature/` | 格式更结构化 |

---

## LLM 调用估算

| 阶段 | 次数 | 说明 |
|------|------|------|
| Stage 1 rank | 1 | 批量评估所有论文 |
| Stage 2 deep | ~5 | 每篇深度分析一次 |
| Stage 3 synthesis | 1 | 跨论文综合 |
| Gap identification | 1 | 结构化缺口 |
| Hypothesis generation | 1 | 假设生成 |
| **总计** | **~9** | 当前为 3-4 次 |

---

## 验证方法

1. **单元验证**: 手动构造一个 `ResearchState`，调用 `IdeationAgent._execute(state)`，检查：
   - `state["papers_reviewed"]` 非空
   - `state["literature_summary"]` 长度 > 1000 字
   - `state["research_gaps"]` 有 5-7 项
   - `state["hypothesis"]` 包含 Hypothesis/Rationale 结构
2. **产出文件检查**: 确认 `ranked_papers.json`、`structured_insights.json`、`research_synthesis.json` 正确生成
3. **缓存验证**: 第二次运行相同论文，Stage 2 应命中缓存（日志显示 "Using cached analysis"）
4. **降级验证**: 断网运行，PDF 下载失败后应退化为 abstract 分析而非崩溃
5. **Pipeline 集成**: 运行 `python -m core.pipeline "momentum strategies"`，确认 IdeationAgent 正常完成并流转到 PlanningAgent

---

## Checklist

- [x] 修改 `agents/llm.py` — extract_json 支持数组
- [x] 修改 `config/agent_config.py` — 添加配置项
- [x] 修改 `core/pipeline.py` — 传入 pdf_reader
- [x] 重写 `agents/ideation_agent.py` — 三阶段流水线
- [x] 更新文件头注释
- [x] 更新 `agents/CLAUDE.md`
