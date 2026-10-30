from __future__ import annotations

import os
import sys

import pytest

from myagent.tools.base import ToolContext
from myagent.tools.shell import ShellTool

pytestmark = [pytest.mark.bronze, pytest.mark.skipif(os.name != "nt", reason="Windows only")]


def ctx(tmp_path, **kwargs):
    return ToolContext(
        workspace=tmp_path,
        timeout_s=10,
        max_output_chars=4000,
        python_exe=sys.executable,
        **kwargs,
    )


def test_powershell_echo(tmp_path):
    result = ShellTool().run({"command": "Write-Output 'hello'"}, ctx(tmp_path))
    assert result.returncode == 0
    assert "hello" in result.output


def test_powershell_chinese(tmp_path):
    result = ShellTool().run({"command": "Write-Output '你好'"}, ctx(tmp_path))
    assert result.returncode == 0
    assert "你好" in result.output


def test_powershell_quotes_and_newlines(tmp_path):
    result = ShellTool().run({'command': 'Write-Output "a`nb"'}, ctx(tmp_path))
    assert result.returncode == 0
    assert "a" in result.output
    assert "b" in result.output


def test_powershell_timeout(tmp_path):
    result = ShellTool().run({"command": "Start-Sleep 5", "timeout_s": 1}, ctx(tmp_path))
    assert result.returncode == -1
    assert "timeout" in result.error


def test_powershell_nonzero_exit(tmp_path):
    result = ShellTool().run({"command": "exit 3"}, ctx(tmp_path))
    assert result.returncode == 3
