# myagent

这是《人工智能综合实验》第 2 次课的 **Bronze 骨架**：一台能跑、能改、会留下轨迹的最小 Agent。

目标不是“做完”，而是：

1. 跑通 `doctor`；
2. 让 agent 调用一个真实工具完成一个小任务；
3. 留下一条 `.jsonl` 轨迹；
4. 在报告第八节写 3–5 条改进建议，知道自己哪里不行。

> 项目文件仅供参考；鼓励从零构建自己的 agent。不参考项目框架、独立实现，加分。

Silver / Gold 的 TODO 也在仓库里，标了 `Silver` / `Gold`；课内不要求。

## 1. 安装（三选一，只选你本机顺手的）

### 原生 Python venv

Windows PowerShell：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m myagent doctor
```

Linux / macOS：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m myagent doctor
```

### uv

```bash
uv sync --extra dev
uv run myagent doctor
```

### Anaconda

```bash
conda create -n myagent python=3.11 -y
conda activate myagent
python -m pip install -e ".[dev]"
python -m myagent doctor
```

> 不要求你适配别人的系统：Windows 同学只管 PowerShell（或自装 Git Bash），Linux/macOS 同学只管 bash/zsh。`run_shell` 的两个后端已经给好；你只需要让自己那一侧通过测试。

## 2. 配置模型

复制 `.env.example` 为 `.env`，填自己的 key：

```
MYAGENT_PROVIDER=dashscope
MYAGENT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MYAGENT_API_KEY=sk-...
MYAGENT_MODEL=qwen3.8-flash
```

DeepSeek：

```
MYAGENT_PROVIDER=deepseek
MYAGENT_BASE_URL=https://api.deepseek.com/v1
MYAGENT_API_KEY=sk-...
MYAGENT_MODEL=deepseek-chat
```

其他 OpenAI 兼容端点用 `MYAGENT_PROVIDER=custom`，自己填 `BASE_URL` / `MODEL`。本地 llama.cpp / vLLM / Ollama 也可以走这条路；`.env.example` 末尾有示例。

`.env` 不要提交。`doctor` 会检查它有没有被 git 跟踪。

## 3. 跑起来

```bash
python -m myagent doctor
python -m myagent run "在 workspace 里创建 hello.txt，内容为 hello myagent"
python -m myagent trace .myagent/sessions/<file>.jsonl
```

Windows 上把 `python` 换成你实际用的解释器（`.venv\Scripts\python.exe`、`uv run`、`conda run` 都可以）。

> 第一次来先读：`../course/实验指导书-第2次课.md`（从 C 到 Python、环境配置、H1/H2 步骤、求助模板）。

> 从骨架根目录用 `--workspace quests/01_env_report` 跑 agent 时，根目录 `.env` 会被自动读取；但 `check.py` 要 `cd` 到 quest 目录里跑（它检查当前目录的产物）。

## 4. 你真正要写的代码

| 位置 | 级别 | 写什么 |
|---|---|---|
| `src/myagent/agent.py::step` / `run` | Bronze | 模型调用 → 工具执行 → 观察回填 → 循环 |
| `src/myagent/tools/registry.py::execute` | Bronze | 工具分发、参数校验、异常/超时/截断 → observation |
| `src/myagent/tools/python_tool.py::run` | Bronze | 用 `sys.executable` 跑 Python 代码/文件，超时杀进程树 |
| `src/myagent/session.py::resume` | Silver | 从 `.jsonl` 断点恢复 |
| `src/myagent/context.py::maybe_compact` | Gold | 上下文压缩 |
| `src/myagent/agent.py::should_stop` | Bronze/Silver | 已经给了一个能用的版本；可以改 |

`src/myagent/tools/shell.py` **已经给好**：Windows PowerShell 和 POSIX bash 两个后端。你只需要跑本机测试；不需要为了“跨平台”去改另一个后端。

## 5. 测试

```bash
python -m pytest -m bronze      # 课内必须绿
python -m pytest -m silver      # 做完 resume 再跑
python -m pytest -m gold        # 做完压缩再跑
python -m pytest                # 全部
```

- `test_loop.py`、`test_tools.py`、`test_e2e.py` 是 Bronze，必须绿；
- `test_shell_win.py` / `test_shell_posix.py` 会自动 skip 掉不属于你系统的那个；
- `test_session.py`（Silver）、`test_context.py`（Gold）默认 skip，做完把 skip 去掉。

测试用 `FakeModel`，不花 API 钱。

## 6. Quest

```bash
cd quests/01_env_report
python check.py
```

- `01_env_report`：让 agent 生成 `env.json`；
- `02_pelican_bicycle`：让 agent 写一个 `pelican.svg`（骑自行车的鹈鹕）；用浏览器打开看，`check.py` 只查结构，不评画功。

从骨架根目录跑 agent 时用 `--workspace quests/02_pelican_bicycle`；`check.py` 要 `cd` 到 quest 目录里跑。

`task.md` 是给 agent 的任务；`check.py` 是判定；不要改 `check.py`。

## 7. 遇到问题

先跑：

```bash
python -m myagent doctor --report
```

把 `.myagent/doctor.json` 贴到群里。里面已经脱敏，不含 key。三张修复卡：

1. **401 / 模型不调工具**：`.env` 没加载、key 错、模型名错、端点不支持 tools。
2. **中文乱码**：Windows 设 `[Console]::OutputEncoding`；所有平台设 `PYTHONUTF8=1`。
3. **解释器不对**：`doctor` 会打印 `sys.executable`；用 `MYAGENT_PYTHON` 指向装了包的那个 Python。

## 8. 边界

- 这是教学骨架，不是生产工具；默认 20 步 / ¥0.5 / 300 秒。
- `run_shell` 可以执行任意命令；quest 在独立目录里做，别在重要仓库里 `--yolo`。
- 你不需要适配三平台；你只需要让自己的机器跑通。
