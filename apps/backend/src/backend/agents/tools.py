from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

from .types import AgentTool, AgentToolResult, AgentToolSchema, TextContent

COMMAND_TIMEOUT = 30
MAX_OUTPUT_BYTES = 50_000

_SAFE_ENV_KEYS = {
    "PATH",
    "HOME",
    "LANG",
    "TERM",
    "TMPDIR",
    "USER",
    "LOGNAME",
    "SHELL",
}

_SAFE_ENV_PREFIXES = ("LC_",)

# Minimal toolset: small, composable primitives.
DEFAULT_TOOL_NAMES = [
    "read_file",
    "write_file",
    "edit_file",
    "run_command",
]


def _text_result(value: str) -> AgentToolResult:
    return AgentToolResult(content=[TextContent(text=value)])


def _safe_env() -> dict[str, str]:
    """Build an environment dict using a strict allowlist."""
    out: dict[str, str] = {}
    for k, v in os.environ.items():
        if k in _SAFE_ENV_KEYS or any(k.startswith(p) for p in _SAFE_ENV_PREFIXES):
            out[k] = v
    return out


def _resolve_path(cwd: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    path = (candidate if candidate.is_absolute() else cwd / candidate).resolve()

    cwd_resolved = cwd.resolve()
    try:
        path.relative_to(cwd_resolved)
    except ValueError as exc:
        raise ValueError(f"Path escapes workspace: {raw_path}") from exc

    return path


def create_culture_engine_tools(team: str, workspace_dir: str) -> list[AgentTool]:
    cwd = Path(workspace_dir).resolve()

    async def read_tool_execute(
        tool_call_id: str, params: dict, **_: object
    ) -> AgentToolResult:
        path = _resolve_path(cwd, params["path"])
        if not path.exists():
            raise ValueError(f"File not found: {path}")
        if path.is_dir():
            raise ValueError(f"Path is a directory: {path}")
        size = path.stat().st_size
        if size > MAX_OUTPUT_BYTES:
            raise ValueError(
                f"File too large to read: {path} ({size} bytes > {MAX_OUTPUT_BYTES} bytes)"
            )
        return _text_result(path.read_text())

    async def write_tool_execute(
        tool_call_id: str, params: dict, **_: object
    ) -> AgentToolResult:
        path = _resolve_path(cwd, params["path"])
        content = params.get("content", "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return _text_result(f"Wrote {len(content)} chars to {path}")

    async def edit_tool_execute(
        tool_call_id: str, params: dict, **_: object
    ) -> AgentToolResult:
        path = _resolve_path(cwd, params["path"])
        old_text = params["old_text"]
        new_text = params["new_text"]

        current = path.read_text()
        if old_text not in current:
            raise ValueError("old_text not found in file")

        updated = current.replace(old_text, new_text, 1)
        path.write_text(updated)
        return _text_result(f"Edited file: {path}")

    def _run_command_sync(
        command: str,
        timeout: int,
    ) -> tuple[bytes, bytes, int, bool, bool]:
        """Run a command in a subprocess, reading output with a size cap.

        Reads stdout and stderr in parallel threads, each capped at
        MAX_OUTPUT_BYTES // 2. If a stream exceeds the cap, the process
        group is killed immediately. The overall run is bounded by timeout.

        Returns (stdout, stderr, returncode, was_truncated, timed_out).
        """
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=str(cwd),
            env=_safe_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        wait_lock = threading.Lock()

        def _kill_pg() -> None:
            with wait_lock:
                if proc.poll() is not None:
                    return
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    return
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    if proc.poll() is None:
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
                    proc.wait()

        def _read_capped(stream, budget: int) -> tuple[bytes, bool]:
            """Read up to budget bytes from stream, then stop."""
            chunks: list[bytes] = []
            total = 0
            while total < budget:
                chunk = stream.read(min(4096, budget - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
            if total >= budget:
                _kill_pg()
            return b"".join(chunks), total >= budget

        def _close_pipes() -> None:
            for stream in (proc.stdout, proc.stderr):
                if stream:
                    try:
                        stream.close()
                    except OSError:
                        pass

        half = MAX_OUTPUT_BYTES // 2
        stdout_result: list[tuple[bytes, bool]] = []
        stderr_result: list[tuple[bytes, bool]] = []

        def _read_stdout() -> None:
            stdout_result.append(_read_capped(proc.stdout, half))

        def _read_stderr() -> None:
            stderr_result.append(_read_capped(proc.stderr, half))

        t_out = threading.Thread(target=_read_stdout)
        t_err = threading.Thread(target=_read_stderr)
        try:
            t_out.start()
            t_err.start()
            start = time.monotonic()
            t_out.join(timeout=timeout)
            remaining = max(0, timeout - (time.monotonic() - start))
            t_err.join(timeout=remaining)

            if t_out.is_alive() or t_err.is_alive():
                _kill_pg()
                _close_pipes()
                t_out.join(timeout=2)
                t_err.join(timeout=2)
                return b"", b"", -1, False, True

            with wait_lock:
                proc.wait()
            stdout, stdout_trunc = stdout_result[0] if stdout_result else (b"", False)
            stderr, stderr_trunc = stderr_result[0] if stderr_result else (b"", False)
            return stdout, stderr, proc.returncode, stdout_trunc or stderr_trunc, False
        finally:
            _close_pipes()

    async def run_command_execute(
        tool_call_id: str, params: dict, **_: object
    ) -> AgentToolResult:
        command = params["command"]
        timeout = max(
            1, min(int(params.get("timeout", COMMAND_TIMEOUT)), COMMAND_TIMEOUT)
        )

        (
            stdout,
            stderr,
            returncode,
            was_truncated,
            timed_out,
        ) = await asyncio.get_running_loop().run_in_executor(
            None, _run_command_sync, command, timeout
        )

        if timed_out:
            return _text_result(f"Command timed out after {timeout}s")

        output = stdout.decode(errors="replace")
        errors = stderr.decode(errors="replace")
        parts = [f"exit_code: {returncode}"]
        if output:
            parts.append(f"stdout:\n{output}")
        if errors:
            parts.append(f"stderr:\n{errors}")
        if was_truncated:
            parts.append(f"... output truncated at {MAX_OUTPUT_BYTES} bytes")
        return _text_result("\n".join(parts))

    return [
        AgentTool(
            name="read_file",
            description="Read a text file from the workspace.",
            parameters=AgentToolSchema(
                properties={
                    "path": {
                        "type": "string",
                        "description": "Absolute or workspace-relative file path.",
                    }
                },
                required=["path"],
            ),
            execute=read_tool_execute,
        ),
        AgentTool(
            name="write_file",
            description="Write text content to a file, creating parent directories if needed.",
            parameters=AgentToolSchema(
                properties={
                    "path": {
                        "type": "string",
                        "description": "Absolute or workspace-relative file path.",
                    },
                    "content": {"type": "string", "description": "File content."},
                },
                required=["path", "content"],
            ),
            execute=write_tool_execute,
        ),
        AgentTool(
            name="edit_file",
            description="Replace the first occurrence of old_text with new_text in a file.",
            parameters=AgentToolSchema(
                properties={
                    "path": {
                        "type": "string",
                        "description": "Absolute or workspace-relative file path.",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "Exact text to replace.",
                    },
                    "new_text": {"type": "string", "description": "Replacement text."},
                },
                required=["path", "old_text", "new_text"],
            ),
            execute=edit_tool_execute,
        ),
        AgentTool(
            name="run_command",
            description=(
                "Run a shell command in the workspace directory. "
                "Secrets are stripped from the environment and commands time out after 30 seconds. "
                "For filesystem search, prefer rg for content and fd for file/path discovery."
            ),
            parameters=AgentToolSchema(
                properties={
                    "command": {
                        "type": "string",
                        "description": (
                            "Shell command to execute. "
                            "For filesystem search, prefer rg -n <pattern> <path> and fd <pattern> <path>."
                        ),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Max seconds to wait (default 30, max 30).",
                        "default": 30,
                    },
                },
                required=["command"],
            ),
            execute=run_command_execute,
        ),
    ]
