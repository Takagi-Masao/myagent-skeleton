# Quest 01 · 环境报告

## 任务

在 workspace 里生成 `env.json`，包含这些字段：

```json
{
  "python_version": "3.11.9",
  "python_executable": "C:\\...\\python.exe",
  "platform": "Windows 11",
  "shell": "PowerShell 7"
}
```

要求：

1. 用 `run_python` 拿真实值，不要手写猜；
2. 完成后调用 `submit`。

## 判定

```bash
python check.py
```

看到 `PASS quest01` 即完成。

## 提示

- `sys.version`、`sys.executable`、`platform.system()`、`platform.release()`；
- shell 可以从环境变量或 `platform` 推断；不用 100% 精确，能说明你怎么得到的即可。
