"""
Pipeline execution manager for running and monitoring research projects.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime
from core.pipeline import create_research_pipeline, run_research_pipeline, resume_research_pipeline
from core.state import ResearchState, create_initial_state
from core.persistence import get_checkpointer, create_config, get_project_state
from tools.file_manager import FileManager
import time


class PipelineRunner:
    """
    Manages execution of research pipelines.
    """

    def __init__(self, max_parallel: int = 3):
        """
        Initialize pipeline runner.

        Args:
            max_parallel: Maximum number of parallel projects
        """
        self.max_parallel = max_parallel
        self.file_manager = FileManager()
        self.checkpointer = get_checkpointer()
        self.active_projects: Dict[str, Dict[str, Any]] = {}
        self.project_queue: List[Dict[str, Any]] = []

    def run_project(
        self,
        research_direction: str,
        project_id: Optional[str] = None,
        background: bool = False
    ) -> ResearchState:
        """
        Execute a research project pipeline.

        Args:
            research_direction: Research focus area
            project_id: Optional project ID
            background: Whether to run in background

        Returns:
            Final research state
        """
        # Create initial state
        initial_state = create_initial_state(research_direction, project_id)
        project_id = initial_state["project_id"]

        # Create project structure
        self.file_manager.create_project_structure(project_id)

        # Register project
        self.active_projects[project_id] = {
            "research_direction": research_direction,
            "started_at": datetime.now().isoformat(),
            "status": "running"
        }

        # Save project metadata
        self._save_project_metadata(project_id, initial_state)

        if background:
            # TODO: Implement background execution with multiprocessing
            print(f"Background execution not yet implemented. Running synchronously.")

        # Run pipeline
        try:
            result = run_research_pipeline(research_direction, project_id)

            # Update project status
            self.active_projects[project_id]["status"] = result["status"]
            self.active_projects[project_id]["completed_at"] = datetime.now().isoformat()

            return result

        except Exception as e:
            # Handle error
            self.active_projects[project_id]["status"] = "failed"
            self.active_projects[project_id]["error"] = str(e)
            self.active_projects[project_id]["completed_at"] = datetime.now().isoformat()

            print(f"Error running project {project_id}: {e}")
            raise

        finally:
            # Remove from active projects
            if project_id in self.active_projects:
                # Move to completed
                self._archive_project_status(project_id)

    def resume_project(self, project_id: str) -> ResearchState:
        """
        Resume a project from its last checkpoint.

        Args:
            project_id: Project ID to resume

        Returns:
            Final research state
        """
        print(f"Resuming project: {project_id}")

        # Check if checkpoint exists
        state = get_project_state(self.checkpointer, project_id)

        if state is None:
            raise ValueError(f"No checkpoint found for project {project_id}")

        # Register as active
        self.active_projects[project_id] = {
            "research_direction": state.get("research_direction", "Unknown"),
            "resumed_at": datetime.now().isoformat(),
            "status": "running"
        }

        # Resume pipeline
        try:
            result = resume_research_pipeline(project_id)

            # Update status
            self.active_projects[project_id]["status"] = result["status"]
            self.active_projects[project_id]["completed_at"] = datetime.now().isoformat()

            return result

        except Exception as e:
            self.active_projects[project_id]["status"] = "failed"
            self.active_projects[project_id]["error"] = str(e)
            raise

        finally:
            self._archive_project_status(project_id)

    def list_projects(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all projects.

        Args:
            status_filter: Optional status to filter by (running, completed, failed)

        Returns:
            List of project information
        """
        projects = []

        # Get all project directories
        output_dir = self.file_manager.output_dir

        if not output_dir.exists():
            return []

        for project_dir in output_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_id = project_dir.name

            # Load metadata
            metadata = self._load_project_metadata(project_id)

            if metadata:
                if status_filter is None or metadata.get("status") == status_filter:
                    projects.append({
                        "project_id": project_id,
                        **metadata
                    })

        return projects

    def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific project.

        Args:
            project_id: Project ID

        Returns:
            Project status dictionary or None
        """
        # Check if active
        if project_id in self.active_projects:
            return self.active_projects[project_id]

        # Load from metadata
        return self._load_project_metadata(project_id)

    def cancel_project(self, project_id: str) -> bool:
        """
        Cancel a running project.

        Args:
            project_id: Project ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        if project_id in self.active_projects:
            self.active_projects[project_id]["status"] = "cancelled"
            self.active_projects[project_id]["cancelled_at"] = datetime.now().isoformat()
            self._archive_project_status(project_id)
            return True

        return False

    def cleanup_old_projects(self, days_old: int = 90) -> int:
        """
        Archive or delete old completed projects.

        Args:
            days_old: Archive projects older than this many days

        Returns:
            Number of projects archived
        """
        from datetime import timedelta

        threshold_date = datetime.now() - timedelta(days=days_old)
        archived_count = 0

        projects = self.list_projects()

        for project in projects:
            if project.get("status") != "running":
                completed_at = project.get("completed_at")

                if completed_at:
                    completed_date = datetime.fromisoformat(completed_at)

                    if completed_date < threshold_date:
                        # Archive project
                        self._archive_project(project["project_id"])
                        archived_count += 1

        return archived_count

    def _save_project_metadata(self, project_id: str, state: ResearchState):
        """Save project metadata to file."""
        metadata = {
            "project_id": project_id,
            "research_direction": state["research_direction"],
            "status": state["status"],
            "created_at": datetime.now().isoformat(),
            "hypothesis": state.get("hypothesis", ""),
        }

        self.file_manager.save_json(
            data=metadata,
            project_id=project_id,
            filename="project_metadata.json"
        )

    def _load_project_metadata(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Load project metadata from file."""
        return self.file_manager.load_json(
            project_id=project_id,
            filename="project_metadata.json"
        )

    def _archive_project_status(self, project_id: str):
        """Archive project status to metadata file."""
        if project_id in self.active_projects:
            status_data = self.active_projects.pop(project_id)

            # Update metadata
            metadata = self._load_project_metadata(project_id) or {}
            metadata.update(status_data)

            self.file_manager.save_json(
                data=metadata,
                project_id=project_id,
                filename="project_metadata.json"
            )

    def _archive_project(self, project_id: str):
        """Move project to archive directory."""
        # Create archive directory
        archive_dir = self.file_manager.output_dir.parent / "archive"
        archive_dir.mkdir(exist_ok=True)

        # Move project
        import shutil
        source = self.file_manager.get_project_path(project_id)
        destination = archive_dir / project_id

        if source.exists():
            shutil.move(str(source), str(destination))

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics about all projects.

        Returns:
            Statistics dictionary
        """
        projects = self.list_projects()

        total = len(projects)
        completed = len([p for p in projects if p.get("status") == "completed"])
        failed = len([p for p in projects if p.get("status") == "failed"])
        running = len([p for p in projects if p.get("status") == "running"])

        return {
            "total_projects": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "success_rate": (completed / total * 100) if total > 0 else 0
        }


# Example usage
def main():
    """Example usage of pipeline runner."""
    runner = PipelineRunner()

    # Run a project
    result = runner.run_project(
        research_direction="momentum strategies in equity markets"
    )

    print(f"Project completed: {result['project_id']}")
    print(f"Status: {result['status']}")

    # List all projects
    projects = runner.list_projects()
    print(f"\nTotal projects: {len(projects)}")

    # Get statistics
    stats = runner.get_statistics()
    print(f"\nStatistics:")
    print(f"  Completed: {stats['completed']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")


if __name__ == "__main__":
    main()
