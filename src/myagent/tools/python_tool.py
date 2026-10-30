from __future__ import annotations

from .base import ToolContext, ToolResult


class PythonTool:
    name = "run_python"
    description = (
        "Run Python code or a Python file with the same interpreter as the agent. "
        "Use this for file/text processing, tests, and small scripts."
    )
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source to run. Use either code or path."},
            "path": {"type": "string", "description": "Path to a .py file inside the workspace."},
            "timeout_s": {"type": "integer", "description": "Timeout in seconds."},
        },
    }

    def run(self, args: dict, ctx: ToolContext) -> ToolResult:
        """Run Python with the same interpreter as the agent.

        Contract:
        - exactly one of code/path; both or neither -> error observation
        - code: write to <workspace>/.myagent/tmp/run_<id>.py
        - path: resolve inside workspace; reject ../ and absolute escapes
        - command: [ctx.python_exe, "-X", "utf8", <file>], cwd=workspace
        - env: PYTHONUTF8=1, PYTHONIOENCODING=utf-8
        - timeout: kill the whole process tree, return code -1, error contains
          "timeout"
        - return stdout+stderr, decoded UTF-8 with errors="replace"
        """
        raise NotImplementedError("H2: implement PythonTool.run() - see the docstring above")
