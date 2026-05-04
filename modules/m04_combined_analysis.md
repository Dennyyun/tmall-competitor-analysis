## Step 4 — 三合一合并分析（历史归档，v6.x）

> **历史说明**：本模块属于 v6.x 合并方案，原 Step 4+5+6 三步合并为一步，一次 LLM 调用输出全部结论。
> **当前 v7.0 主流程不再派发本模块**：请改用 `m04a_landscape.md`、`m04b_jtbd.md`、`m04c_insights.md`，再由 `merge_step4.py` 合并。
> 
> **核心收益**：省去 2 次子 Agent 冷启动 + 2 次 Session 通信 = **节省 12~15 分钟**

---

### 前置条件

- Step 3 已完成
- `parse_result.json` 已存在于 `{taskDir}/raw/`
- Step 7（原始数据 MD）可与本步骤并行执行

---

### 输入数据

```python
# 读取解析后的数据
parse_result = load_json(f"{taskDir}/raw/parse_result.json")
# 包含：self.json, p1.json, p2.json, p3.json 的完整解析内容
```

---

### 输出要求

**输出目标**：直接更新 `output/analysis.json`，写入以下字段（使用 analysis_manager.py）：

```json
{
  "analysis_date": "{日期}",
  "hero_badge": "{brand} · 竞品分析报告",
  "hero_title": "客厅吸顶灯竞品全景分析",
  "hero_exec_cards": [
    {"label": "竞品数量", "value": "3个核心竞品<br>+ 1个自家商品"},
    {"label": "核心JTBD", "value": "一句话描述"},
    {"label": "最大机会点", "value": "一句话描述"},
    {"label": "最需规避陷阱", "value": "一句话描述"},
    {"label": "流量格局", "value": "搜索截流型/种草型/混合型"}
  ],
  "positioning": { ... },
  "decision_factors": [ ... ],
  "jtbd_functional": [ ... ],
  "jtbd_emotional": [ ... ],
  "key_findings": [ ... ],
  "price_matrix": [
    "¥200-300 性价比区：品牌A vs 品牌B — 竞争最激烈，红海肉搏",
    "¥500-600 中端区：品牌C — 设计溢价路线",
    "¥800+ 高端护眼蓝海：品牌D — 独占护眼心智，定价权最强"
  ],
  "opportunity_1": { ... },
  "opportunity_2": { ... },
  "threat_1": { ... },
  "threat_2": { ... },
  "feedback_insights": [ ... ],
  "feedback_pain_points": { ... },
  "feedback_eye_rate": { ... }
}
```

---

### 分析框架（主 Agent 必须覆盖）

#### A. 流量结构判断（来自原 Step 4）

| 品牌 | 关键词策略类型 | 主要引流词 | 人群标签 | 流量来源 |
|------|---------------|-----------|---------|---------|
| self | | | | |
| p1 | | | | |
| p2 | | | | |
| p3 | | | | |

**判断依据**：
- 标题词频密度 → 直通车依赖型 / 自然搜索型
- 主图生活化程度 → 内容种草型
- feedback 集中度 → 活动/达人驱动型

#### B. JTBD 解码 + 决策阻力（来自原 Step 5）

```
功能性 JTBD：
- 护眼效果（解决孩子近视焦虑）
- 亮度/色温（够亮+可调）
- 安装便捷（不想麻烦）

情感性 JTBD：
- 家里变好看（档次感）
- 孩子喜欢（满足感）
- 被问哪买的（社交价值）

决策阻力地图：
- 质量耐用性：用久了会不会坏
- 安装复杂度：担心自己装不好
- 护眼有效性：是不是真的护眼
```

#### C. 竞争格局定位（来自原 Step 6）

**参数对比表**（从 raw/*.json 读取）：

| 对比项 | p1 | p2 | p3 | self |
|--------|-----|-----|-----|------|
| 券后价 | | | | |
| 原价 | | | | |
| 已售数量 | | | | |
| 评价总数 | | | | |
| 店铺评分 | | | | |
| 护眼认证 | | | | |
| 显色指数 Ra | | | | |
| 色温范围 | | | | |
| 无频闪 | | | | |
| 防蓝光 | | | | |
| 尺寸 | | | | |
| 光源寿命 | | | | |
| 保修期 | | | | |

**格局坐标轴**：
- X轴：价格（低 → 高）
- Y轴：护眼指数（弱 → 强）
- 标注各品牌位置
- 找出空白象限 = 机会点

---

### 强制校验规则

```python
# 完成后必须校验，所有字段不得为空
required_fields = [
    # 基础信息
    'analysis_date', 'hero_badge', 'hero_title', 'hero_exec_cards',
    # 定位
    'positioning.self', 'positioning.p1', 'positioning.p2', 'positioning.p3',
    # JTBD + 决策
    'decision_factors',  # 7条
    'jtbd_functional', 'jtbd_emotional',
    # 格局
    'key_findings',  # 4条
    'price_matrix',  # 3条
    'opportunity_1', 'opportunity_2',
    'threat_1', 'threat_2',
    # 用户反馈
    'feedback_insights',  # 4条
    'feedback_pain_points',
    'feedback_eye_rate'
]

def check_field(data, path):
    """检查嵌套字段，如 'positioning.self'"""
    keys = path.split('.')
    value = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return False
    return bool(value)

missing = []
for field in required_fields:
    if '.' in field:
        # 嵌套字段
        if not check_field(analysis, field):
            missing.append(field)
    else:
        # 顶层字段
        if not analysis.get(field):
            missing.append(field)

if missing:
    raise ValueError(f"Step 4 分析不完整，缺失字段: {', '.join(missing)}")
```

---

### 状态上报

```
STATUS: SUCCESS | path={taskDir}/output | files=[analysis.json]
```

---

### ⚠️ 风险控制

**单次 LLM 调用超载风险**：prompt 很长，确保：
1. 明确告知 LLM 输出格式必须严格遵循 JSON schema
2. 完成后用 JSON 验证器校验所有字段
3. 如校验失败，写入失败日志，重新调用一次（最多1次重试）
