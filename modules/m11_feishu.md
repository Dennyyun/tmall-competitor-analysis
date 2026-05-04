## Step 11 — 飞书存档（子 Agent 执行）

> **【顺序依赖】Step 11 必须在 Step 10.5 完成后执行，读取 Cloudflare URL**

**前置检查**（子 Agent 必须执行）：

```python
import os

# 检查 Step 10 是否已完成
task_dir = f"shared/tasks/{taskId}"
html_path = f"{task_dir}/output/竞品分析报告_完整版_{taskId}.html"

if not os.path.exists(html_path):
    raise RuntimeError(f"Step 11 前置条件不满足: HTML 报告未找到: {html_path}，请先执行 Step 10")

# 验证文件大小合理（至少 20KB，经验值良好报告在 40-80KB）
file_size = os.path.getsize(html_path)
if file_size < 20 * 1024:  # 20KB
    raise RuntimeError(f"Step 11 前置条件不满足: HTML 报告文件过小 ({file_size} bytes)，可能生成不完整")

# ★ 新增：读取 Cloudflare URL（Step 10.5 生成）
url_file = f"{task_dir}/output/cloudflare_url.txt"
cloudflare_url = ""
if os.path.exists(url_file):
    with open(url_file, 'r', encoding='utf-8') as f:
        cloudflare_url = f.read().strip()
    print(f"[INFO] 读取到 Cloudflare URL: {cloudflare_url}")
else:
    print(f"[WARNING] 未找到 Cloudflare URL 文件: {url_file}")
```

***

### 11.1 多维表格信息

```
app_token：{FEISHU_BASE_APP_TOKEN}
table_id：{FEISHU_BASE_TABLE_ID}
```

### 11.2 写入字段

| 字段名         | 值来源                                   | <br /> |
| ----------- | ------------------------------------- | :----- |
| `任务记录ID`    | taskId                                | <br /> |
| `分析日期`      | 当天日期时间戳（ms）                           | <br /> |
| `自家商品ID`    | 用户输入                                  | <br /> |
| `竞品1~3商品ID` | 用户输入                                  | <br /> |
| `竞品品牌`      | raw/p1.json \~ p3.json 的 `店铺名称`       | <br /> |
| `核心JTBD`    | analysis.json → `jtbd_functional`     | <br /> |
| `最大机会点`     | analysis.json → `opportunity_1.title` | <br /> |
| `流量格局`      | analysis.json → `hero_exec_cards[4]`  | <br /> |
| `价格带`       | raw/\*.json 的 `价格.券后价` 汇总             | <br /> |
| `分析报告`      | cloudflare\_url                       | <br /> |
| `状态`        | 已完成                                   | <br /> |

***

### 11.3 飞书文档内容模板

创建飞书文档时，在文档开头添加 Cloudflare 链接：

```markdown
# 竞品分析报告

> **在线预览**: [点击查看完整报告]({cloudflare_url})

---

## 报告摘要
...
```

***

### 11.4 失败处理与重试机制

**飞书 API 失败时的处理策略**：

```python
import time

def write_to_feishu_with_retry(data, max_retries=3, retry_delay=5):
    """
    写入飞书，带重试机制
    
    Args:
        data: 要写入的数据
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
    """
    for attempt in range(1, max_retries + 1):
        try:
            # 尝试写入飞书
            result = write_to_feishu(data)
            print(f"[SUCCESS] 飞书写入成功（第{attempt}次尝试）", flush=True)
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"[WARNING] 飞书写入失败（第{attempt}次）: {error_msg}", flush=True)
            
            if attempt < max_retries:
                print(f"[INFO] 等待 {retry_delay} 秒后重试...", flush=True)
                time.sleep(retry_delay)
            else:
                # 所有重试都失败
                print(f"[FAILED] 飞书写入失败，已重试 {max_retries} 次", flush=True)
                
                # 记录错误日志
                log_path = f"{task_dir}/output/feishu_error.log"
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Error: {error_msg}\n")
                    f.write(f"Data: {json.dumps(data, ensure_ascii=False)}\n")
                
                # 上报失败状态
                print(f"STATUS: FAILED | reason=飞书写入失败（已重试{max_retries}次）: {error_msg}")
                raise RuntimeError(f"飞书写入失败: {error_msg}")
    
    return None
```

**主 Agent 决策选项**：

当飞书写入失败时，主 Agent 可选择：

1. **终止任务**：上报错误，等待人工处理
2. **跳过飞书**：继续执行，但标记为"未存档"
3. **手动重试**：等待一段时间后重新调用 Step 11

**建议**：默认选择**终止任务**，确保数据完整性。

***

## 文件输出目录（v7.0）

```
{TASK_BASE_DIR}\{taskId}\              # 默认 TASK_BASE_DIR=shared/tasks
├── raw\
│   ├── self.json
│   ├── p1.json
│   ├── p2.json
│   ├── p3.json
│   ├── collection_errors.log
│   └── parse_result.json
└── output\
    ├── analysis.json
    ├── step1_竞品1_原始数据.md
    ├── step1_竞品2_原始数据.md
    ├── step1_竞品3_原始数据.md
    ├── step1_自身_原始数据.md
    ├── step8_visual_analysis.json  # 可选调试文件，非后续必需输入
    ├── step9_plan.json
    ├── 竞品分析报告_完整版_{taskId}.html
    └── cloudflare_url.txt          # ★ 新增：Step 10.5 生成
```

***

## 工具清单

| 工具                                      | 用途                               | 调用方                 | <br /> |
| --------------------------------------- | -------------------------------- | ------------------- | :----- |
| `scripts/product_collector.run_batch()` | 影刀采集，含风控                         | 子 Agent（Step 2）     | <br /> |
| `scripts/parse_raw_data.py`             | 解析原始数据 → parse\_result.json      | 主 Agent（Step 3）     | <br /> |
| `scripts/generate_raw_md.py`            | 生成 step1\_\*.md 原始数据文件           | 主 Agent（Step 7）     | <br /> |
| `scripts/report_template.py`            | 从 raw + analysis.json 生成 HTML 报告 | 主 Agent（Step 10）    | <br /> |
| `scripts/consolidate_json.py`           | 合并 Step 9 的 JSON 到 analysis.json | 主 Agent（Step 9.5）   | <br /> |
| `scripts/upload_to_cloudflare.py`       | 上传报告到 Cloudflare R2              | 主 Agent（Step 10.5）  | ★ 新增   |
| `image`                                 | 分析主图和详情页长图 URL                   | **子 Agent（Step 8）** | <br /> |
| 生意参谋 / 蝉妈妈（可选）                          | 搜索词数据                            | 主 Agent（Step 4）     | <br /> |
| 飞书 MCP                                  | 写文档 + 多维表格                       | 子 Agent（Step 11）    | <br /> |

***

## 质量自检清单（主 Agent 在推进下一 Step 前必过）

```
Step 2 完成后：
□ raw/ 下 self.json, p1.json, p2.json, p3.json 已生成
□ collection_errors.log 无内容（或失败商品已告知用户）
□ feedback / question 字段非空

Step 4 完成后：
□ output/analysis.json 已生成
□ positioning、decision_factors、jtbd_functional/emotional、key_findings、
   price_matrix、opportunity/threat、feedback_insights/pain_points/eye_rate 等字段已填入
□ hero_exec_cards 已填入

Step 7 完成后：
□ 所有 step1_*.md 文件已生成（4个品牌）

Step 8 完成后：
□ output/analysis.json 中已写入 visual_analysis
□ visual_analysis 包含 self/p1/p2/p3 四个品牌
□ 每个品牌包含 desc（必填）、score（必填）、main_images、detail_page

Step 9 完成后：
□ output/step9_plan.json 已生成
□ decision_mode、data_quality_gate 已填入
□ conversion_blockers、evidence_chain 已填入
□ decision_summary 已填入，包含唯一主决策、Top3动作、本轮不做和置信度
□ validation_plan 已填入，包含主指标、辅指标和无 baseline 规则
□ title_analysis、pricing_strategy、review_qa_insights、kpi_table 等支撑字段按需填入

Step 10 完成后：
□ HTML 文件可在浏览器正常打开
□ HTML 文件大小合理（≥ 20KB）
□ 报告中的品牌名/价格/销量与本次 raw 数据一致

Step 10.5 完成后：            # ★ 新增
□ cloudflare_url.txt 已生成
□ URL 可正常访问

Step 11 完成后：
□ 多维表格记录 ID 已返回
□ 飞书文档链接可访问
□ Cloudflare 链接已写入多维表格
```

***
