# 竞品分析系统 运行时参考手册

> **说明：此文件为 SKILL.md 的扩展，包含各环节的具体技术规范、架构约束与禁止行为。在需要排查底层逻辑或编写新 Agent 指令时查阅。**

---

##  product\_collector.py 风控规范

> **采集风控约束必须封装在脚本函数内部，不依赖 Skill 文档提示。**
> 主 Agent 在 Step 2 前，必须先验证脚本中的以下常量是否存在且未被修改。
> 如任一常量缺失或被修改，**立即终止任务，上报错误，等待用户处理**。

### 脚本必须包含的硬编码常量

```python
# ═══════════════════════════════════════════
# ⚠️  风控红线 — 严禁修改以下常量
# ═══════════════════════════════════════════

DOWNLOAD_RETRIES   = 3     # 下载结果最大重试次数（网络问题单独重试）
RETRY_DELAY_SEC    = 10.0  # 重试前等待时间（秒）
DOWNLOAD_RETRY_DELAY = 5.0 # 下载重试间隔（秒）
BETWEEN_JOBS_SEC   = 6.0   # 两个商品之间强制间隔（秒）
POLL_INTERVAL_SEC  = 10.0  # 影刀任务状态轮询间隔（秒）
JOB_TIMEOUT_MIN    = 10    # 单任务最长等待时间（分钟）
# ═══════════════════════════════════════════
````

### 影刀返回数据结构说明

影刀任务完成后，`robotParams.outputs[0].value` 返回的是 **JSON 文件下载链接**（如 `https://xxx.r2.dev/.../analysis_xxx.json`），而非内联 JSON 数据。

脚本必须实现以下流程：

1. 从 `outputs` 提取下载链接
2. 使用 `requests.get()` 下载 JSON 文件内容
3. 验证内容为有效 JSON 后返回字符串

### 脚本必须包含的下载函数

```python
def download_json_from_url(url: str, timeout: int = 60) -> str:
    """从下载链接获取 JSON 内容

    Args:
        url: JSON 文件下载链接（影刀返回的 outputs[0]["value"]）
        timeout: 下载超时时间（秒）

    Returns:
        str: JSON 字符串内容

    Raises:
        RuntimeError: 下载失败或内容不是有效 JSON
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        # 验证是否为有效 JSON
        json.loads(response.text)
        return response.text
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"下载 JSON 文件失败: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"下载内容不是有效 JSON: {e}")
```

```python
def download_with_retry(download_url: str, max_retries: int = DOWNLOAD_RETRIES) -> str:
    """下载采集结果，支持独立重试（影刀任务已成功，只重试下载）"""
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return download_json_from_url(download_url)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(DOWNLOAD_RETRY_DELAY)

    raise RuntimeError(f"下载失败，已重试 {max_retries} 次。最后错误：{last_error}")
```

### 脚本必须包含的采集函数结构

```python
import time, random

def run(goods: str) -> str:
    """
    调用影刀采集单个商品数据。
    重试逻辑、延迟、超时均在函数内部强制执行，调用方不得覆盖。
    """
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            access_token = get_accesstoken()
            job_uuid = run_application(access_token, goods)
            deadline = time.time() + JOB_TIMEOUT_MIN * 60
            while time.time() < deadline:
                result_data = query_applicaton_status(access_token, job_uuid)
                status = result_data["statusName"]
                if status == "完成":
                    outputs = result_data["robotParams"]["outputs"]
                    download_url = outputs[0]["value"]
                    return download_with_retry(download_url)
                elif status == "异常":
                    raise RuntimeError(f"影刀任务异常：{result_data}")
                time.sleep(POLL_INTERVAL_SEC)
            raise TimeoutError(f"任务超时，已等待 {JOB_TIMEOUT_MIN} 分钟")
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)
    raise RuntimeError(f"采集失败，已重试 {MAX_RETRIES} 次。最后错误：{last_error}")


def run_batch(goods_list: list, output_dir: str = None, reset_log: bool = True, attempt_label: str = "initial") -> dict:
    """
    批量采集入口。每个商品之间强制间隔 BETWEEN_JOBS_SEC 秒。
    【层一修复】采集完成后立即写盘，验证 JSON 合法性，返回写入状态。
    """
    import os
    
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
    
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "collection_errors.log")
    
    results = {}
    for i, (brand, url) in enumerate(goods_list):
        file_path = os.path.join(output_dir, f"{brand}.json")
        try:
            # 1. 采集数据
            json_content = run(url)
            
            # 2. 验证 JSON 合法性
            json.loads(json_content)
            
            # 3. 原子写盘
            temp_path = file_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(json_content)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_path, file_path)
            
            # 4. 验证文件写入成功
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                raise RuntimeError(f"文件写入验证失败: {file_path}")
            
            # 5. 返回写入状态
            results[brand] = {
                "status": "success",
                "file": file_path,
                "size": os.path.getsize(file_path),
                "error": None
            }
        except Exception as e:
            error_msg = str(e)
            results[brand] = {
                "status": "failed",
                "file": None,
                "size": 0,
                "error": error_msg
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[FAILED] {brand} | {url} | {error_msg}\n")
        
        if i < len(goods_list) - 1:
            time.sleep(BETWEEN_JOBS_SEC)
    
    return results
```

## ▌：报告生成方式规范

> **Step 10 使用模板脚本 + analysis.json 生成报告，禁止手写 HTML 拼接代码。**

### 核心架构：数据层 + 模板层分离

```
{taskDir}/raw/*.json    ← 采集数据（影刀产出，自动生成）
{taskDir}/output/analysis.json ← Agent 分析结论（Step 4~9 收敛产出）
scripts/report_template.py ← HTML 模板脚本（固定不变）
```

**流程**：Step 4\~9 的子 Agent 将分析结论写入 `{taskDir}/output/analysis.json` → Step 10 执行 `python scripts/report_template.py {taskId}` → 自动读取 `{taskDir}` 下的两个数据源生成 HTML

### 核心原则

1. **采集数据从** **`{taskDir}/raw/self.json, p1.json, p2.json, p3.json`** **读取**（价格/销量/评分/热词等数值型字段）
2. **分析结论从** **`{taskDir}/output/analysis.json`** **读取**（定位/洞察/方案/行动等文本型字段）
3. **模板脚本** **`report_template.py`** **固定不变**，CSS/HTML 结构/辅助函数全部封装在脚本内
4. **Agent 不得手写 HTML 拼接代码**，只需按 schema 填入 analysis.json
5. **禁止 Jinja2 等模板引擎**，使用纯 Python 字符串拼接

### analysis.json 数据结构

完整 schema 见 `scripts/analysis_schema.json`，关键字段：

| 字段                          | 来源 Step    | 说明                           |
| --------------------------- | ---------- | ---------------------------- |
| `positioning`               | Step 4     | 4个品牌的核心定位                    |
| `key_findings`              | Step 4     | 竞品数据总览的关键发现（4条）              |
| `price_matrix`              | Step 4     | 价格定位矩阵（3条）                   |
| `visual_analysis`           | **Step 8** | 4个品牌的主图分析描述+评分（**子 Agent 基于精简输入执行**） |
| `decision_factors`          | Step 4     | 7个购买决策因子                     |
| `jtbd_functional/emotional` | Step 4     | 功能性/情感性 JTBD                 |
| `opportunity_1/2`           | Step 4     | 2个机会点                        |
| `threat_1/2`                | Step 4     | 2个威胁/陷阱                      |
| `feedback_insights`         | Step 4     | 热词核心洞察                       |
| `avoid_list`                | Step 9     | 不该模仿清单                       |
| `decision_mode`             | Step 9     | 决策目标、类型、范围和原因                |
| `data_quality_gate`         | Step 9     | 数据门槛、缺失数据、弱数据点和决策限制          |
| `conversion_blockers`       | Step 9     | 转化阻力诊断                       |
| `evidence_chain`            | Step 9     | 原始证据、来源、运营解释和支撑判断            |
| `decision_summary`          | Step 9     | 唯一主决策、Top3动作、本轮不做、置信度和风险    |
| `validation_plan`           | Step 9     | 验证方法、主指标、辅指标和无 baseline 规则    |
| `title_analysis`            | Step 9     | 标题关键词和可测试标题                  |
| `pricing_strategy`          | Step 9     | 价格位置和促销判断                    |
| `review_qa_insights`        | Step 9     | 评价购买理由和问答下单阻力                |
| `kpi_table`                 | Step 9     | 简报验证指标                       |

### Step 10 执行方式

```bash
python scripts/report_template.py {taskId}
```

脚本会自动：

1. 读取 `shared/tasks/{taskId}/raw/self.json, p1.json, p2.json, p3.json`
2. 读取 `shared/tasks/{taskId}/output/analysis.json`
3. 生成 `shared/tasks/{taskId}/output/竞品分析报告_完整版_{taskId}.html`

### 报告必须包含的 5 个 Section

| #   | Section 名称  | 内容要点                        |
| --- | ----------- | --------------------------- |
| S1  | 本轮主决策       | 一句话决策、为什么、暂缓事项、数据质量限制       |
| S2  | 为什么这样做      | Top 转化阻力、3-5条证据链、机会与风险     |
| S3  | Top3执行动作    | 负责人、动作、截止时间、验收标准            |
| S4  | 验证方案        | 主指标、辅指标、无 baseline 规则、关键KPI |
| S5  | 关键支撑数据      | 竞品价格/评价体量、标题关键词、价格判断、用户反馈 |

历史 HTML 样例已归档至 `archive/legacy_report_examples/`，仅作历史参考，不作为新报告模板。

### 生成后必须验证

- [ ] 报告中所有竞品名称、价格、销量、好评标签与本次 `raw/` 数据一致
- [ ] 不得出现旧竞品名字（如上一次任务的「简顿」「Yeelight」）
- [ ] HTML 文件大小合理（通常 20-30KB）
- [ ] analysis.json 中所有字段已填入，无占位符残留
- [ ] 不得出现归档样例中的旧章节结构

***

## ▌禁止行为铁律

> **以下行为属于重大错误，一旦违反导致报告内容全错。**
> 子 Agent 严禁执行，主 Agent 有责任在派发任务前核查。

### 禁止1：用旧报告/参考案例做字符串替换生成新报告

- **错误做法：** 找一个旧报告文件，只换品牌名/价格等少量字段后直接输出
- **正确做法：** 从本次任务目录下的 `raw/*.json` + `output/analysis.json` 生成内容
- **原因：** 旧报告中大量内容（竞品名称/标签/洞察/方案）与本次竞品无关，替换不干净导致报告内容完全错误。

### 禁止2：在报告生成阶段参考任何旧任务的输出文件

- 包含但不限于：旧任务的 HTML / MD / JSON / 脚本文件
- 脚本可以参考逻辑，但内容不得从旧文件读取或替换
- **数据源仅有两个：** 当前任务目录下的 `raw/*.json`（采集数据）+ `output/analysis.json`（分析结论）

### 禁止3：手写 HTML 拼接代码

- Step 10 **禁止**手写 HTML 拼接代码或创建新的 HTML 生成脚本
- **正确做法：** 只需按 `scripts/analysis_schema.json` 填入当前任务目录下的 `output/analysis.json`，然后执行 `python scripts/report_template.py {taskId}`
- **原因：** 手写 HTML 会导致每次报告格式不一致、CSS 漂移、硬编码旧数据

### 禁止4：在 analysis.json 中硬编码品牌名或分析结论

- 品牌名/店铺名/价格/销量等数值型字段必须从 `raw/*.json` 动态读取，不得硬编码
- analysis.json 中只填入 Agent 的**分析结论**（定位/洞察/方案/行动等），不填入原始数据
- **原因：** 硬编码品牌名会导致换竞品后报告内容错误

***

