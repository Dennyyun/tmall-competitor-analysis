## Step 4a — 竞争格局数值计算（本地 Python 执行）

> **执行方式**：Master Agent 直接调用 Python 脚本，不派发子 Agent
> **LLM 调用**：零
> **耗时**：< 2 秒

---

### 前置条件

- Step 3 已完成
- `raw/self.json`, `raw/p1.json`, `raw/p2.json`, `raw/p3.json` 均已存在

---

### 执行命令

```bash
python scripts/compute_landscape.py {taskId} {taskDir}
```

### 输出

写入 `output/step4a_landscape.json`，包含：

| 字段 | 类型 | 说明 |
|------|------|------|
| `key_findings` | `list[str]` | 4 条关键发现（价格/销量/评分/店铺评分对比） |
| `price_matrix` | `list[str]` | 价格带归类（性价比区/中端区/高端蓝海） |
| `positioning` | `dict` | 4 品牌基础定位（品牌名 + 价格带 + 销量级别） |
| `hero_exec_cards` | `list[dict]` | 首屏速览卡片骨架（JTBD/机会/威胁由 4b/4c 补充） |
| `analysis_date` | `str` | 分析日期 |
| `hero_badge` | `str` | 品牌标识 |
| `hero_title` | `str` | 报告标题 |

### 成功判定

```
STATUS: SUCCESS | path=output/step4a_landscape.json
```

### 失败处理

脚本以非零退出码退出，Master 读取 stderr 后上报。

---

### 后续步骤

Step 4a 完成后，Master 应**立即启动** Step 4b 和 Step 4c（可并行）。
