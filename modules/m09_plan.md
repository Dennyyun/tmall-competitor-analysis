## Step 9 — 运营决策 JSON 生成（子 Agent 执行）

> Step 9 的目标是生成“运营决策简报”所需的结构化 JSON，而不是生成归档报告样例中的冗长报告结构。
> 子 Agent 只输出纯净 JSON，写入 `output/step9_plan.json`，由 Step 9.5 合并到 `analysis.json`。

---

### 前置检查

```python
from scripts.analysis_manager import safe_read_analysis

task_dir = f"shared/tasks/{taskId}"
analysis = safe_read_analysis(task_dir)

if not analysis.get("visual_analysis"):
    raise RuntimeError("Step 9 前置条件不满足: analysis.json 缺少 visual_analysis")

step9_context = {
    "positioning": analysis.get("positioning"),
    "visual_analysis": analysis.get("visual_analysis"),
    "opportunity_1": analysis.get("opportunity_1"),
    "opportunity_2": analysis.get("opportunity_2"),
    "threat_1": analysis.get("threat_1"),
    "threat_2": analysis.get("threat_2"),
    "key_findings": analysis.get("key_findings"),
    "price_matrix": analysis.get("price_matrix"),
    "decision_factors": analysis.get("decision_factors"),
    "jtbd_functional": analysis.get("jtbd_functional"),
    "jtbd_emotional": analysis.get("jtbd_emotional"),
    "feedback_insights": analysis.get("feedback_insights"),
    "feedback_pain_points": analysis.get("feedback_pain_points"),
    "feedback_eye_rate": analysis.get("feedback_eye_rate"),
}
```

Master 如能读取 `raw/self.json`、`raw/p1.json`、`raw/p2.json`、`raw/p3.json`，必须额外投影商品标题、价格、销量、评价数、店铺评分、feedback 标签、question 顾虑标签和 SKU/评价抽样中的高频功能词。

---

### 决策机制

Step 9 必须按以下顺序推导：

1. **数据门槛**：标题、主图、SKU/规格、评价/问答、价格、竞品是否足以支撑决策。
2. **转化阻力诊断**：按搜索承接、首图点击、SKU选择、详情页信任、评价问答、投放承接定位阻力。
3. **证据链**：每个关键判断写出“原始数据 → 运营解释 → 支撑的决策”。
4. **单一主决策**：只选择一个本轮最该做的主策略；其他方向进入 `not_do_now` 或 P1/P2 动作。
5. **验证闭环**：没有真实 baseline 时，只能写新旧版本胜出，不得编造精确增长比例。

`decision_type` 只能使用：

| 类型 | 使用条件 |
|---|---|
| `execute` | 数据足够且多个证据指向同一个转化阻力，可直接执行 |
| `experiment` | 有明确判断但缺真实转化数据，需要 A/B 测试验证 |
| `collect_data` | 缺少关键数据，不能下强结论，先补评价/问答/图片/点击率/SKU数据 |
| `hold` | 当前动作可能带来误改或浪费，不建议本轮行动 |

---

### 灯具行业决策规则库

1. 如果标题缺少“吸顶灯/客厅主灯/全光谱/护眼/智能/适用面积”等词，而 SKU 或评价中存在这些卖点，优先判断为“搜索承接弱”。
2. 如果评价/问答高频出现“够不够亮、多少平、刺不刺眼、安装费”，详情页必须优先补“面积选型 + 亮度说明 + 安装说明”。
3. 如果商品价格明显低于品牌竞品，但评价体量弱，不能只主打低价，应主打“同配置更省 + 服务保障”。
4. 如果出现“塑料感、廉价、色差、不开灯不好看”等疑虑，主图/详情页必须补材质近景和不开灯实拍。
5. 如果全屋套餐存在但标题/首图没有表达，优先补套餐省钱心智，而不是只放在 SKU 里。
6. 如果声称护眼、无频闪、Ra97、全光谱，但缺少检测报告或证明素材，允许建议表达方向，但必须标注“需要证据素材支撑”。

---

### 输出 JSON Schema

只输出以下字段。不要输出归档报告样例中的冗长结构、团队大清单或长篇附录字段。

```json
{
  "decision_mode": {
    "business_goal": "提升转化",
    "decision_type": "execute | experiment | collect_data | hold",
    "decision_scope": "标题首图 | SKU | 详情页 | 评价问答 | 价格 | 投放",
    "reason": "为什么当前属于这个决策类型"
  },
  "data_quality_gate": {
    "can_make_final_decision": true,
    "missing_critical_data": ["缺失后会限制决策的关键数据"],
    "weak_data_points": ["存在但证据弱的数据点"],
    "decision_limitation": "本轮决策的边界和限制"
  },
  "conversion_blockers": [
    {
      "blocker": "搜索承接弱",
      "severity": "high | medium | low",
      "evidence": "支撑该阻力的具体数据或字段",
      "affected_stage": "搜索点击前 | 点击决策 | 加购决策 | 下单决策 | 流量放大",
      "priority": "P0 | P1 | P2"
    }
  ],
  "evidence_chain": [
    {
      "evidence": "原始证据",
      "source": "数据来源",
      "business_interpretation": "运营解释",
      "supports_decision": "该证据支持的决策判断"
    }
  ],
  "decision_summary": {
    "final_decision": "本轮唯一主决策",
    "why_this": "为什么优先做这个",
    "why_not_others": "为什么其他方案暂缓",
    "top3_actions": [
      {
        "priority": "P0",
        "action_type": "页面改版 | 数据补齐 | AB测试 | 评价运营 | 投放调整",
        "owner": "商品运营/设计/客服/投放/产品",
        "action": "具体动作",
        "acceptance_criteria": "验收标准；无baseline时只能写新旧版本胜出",
        "dependent_data": ["依赖的数据字段"],
        "deadline": "3天内/第1周",
        "risk": "执行风险"
      }
    ],
    "not_do_now": [
      {
        "item": "本轮暂不做的事项",
        "reason": "暂不做的原因"
      }
    ],
    "expected_impact": "预期影响，不编造精确提升比例",
    "confidence_level": {
      "level": "high | medium | low",
      "reason": "置信度原因",
      "what_would_increase_confidence": ["提升置信度所需数据"]
    },
    "decision_risks": ["最大风险或验证风险"]
  },
  "validation_plan": {
    "method": "AB测试 | 前后对比 | 人工审核 | 数据补齐",
    "primary_metric": "主指标",
    "secondary_metric": ["辅指标"],
    "no_baseline_rule": "没有baseline时，只判断新旧版本胜负，不编造精确增长比例"
  },
  "title_analysis": {
    "current_title": "当前自家标题",
    "missing_keywords": ["漏掉的高转化关键词"],
    "competitor_keyword_patterns": ["竞品标题共性"],
    "optimized_titles": [
      {
        "title": "可测试标题A",
        "intent": "对应搜索意图/人群"
      }
    ]
  },
  "pricing_strategy": {
    "price_position": "我方价格带和竞品差距",
    "promotion": ["优惠券/套餐优惠/赠品/价保建议"]
  },
  "review_qa_insights": {
    "purchase_reasons": ["好评中反复出现的购买理由"],
    "conversion_blockers": ["问答中反复出现的下单顾虑"],
    "review_guidance": ["评价引导模板"],
    "qa_to_seed": ["建议补充的买家问答"]
  },
  "kpi_table": [
    {
      "metric": "指标",
      "current": "当前基准",
      "target": "目标：新旧版本对比胜出",
      "target_cls": "green",
      "action": "关键行动"
    }
  ]
}
```

---

### 禁止事项

- 不要输出 Markdown 代码块标记。
- 不要输出任何自然语言解释。
- 不要输出多个并列推荐方案。
- 不要输出归档报告样例中的冗长字段或长篇附录字段。
- 不要编造点击率、转化率、增长百分比。

---

### 状态上报

```
STATUS: SUCCESS | file=output/step9_plan.json
```
