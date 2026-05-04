## Step 4b — JTBD 解码 + 决策因子（子 Agent 执行）

> **执行方式**：派发子 Agent 执行，推理密集型任务
> **可与 Step 4c 并行执行**

---

### 前置条件

- Step 4a 已完成
- `raw/parse_result.json` 已存在

---

### 输入数据

子 Agent 读取 `raw/parse_result.json` 中的以下字段（仅摘要，不传完整 JSON）：
- 每个品牌的 `feedback`（前 500 字）
- 每个品牌的 `question`（前 300 字）
- 每个品牌的 `商品标题`
- 每个品牌的 `价格.券后价`

---

### 输出要求

**纯 JSON 输出**，写入 `output/step4b_jtbd.json`：

```json
{
  "decision_factors": [
    {
      "rank": 1,
      "rank_cls": "orange bold",
      "name": "亮度/够亮",
      "weight": "25%",
      "status": "有口碑（96+反馈）",
      "status_cls": "green",
      "gap": "良好",
      "gap_cls": "green"
    }
  ],
  "jtbd_functional": [
    "提供充足客厅照明（20-40㎡大空间够亮）",
    "护眼需求——儿童视力保护、全光谱低蓝光",
    "减少安装麻烦——免费上门安装、拆旧服务"
  ],
  "jtbd_emotional": [
    "让家\"显得有档次\"——大气体面，拒绝廉价感",
    "跟装修风格匹配——简约/中古/奶油风",
    "朋友来访时有面子，符合\"会选东西\"认知"
  ]
}
```

### decision_factors 字段规范

- **必须 7 条**，按权重从高到低排列
- `weight` 必须为百分比字符串（如 `"25%"`），7 条合计 = 100%
- `rank_cls`：前 3 名用 `"orange bold"`，其余留空
- `status_cls`：`green`（有优势）/ `orange`（中等）/ `red`（有差距）/ `gray`（待验证）
- `gap_cls`：同 `status_cls`
- `status` 必须包含具体数据支撑（如"有口碑（96+反馈）"），**禁止泛泛描述**

### jtbd 字段规范

- `jtbd_functional`：3-4 条，聚焦使用场景
- `jtbd_emotional`：3-4 条，聚焦情感/社会价值

---

### 状态上报

```
STATUS: SUCCESS | path=output/step4b_jtbd.json
```

### ⚠️ 禁止事项

1. 禁止输出 key_findings / price_matrix / positioning（这些由 Step 4a Python 生成）
2. 禁止输出 opportunity / threat / feedback_insights（这些由 Step 4c 生成）
3. 输出必须是**纯 JSON**，不得包含 markdown 包裹或解释文字
