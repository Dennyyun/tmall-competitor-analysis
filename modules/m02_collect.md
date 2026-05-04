## Step 2 — 影刀采集（子 Agent 执行）

**子 Agent 被分配的任务**：调用 `run_batch()` 采集所有商品，将 JSON 写入当前任务目录的 `raw/`。

> **重要**：默认任务目录为 `shared/tasks/{taskId}`；实际路径由 `scripts/task_paths.py` 解析，可通过 `TASK_BASE_DIR` 或显式 `taskDir` 覆盖。
> `raw/` 目录下的 JSON 文件必须命名为 `self.json` / `p1.json` / `p2.json` / `p3.json`，后续 Step 3\~10 和 `report_template.py` 均依赖此命名。

### 执行方式（推荐）

```bash
python scripts/run_collect.py {taskId} "{自身链接}" "{竞品1链接}" "{竞品2链接}" "{竞品3链接}"
```

脚本执行后将自动：

1. 调用 `run_batch()`，并遵守 `product_collector.py` 内置风控常量
2. 【层一修复】`run_batch()` 内部自动写盘，无需外部处理
3. 将成功结果写入 `shared/tasks/{taskId}/raw/{brand}.json`
4. 将失败结果写入 `shared/tasks/{taskId}/raw/collection_errors.log`
5. 若存在失败品牌，先校验已成功文件真实可读，再只对失败品牌做定点补采

### 执行方式（直接调用 Python）

```python
from scripts.product_collector import run_batch
import os

task_dir = f"shared/tasks/{taskId}"
goods_list = [
    ('self', '{自身链接}'),
    ('p1', '{竞品1链接}'),
    ('p2', '{竞品2链接}'),
    ('p3', '{竞品3链接}'),
]

# 【v7.0】run_batch 内部已含定点补采（SELECTIVE_RETRY_ROUNDS=1）
# 禁止在外层再做 retry，重试权全部收归 run_batch
results = run_batch(goods_list, output_dir=f"{task_dir}/raw")

failed = [brand for brand, r in results.items() if r['status'] != 'success']
if failed:
    print(f"STATUS: FAILED | reason=采集失败: {', '.join(failed)}")
else:
    files = [f"{task_dir}/raw/{b}.json" for b in ['self', 'p1', 'p2', 'p3']]
    print(f"STATUS: SUCCESS | path={task_dir}/raw | files={files}")
```

### 子 Agent 完成后上报

```
STATUS: SUCCESS | path=shared/tasks/{taskId}/raw | files=[shared/tasks/{taskId}/raw/self.json, shared/tasks/{taskId}/raw/p1.json, ...]
```

或失败时：

```
STATUS: FAILED | reason=文件缺失或为空: p2, p3
```
