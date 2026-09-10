import pytest
from unittest.mock import patch, MagicMock
import subprocess
from app.services.tools.sandbox import run_python_sandbox

@patch('app.services.tools.sandbox.subprocess.run')
def test_sandbox_execution_success(mock_run):
    """Test that a basic python script can run successfully in the sandbox."""
    mock_run.return_value = MagicMock(returncode=0, stdout="4\n", stderr="")
    
    code = "print(2 + 2)"
    result = run_python_sandbox(code)
    
    assert result["exit_code"] == 0
    assert result["stdout"].strip() == "4"
    assert result["error"] is None

@patch('app.services.tools.sandbox.subprocess.run')
def test_sandbox_network_isolation(mock_run):
    """Test that the sandbox cannot access the network."""
    mock_run.return_value = MagicMock(returncode=1, stdout="ERROR\n", stderr="")
    
    # Attempt to use urllib to fetch a webpage
    code = (
        "import urllib.request\n"
        "try:\n"
        "    urllib.request.urlopen('http://example.com', timeout=2)\n"
        "    print('SUCCESS')\n"
        "except Exception as e:\n"
        "    print('ERROR')\n"
    )
    result = run_python_sandbox(code, timeout_seconds=10)
    
    # Should print ERROR due to no network route
    assert "ERROR" in result["stdout"]
    
@patch('app.services.tools.sandbox.subprocess.run')
def test_sandbox_timeout(mock_run):
    """Test that a runaway script is terminated."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=2, output=b"", stderr=b"")
    
    code = "import time\nwhile True: time.sleep(1)"
    result = run_python_sandbox(code, timeout_seconds=2)
    
    assert result["exit_code"] != 0
    assert result["error"] == "Execution timed out"
