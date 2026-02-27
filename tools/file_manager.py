"""
File management utilities for the research automation system.

Handles file I/O, directory creation, and project organization.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime


class FileManager:
    """
    Manages file operations for research projects.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize FileManager.

        Args:
            base_dir: Base directory for all projects (default: current directory)
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.data_dir = self.base_dir / "data"
        self.output_dir = self.base_dir / "outputs"

        # Ensure base directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_project_structure(self, project_id: str) -> Path:
        """
        Create directory structure for a new project.

        Args:
            project_id: Unique project identifier

        Returns:
            Path to project root directory
        """
        project_root = self.output_dir / project_id

        # Create subdirectories
        (project_root / "literature").mkdir(parents=True, exist_ok=True)
        (project_root / "experiments").mkdir(parents=True, exist_ok=True)
        (project_root / "reports").mkdir(parents=True, exist_ok=True)
        (project_root / "visualizations").mkdir(parents=True, exist_ok=True)

        return project_root

    def get_project_path(self, project_id: str, subdir: Optional[str] = None) -> Path:
        """
        Get path to project directory or subdirectory.

        Args:
            project_id: Project identifier
            subdir: Optional subdirectory (literature, experiments, reports)

        Returns:
            Path to requested directory
        """
        project_root = self.output_dir / project_id

        if subdir:
            return project_root / subdir

        return project_root

    def save_json(
        self,
        data: Dict[str, Any],
        project_id: str,
        filename: str,
        subdir: Optional[str] = None
    ) -> Path:
        """
        Save data as JSON file.

        Args:
            data: Dictionary to save
            project_id: Project identifier
            filename: Name of JSON file
            subdir: Optional subdirectory

        Returns:
            Path to saved file
        """
        if subdir:
            file_path = self.get_project_path(project_id, subdir) / filename
        else:
            file_path = self.get_project_path(project_id) / filename

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return file_path

    def load_json(
        self,
        project_id: str,
        filename: str,
        subdir: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load data from JSON file.

        Args:
            project_id: Project identifier
            filename: Name of JSON file
            subdir: Optional subdirectory

        Returns:
            Loaded dictionary or None if file doesn't exist
        """
        if subdir:
            file_path = self.get_project_path(project_id, subdir) / filename
        else:
            file_path = self.get_project_path(project_id) / filename

        if not file_path.exists():
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_text(
        self,
        content: str,
        project_id: str,
        filename: str,
        subdir: Optional[str] = None
    ) -> Path:
        """
        Save text content to file.

        Args:
            content: Text content to save
            project_id: Project identifier
            filename: Name of file
            subdir: Optional subdirectory

        Returns:
            Path to saved file
        """
        if subdir:
            file_path = self.get_project_path(project_id, subdir) / filename
        else:
            file_path = self.get_project_path(project_id) / filename

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_path

    def load_text(
        self,
        project_id: str,
        filename: str,
        subdir: Optional[str] = None
    ) -> Optional[str]:
        """
        Load text content from file.

        Args:
            project_id: Project identifier
            filename: Name of file
            subdir: Optional subdirectory

        Returns:
            File content or None if file doesn't exist
        """
        if subdir:
            file_path = self.get_project_path(project_id, subdir) / filename
        else:
            file_path = self.get_project_path(project_id) / filename

        if not file_path.exists():
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def list_projects(self) -> list[str]:
        """
        List all project IDs.

        Returns:
            List of project identifiers
        """
        if not self.output_dir.exists():
            return []

        return [
            p.name for p in self.output_dir.iterdir()
            if p.is_dir() and not p.name.startswith('.')
        ]

    def get_literature_cache_path(self) -> Path:
        """
        Get path to literature cache directory.

        Returns:
            Path to literature cache
        """
        cache_path = self.data_dir / "literature" / "pdfs"
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path

    def save_paper_pdf(self, arxiv_id: str, pdf_content: bytes) -> Path:
        """
        Save paper PDF to cache.

        Args:
            arxiv_id: arXiv paper ID
            pdf_content: PDF file content as bytes

        Returns:
            Path to saved PDF
        """
        cache_path = self.get_literature_cache_path()
        # Sanitize arxiv_id for filename
        safe_id = arxiv_id.replace("/", "_").replace(":", "_")
        pdf_path = cache_path / f"{safe_id}.pdf"

        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)

        return pdf_path

    def get_paper_pdf_path(self, arxiv_id: str) -> Optional[Path]:
        """
        Get path to cached paper PDF.

        Args:
            arxiv_id: arXiv paper ID

        Returns:
            Path to PDF if cached, None otherwise
        """
        cache_path = self.get_literature_cache_path()
        safe_id = arxiv_id.replace("/", "_").replace(":", "_")
        pdf_path = cache_path / f"{safe_id}.pdf"

        return pdf_path if pdf_path.exists() else None

    def create_backup(self, project_id: str) -> Path:
        """
        Create a backup of project directory.

        Args:
            project_id: Project identifier

        Returns:
            Path to backup directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{project_id}_backup_{timestamp}"
        backup_path = self.output_dir / backup_name

        # Copy project directory
        import shutil
        source_path = self.get_project_path(project_id)

        if source_path.exists():
            shutil.copytree(source_path, backup_path)

        return backup_path
