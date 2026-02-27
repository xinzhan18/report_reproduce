"""
Persistence and checkpointing for the research automation system.

Uses LangGraph's SQLite checkpointer to persist state between agent executions.
"""

from pathlib import Path
from typing import Optional, Dict, Any
from langgraph.checkpoint.sqlite import SqliteSaver
import os


# Default checkpoint database path
DEFAULT_CHECKPOINT_DB = Path("data/checkpoints/research.db")


def get_checkpointer(db_path: Optional[Path] = None) -> SqliteSaver:
    """
    Get or create a SQLite checkpointer for state persistence.

    Args:
        db_path: Path to the SQLite database. Uses default if not specified.

    Returns:
        Configured SqliteSaver instance
    """
    if db_path is None:
        db_path = DEFAULT_CHECKPOINT_DB

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create and return checkpointer
    return SqliteSaver.from_conn_string(str(db_path))


def create_config(project_id: str) -> Dict[str, Any]:
    """
    Create LangGraph configuration for a research project.

    Each project gets a unique thread_id for state isolation.

    Args:
        project_id: Unique identifier for the research project

    Returns:
        Configuration dict with thread_id
    """
    return {
        "configurable": {
            "thread_id": f"research_{project_id}"
        }
    }


def get_project_state(
    checkpointer: SqliteSaver,
    project_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve the latest state for a project.

    Args:
        checkpointer: The SqliteSaver instance
        project_id: Project identifier

    Returns:
        Latest state dict or None if not found
    """
    config = create_config(project_id)
    try:
        checkpoint = checkpointer.get(config)
        if checkpoint:
            return checkpoint.get("values")
    except Exception as e:
        print(f"Error retrieving state for {project_id}: {e}")

    return None


def list_all_projects(checkpointer: SqliteSaver) -> list[str]:
    """
    List all project IDs in the checkpoint database.

    Args:
        checkpointer: The SqliteSaver instance

    Returns:
        List of project IDs
    """
    # This is a simplified version - actual implementation would query the DB
    # For now, we return empty list as LangGraph's API doesn't expose this directly
    return []


def cleanup_old_checkpoints(
    checkpointer: SqliteSaver,
    days_old: int = 30
) -> int:
    """
    Clean up checkpoints older than specified days.

    Args:
        checkpointer: The SqliteSaver instance
        days_old: Remove checkpoints older than this many days

    Returns:
        Number of checkpoints removed
    """
    # TODO: Implement cleanup logic
    # This would require direct SQL access to the checkpoint tables
    return 0


class CheckpointManager:
    """
    High-level manager for checkpoint operations.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.checkpointer = get_checkpointer(db_path)
        self.db_path = db_path or DEFAULT_CHECKPOINT_DB

    def get_state(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get latest state for a project."""
        return get_project_state(self.checkpointer, project_id)

    def create_config(self, project_id: str) -> Dict[str, Any]:
        """Create configuration for a project."""
        return create_config(project_id)

    def cleanup(self, days_old: int = 30) -> int:
        """Clean up old checkpoints."""
        return cleanup_old_checkpoints(self.checkpointer, days_old)

    def close(self):
        """Close the checkpointer connection."""
        # SqliteSaver doesn't expose close method, connection is managed internally
        pass
