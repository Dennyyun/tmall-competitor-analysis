## Step 8 — 视觉分析 JSON 生成（子 Agent 执行）

> **【v7.0 变更】Step 8 改为子 Agent 执行，输入源从 step1_*.md 改为精简的 step8_visual_input.json**
> 
> **核心收益**：上下文从 ~38KB 降至 ~3KB，消除 feedback/question 文本污染视觉分析

---

### 前置步骤（Master 执行）

Master 在派发子 Agent 前，先执行输入生成脚本：

```bash
python scripts/generate_visual_input.py {taskId} {taskDir}
```

此脚本从 `raw/*.json` 提取仅视觉分析所需的字段，输出 `output/step8_visual_input.json`。

---

### 前置检查

```python
import os

task_dir = f"shared/tasks/{taskId}"

# 检查精简输入文件
visual_input_path = f"{task_dir}/output/step8_visual_input.json"
if not os.path.exists(visual_input_path):
    raise RuntimeError("Step 8 前置条件不满足: 缺少 step8_visual_input.json，请先执行 generate_visual_input.py")

# 检查 analysis.json 中 Step 4 已写入 positioning
from scripts.analysis_manager import safe_read_analysis
analysis = safe_read_analysis(task_dir)
if not analysis.get("positioning"):
    raise RuntimeError("Step 8 前置条件不满足: analysis.json 缺少 positioning 字段")
```

---

### 输入数据

**仅读取** `output/step8_visual_input.json`，结构如下：

```json
{
  "self": {
    "shop_name": "澳饰嘉官方旗舰店",
    "title": "商品标题",
    "price": "264.71",
    "main_images": ["url1", "url2", "url3", "url4", "url5"],
    "detail_image": "详情图URL",
    "positioning": "性价比·3000+销量"
  },
  "p1": { ... },
  "p2": { ... },
  "p3": { ... }
}
```

> **⚠️ 禁止读取 step1_*.md 文件。** 这些文件包含大量与视觉无关的 feedback/question 文本，会导致上下文爆炸。

---

### 输出要求

**纯净 JSON，不要 Markdown 代码块**

写入 `output/step8_visual_analysis.json`：

```json
{
  "visual_analysis": {
    "self": {
      "desc": "自家主图弱点/机会的汇总文字（必填，支持HTML标签如<b>加粗</b>）",
      "score": "★★★☆☆",
      "score_cls": "score-mid",
      "overall_score": "6.5/10",
      "main_images": [
        {"strengths": "...", "weaknesses": "...", "opportunities": "...", "recommended_task": "主图1应承担的转化任务"},
        {"strengths": "...", "weaknesses": "...", "opportunities": "...", "recommended_task": "主图2应承担的转化任务"},
        {"strengths": "...", "weaknesses": "...", "opportunities": "...", "recommended_task": "主图3应承担的转化任务"},
        {"strengths": "...", "weaknesses": "...", "opportunities": "...", "recommended_task": "主图4应承担的转化任务"},
        {"strengths": "...", "weaknesses": "...", "opportunities": "...", "recommended_task": "主图5应承担的转化任务"}
      ],
      "detail_page": {"structure": "...", "trust": "...", "cta": "...", "recommended_order": ["第1屏：...", "第2屏：..."]}
    },
    "p1": { ... },
    "p2": { ... },
    "p3": { ... }
  }
}
```

---

### score_cls 必须正确映射

| overall_score 范围 | score_cls |
|---|---|
| 8.0-10.0 | `score-high` |
| 6.0-7.9 | `score-mid` |
| 0-5.9 | `score-low` |

**禁止所有品牌都用 `score-low`。** 根据实际分析结果赋予差异化评分。

---

### 分析内容要求

基于 `step8_visual_input.json` 中的主图 URL 和详情图 URL：

1. **商品主图**（5张）— 画面内容、文案信息、视觉策略、与竞品差异
2. **详情页长图** — 整体结构、卖点呈现、信任建立、行动引导
3. **主图任务分工** — 为每张主图给出推荐任务，例如首屏购买理由、核心痛点证明、功能参数证明、材质细节证明、套餐/价格/服务证明
4. **详情页模块顺序** — 输出推荐详情页顺序，供 Step 9 生成可执行优化方案

**不要分析 feedback 和 question** — 这些已由 Step 4c 处理。

---

### 字段说明

| 字段 | 必须 | 说明 |
|------|------|------|
| `visual_analysis.{brand}.desc` | ✅ | 弱点/机会汇总，支持HTML，**必须提及具体竞品对比** |
| `visual_analysis.{brand}.score` | ✅ | 星级评分，如 ★★★☆☆ |
| `visual_analysis.{brand}.score_cls` | ✅ | CSS class，必须与 overall_score 匹配 |
| `visual_analysis.{brand}.overall_score` | ✅ | 数字评分，如 6.5/10 |
| `visual_analysis.{brand}.main_images` | ✅ | 5张主图逐一分析，建议包含 recommended_task |
| `visual_analysis.{brand}.detail_page` | ✅ | 详情页分析，建议包含 recommended_order |

---

### 状态上报

```
STATUS: SUCCESS | path=output/step8_visual_analysis.json
```

---

### ⚠️ 禁止事项

1. **禁止读取 step1_*.md** — 使用 step8_visual_input.json 作为唯一输入
2. **禁止所有品牌 score_cls 相同** — 必须有差异化评分
3. **禁止在 desc 中分析 feedback/question** — 仅分析视觉元素
