## Step 4c — 机会/威胁/反馈洞察（子 Agent 执行）

> **执行方式**：派发子 Agent 执行，推理密集型任务
> **可与 Step 4b 并行执行**

---

### 前置条件

- Step 4a 已完成
- `raw/parse_result.json` 已存在
- `output/step4a_landscape.json` 已存在（需读取 positioning）

---

### 输入数据

子 Agent 读取：
1. `raw/parse_result.json` — 每个品牌的 feedback（前 500 字）、question（前 300 字）
2. `output/step4a_landscape.json` — positioning 和 key_findings（作为分析上下文）

---

### 输出要求

**纯 JSON 输出**，写入 `output/step4c_insights.json`：

```json
{
  "opportunity_1": {
    "icon": "🚀",
    "title": "最大机会点标题",
    "content": "详细描述，包含具体数据支撑"
  },
  "opportunity_2": {
    "icon": "🌟",
    "title": "第二机会点标题",
    "content": "详细描述"
  },
  "threat_1": {
    "icon": "⚠️",
    "title": "最大威胁标题",
    "content": "详细描述，包含具体竞品数据"
  },
  "threat_2": {
    "icon": "🔒",
    "title": "第二威胁标题",
    "content": "详细描述"
  },
  "feedback_insights": [
    "洞察1：含具体数据对比",
    "洞察2：含具体数据对比",
    "洞察3：含具体数据对比",
    "洞察4：含具体数据对比"
  ],
  "feedback_pain_points": {
    "品牌A": "痛点描述",
    "品牌B": "痛点描述",
    "品牌C": "痛点描述",
    "品牌D": "痛点描述"
  },
  "feedback_eye_rate": {
    "品牌A": "护眼提及率描述",
    "品牌B": "护眼提及率描述",
    "品牌C": "护眼提及率描述",
    "品牌D": "护眼提及率描述"
  }
}
```

### 字段规范

- `opportunity_1` / `opportunity_2`：机会点，description 必须包含具体竞品数据和可行动建议
- `threat_1` / `threat_2`：威胁点，description 必须引用竞品具体销量/评价数据
- `feedback_insights`：4 条，每条必须包含至少一个具体数字（如"简顿亮度反馈(640)是澳饰嘉(96)的6.7倍"）
- `feedback_pain_points`：key 为品牌短名（不含"官方旗舰店"），value 描述该品牌的用户痛点
- `feedback_eye_rate`：key 同上，value 描述护眼内容提及程度

---

### 状态上报

```
STATUS: SUCCESS | path=output/step4c_insights.json
```

### ⚠️ 禁止事项

1. 禁止输出 decision_factors / jtbd（由 Step 4b 生成）
2. 禁止输出 key_findings / price_matrix / positioning（由 Step 4a Python 生成）
3. 输出必须是**纯 JSON**，不得包含 markdown 包裹或解释文字
