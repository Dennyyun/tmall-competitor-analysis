## Step 1 —任务初始化（主 Agent 执行）

### 1.1 生成任务标识

```
taskId 格式：YYYYMMDD-HHMMSS
示例：20260402-143022
```

### 1.2 与用户确认输入清单

```
□ 竞品1 商品链接/ID：{URL 或 ID}    品牌名：{品牌1}
□ 竞品2 商品链接/ID：{URL 或 ID}    品牌名：{品牌2}
□ 竞品3 商品链接/ID：{URL 或 ID}    品牌名：{品牌3}
□ 自身  商品链接/ID：{URL 或 ID}    品牌名：澳饰嘉
```

确认无误后，主 Agent 回复用户：

```
任务已初始化，taskId = {taskId}
即将开始 Step 2 影刀采集，预计耗时约 3~5 分钟（4个商品），是否继续？
```

### 1.3 建立目录结构

```
{TASK_BASE_DIR}\{taskId}\              # 默认 TASK_BASE_DIR=shared/tasks
├── raw\
│   ├── {品牌}_data.json         # 影刀采集的原始 JSON
│   ├── collection_errors.log    # 采集失败记录
│   └── main_images\             # 仅记录 URL，不下载
└── output\                      # 分析文件输出目录
```

---
