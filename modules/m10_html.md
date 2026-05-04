## Step 10 — 生成 HTML 报告【本地执行】

> **【v7.1-merged】Step 10 为本地执行**：纯模板渲染，无需子 Agent
> 
> **执行方式**：主 Agent 执行 `python scripts/report_template.py <taskId>`

---

### 前置检查

```python
import os
from scripts.analysis_manager import safe_read_analysis

task_dir = f"shared/tasks/{taskId}"

# 检查前置文件
required_files = [
    f"{task_dir}/raw/self.json",
    f"{task_dir}/raw/p1.json", 
    f"{task_dir}/raw/p2.json",
    f"{task_dir}/raw/p3.json",
    f"{task_dir}/output/analysis.json"
]

for f in required_files:
    if not os.path.exists(f):
        raise RuntimeError(f"Step 10 前置条件不满足: {f} 未找到")

# 检查 analysis.json 完整性
analysis = safe_read_analysis(task_dir)
required_fields = [
    'visual_analysis',
    'decision_mode',
    'data_quality_gate',
    'conversion_blockers',
    'evidence_chain',
    'decision_summary',
    'validation_plan',
]
for field in required_fields:
    if field not in analysis:
        raise RuntimeError(f"Step 10 前置条件不满足: analysis.json 缺少 {field} 字段")

# 决策简报支撑字段为推荐字段；缺失时报告仍会生成，但支撑数据会减少
recommended_fields = [
    'title_analysis',
    'pricing_strategy',
    'review_qa_insights',
    'kpi_table',
]
missing_recommended = [f for f in recommended_fields if not analysis.get(f)]
if missing_recommended:
    print(f"[WARN] 缺少决策简报支撑字段: {', '.join(missing_recommended)}")
    print("[NOTE] 报告仍会生成；如需完整关键支撑数据，请重新执行 Step 9")
```

---

### 执行命令

```bash
python scripts/report_template.py {taskId}
```

脚本自动完成：
1. 读取 `raw/*.json`（原始采集数据）
2. 读取 `output/analysis.json`（分析结论）
3. 校验决策简报所需字段，缺少 `decision_summary` / `decision_mode` / `data_quality_gate` 等字段时中止
4. 将 `experiment`、`medium`、`can_make_final_decision` 等技术字段翻译为运营可读语言
5. 渲染 5 段式运营决策简报：本轮主决策、为什么这样做、Top3执行动作、验证方案、关键支撑数据
6. 压缩展示标题、价格、评价问答等支撑材料，只保留决策简报需要的信息
7. 输出 `竞品分析报告_完整版_{taskId}.html`

---

### 输出文件

**文件路径**：`shared/tasks/{taskId}/output/竞品分析报告_完整版_{taskId}.html`

---

### 状态上报

```
STATUS: SUCCESS | path=shared/tasks/{taskId}/output/竞品分析报告_完整版_{taskId}.html
```

---
