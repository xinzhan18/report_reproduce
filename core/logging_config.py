"""
Comprehensive logging and monitoring configuration.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import json


class ResearchLogger:
    """
    Centralized logging for research automation system.
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        log_level: str = "INFO"
    ):
        """
        Initialize logging configuration.

        Args:
            log_dir: Directory for log files (default: logs/)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_dir = log_dir or Path("logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_level = getattr(logging, log_level.upper())
        self._setup_loggers()

    def _setup_loggers(self):
        """Setup all loggers."""
        # Main application logger
        self.app_logger = self._create_logger(
            "research_automation",
            self.log_dir / "app.log"
        )

        # Agent-specific loggers
        self.ideation_logger = self._create_logger(
            "ideation_agent",
            self.log_dir / "ideation.log"
        )

        self.planning_logger = self._create_logger(
            "planning_agent",
            self.log_dir / "planning.log"
        )

        self.experiment_logger = self._create_logger(
            "experiment_agent",
            self.log_dir / "experiment.log"
        )

        self.writing_logger = self._create_logger(
            "writing_agent",
            self.log_dir / "writing.log"
        )

        # API call logger
        self.api_logger = self._create_logger(
            "api_calls",
            self.log_dir / "api_calls.log"
        )

        # Error logger
        self.error_logger = self._create_logger(
            "errors",
            self.log_dir / "errors.log",
            level=logging.ERROR
        )

    def _create_logger(
        self,
        name: str,
        log_file: Path,
        level: Optional[int] = None
    ) -> logging.Logger:
        """
        Create a logger with file and console handlers.

        Args:
            name: Logger name
            log_file: Path to log file
            level: Logging level (uses self.log_level if not specified)

        Returns:
            Configured logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(level or self.log_level)

        # Clear existing handlers
        logger.handlers = []

        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level or self.log_level)

        # Console handler (only for WARNING and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def log_agent_start(self, agent_name: str, project_id: str):
        """Log agent start."""
        logger = self._get_agent_logger(agent_name)
        logger.info(f"Agent started for project: {project_id}")

    def log_agent_complete(
        self,
        agent_name: str,
        project_id: str,
        status: str,
        duration: float
    ):
        """Log agent completion."""
        logger = self._get_agent_logger(agent_name)
        logger.info(
            f"Agent completed - Project: {project_id}, "
            f"Status: {status}, Duration: {duration:.2f}s"
        )

    def log_api_call(
        self,
        agent_name: str,
        model: str,
        tokens: int,
        cost: Optional[float] = None
    ):
        """Log API call."""
        self.api_logger.info(
            f"API Call - Agent: {agent_name}, Model: {model}, "
            f"Tokens: {tokens}, Cost: ${cost:.4f}" if cost else f"Tokens: {tokens}"
        )

    def log_error(
        self,
        agent_name: str,
        error: Exception,
        context: Optional[str] = None
    ):
        """Log error."""
        self.error_logger.error(
            f"Error in {agent_name}: {str(error)}",
            exc_info=True
        )

        if context:
            self.error_logger.error(f"Context: {context}")

    def log_paper_fetch(self, count: int, source: str):
        """Log paper fetching."""
        self.app_logger.info(f"Fetched {count} papers from {source}")

    def log_citation_added(self, arxiv_id: str, project_id: str):
        """Log citation addition."""
        self.app_logger.debug(
            f"Citation added - Paper: {arxiv_id}, Project: {project_id}"
        )

    def log_iteration_complete(
        self,
        project_id: str,
        iteration: int,
        findings: int,
        issues: int
    ):
        """Log iteration completion."""
        self.app_logger.info(
            f"Iteration {iteration} complete - Project: {project_id}, "
            f"Findings: {findings}, Issues: {issues}"
        )

    def _get_agent_logger(self, agent_name: str) -> logging.Logger:
        """Get logger for specific agent."""
        logger_map = {
            "ideation": self.ideation_logger,
            "planning": self.planning_logger,
            "experiment": self.experiment_logger,
            "writing": self.writing_logger
        }

        return logger_map.get(agent_name.lower(), self.app_logger)

    def generate_log_summary(self, hours: int = 24) -> Dict[str, any]:
        """
        Generate summary of recent logs.

        Args:
            hours: Number of hours to summarize

        Returns:
            Summary statistics
        """
        # This is a simplified version
        # In production, would parse log files

        return {
            "period_hours": hours,
            "total_api_calls": 0,  # Would count from api_calls.log
            "total_errors": 0,  # Would count from errors.log
            "agents_run": [],  # Would extract from agent logs
            "timestamp": datetime.now().isoformat()
        }


# Global logger instance
_logger: Optional[ResearchLogger] = None


def get_logger() -> ResearchLogger:
    """Get or create global logger instance."""
    global _logger
    if _logger is None:
        import os
        log_level = os.getenv("LOG_LEVEL", "INFO")
        _logger = ResearchLogger(log_level=log_level)
    return _logger


def log_info(message: str, agent: str = "app"):
    """Quick info log."""
    logger = get_logger()
    logger._get_agent_logger(agent).info(message)


def log_error(message: str, error: Optional[Exception] = None, agent: str = "app"):
    """Quick error log."""
    logger = get_logger()
    if error:
        logger.log_error(agent, error, message)
    else:
        logger._get_agent_logger(agent).error(message)


def log_warning(message: str, agent: str = "app"):
    """Quick warning log."""
    logger = get_logger()
    logger._get_agent_logger(agent).warning(message)
