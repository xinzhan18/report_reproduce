"""
SandboxManager — 实验代码的隔离执行环境

提供工作目录隔离、文件读写、进程执行、安全限制。
面板数据注入 + evaluate_factor 注入（因子研究模式）。
"""

# INPUT:  pathlib, subprocess, json, shutil, logging, inspect,
#         agents.experiment.metrics (evaluate_factor 源码注入)
# OUTPUT: SandboxManager 类
# POSITION: agents/experiment 子包 - 沙箱管理器

import json
import logging
import os
import shlex
import shutil
import subprocess
import inspect
from pathlib import Path

from agents.experiment.metrics import evaluate_factor

logger = logging.getLogger("agents.experiment.sandbox")

# 命令黑名单（子字符串匹配）
COMMAND_BLACKLIST = [
    "rm -rf /", "rm -rf /*", "rmdir /s", "del /f /s /q C:",
    "shutdown", "reboot", "mkfs", "format C:",
    ":(){:|:&};:", "fork bomb",
    "sudo", "chmod 777", "wget", "curl", "nc -l", "netcat",
]

SHELL_METACHARACTERS = [';', '|', '&&', '||', '$(', '`', '>>', '>', '<']

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
        """将 DataFrame dict 写入 sandbox/data/ 为 per-symbol CSV + panel.csv + manifest。

        写入:
        - data/<symbol>.csv — 每个品种独立 CSV
        - data/panel.csv — 长格式面板数据 (含 symbol 列)
        - data_manifest.json — {symbol: csv_path, _meta: {total_symbols, columns}}
        """
        import pandas as pd

        manifest = {}
        panel_frames = []

        for symbol, df in data_dict.items():
            csv_path = f"data/{symbol}.csv"
            df.to_csv(self.workdir / csv_path)
            manifest[symbol] = csv_path

            # 构建长格式面板
            frame = df.copy()
            frame["symbol"] = symbol
            panel_frames.append(frame)

        # 写 panel.csv（长格式）
        if panel_frames:
            panel = pd.concat(panel_frames)
            panel.to_csv(self.workdir / "data" / "panel.csv")

        # 写 manifest（含元信息）
        columns = list(data_dict[next(iter(data_dict))].columns) if data_dict else []
        manifest["_meta"] = {
            "total_symbols": len(data_dict),
            "columns": columns,
        }
        with open(self.workdir / "data_manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Injected {len(data_dict)} datasets into sandbox")

    def inject_helpers(self) -> None:
        """将 evaluate_factor 函数源码写入 sandbox。"""
        # 获取 evaluate_factor 及其私有辅助函数的源码
        import agents.experiment.metrics as metrics_module
        source = inspect.getsource(metrics_module)
        # 移除模块级 docstring 和 header comments，保留 import 和函数
        lines = source.split("\n")
        code_lines = []
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') and not in_docstring:
                in_docstring = True
                if stripped.count('"""') >= 2:
                    in_docstring = False
                continue
            if in_docstring:
                if '"""' in stripped:
                    in_docstring = False
                continue
            if stripped.startswith("#") and not code_lines:
                continue
            code_lines.append(line)

        helper_code = "\n".join(code_lines)
        with open(self.workdir / "evaluate_factor.py", "w", encoding="utf-8") as f:
            f.write(helper_code)
        logger.info("Injected evaluate_factor.py into sandbox")

    def run_command(self, command: str, timeout: int = 300) -> dict:
        """执行 shell 命令，返回 {stdout, stderr, returncode}。"""
        # 安全检查: 黑名单
        cmd_lower = command.lower().strip()
        for blocked in COMMAND_BLACKLIST:
            if blocked in cmd_lower:
                return {
                    "stdout": "",
                    "stderr": f"Blocked: command contains forbidden pattern '{blocked}'",
                    "returncode": -1,
                }

        # 安全检查: shell 元字符
        for meta in SHELL_METACHARACTERS:
            if meta in command:
                return {
                    "stdout": "",
                    "stderr": f"Blocked: shell metacharacter '{meta}' not allowed",
                    "returncode": -1,
                }

        # 解析命令为参数列表 (shell=False)
        try:
            cmd_parts = shlex.split(command, posix=(os.name != 'nt'))
        except ValueError as e:
            return {
                "stdout": "",
                "stderr": f"Invalid command: {e}",
                "returncode": -1,
            }

        try:
            result = subprocess.run(
                cmd_parts,
                shell=False,
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
        except FileNotFoundError:
            return {
                "stdout": "",
                "stderr": f"Command not found: {cmd_parts[0]}",
                "returncode": -1,
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
