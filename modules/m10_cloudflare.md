## Step 10.5 — Cloudflare R2 上传（本地执行）

> **【顺序依赖】Step 10.5 必须在 Step 10 完成后执行，为 Step 11 提供公共访问链接**

**前置检查**（主 Agent 必须执行）：

```python
import os

# 检查 Step 10 是否已完成
task_dir = f"shared/tasks/{taskId}"
html_path = f"{task_dir}/output/竞品分析报告_完整版_{taskId}.html"

if not os.path.exists(html_path):
    raise RuntimeError(f"Step 10.5 前置条件不满足: HTML 报告未找到: {html_path}，请先执行 Step 10")

# 验证文件大小合理（至少 20KB）
file_size = os.path.getsize(html_path)
if file_size < 20 * 1024:  # 20KB
    raise RuntimeError(f"Step 10.5 前置条件不满足: HTML 报告文件过小 ({file_size} bytes)")
```

***

### 10.5.1 执行上传脚本

**主 Agent 执行命令**：

```bash
python scripts/upload_to_cloudflare.py {taskId}
```

或指定完整路径：

```bash
python scripts/upload_to_cloudflare.py {taskId} "{task_dir}/output/竞品分析报告_完整版_{taskId}.html"
```

***

### 10.5.2 成功输出格式

脚本执行成功后，输出格式：

```
Uploading report for task: {taskId}...
SUCCESS: https://your-domain.com/reports/{taskId}/report_{taskId}_{random}.html
[INFO] URL 已保存到: {task_dir}/output/cloudflare_url.txt
```

脚本会自动将 URL 保存到 `cloudflare_url.txt` 文件，供 Step 11 读取。

***

### 10.5.3 失败处理

**上传失败时的处理**：

```python
# 如果 upload_to_cloudflare.py 返回 FAILED
if "FAILED" in output:
    error_msg = output.replace("FAILED:", "").strip()
    
    # 记录错误日志
    error_log = f"{task_dir}/output/cloudflare_error.log"
    with open(error_log, 'w', encoding='utf-8') as f:
        f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Error: {error_msg}\n")
    
    print(f"STATUS: FAILED | reason=Cloudflare 上传失败: {error_msg}")
    
    # 主 Agent 决策：
    # 1. 终止任务（推荐）
    # 2. 跳过 Cloudflare 上传，继续执行 Step 11（但标记为"无公共链接"）
    raise RuntimeError(f"Cloudflare 上传失败: {error_msg}")
```

***

### 10.5.4 环境变量检查

执行前主 Agent 应检查环境变量：

```python
import os

required_env = ['R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY']
missing = [key for key in required_env if not os.environ.get(key)]

if missing:
    print(f"[WARNING] 缺少 Cloudflare 环境变量: {', '.join(missing)}")
    print("[INFO] 尝试从 .env 文件加载...")
    
    # 检查 .env 文件是否存在
    env_path = "scripts/.env"
    if not os.path.exists(env_path):
        raise RuntimeError(f"Cloudflare 配置缺失: 请设置环境变量或创建 {env_path} 文件")
```

***

## 输出文件

```
{TASK_BASE_DIR}\{taskId}\output\       # 默认 TASK_BASE_DIR=shared/tasks
├── 竞品分析报告_完整版_{taskId}.html
├── cloudflare_url.txt          # ★ 脚本自动生成：Cloudflare 公共链接
└── ...
```

***

## 与 Step 11 的衔接

Step 11 飞书存档时读取 URL：

```python
# Step 11 读取 Cloudflare URL
url_file = f"{task_dir}/output/cloudflare_url.txt"
cloudflare_url = ""
if os.path.exists(url_file):
    with open(url_file, 'r', encoding='utf-8') as f:
        cloudflare_url = f.read().strip()

# 写入多维表格字段
feishu_data = {
    "任务记录ID": taskId,
    "Cloudflare报告链接": cloudflare_url,  # ★ 新增字段
    # ... 其他字段
}
```
