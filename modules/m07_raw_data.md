## Step 7 — 生成 step1 原始数据文件【本地执行】

> **【当前 v7.0 沿用】Step 7 为本地执行**：纯数据格式化，无需子 Agent
> 
> **执行方式**：主 Agent 执行 `python scripts/generate_raw_md.py <taskId>`

---

### 前置检查

```python
import os

task_dir = f"shared/tasks/{taskId}"
required_files = [
    f"{task_dir}/raw/self.json",
    f"{task_dir}/raw/p1.json",
    f"{task_dir}/raw/p2.json",
    f"{task_dir}/raw/p3.json",
    f"{task_dir}/raw/parse_result.json",
]

for file_path in required_files:
    if not os.path.exists(file_path):
        raise RuntimeError(f"Step 7 前置条件不满足: {file_path} 未找到，请先完成 Step 3")
```

---

### 执行命令

```bash
python scripts/generate_raw_md.py {taskId}
```

脚本自动完成：
1. 读取 `raw/*.json`（self.json, p1.json, p2.json, p3.json）
2. 读取 `raw/parse_result.json`
3. 生成 4 个 step1_*.md 文件

---

**文件命名**：`output/step1_自身_原始数据.md`、`output/step1_竞品1_原始数据.md`、`output/step1_竞品2_原始数据.md`、`output/step1_竞品3_原始数据.md`

例如：
- `output/step1_竞品1_原始数据.md`
- `output/step1_竞品2_原始数据.md`
- `output/step1_竞品3_原始数据.md`
- `output/step1_自身_原始数据.md`

---


### 内容结构

每个文件包含：
- 基本信息（商品ID、标题、店铺、价格、销量等）
- 店铺评分
- 主图/详情图 URL
- 评价分析（完整原文）
- 问大家分析（完整原文）

### 状态上报

```
STATUS: SUCCESS | files=[output/step1_竞品1_原始数据.md, output/step1_竞品2_原始数据.md, output/step1_竞品3_原始数据.md, output/step1_自身_原始数据.md]
```

---

