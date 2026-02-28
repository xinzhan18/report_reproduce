"""
BaseAgent - 所有研究 Agent 的基类

Template Method Pattern: 子类只需实现 _execute() 业务逻辑。
"""

# INPUT:  abc, typing, logging, json,
#         agents.llm (call_llm/call_llm_json),
#         core.memory (AgentMemory),
#         core.knowledge_graph (get_knowledge_graph),
#         core.state (ResearchState),
#         config.agent_config (get_agent_config)
# OUTPUT: BaseAgent 抽象基类
# POSITION: Agent 层抽象基类

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import json
import logging

from agents.llm import call_llm, call_llm_json
from core.memory import AgentMemory
from core.knowledge_graph import get_knowledge_graph
from core.state import ResearchState
from config.agent_config import get_agent_config


class BaseAgent(ABC):
    """所有研究 Agent 的抽象基类。子类只需实现 _execute()。"""

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

    def __call__(self, state: ResearchState) -> ResearchState:
        """统一执行流: setup → execute → save_log。"""
        try:
            self.logger.info(f"{'=' * 60}")
            self.logger.info(f"Starting {self.agent_name} agent")
            self.logger.info(f"{'=' * 60}")

            # Setup: 构建 system prompt
            self._system_prompt = self.memory.build_system_prompt()
            state["status"] = self.agent_name

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
