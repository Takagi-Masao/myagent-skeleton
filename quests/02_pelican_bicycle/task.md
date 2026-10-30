# Quest 02 · 骑自行车的鹈鹕

## 任务

在 workspace 里写一个 `pelican.svg`：**一只鹈鹕骑自行车**。

要求：

1. 单文件 SVG，不引用外部图片/字体；
2. 至少两个轮子（`circle`）；
3. 有车架/车身/鹈鹕（`path` / `line` / `rect` / `ellipse` / `polygon` 都行）；
4. 至少 3 种颜色；
5. `<title>` 写 `学号-鹈鹕骑车`；
6. 用浏览器打开能看；完成后调用 `submit`。

## 判定

```bash
python check.py
```

看到 `PASS quest02` 即完成。

## 提示

- 先让 agent 写一个粗糙版本，再让它自己读、改、验证；
- 这不是绘画比赛，考的是“用 harness 完成一个编码任务”；
- 画得抽象没关系，`check.py` 只看结构，不评画功；
- 想加动画/表情，属于加分项，不做也行。
