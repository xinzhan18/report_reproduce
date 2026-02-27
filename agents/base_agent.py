"""
BaseAgent - Foundation class for all research agents

Implements Template Method Pattern to eliminate code duplication across agents.
All agents inherit from this class and implement only their specific business logic.
"""

# ============================================================================
# 文件头注释 (File Header)
# INPUT:  外部依赖 - abc (抽象基类), typing (类型系统), logging (日志),
#                   pathlib (路径), core/state (ResearchState状态定义),
#                   config/agent_config (Agent配置),
#                   agents/services (LLMService, IntelligenceContext, OutputManager)
# OUTPUT: 对外提供 - BaseAgent抽象基类,定义execute()生命周期、
#                   call_llm()、save_artifact()等通用方法,
#                   子类只需实现_execute()业务逻辑
# POSITION: 系统地位 - Agent/Base (智能体层-抽象基类)
#                     Template Method Pattern核心,消除四个Agent的重复代码
#
# 注意：当本文件更新时,必须更新文件头注释和所属文件夹的CLAUDE.md
# ============================================================================

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from pathlib import Path

from core.state import ResearchState
from config.agent_config import get_agent_config


class BaseAgent(ABC):
    """
    Abstract base class for all research agents.

    Provides common infrastructure:
    - Memory and knowledge graph loading
    - LLM service integration
    - Output management
    - Logging and monitoring
    - Execution lifecycle management

    Subclasses must implement:
    - _execute(state) -> state: Core business logic
    """

    def __init__(
        self,
        llm,
        file_manager,
        agent_name: str,
        intelligence_context=None,
        llm_service=None,
        output_manager=None
    ):
        """
        Initialize base agent infrastructure.

        Args:
            llm: LLM client (Anthropic API client)
            file_manager: File management utility
            agent_name: Name of the agent (e.g., "ideation", "planning")
            intelligence_context: Optional IntelligenceContext instance (for testing)
            llm_service: Optional LLMService instance (for testing)
            output_manager: Optional OutputManager instance (for testing)
        """
        self.llm = llm
        self.file_manager = file_manager
        self.agent_name = agent_name
        self.config = get_agent_config(agent_name)

        # Setup logging
        self.logger = self._setup_logger()

        # Lazy import to avoid circular dependencies
        if intelligence_context is None:
            from agents.services.intelligence_context import IntelligenceContext
            self.intelligence = IntelligenceContext(agent_name)
        else:
            self.intelligence = intelligence_context

        if llm_service is None:
            from agents.services.llm_service import LLMService
            self.llm_service = LLMService(llm, self.intelligence.system_prompt)
        else:
            self.llm_service = llm_service

        if output_manager is None:
            from agents.services.output_manager import OutputManager
            self.output_manager = OutputManager(file_manager)
        else:
            self.output_manager = output_manager

    def __call__(self, state: ResearchState) -> ResearchState:
        """
        Template Method Pattern - Unified execution flow for all agents.

        Workflow:
        1. Setup: Load memories, initialize context
        2. Execute: Run agent-specific logic (implemented by subclass)
        3. Finalize: Save logs, update knowledge graph

        Args:
            state: Current research state

        Returns:
            Updated research state
        """
        try:
            # Phase 1: Setup
            self.logger.info(f"{'='*60}")
            self.logger.info(f"Starting {self.agent_name} agent")
            self.logger.info(f"{'='*60}")
            state = self._setup(state)

            # Phase 2: Execute (implemented by subclass)
            self.logger.info(f"Executing {self.agent_name} agent logic...")
            state = self._execute(state)

            # Phase 3: Finalize
            state = self._finalize(state)

            self.logger.info(f"{self.agent_name} agent completed successfully")
            return state

        except Exception as e:
            self.logger.error(f"Error in {self.agent_name} agent: {str(e)}", exc_info=True)
            state["status"] = f"error_{self.agent_name}"
            state["error"] = str(e)
            raise

    def _setup(self, state: ResearchState) -> ResearchState:
        """
        Setup phase: Load memories and initialize context.

        This method:
        - Loads agent persona, long-term memory, mistakes registry
        - Updates system prompt with memories
        - Sets agent status in state
        - Logs setup information

        Args:
            state: Current research state

        Returns:
            Updated state with status
        """
        self.logger.info("🧠 Loading agent intelligence context...")

        # Load memories and knowledge
        memories, knowledge = self.intelligence.load_context()

        # Update LLM service with new system prompt
        self.llm_service.update_system_prompt(self.intelligence.system_prompt)

        self.logger.info(f"✓ Loaded persona, long-term memory ({len(memories.get('long_term', []))} entries)")
        self.logger.info(f"✓ Loaded mistakes registry ({len(memories.get('mistakes', []))} entries)")
        self.logger.info(f"✓ Loaded knowledge graph ({len(knowledge)} related nodes)")

        # Update state status
        state["status"] = self.agent_name.lower()

        return state

    @abstractmethod
    def _execute(self, state: ResearchState) -> ResearchState:
        """
        Execute agent-specific business logic.

        This is the only method subclasses MUST implement.
        All infrastructure is handled by BaseAgent.

        Args:
            state: Current research state

        Returns:
            Updated state with agent outputs
        """
        pass

    def _finalize(self, state: ResearchState) -> ResearchState:
        """
        Finalize phase: Save logs and update knowledge.

        This method:
        - Generates execution summary
        - Saves daily log to memory system
        - Updates knowledge graph with new learnings
        - Logs completion information

        Args:
            state: Current research state

        Returns:
            Final state
        """
        self.logger.info("📝 Finalizing execution...")

        # Generate execution summary
        execution_summary = self._generate_execution_summary(state)

        # Save daily log
        if state.get("project_id"):
            self.intelligence.save_execution_log(
                project_id=state["project_id"],
                execution_summary=execution_summary
            )
            self.logger.info(f"✓ Saved execution log to memory system")

        # Update knowledge graph
        try:
            self.intelligence.update_knowledge(state)
            self.logger.info(f"✓ Updated knowledge graph")
        except Exception as e:
            self.logger.warning(f"Failed to update knowledge graph: {e}")

        self.logger.info("✓ Finalization complete")

        return state

    def _generate_execution_summary(self, state: ResearchState) -> Dict[str, Any]:
        """
        Generate execution summary for daily log.

        Subclasses can override this to provide agent-specific summaries.

        Args:
            state: Current research state

        Returns:
            Execution summary with log, learnings, mistakes, reflection
        """
        return {
            "log": f"{self.agent_name} agent executed successfully",
            "learnings": self._extract_learnings(state),
            "mistakes": [],
            "reflection": f"Completed {self.agent_name} phase"
        }

    def _extract_learnings(self, state: ResearchState) -> list:
        """
        Extract learnings from execution.

        Subclasses can override to extract domain-specific learnings.

        Args:
            state: Current research state

        Returns:
            List of learning strings
        """
        return []

    def _setup_logger(self) -> logging.Logger:
        """
        Setup structured logger for this agent.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(f"agent.{self.agent_name}")

        # Don't add handlers if already configured
        if not logger.handlers:
            logger.setLevel(logging.INFO)

            # Console handler
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)

            # Format with agent name
            formatter = logging.Formatter(
                f'[%(asctime)s] [{self.agent_name.upper()}] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def save_artifact(
        self,
        content: Any,
        project_id: str,
        filename: str,
        subdir: str,
        format: str = "auto"
    ):
        """
        Convenience method to save artifacts using OutputManager.

        Args:
            content: Content to save
            project_id: Project ID
            filename: File name
            subdir: Subdirectory within project
            format: Format ("auto", "json", "text", "markdown")
        """
        self.output_manager.save_artifact(
            content=content,
            project_id=project_id,
            filename=filename,
            subdir=subdir,
            format=format
        )
        self.logger.info(f"✓ Saved artifact: {subdir}/{filename}")

    def call_llm(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        response_format: str = "text"
    ) -> Any:
        """
        Convenience method to call LLM using LLMService.

        Args:
            prompt: User prompt
            model: Model name ("sonnet", "haiku", "opus") - defaults to agent config
            max_tokens: Maximum tokens to generate
            temperature: Temperature for sampling
            response_format: "text" or "json"

        Returns:
            LLM response (str or dict depending on format)
        """
        if model is None:
            model = self.config.get("model", "sonnet")

        return self.llm_service.call(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format
        )
