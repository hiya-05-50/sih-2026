from __future__ import annotations

"""Sprint 3 – Sandbox Tool implementation.

Provides the 'run_python' tool using a rootless Docker container
for strict Sovereignty OS isolation.
"""

import logging
import shlex
import subprocess
from typing import Any, Dict

from app.services.tools.registry import ToolDefinition, ToolResourceLimits
from shared.enums import RiskLevel, UserRole

logger = logging.getLogger(__name__)


def run_python_sandbox(code: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Execute arbitrary python code in an isolated Docker container.
    
    Args:
        code: The Python code to run.
        timeout_seconds: Hard timeout.
        
    Returns:
        Dict containing stdout, stderr, and exit_code.
    """
    logger.info("Executing code in sandbox...")
    
    # We use python:3.13-slim to match backend version
    # Enforce network=none for Sovereignty bounds
    cmd = [
        "docker", "run", "--rm",
        "--network", "none",
        "--memory", "256m",
        "--cpus", "1.0",
        "python:3.13-slim",
        "python", "-c", code
    ]
    
    try:
        # Run process and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "error": None
        }
    except subprocess.TimeoutExpired as e:
        return {
            "stdout": e.stdout.decode('utf-8') if e.stdout else "",
            "stderr": e.stderr.decode('utf-8') if e.stderr else "",
            "exit_code": -1,
            "error": "Execution timed out"
        }
    except Exception as e:
        logger.error(f"Sandbox execution failed to start: {e}")
        return {
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
            "error": str(e)
        }


def get_run_python_tool() -> ToolDefinition:
    """Return the registry definition for run_python."""
    return ToolDefinition(
        name="run_python",
        description="Execute arbitrary Python code in an isolated, network-less sandbox.",
        parameters={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The python code to execute."
                }
            },
            "required": ["code"]
        },
        risk_level=RiskLevel.AMBER,
        required_role=UserRole.ENGINEER,
        resource_limits=ToolResourceLimits(
            max_memory_mb=256,
            max_cpu_cores=1.0,
            timeout_seconds=30,
            network_access=False
        ),
        handler=run_python_sandbox
    )
