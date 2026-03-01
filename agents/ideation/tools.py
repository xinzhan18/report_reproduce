"""
Tool 定义与执行器 — IdeationAgent 工具集

4 个专用工具 + 通用工具(browse_webpage, google_search, search_knowledge_graph from common_tools)。
适配 ToolRegistry 的 (name, schema, executor) 格式。
"""

# INPUT:  tools.paper_fetcher, tools.pdf_reader, agents.common_tools
# OUTPUT: get_tool_definitions() 函数
# POSITION: agents/ideation 子包 - 工具 schema + executor (ToolRegistry 格式)

from __future__ import annotations
import json

from agents.common_tools import get_common_tools


# ======================================================================
# Tool schemas (Anthropic API 格式) — IdeationAgent 专用
# ======================================================================

SEARCH_PAPERS_SCHEMA = {
    "name": "search_papers",
    "description": (
        "Search arXiv papers by keywords. Returns a list of paper metadata "
        "(arxiv_id, title, authors, abstract, published, categories, pdf_url)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of search keywords",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 20)",
            },
        },
        "required": ["keywords"],
    },
}

FETCH_RECENT_PAPERS_SCHEMA = {
    "name": "fetch_recent_papers",
    "description": (
        "Fetch recent papers from specified arXiv categories. "
        "Returns papers published in the last N days."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "categories": {
                "type": "array",
                "items": {"type": "string"},
                "description": "arXiv categories (e.g. ['q-fin.PM', 'q-fin.TR', 'stat.ML'])",
            },
            "days_back": {
                "type": "integer",
                "description": "Number of days to look back (default: 7)",
            },
        },
        "required": ["categories"],
    },
}

DOWNLOAD_AND_READ_PDF_SCHEMA = {
    "name": "download_and_read_pdf",
    "description": (
        "Download a paper's PDF from arXiv and extract full text with section structure. "
        "Returns the extracted text organized by sections."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "arxiv_id": {
                "type": "string",
                "description": "The arXiv paper ID (e.g. '2301.12345')",
            },
            "pdf_url": {
                "type": "string",
                "description": "Optional direct PDF URL. If not provided, constructs from arxiv_id.",
            },
        },
        "required": ["arxiv_id"],
    },
}

SUBMIT_RESULT_SCHEMA = {
    "name": "submit_result",
    "description": (
        "Submit the final literature review results and end the analysis. "
        "Must include: papers_reviewed, literature_summary, research_gaps, hypothesis. "
        "This terminates the agentic loop."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "object",
                "description": "The final results object",
                "properties": {
                    "papers_reviewed": {
                        "type": "array",
                        "description": "List of paper metadata dicts",
                    },
                    "literature_summary": {
                        "type": "string",
                        "description": "Comprehensive literature synthesis (800-1200 words)",
                    },
                    "research_gaps": {
                        "type": "array",
                        "description": "List of research gap objects with description, severity, evidence, opportunity_score",
                    },
                    "hypothesis": {
                        "type": "object",
                        "description": "Hypothesis object with statement, rationale, supporting_evidence, feasibility_score, novelty_score",
                    },
                },
                "required": ["papers_reviewed", "literature_summary", "research_gaps", "hypothesis"],
            }
        },
        "required": ["results"],
    },
}


# ======================================================================
# Executors — IdeationAgent 专用
# ======================================================================

def _exec_search_papers(tool_input: dict, paper_fetcher=None, **_) -> str:
    if paper_fetcher is None:
        return "[ERROR] paper_fetcher not available"
    keywords = tool_input["keywords"]
    max_results = tool_input.get("max_results", 20)
    papers = paper_fetcher.fetch_papers_by_keywords(
        keywords=keywords, max_results=max_results,
    )
    if not papers:
        return "No papers found for the given keywords."
    lines = []
    for p in papers:
        lines.append(
            f"- [{p['arxiv_id']}] {p['title']}\n"
            f"  Authors: {', '.join(p['authors'][:3])}\n"
            f"  Categories: {', '.join(p.get('categories', []))}\n"
            f"  Abstract: {p['abstract'][:300]}..."
        )
    return f"Found {len(papers)} papers:\n\n" + "\n\n".join(lines)


def _exec_fetch_recent_papers(tool_input: dict, paper_fetcher=None, **_) -> str:
    if paper_fetcher is None:
        return "[ERROR] paper_fetcher not available"
    categories = tool_input["categories"]
    days_back = tool_input.get("days_back", 7)
    papers = paper_fetcher.fetch_recent_papers(categories=categories, days_back=days_back)
    if not papers:
        return "No recent papers found."
    lines = []
    for p in papers:
        lines.append(
            f"- [{p['arxiv_id']}] {p['title']}\n"
            f"  Published: {p.get('published', 'N/A')}\n"
            f"  Abstract: {p['abstract'][:300]}..."
        )
    return f"Found {len(papers)} recent papers:\n\n" + "\n\n".join(lines)


def _exec_download_and_read_pdf(tool_input: dict, pdf_reader=None, **_) -> str:
    if pdf_reader is None:
        return "[ERROR] pdf_reader not available"
    arxiv_id = tool_input["arxiv_id"]
    pdf_url = tool_input.get("pdf_url")
    try:
        pdf_path = pdf_reader.download_pdf(arxiv_id, pdf_url)
        if not pdf_path:
            return f"[ERROR] Failed to download PDF for {arxiv_id}"
        full_text = pdf_reader.extract_text(pdf_path)
        if not full_text:
            return f"[ERROR] Failed to extract text from PDF for {arxiv_id}"
        sections = pdf_reader.extract_sections(full_text)
        if sections:
            result = f"# PDF Content for {arxiv_id}\n\n"
            for name, content in sections.items():
                result += f"## {name.upper()}\n{content[:2000]}\n\n"
            return result[:15000]
        return f"# Full Text for {arxiv_id}\n\n{full_text[:10000]}"
    except Exception as e:
        return f"[ERROR] PDF processing failed for {arxiv_id}: {e}"


# ======================================================================
# ToolRegistry 注册接口
# ======================================================================

def get_tool_definitions(include_browser: bool = False) -> list[tuple[str, dict, callable]]:
    """返回 IdeationAgent 工具定义列表，适配 ToolRegistry.register_many()。

    Args:
        include_browser: 是否包含浏览器工具

    Returns:
        [(name, schema, executor), ...]
    """
    tools = [
        ("search_papers", SEARCH_PAPERS_SCHEMA, _exec_search_papers),
        ("fetch_recent_papers", FETCH_RECENT_PAPERS_SCHEMA, _exec_fetch_recent_papers),
        ("download_and_read_pdf", DOWNLOAD_AND_READ_PDF_SCHEMA, _exec_download_and_read_pdf),
        ("submit_result", SUBMIT_RESULT_SCHEMA, lambda tool_input, **_: ""),  # handled by _agentic_loop
    ]

    # 通用工具: browse_webpage, google_search, search_knowledge_graph
    tools.extend(get_common_tools(
        include_browser=include_browser,
        include_kg=True,
        include_file=False,
    ))

    return tools
