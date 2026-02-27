"""
OutputManager - Unified artifact saving and file management

Provides:
- Standardized artifact saving
- Format detection and conversion
- File organization
- Error handling
"""

from typing import Union, Dict, List, Any
import json
import logging
from pathlib import Path


class OutputManager:
    """
    Manages output artifacts for agents.

    Features:
    - Auto-format detection
    - JSON and text saving
    - Consistent file organization
    - Error handling and logging
    """

    def __init__(self, file_manager):
        """
        Initialize output manager.

        Args:
            file_manager: FileManager instance from tools
        """
        self.file_manager = file_manager
        self.logger = logging.getLogger("output_manager")

    def save_artifact(
        self,
        content: Union[str, Dict, List],
        project_id: str,
        filename: str,
        subdir: str,
        format: str = "auto"
    ):
        """
        Save artifact to file system.

        Args:
            content: Content to save (str, dict, or list)
            project_id: Project identifier
            filename: File name (with extension)
            subdir: Subdirectory within project (e.g., "literature", "experiments")
            format: Format type:
                - "auto": Auto-detect from content type
                - "json": Force JSON format
                - "text": Force text format
                - "markdown": Force markdown format

        Raises:
            Exception if saving fails
        """
        # Detect format if auto
        if format == "auto":
            format = self._detect_format(content, filename)

        try:
            if format == "json":
                self._save_json(content, project_id, filename, subdir)
            else:
                self._save_text(content, project_id, filename, subdir)

            self.logger.info(f"✓ Saved {format} artifact: {subdir}/{filename}")

        except Exception as e:
            self.logger.error(f"Failed to save artifact {subdir}/{filename}: {e}")
            raise

    def _detect_format(self, content: Any, filename: str) -> str:
        """
        Auto-detect format from content type and filename.

        Args:
            content: Content to save
            filename: File name

        Returns:
            Format string ("json", "text", or "markdown")
        """
        # Check filename extension
        if filename.endswith('.json'):
            return "json"
        elif filename.endswith('.md'):
            return "markdown"
        elif filename.endswith('.txt'):
            return "text"

        # Check content type
        if isinstance(content, (dict, list)):
            return "json"
        else:
            return "text"

    def _save_json(
        self,
        content: Union[Dict, List, str],
        project_id: str,
        filename: str,
        subdir: str
    ):
        """
        Save content as JSON.

        Args:
            content: Content (dict, list, or JSON string)
            project_id: Project ID
            filename: File name
            subdir: Subdirectory
        """
        # Convert string to dict if needed
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                # If it's not valid JSON, save as text with JSON extension warning
                self.logger.warning(
                    f"Content is string but not valid JSON, saving as text"
                )
                self._save_text(content, project_id, filename, subdir)
                return

        # Ensure .json extension
        if not filename.endswith('.json'):
            filename = f"{filename}.json"

        self.file_manager.save_json(
            data=content,
            project_id=project_id,
            filename=filename,
            subdir=subdir
        )

    def _save_text(
        self,
        content: Union[str, Dict, List],
        project_id: str,
        filename: str,
        subdir: str
    ):
        """
        Save content as text.

        Args:
            content: Content (str, dict, or list)
            project_id: Project ID
            filename: File name
            subdir: Subdirectory
        """
        # Convert non-string content to string
        if isinstance(content, (dict, list)):
            text_content = json.dumps(content, indent=2)
        else:
            text_content = str(content)

        self.file_manager.save_text(
            content=text_content,
            project_id=project_id,
            filename=filename,
            subdir=subdir
        )

    def save_multiple(
        self,
        artifacts: List[Dict[str, Any]],
        project_id: str
    ):
        """
        Save multiple artifacts at once.

        Args:
            artifacts: List of artifact dicts, each with keys:
                - content: Content to save
                - filename: File name
                - subdir: Subdirectory
                - format (optional): Format type
            project_id: Project ID
        """
        self.logger.info(f"Saving {len(artifacts)} artifacts...")

        for i, artifact in enumerate(artifacts, 1):
            try:
                self.save_artifact(
                    content=artifact["content"],
                    project_id=project_id,
                    filename=artifact["filename"],
                    subdir=artifact["subdir"],
                    format=artifact.get("format", "auto")
                )
            except Exception as e:
                self.logger.error(f"Failed to save artifact {i}/{len(artifacts)}: {e}")
                # Continue with other artifacts

        self.logger.info(f"✓ Completed saving artifacts")

    def load_artifact(
        self,
        project_id: str,
        filename: str,
        subdir: str,
        format: str = "auto"
    ) -> Union[str, Dict, List]:
        """
        Load artifact from file system.

        Args:
            project_id: Project ID
            filename: File name
            subdir: Subdirectory
            format: Format type ("auto", "json", "text")

        Returns:
            Loaded content

        Raises:
            FileNotFoundError if file doesn't exist
        """
        # Build file path
        file_path = Path("outputs") / project_id / subdir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Artifact not found: {file_path}")

        # Detect format
        if format == "auto":
            format = self._detect_format(None, filename)

        # Load based on format
        if format == "json":
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()

    def artifact_exists(
        self,
        project_id: str,
        filename: str,
        subdir: str
    ) -> bool:
        """
        Check if artifact exists.

        Args:
            project_id: Project ID
            filename: File name
            subdir: Subdirectory

        Returns:
            True if exists, False otherwise
        """
        file_path = Path("outputs") / project_id / subdir / filename
        return file_path.exists()
