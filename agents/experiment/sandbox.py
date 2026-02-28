"""
SandboxManager — 实验代码的隔离执行环境

提供工作目录隔离、文件读写、进程执行、安全限制。
"""

# INPUT:  pathlib, subprocess, json, shutil, logging, inspect,
#         agents.experiment.metrics (compute_metrics 源码注入)
# OUTPUT: SandboxManager 类
# POSITION: agents/experiment 子包 - 沙箱管理器

import json
import logging
import shutil
import subprocess
import inspect
from pathlib import Path

from agents.experiment.metrics import compute_metrics

logger = logging.getLogger("agents.experiment.sandbox")

# 命令黑名单（子字符串匹配）
COMMAND_BLACKLIST = [
    "rm -rf /", "rm -rf /*", "rmdir /s", "del /f /s /q C:",
    "shutdown", "reboot", "mkfs", "format C:",
    ":(){:|:&};:", "fork bomb",
]

# 输出截断限制
MAX_STDOUT = 10000
MAX_STDERR = 5000


class SandboxManager:
    """实验代码的隔离执行环境。"""

    def __init__(self, base_dir: str = "sandbox_workspaces"):
        self.base_dir = Path(base_dir).resolve()
        self.workdir: Path | None = None

    def create(self, experiment_id: str) -> Path:
        """创建隔离工作目录。"""
        self.workdir = (self.base_dir / experiment_id).resolve()
        self.workdir.mkdir(parents=True, exist_ok=True)
        (self.workdir / "data").mkdir(exist_ok=True)
        logger.info(f"Sandbox created: {self.workdir}")
        return self.workdir

    def inject_data(self, data_dict: dict) -> None:
        """将 DataFrame dict 写入 sandbox/data/ 为 CSV + manifest。"""
        manifest = {}
        for symbol, df in data_dict.items():
            csv_path = f"data/{symbol}.csv"
            df.to_csv(self.workdir / csv_path)
            manifest[symbol] = csv_path
        # 写 manifest
        with open(self.workdir / "data_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Injected {len(data_dict)} datasets into sandbox")

    def inject_helpers(self) -> None:
        """将 compute_metrics 函数源码写入 sandbox。"""
        source = inspect.getsource(compute_metrics)
        # 构造一个独立可 import 的 Python 文件
        helper_code = (
            "import pandas as pd\nimport numpy as np\n\n"
            + source
        )
        with open(self.workdir / "compute_metrics.py", "w", encoding="utf-8") as f:
            f.write(helper_code)
        logger.info("Injected compute_metrics.py into sandbox")

    def run_command(self, command: str, timeout: int = 300) -> dict:
        """执行 shell 命令，返回 {stdout, stderr, returncode}。"""
        # 安全检查
        cmd_lower = command.lower().strip()
        for blocked in COMMAND_BLACKLIST:
            if blocked in cmd_lower:
                return {
                    "stdout": "",
                    "stderr": f"Blocked: command contains forbidden pattern '{blocked}'",
                    "returncode": -1,
                }

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workdir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "stdout": result.stdout[:MAX_STDOUT],
                "stderr": result.stderr[:MAX_STDERR],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Command execution error: {e}",
                "returncode": -1,
            }

    def run_python(self, script_path: str, timeout: int = 300) -> dict:
        """运行 sandbox 中的 Python 脚本。"""
        resolved = self._resolve_path(script_path)
        if resolved is None:
            return {
                "stdout": "",
                "stderr": f"Path '{script_path}' is outside sandbox or does not exist",
                "returncode": -1,
            }

        import sys
        python_exe = sys.executable
        try:
            result = subprocess.run(
                [python_exe, str(resolved)],
                cwd=str(self.workdir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "stdout": result.stdout[:MAX_STDOUT],
                "stderr": result.stderr[:MAX_STDERR],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Script timed out after {timeout}s",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Script execution error: {e}",
                "returncode": -1,
            }

    def read_file(self, path: str) -> str:
        """读取 sandbox 中的文件。"""
        resolved = self._resolve_path(path)
        if resolved is None:
            return f"[ERROR] Path '{path}' is outside sandbox or does not exist"
        if not resolved.exists():
            return f"[ERROR] File not found: {path}"
        try:
            content = resolved.read_text(encoding="utf-8")
            if len(content) > MAX_STDOUT:
                content = content[:MAX_STDOUT] + f"\n... [truncated, total {len(content)} chars]"
            return content
        except Exception as e:
            return f"[ERROR] Failed to read file: {e}"

    def write_file(self, path: str, content: str) -> str:
        """写文件到 sandbox。"""
        resolved = self._resolve_path(path, must_exist=False)
        if resolved is None:
            return f"[ERROR] Path '{path}' resolves outside sandbox"
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        return f"OK: wrote {len(content)} chars to {path}"

    def delete_file(self, path: str) -> str:
        """删除 sandbox 中的文件。"""
        resolved = self._resolve_path(path)
        if resolved is None:
            return f"[ERROR] Path '{path}' is outside sandbox or does not exist"
        if not resolved.exists():
            return f"[ERROR] File not found: {path}"
        resolved.unlink()
        return f"OK: deleted {path}"

    def cleanup(self) -> None:
        """清理 sandbox 工作目录。"""
        if self.workdir and self.workdir.exists():
            shutil.rmtree(self.workdir, ignore_errors=True)
            logger.info(f"Sandbox cleaned up: {self.workdir}")

    def list_files(self) -> list[str]:
        """列出 sandbox 中的所有文件（相对路径）。"""
        if not self.workdir:
            return []
        files = []
        for p in self.workdir.rglob("*"):
            if p.is_file():
                files.append(str(p.relative_to(self.workdir)))
        return sorted(files)

    def _resolve_path(self, path: str, must_exist: bool = False) -> Path | None:
        """解析路径，禁止逃逸 workdir。返回 None 表示非法路径。"""
        if self.workdir is None:
            return None
        resolved = (self.workdir / path).resolve()
        # 路径隔离检查
        if not str(resolved).startswith(str(self.workdir)):
            return None
        if must_exist and not resolved.exists():
            return None
        return resolved
