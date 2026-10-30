# 痛点日志（可选工作笔记，不提交）

每条格式固定，方便后面比较。至少 3 条，至少 1 条有前后指标；最终写进报告第八节。

```yaml
- id: P001
  date: 2026-10-25
  task: "quest 02 画鹈鹕"
  symptom: "agent 重复同一条失败命令 4 次"
  evidence: "traj.jsonl#L42-L57"
  diagnosis: "observation 没带 returncode；prompt 没说连续失败要停"
  fix: "observation 加 returncode；连续 3 次错误注入提醒"
  metric_before: { success: false, steps: 18, tokens: 24000 }
  metric_after:  { success: true,  steps: 9,  tokens: 13000 }
```

## 我的记录

- P001：
- P002：
- P003：
