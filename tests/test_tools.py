from __future__ import annotations

import sys

import pytest

from myagent.tools.base import ToolContext
from myagent.tools.files import ListDirTool, ReadFileTool, WriteFileTool
from myagent.tools.python_tool import PythonTool
from myagent.tools.registry import ToolRegistry
from myagent.tools.submit import SubmitTool

pytestmark = pytest.mark.bronze


def ctx(tmp_path, **kwargs):
    defaults = {
        "workspace": tmp_path,
        "timeout_s": 5,
        "max_output_chars": 2000,
        "python_exe": sys.executable,
    }
    defaults.update(kwargs)
    return ToolContext(**defaults)


def test_unknown_tool_lists_available(tmp_path):
    registry = ToolRegistry()
    registry.register(PythonTool())
    result = registry.execute("nope", {}, ctx(tmp_path))
    assert result.returncode == -1
    assert "unknown tool" in result.error
    assert "run_python" in result.error


def test_invalid_json_arguments(tmp_path):
    registry = ToolRegistry()
    registry.register(PythonTool())
    result = registry.execute("run_python", "{not json", ctx(tmp_path))
    assert result.returncode == -1
    assert "invalid JSON" in result.error


def test_non_dict_arguments(tmp_path):
    registry = ToolRegistry()
    registry.register(PythonTool())
    result = registry.execute("run_python", ["code"], ctx(tmp_path))
    assert result.returncode == -1
    assert "JSON object" in result.error


def test_run_python_code(tmp_path):
    result = PythonTool().run({"code": "print('hello')"}, ctx(tmp_path))
    assert result.returncode == 0
    assert "hello" in result.output


def test_run_python_chinese_output(tmp_path):
    result = PythonTool().run({"code": "print('你好')"}, ctx(tmp_path))
    assert result.returncode == 0
    assert "你好" in result.output


def test_run_python_path_escape(tmp_path):
    result = PythonTool().run({"path": "../outside.py"}, ctx(tmp_path))
    assert result.returncode == -1
    assert "escapes workspace" in result.error


def test_run_python_timeout(tmp_path):
    result = PythonTool().run(
        {"code": "import time; time.sleep(5)", "timeout_s": 1},
        ctx(tmp_path),
    )
    assert result.returncode == -1
    assert "timeout" in result.error


def test_run_python_output_truncated(tmp_path):
    result = PythonTool().run({"code": "print('x' * 5000)"}, ctx(tmp_path, max_output_chars=300))
    assert result.returncode == 0
    assert result.truncated is True
    assert "chars omitted" in result.output


def test_write_read_list(tmp_path):
    write = WriteFileTool().run({"path": "notes/a.txt", "content": "line1\nline2\n"}, ctx(tmp_path))
    assert write.returncode == 0
    read = ReadFileTool().run({"path": "notes/a.txt", "start_line": 2, "end_line": 2}, ctx(tmp_path))
    assert read.returncode == 0
    assert "line2" in read.output
    listing = ListDirTool().run({"path": "notes"}, ctx(tmp_path))
    assert listing.returncode == 0
    assert "a.txt" in listing.output


def test_read_file_path_escape(tmp_path):
    result = ReadFileTool().run({"path": "../secret.txt"}, ctx(tmp_path))
    assert result.returncode == -1
    assert "escapes workspace" in result.error


def test_submit_sets_context(tmp_path):
    context = ctx(tmp_path)
    result = SubmitTool().run({"summary": "all done"}, context)
    assert result.returncode == 0
    assert context.submitted is True
    assert context.submission == "all done"
