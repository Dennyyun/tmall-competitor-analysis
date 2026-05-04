# tmall-ecommerce-competitor-analysis

天猫/淘宝竞品分析 Skill，用于串联商品采集、结构化解析、竞品格局计算、视觉分析、运营决策 JSON 生成、HTML 决策简报渲染和可选归档流程。此版本内置灯具行业运营决策框架，适合对已有商品 JSON 直接输出主决策、Top3动作、本轮不做事项、验证方案和关键支撑数据。

当前版本：v7.1-merged。

## 能力概览

- 通过影刀采集天猫/淘宝商品原始 JSON。
- 将 `raw/self.json`、`raw/p1.json`、`raw/p2.json`、`raw/p3.json` 解析成统一结构。
- 使用本地 Python 完成价格、销量、评分、定位等规则计算，减少 LLM 幻觉。
- 将 JTBD、机会威胁、视觉分析和运营决策拆成结构化 JSON 输出。
- 使用 `report_template.py` 生成 5 段式 HTML 运营决策简报。
- 可选上传 Cloudflare R2，并可选写入飞书文档/多维表格。
- 内置 `TaskStateMachine`，支持长流程断点续跑。
- 可直接读取本地商品 JSON，跳过采集步骤，按运营决策框架输出 HTML 决策简报。
- 强制输出 `decision_mode`、`data_quality_gate`、`conversion_blockers`、`evidence_chain`、`decision_summary`、`validation_plan`。
- 强制覆盖标题关键词、价格判断、评价问答、验证指标等关键支撑材料。

## 目录结构

```text
.
├── SKILL.md                 # Skill 主入口和执行规范
├── SKILL_REFERENCE.md       # 运行时参考手册
├── agents/                  # Codex agent 元数据
├── modules/                 # 每个 Step 的执行说明
├── references/              # 运营分析框架
├── scripts/                 # 采集、解析、合并、渲染脚本
├── tests/                   # 可公开的回归测试
├── .env.example             # 环境变量模板
└── requirements.txt
```

## 环境变量

复制 `.env.example` 为 `scripts/.env` 或设置系统环境变量。

```text
YINGDAO_ACCESS_KEY_ID=
YINGDAO_ACCESS_KEY_SECRET=
YINGDAO_ACCOUNT_NAME=
YINGDAO_ROBOT_UUID=

R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=reports
R2_PUBLIC_DOMAIN=

TASK_BASE_DIR=shared/tasks
```

飞书归档需要你在 `modules/m11_feishu.md` 中将 `{FEISHU_BASE_APP_TOKEN}` 和 `{FEISHU_BASE_TABLE_ID}` 替换为自己的飞书多维表格配置，或在派发子任务时显式传入。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 基本流程

1. 按 `SKILL.md` 初始化任务目录和商品清单。
2. 执行 Step 2 采集，产出 `raw/self.json`、`raw/p1.json`、`raw/p2.json`、`raw/p3.json`。
3. 执行 Step 3/4/7/8/9/9.5/10 生成 `output/analysis.json` 和 HTML 报告。
4. 按需执行 Step 10.5 上传 Cloudflare R2。
5. 按需执行 Step 11 飞书归档。

## 测试

```bash
python -m unittest tests.test_regression
```

## 开源发布说明

本仓库不应包含真实任务数据、真实报告、`.env`、API 密钥、Cloudflare R2 凭证、飞书 app token 或本机缓存。`.gitignore` 已默认排除这些内容。

## License

MIT
