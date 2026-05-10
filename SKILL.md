---
name: tmall-ecommerce-competitor-analysis
description: 天猫/淘宝竞品采集流水线、电商运营竞品分析与新品上架全案技能。当天猫/淘宝商品链接、商品 ID、本地商品 JSON、竞品分析、商品拆解、定位分析、采集数据、生成 HTML 竞品报告、参考竞品做新品上架方案、设计超过竞品的卖点、五张主图逻辑、卖点转买点、决策指导、标题/主图/详情页/SKU/价格/评价/投放/30天行动计划等请求出现时使用；适合从链接自动采集，也适合对已有商品 JSON 直接做深度运营策略分析。
---

# 天猫/电商竞品分析 Skill（采集流水线 + 运营策略版）

***

## 触发条件

满足以下任一场景时激活本 Skill：

- 用户发送天猫/淘宝商品链接（含 `tmall.com / taobao.com`）
- 用户提供本地商品 JSON，并说明哪个是自家商品、哪些是竞品
- 用户说「竞品分析」「分析这个商品」「拆解竞品」「做定位分析」
- 用户说「采集数据」「出竞品报告」「直接分析这些 JSON」
- 用户提供商品链接 / 商品 ID + 任务类型
- 用户要求优化标题、主图、详情页、SKU、价格、评价、广告投放或 30 天行动计划
- 用户要求「参考竞品做新品上架方案」「完全超过竞品的卖点设计」「五张主图逻辑」「卖点转买点」「决策指导」

***

## ▌融合版使用原则

本 Skill 合并两类能力：

1. **自动化流水线能力**：沿用原 `tmall_competitor_analysis` 的采集、解析、状态机、HTML 报告、Cloudflare 上传、飞书归档能力。
2. **运营决策能力**：采用 `ecommerce-competitor-analysis` 的分析框架，把标题关键词、SKU、价格带、用户评价、买家问答、转化阻力、竞品成交逻辑和可执行优化动作收敛为一个主决策。
3. **新品上架全案能力**：参考竞品弱点和用户顾虑，设计自家超过竞品的卖点体系，将参数卖点转成用户买点，并落到标题、SKU、五张主图、详情页、合规文案和决策指导。

执行时按数据来源选择路径：

- **用户给天猫/淘宝链接或商品 ID**：优先走 Step 1-11 全流程，先采集再分析。
- **用户已给本地 JSON 文件**：跳过 Step 2 采集，从 Step 3/4/7/8/9 开始；若 JSON 已是结构化商品数据，也可直接按「运营分析标准」输出 Markdown/HTML 报告。
- **用户只要策略，不要 HTML/归档**：可只执行数据读取 + 运营分析报告，不强制上传 Cloudflare 或写飞书。
- **用户要新品上架全案**：Step 9 必须读取 `references/product-launch-plan-framework.md`，在常规决策字段之外输出 `launch_plan`；随后执行 `scripts/render_launch_plan.py` 生成固定六章结构 Markdown。若只需 Markdown 全案，可不强制执行 Step 10。

### 运营决策标准（Step 9 必须吸收）

所有竞品报告必须先给出一个默认以“提升转化”为目标的主决策，然后再展示支撑分析。Step 9 必须输出：

- `decision_mode`：执行、实验、补数据或暂缓。
- `data_quality_gate`：判断数据是否足以支撑结论。
- `conversion_blockers`：按搜索承接、首图点击、SKU选择、详情页信任、评价问答、投放承接诊断阻力。
- `evidence_chain`：原始数据 → 运营解释 → 决策判断 → 执行动作。
- `decision_summary`：本轮主决策、Top3动作、本轮不做、置信度和风险。
- `validation_plan`：AB测试或前后对比规则；没有 baseline 时只判断新旧版本胜负，不编造增长比例。
- `launch_plan`（按需）：新品上架全案，包含市场概览、SKU方案、超过竞品的核心打法、三层买点体系、卖点转买点、五张主图执行稿、详情页方案、决策指导和合规注意事项。
- `新品上架全案_{taskId}.md`（按需）：最终交付给运营/美工的固定六章 Markdown 全案，必须由原始评价和问答证据支撑。

支撑分析必须覆盖：

- 基础对比：商品定位、价格/到手价、销量/评价体量、店铺评分、核心卖点、优劣势。
- 标题关键词：品牌词、类目词、功能词、场景词、风格词、套餐/价格词；指出我方缺失的高转化词。
- 评价洞察：好评=成交理由，差评/负面表达=风险点，用户原话优先转成页面和广告文案。
- 问答洞察：问答=下单阻力，重点看质量、效果/亮度、适用面积、安装、售后、正品、廉价感、耐用、价格保护等。
- 价格与 SKU：判断引流款、主推款、利润款、升级款、套餐款；判断低价是高性价比还是低质心智。
- 竞品成功逻辑：逐个解释竞品靠品牌、价格、功能、套餐、服务、视觉、内容或渠道中的哪一个成交。
- 我方突破口：用「竞品弱点 / 用户痛点 / 我方打法」表格输出。
- 可执行方案：标题、主图逐张任务、详情页模块顺序、SKU命名、价格梯度、评价引导、搜索词/竞品词/内容种草方向。
- 新品上架全案：当用户要求参考竞品做新品方案时，必须输出“如果要超过竞品，我方靠什么赢”、五张主图逻辑、卖点转买点表和决策指导模块。
- 用户反馈洞察：涉及评论、评价、问答的判断必须从 `raw/*.json` 的 `feedback` / `question` 原文提取，回到评价编号或问答 Q 编号；不得只使用摘要字段。
- 本轮不做：明确暂不降价、暂不放大投放或暂不大改详情页等运营取舍。
- 30天行动计划：第1周到第4周给出运营、美工、投放、客服可执行动作。

详细检查清单见 `references/operations-analysis-framework.md`。

***

## ▌ Agent 角色定义与边界

> **这是本 Skill 最优先的执行规范，主/子 Agent 必须在启动前读取并遵守。**

### 主 Agent（Master）职责

- 接收用户输入，确认任务清单
- 按 Step 顺序逐一派发子任务给子 Agent
- 等待子 Agent 返回状态报告后，才派发下一个子任务
- 汇总所有结果，与用户确认后推进下一 Step
- **唯一有权与用户交互的 Agent，子 Agent 不得直接回复用户**
- 子 Agent 返回失败时，由主 Agent 决定是否重试或跳过，不得自行判断

### 子 Agent（Worker）职责与禁令

- 只执行被主 Agent 分配的**单一、明确定义的任务**
- 完成后将结果写入指定文件路径，并上报以下状态之一：
  ```
  STATUS: SUCCESS | path={输出文件路径} | files=[文件1, 文件2, ...]
  STATUS: FAILED  | reason={失败原因，不超过50字}
  ```
- **禁止自行扩展任务范围**（如被分配"采集竞品1"，不得顺带采集竞品2）
- **禁止自行重试**，最多执行 1 次，失败直接上报，由主 Agent 决策
- **禁止自行调用未在本次子任务中明确授权的工具**
- **禁止在未完成当前任务时启动新任务**

#### 子 Agent 写盘验证规范（Step 2 必须遵守）

> 调用 `run_batch()` 后，必须执行以下验证步骤，否则禁止上报 SUCCESS：

```python
from scripts.product_collector import run_batch
import os

goods_list = [("self", "..."), ("p1", "..."), ("p2", "..."), ("p3", "...")]
results = run_batch(goods_list, output_dir=f"{task_dir}/raw")

# 【强制】验证所有文件存在且非空
missing_files = []
for brand in ["self", "p1", "p2", "p3"]:
    file_path = f"{task_dir}/raw/{brand}.json"
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        missing_files.append(brand)

if missing_files:
    # 有文件缺失，必须上报 FAILED
    print(f"STATUS: FAILED | reason=文件缺失: {', '.join(missing_files)}")
else:
    # 全部验证通过，上报 SUCCESS 并列出所有文件路径
    files = [f"{task_dir}/raw/{b}.json" for b in ["self", "p1", "p2", "p3"]]
    print(f"STATUS: SUCCESS | path={task_dir}/raw | files={files}")
```

**违反后果**：若子 Agent 未验证文件存在就上报 SUCCESS，导致 Step 3 读取不到数据，属于**重大执行错误**。

### Step 派发规则（主 Agent 必须遵守）

```
每个 Step 启动前，主 Agent 必须确认：
  □ 上一个 Step 的所有子 Agent 已返回 SUCCESS
  □ 输出文件已存在于指定路径
  □ 未满足以上两条，禁止派发下一 Step
```

### Step 2 → Step 3 强制核对规则

> 主 Agent 在派发 Step 3 前，**必须**执行以下验证，否则禁止继续：

```python
import os

def verify_step2_completion(task_dir: str) -> bool:
    """
    验证 Step 2 采集任务是否真正完成。
    返回 True 表示可以派发 Step 3，False 表示必须终止并上报错误。
    """
    raw_dir = f"{task_dir}/raw"
    required_files = ["self.json", "p1.json", "p2.json", "p3.json"]
    
    # 检查目录存在
    if not os.path.exists(raw_dir):
        print(f"[ERROR] raw/ 目录不存在: {raw_dir}")
        return False
    
    # 检查每个文件存在且非空
    missing_or_empty = []
    for filename in required_files:
        file_path = os.path.join(raw_dir, filename)
        if not os.path.exists(file_path):
            missing_or_empty.append(f"{filename}(不存在)")
        elif os.path.getsize(file_path) == 0:
            missing_or_empty.append(f"{filename}(空文件)")
    
    if missing_or_empty:
        print(f"[ERROR] Step 2 文件验证失败: {', '.join(missing_or_empty)}")
        return False
    
    total_size = sum(os.path.getsize(os.path.join(raw_dir, f)) for f in required_files)
    print(f"[VERIFY] Step 2 完成: 4个文件已就绪，总大小 {total_size} bytes")
    return True

if not verify_step2_completion(task_dir):
    raise RuntimeError("Step 2 未完成，任务终止")
```

**违反后果**：若主 Agent 未验证文件就派发 Step 3，属于**重大执行错误**。

### 主 Agent 调用方式（Step 2 统一使用 run\_batch）

```python
from scripts.product_collector import run_batch

goods_list = [
    ("self", "完整天猫链接或纯商品ID"),
    ("p1",   "完整天猫链接或纯商品ID"),
    ("p2",   "完整天猫链接或纯商品ID"),
    ("p3",   "完整天猫链接或纯商品ID"),
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

***

【当前版本】v7.1 灯具/照明新品上架全案生产版。历史上 Step 5/6 已在 v6.0 合并入 Step 4；v7.0 将 Step 4 拆分为 4a/4b/4c/4d 并新增状态机断点续跑；v7.1 合并运营决策框架和新品上架全案框架，默认支持灯具/照明类目的新品上架全案交付。

***

### 状态机集成（v7.0 新增）

主 Agent 启动时必须初始化状态机，支持崩溃后断点续跑：

```python
from scripts.task_state_machine import TaskStateMachine, StepStatus

sm = TaskStateMachine(task_dir)
resume = sm.get_resume_point()
if resume and resume != "step_1":
    print(f"检测到未完成任务，从 {resume} 断点续跑")

# 每个 Step 派发前
can, reason = sm.can_proceed(current_step)
if not can:
    raise RuntimeError(f"前置依赖未满足: {reason}")
sm.mark(current_step, StepStatus.RUNNING)

# Step 完成后
sm.mark(current_step, StepStatus.SUCCESS)
# 失败时
sm.mark(current_step, StepStatus.FAILED, error=error_msg)
```

***

### Step 派发总表（v7.0）

主 Agent 在派发每个 Step 时，载入对应模块文件：

| Step | 执行方式 | 模块/脚本 | 说明 |
|------|----------|-----------|------|
| Step 1 | Master | m01\_init.md | 初始化任务目录 |
| Step 2 | 子 Agent | m02\_collect.md | 数据采集 |
| Step 3 | Master 脚本 | m03\_parse.md → parse\_raw\_data.py | 解析原始数据 |
| **Step 4a** | **Master 脚本** | **m04a\_landscape.md → compute\_landscape.py** | **纯 Python 数值计算（零 LLM）** |
| **Step 4b** | **子 Agent** | **m04b\_jtbd.md** | **JTBD + 决策因子（可与 4c 并行）** |
| **Step 4c** | **子 Agent** | **m04c\_insights.md** | **机会/威胁/反馈洞察（可与 4b 并行）** |
| **Step 4d** | **Master 脚本** | **merge\_step4.py** | **合并 4a+4b+4c → analysis.json** |
| Step 7 | Master 脚本 | m07\_raw\_data.md → generate\_raw\_md.py | 生成原始数据 MD |
| **Step 8** | **子 Agent** | **m08\_analysis.md** | **视觉分析（输入: step8\_visual\_input.json, ~3KB）** |
| Step 9 | 子 Agent | m09\_plan.md | 优化方案生成 |
| Step 9.5 | Master 脚本 | consolidate\_json.py | 合并 Step 8+9 到 analysis.json |
| Step 9.6 | Master 脚本 | render\_launch\_plan.py | 按需生成固定六章 Markdown 新品上架全案 |
| Step 10 | Master 脚本 | m10\_html.md → report\_template.py | HTML 报告生成 |
| Step 10.5 | Master 脚本 | upload\_to\_cloudflare.py | 上传到 Cloudflare R2 |
| Step 11 | 子 Agent | m11\_feishu.md | 飞书通知 |

> **【v7.0 变更】Step 4 拆分为 4a/4b/4c/4d，其中 4a 为纯 Python（零 LLM），4b 和 4c 可并行执行**
> **【v7.0 变更】Step 8 改为子 Agent 执行，输入源从 step1\_*.md（~38KB）改为 step8\_visual\_input.json（~3KB）**
> **【v7.0 变更】新增 TaskStateMachine 状态机，支持崩溃后断点续跑**

子 Agent 被派发时，只接收对应模块内容，不载入完整 SKILL.md。

````

***

> 📖 **技术规范与架构约束已抽离至 [SKILL_REFERENCE.md](./SKILL_REFERENCE.md) ，如需查看风控配置、报告生成底层逻辑、或禁止行为准则，请参阅该文件。**
> 📖 **运营分析维度已抽离至 [operations-analysis-framework.md](./references/operations-analysis-framework.md)，Step 8/9 或直接分析本地 JSON 时必须遵守。**
> 📖 **新品上架全案框架已抽离至 [product-launch-plan-framework.md](./references/product-launch-plan-framework.md)，当用户要求新品上架、五张主图、卖点转买点或决策指导时必须遵守。**
> 📖 **正式使用 SOP 已沉淀至 [production-sop.md](./references/production-sop.md)，用于规范 self/p1/p2/p3 准备、taskId 命名、运行命令和最终 Markdown 验收。**

***

## 执行流程总览（v7.0）

```
Step 1     任务初始化（主 Agent：确认输入 / 建立目录）
Step 2     影刀采集（子 Agent：调用 run_batch() 获取 JSON，写入 raw/）
Step 3     解析数据【本地执行】（主 Agent：执行 parse_raw_data.py）
Step 4a    格局计算【本地执行】（主 Agent：执行 compute_landscape.py → step4a_landscape.json）
Step 4b    JTBD分析【子 Agent】（读取 raw/parse_result.json → step4b_jtbd.json）
Step 4c    洞察分析【子 Agent】（读取 raw/parse_result.json → step4c_insights.json）
Step 4d    数据合并【本地执行】（主 Agent：执行 merge_step4.py → analysis.json）
Step 7     生成原始数据 MD【本地执行】（主 Agent：执行 generate_raw_md.py）
Step 8     视觉分析【子 Agent】（先执行 generate_visual_input.py，然后派发 → analysis.json）
Step 9     运营决策【子 Agent】（输出 step9_plan.json，首要字段为 decision_summary；按需输出 launch_plan）
Step 9.5   数据收敛【本地执行】（主 Agent：执行 consolidate_json.py）
Step 9.6   新品上架全案【本地执行】（按需执行 render_launch_plan.py，输出固定六章 Markdown）
Step 10    生成报告【本地执行】（主 Agent：执行 report_template.py）
Step 10.5  上传报告【本地执行】（主 Agent：执行 upload_to_cloudflare.py）
Step 11    飞书存档【子 Agent】（飞书通知）
```

> **版本沿革**：v6.0 将原 Step 4/5/6 合并，v6.1 新增 Step 10.5 Cloudflare 上传，v7.0 拆分 Step 4a/4b/4c/4d 并加入状态机断点续跑。
> **当前主流程以 v7.0 为准**：Step 4a 为纯 Python，Step 4b/4c 为子 Agent，Step 4d 负责合并；Step 8 由子 Agent 基于精简输入执行。

### 步骤依赖关系（v7.0）

```
Step 1 (初始化)
    ↓
Step 2 (采集) → raw/*.json
    ↓
Step 3 (解析) → parse_result.json 【本地执行，原子操作】
    ↓
Step 4a (格局计算) → step4a_landscape.json 【本地执行，零LLM】
    │
    ├─ Step 4b (JTBD) → step4b_jtbd.json 【子Agent】
    │
    ├─ Step 4c (洞察) → step4c_insights.json 【子Agent】
    │
    ├─ Step 7 (原始数据) → step1_*.md 【本地执行，与4a/4b/4c并行】
    │
Step 4d (数据合并) → analysis.json 【本地执行，等待4b+4c完成】
    │
Step 8 (视觉分析) → analysis.json.visual_analysis 【子Agent，等待4a+7完成，可与4b/4c/4d并行】
    ↓
Step 9 (优化方案) → step9_plan.json 【子Agent，依赖Step8的visual_analysis】
    ↓
Step 9.5 (数据收敛) → analysis.json 更新 【本地执行，合并Step9 JSON】
    ↓
Step 9.6 (新品上架全案) → 新品上架全案_{taskId}.md 【本地执行，按需生成】
    ↓
Step 10 (HTML决策简报) → HTML文件 【本地执行，模板渲染】
    ↓
Step 10.5 (Cloudflare上传) → 读取 ./modules/m10\_cloudflare.md 并执行 upload\_to\_cloudflare.py → cloudflare\_url.txt 【本地执行，获取公共URL】 ★ 新增
    ↓
Step 11 (飞书) → 飞书存档 【子Agent，飞书API调用】
```

**执行方式说明（v7.0）**：

- 🟢 **本地脚本**（Step 3, 4a, 4d, 7, 9.5, 10, 10.5）：文件 IO、规则计算或模板渲染
- 🟡 **主 Agent 编排**（Step 1 及所有 Step 边界）：初始化任务、检查依赖、更新状态机、决定是否继续
- 🔵 **子 Agent**（Step 2, 4b, 4c, 8, 9, 11）：采集、LLM 分析、优化方案与飞书归档

**关键依赖规则（v7.0 + 运营分析标准）**：

- Step 7 可在 Step 3 后执行，并可与 Step 4a/4b/4c 并行（不修改 analysis.json，无冲突）
- Step 8 必须在 Step 4a 和 Step 7 完成后执行（依赖 step4a_landscape.json 中的定位字段，也依赖 step1_*.md 原始数据文件，可与 4b/4c 并行）
- Step 8 写入 visual\_analysis 时**必须包含 desc 字段**（模板通过 `visual.get('self',{}).get('desc','')` 读取）
- Step 9 必须在 Step 8 完成后执行（依赖 analysis.json 中的 visual\_analysis），且必须吸收 `references/operations-analysis-framework.md` 中的决策机制、数据门槛、证据链、转化阻力、标题、主图、详情页、SKU、价格、评价、投放和 30 天计划标准
- 当任务包含新品上架方案、超过竞品、五张主图、卖点转买点或决策指导时，Step 9 必须额外吸收 `references/product-launch-plan-framework.md`，输出 `launch_plan`，其中 `decision_guidance` 必须说明本轮优先动作、暂不做事项和验证规则
- 当用户最终要“新品上架全案/新品策划全案”正文时，必须在 Step 9/9.5 后执行 `scripts/render_launch_plan.py`，最终 Markdown 顶层结构固定为：一、竞品市场概览；二、卖点策划方案；三、SKU方案策划；四、卖点转化为买点：创意图文案；五、决策指导模块；六、合规注意事项
- 评价/问答洞察必须直接来自原始 `feedback` / `question`，并引用评价编号或问答 Q 编号；摘要字段只能辅助定位
- Step 9 必须写入 `decision_mode`、`data_quality_gate`、`conversion_blockers`、`evidence_chain`、`decision_summary`、`validation_plan`；缺失时 Step 10 禁止生成决策简报
- Step 9.5 必须在 Step 9 完成后执行（合并 step9\_plan.json 进 analysis.json）
- Step 10 必须等待 Step 9.5 完成（检查 analysis.json 完整字段）
- **Step 10.5 必须等待 Step 10 完成（检查 HTML 文件存在）**
- **Step 11 必须等待 Step 10.5 完成（读取 cloudflare\_url.txt）**

**违反依赖规则的后果**：

- 前置步骤未完成就执行后续步骤 → **数据不完整或错误**
- 多个步骤同时写入 analysis.json → **数据损坏或丢失**（已用 analysis\_manager.py 防护）

***

## 完成回报格式（主 Agent 发给用户）

```
✅ DONE: {taskId}

报告路径：shared/tasks/{taskId}/output/竞品分析报告_完整版_{taskId}.html
Cloudflare链接：{cloudflare_url}          ★ 新增
飞书文档：{飞书文档链接}
多维表格记录：{record_id}

简报：
  本轮主决策：{一句话}
  Top3动作：{一句话概括}
  本轮不做：{一句话}
  验证方案：{一句话}

采集异常：{无 / 或列出失败商品}
```

***

_Skill 版本：v7.1 灯具/照明新品上架全案生产版_
_核心优化：在 v7.0 采集/解析/HTML/归档流水线基础上，合并电商运营决策框架与新品上架全案框架，强化数据门槛、证据链、转化阻力诊断、唯一主决策、Top3动作、五张主图、卖点转买点、决策指导和验证闭环。_
_Last updated: 2026-05-06_
