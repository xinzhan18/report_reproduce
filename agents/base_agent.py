"""
BaseAgent - 所有研究 Agent 的基类

Template Method Pattern: 子类只需实现 _execute() 业务逻辑。
Agentic Tool-Use: 子类可覆盖 _register_tools() + _build_tool_system_prompt() +
    _build_task_prompt() + _on_submit_result() 四个钩子，通过 _agentic_loop() 获得工具自治能力。
"""

# INPUT:  abc, typing, logging, json,
#         agents.llm (call_llm/call_llm_json/call_llm_tools),
#         agents.tool_registry (ToolRegistry),
#         core.memory (AgentMemory),
#         core.knowledge_graph (get_knowledge_graph),
#         core.state (ResearchState),
#         config.agent_config (get_agent_config)
# OUTPUT: BaseAgent 抽象基类
# POSITION: Agent 层抽象基类（含通用 agentic tool-use 循环）

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import json
import logging

from agents.llm import call_llm, call_llm_json, call_llm_tools
from agents.tool_registry import ToolRegistry
from core.memory import AgentMemory
from core.knowledge_graph import get_knowledge_graph
from core.state import ResearchState
from config.agent_config import get_agent_config


class BaseAgent(ABC):
    """所有研究 Agent 的抽象基类。

    子类必须实现 _execute()。
    子类可覆盖 _register_tools / _build_tool_system_prompt / _build_task_prompt / _on_submit_result
    以获得 agentic tool-use 循环能力。
    """

    _submit_result_key = "submit_result"

    def __init__(self, llm, file_manager, agent_name: str, **tools):
        self.llm = llm
        self.file_manager = file_manager
        self.agent_name = agent_name
        self.config = get_agent_config(agent_name)
        self.memory = AgentMemory(agent_name)
        self.knowledge_graph = get_knowledge_graph()
        self.logger = self._setup_logger()

        # 子类工具通过 kwargs 传入 (paper_fetcher, data_fetcher 等)
        for k, v in tools.items():
            setattr(self, k, v)

        # 运行时 system prompt（在 __call__ 中构建）
        self._system_prompt = ""

        # ToolRegistry（在 __call__ 中重建）
        self.tool_registry = ToolRegistry()

    def __call__(self, state: ResearchState) -> ResearchState:
        """统一执行流: setup → register_tools → execute → save_log。"""
        try:
            self.logger.info(f"{'=' * 60}")
            self.logger.info(f"Starting {self.agent_name} agent")
            self.logger.info(f"{'=' * 60}")

            # Setup: 构建 system prompt
            self._system_prompt = self.memory.build_system_prompt()
            state["status"] = self.agent_name

            # 重建 ToolRegistry 并注册工具
            self.tool_registry = ToolRegistry()
            self._register_tools(state)

            # Execute: 子类业务逻辑
            self.logger.info(f"Executing {self.agent_name} agent logic...")
            state = self._execute(state)

            # Save log
            self._save_log(state)

            self.logger.info(f"{self.agent_name} agent completed successfully")
            return state

        except Exception as e:
            self.logger.error(f"Error in {self.agent_name} agent: {e}", exc_info=True)
            state["status"] = f"error_{self.agent_name}"
            state["error"] = str(e)
            raise

    @abstractmethod
    def _execute(self, state: ResearchState) -> ResearchState:
        """子类实现业务逻辑。"""
        pass

    # ------------------------------------------------------------------
    # Agentic Tool-Use 钩子（子类覆盖）
    # ------------------------------------------------------------------

    def _register_tools(self, state: ResearchState):
        """注册工具到 self.tool_registry。默认不注册任何工具。"""
        pass

    def _build_tool_system_prompt(self, state: ResearchState) -> str:
        """构建 tool-use 模式的 system prompt。默认返回 agent memory prompt。"""
        return self._system_prompt

    def _build_task_prompt(self, state: ResearchState) -> str:
        """构建初始 task prompt。默认返回空字符串。"""
        return ""

    def _on_submit_result(self, results: dict, state: ResearchState):
        """映射 submit_result 结果到 state。默认不做任何处理。"""
        pass

    # ------------------------------------------------------------------
    # Agentic Tool-Use 循环
    # ------------------------------------------------------------------

    def _agentic_loop(
        self,
        state: ResearchState,
        max_turns: int | None = None,
        **tool_context,
    ) -> tuple[dict | None, str]:
        """通用多轮 tool_use 循环。

        Args:
            state: 当前 ResearchState
            max_turns: 最大轮次，None 时从 config 读取
            **tool_context: 传递给 tool executor 的上下文 (sandbox, paper_fetcher 等)

        Returns:
            (submitted_results, execution_log)
        """
        if max_turns is None:
            max_turns = self.config.get("max_agent_turns", 30)

        system_prompt = self._build_tool_system_prompt(state)
        task_prompt = self._build_task_prompt(state)
        tools = self.tool_registry.get_schemas()

        if not tools:
            self.logger.warning("No tools registered, skipping agentic loop")
            return None, "[WARNING] No tools registered"

        model = self.config.get("model", "sonnet")
        temperature = self.config.get("temperature", 0.2)
        max_tokens = self.config.get("max_tokens", 4096)

        messages = [{"role": "user", "content": task_prompt}]
        log_lines = []
        submitted_results = None

        for turn in range(1, max_turns + 1):
            self.logger.info(f"--- Agentic Turn {turn}/{max_turns} ---")
            log_lines.append(f"\n{'='*40} Turn {turn} {'='*40}")

            try:
                response = call_llm_tools(
                    self.llm, messages, tools,
                    system_prompt=system_prompt,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except Exception as e:
                self.logger.error(f"LLM API call failed: {e}")
                log_lines.append(f"[ERROR] LLM API call failed: {e}")
                break

            # 记录 assistant response
            messages.append({"role": "assistant", "content": response.content})

            # 记录文本输出
            for block in response.content:
                if block.type == "text" and block.text.strip():
                    self.logger.info(f"LLM: {block.text[:200]}")
                    log_lines.append(f"[LLM] {block.text}")

            # 检查 stop reason
            if response.stop_reason == "end_turn":
                self.logger.info("LLM ended turn without tool use")
                log_lines.append("[INFO] LLM ended turn (no tool call)")
                break

            if response.stop_reason != "tool_use":
                self.logger.info(f"Unexpected stop_reason: {response.stop_reason}")
                log_lines.append(f"[INFO] Stop reason: {response.stop_reason}")
                break

            # 处理 tool_use blocks
            tool_results = []
            should_break = False

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                self.logger.info(f"Tool: {tool_name}({json.dumps(tool_input, ensure_ascii=False)[:200]})")
                log_lines.append(f"[TOOL] {tool_name}: {json.dumps(tool_input, ensure_ascii=False)[:500]}")

                # submit_result 特殊处理：截获结果，结束循环
                if tool_name == self._submit_result_key:
                    submitted_results = tool_input.get("results", tool_input)
                    self.logger.info(f"Results submitted: {json.dumps(submitted_results, ensure_ascii=False)[:300]}")
                    log_lines.append(f"[SUBMIT] {json.dumps(submitted_results, ensure_ascii=False)[:1000]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": "Results submitted successfully. Task complete.",
                    })
                    should_break = True
                else:
                    # 执行工具
                    result_str = self.tool_registry.execute(tool_name, tool_input, **tool_context)
                    log_lines.append(f"[RESULT] {result_str[:500]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_str,
                    })

            # 将 tool results 追加为 user message
            messages.append({"role": "user", "content": tool_results})

            if should_break:
                break

        else:
            self.logger.warning(f"Agentic loop reached max turns ({max_turns})")
            log_lines.append(f"[WARNING] Reached max turns ({max_turns})")

        execution_log = "\n".join(log_lines)

        # 如果有提交结果，调用 _on_submit_result 映射到 state
        if submitted_results is not None:
            self._on_submit_result(submitted_results, state)

        return submitted_results, execution_log

    def _generate_execution_summary(self, state: ResearchState) -> Dict[str, Any]:
        """生成执行摘要，子类可覆盖。"""
        return {
            "log": f"{self.agent_name} agent executed successfully",
            "learnings": [],
            "mistakes": [],
            "reflection": f"Completed {self.agent_name} phase",
        }

    def _save_log(self, state: ResearchState):
        """保存执行日志到记忆系统。"""
        if not state.get("project_id"):
            return
        summary = self._generate_execution_summary(state)
        try:
            self.memory.save_daily_log(
                project_id=state["project_id"],
                execution_log=summary.get("log", ""),
                learnings=summary.get("learnings", []),
                mistakes=summary.get("mistakes", []),
                reflection=summary.get("reflection", ""),
            )
            self.logger.info("Saved execution log to memory system")
        except Exception as e:
            self.logger.warning(f"Failed to save execution log: {e}")

    # ------------------------------------------------------------------
    # LLM 调用
    # ------------------------------------------------------------------

    def call_llm(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        response_format: str = "text",
    ) -> Union[str, dict]:
        """调用 LLM。response_format="json" 时自动解析 JSON。"""
        if model is None:
            model = self.config.get("model", "sonnet")

        if response_format == "json":
            return call_llm_json(
                self.llm, prompt,
                system_prompt=self._system_prompt,
                model=model, max_tokens=max_tokens, temperature=temperature,
            )
        return call_llm(
            self.llm, prompt,
            system_prompt=self._system_prompt,
            model=model, max_tokens=max_tokens, temperature=temperature,
        )

    def call_llm_json(self, prompt: str, **kwargs) -> dict:
        """调用 LLM 并返回 JSON dict。"""
        kwargs.setdefault("model", self.config.get("model", "sonnet"))
        return call_llm_json(
            self.llm, prompt,
            system_prompt=self._system_prompt,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # 文件保存
    # ------------------------------------------------------------------

    def save_artifact(
        self,
        content: Any,
        project_id: str,
        filename: str,
        subdir: str,
        format: str = "auto",
    ):
        """保存输出文件。"""
        # 检测格式
        if format == "auto":
            if filename.endswith(".json"):
                format = "json"
            elif isinstance(content, (dict, list)):
                format = "json"
            else:
                format = "text"

        if format == "json":
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError:
                    pass
            if not filename.endswith(".json"):
                filename = f"{filename}.json"
            self.file_manager.save_json(
                data=content, project_id=project_id,
                filename=filename, subdir=subdir,
            )
        else:
            if isinstance(content, (dict, list)):
                text_content = json.dumps(content, indent=2)
            else:
                text_content = str(content)
            self.file_manager.save_text(
                content=text_content, project_id=project_id,
                filename=filename, subdir=subdir,
            )

        self.logger.info(f"Saved artifact: {subdir}/{filename}")

    # ------------------------------------------------------------------
    # Logger
    # ------------------------------------------------------------------

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"agent.{self.agent_name}")
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                f'[%(asctime)s] [{self.agent_name.upper()}] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
