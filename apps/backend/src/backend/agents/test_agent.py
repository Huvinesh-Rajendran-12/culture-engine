import asyncio
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class TestResult:
    passed: bool
    output: str
    error: Optional[str]
    execution_time: float
    workflow_path: str


async def test_workflow(workflow_path: str) -> TestResult:
    path = Path(workflow_path)

    if not path.exists():
        return TestResult(
            passed=False,
            output="",
            error=f"Workflow file not found: {workflow_path}",
            execution_time=0.0,
            workflow_path=workflow_path,
        )

    if not path.suffix == ".py":
        return TestResult(
            passed=False,
            output="",
            error=f"Invalid file type. Expected .py file, got {path.suffix}",
            execution_time=0.0,
            workflow_path=workflow_path,
        )

    start_time = time.time()

    try:
        process = await asyncio.create_subprocess_exec(
            "python",
            str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(path.parent),
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=30.0,
        )

        elapsed = time.time() - start_time

        output = stdout.decode("utf-8", errors="replace").strip()
        error_output = stderr.decode("utf-8", errors="replace").strip()

        passed = process.returncode == 0

        return TestResult(
            passed=passed,
            output=output,
            error=error_output if error_output else None,
            execution_time=elapsed,
            workflow_path=workflow_path,
        )

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        return TestResult(
            passed=False,
            output="",
            error="Workflow execution exceeded 30 second timeout",
            execution_time=elapsed,
            workflow_path=workflow_path,
        )
    except Exception as e:
        elapsed = time.time() - start_time
        return TestResult(
            passed=False,
            output="",
            error=f"Test execution failed: {str(e)}",
            execution_time=elapsed,
            workflow_path=workflow_path,
        )
