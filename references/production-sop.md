# 内部 SOP：灯具/照明新品上架全案生产流程

适用版本：`v7.1 灯具/照明新品上架全案生产版`

本 SOP 用于把 1 个自家商品 + 3 个竞品商品 JSON 生成可交付给运营、美工和投放同事的《新品上架全案》Markdown。当前生产范围优先覆盖灯具/照明类目，尤其是吸顶灯、风扇灯、卧室灯、客厅灯等相近商品。

---

## 1. 任务输入准备

每个任务必须准备 4 个商品 JSON，并在任务目录中固定命名：

| 文件名 | 角色 | 选择标准 |
|---|---|---|
| `self.json` | 自家商品 | 本次要上架或要优化的商品 |
| `p1.json` | 竞品A | 最直接价格带竞品，优先选同价位/同功能/高销量商品 |
| `p2.json` | 竞品B | 第二核心竞品，可选同类目高销量、强服务或强品牌商品 |
| `p3.json` | 竞品C | 对标标杆或高价竞品，用来提炼差异化和信任打法 |

JSON 至少应包含以下字段，字段名以采集脚本输出为准：

| 字段 | 用途 |
|---|---|
| `商品ID` | 报告识别商品 |
| `商品标题` | 推断类目、标题关键词、功能词 |
| `店铺名称` | 生成自家/竞品标签 |
| `价格` | 生成价格带和 SKU 策略 |
| `已售数量` / `评价总数` | 判断市场规模和信任差距 |
| `店铺评分` | 市场概览对比 |
| `skus` | SKU 命名、价格梯度、套餐分析 |
| `feedback` | 评价证据，必须用于用户反馈洞察 |
| `question` | 问答证据，必须用于下单顾虑洞察 |

> 规则：涉及评论、评价、问答的结论，必须从 `feedback` / `question` 原文提取，并在最终报告中保留 `评价#编号` 或 `问答Q编号`。不得只引用摘要字段。

---

## 2. taskId 命名规范

新任务目录使用以下格式：

```text
YYYYMMDD-launch-{category}-{selfProductId}
```

示例：

```text
20260510-launch-fanlight-850298950508
20260510-launch-ceiling-light-766442618180
```

命名规则：

| 片段 | 说明 |
|---|---|
| `YYYYMMDD` | 任务创建日期 |
| `launch` | 表示本任务交付新品上架全案 |
| `{category}` | 英文类目短名，如 `fanlight`、`ceiling-light`、`bedroom-light` |
| `{selfProductId}` | 自家商品 ID |

如果同一天同商品需要重跑，使用后缀：

```text
20260510-launch-fanlight-850298950508-01
```

不得复用旧任务目录，避免覆盖历史报告和证据链。

---

## 3. 目录结构

每个任务目录结构固定为：

```text
shared/tasks/{taskId}/
├── raw/
│   ├── self.json
│   ├── p1.json
│   ├── p2.json
│   ├── p3.json
│   └── parse_result.json
├── output/
│   ├── step1_自身_原始数据.md
│   ├── step1_竞品1_原始数据.md
│   ├── step1_竞品2_原始数据.md
│   ├── step1_竞品3_原始数据.md
│   ├── step4a_landscape.json
│   ├── assets/
│   └── 新品上架全案_{taskId}.md
└── meta.md
```

正式运行前建议固定任务根目录：

```powershell
$env:TASK_BASE_DIR='E:\SKills\tmall-ecommerce-competitor-analysis\shared\tasks'
```

---

## 4. 标准运行命令

在项目根目录执行：

```powershell
cd E:\SKills\tmall-ecommerce-competitor-analysis
$env:TASK_BASE_DIR='E:\SKills\tmall-ecommerce-competitor-analysis\shared\tasks'
```

将 4 个 JSON 放入：

```text
shared/tasks/{taskId}/raw/self.json
shared/tasks/{taskId}/raw/p1.json
shared/tasks/{taskId}/raw/p2.json
shared/tasks/{taskId}/raw/p3.json
```

依次运行：

```powershell
python scripts\parse_raw_data.py {taskId}
python scripts\generate_raw_md.py {taskId}
python scripts\compute_landscape.py {taskId}
python scripts\render_launch_plan.py {taskId}
```

最终交付文件：

```text
shared/tasks/{taskId}/output/新品上架全案_{taskId}.md
```

---

## 5. 最终 Markdown 验收清单

交付前必须检查以下项目：

| 检查项 | 合格标准 |
|---|---|
| 标题 | 标题应为 `{类目} · 天猫新品上架全案`，不能残留其他旧类目 |
| 自家商品 | 页头自家商品 ID 与 `self.json` 一致 |
| 竞品映射 | 表格中竞品A/B/C 与 `p1/p2/p3` 一致 |
| 六章结构 | 必须包含市场概览、卖点策划、SKU方案、卖点转买点、决策指导、合规注意事项 |
| 评价/问答证据 | 用户反馈洞察必须出现 `评价#编号` 或 `问答Q编号` |
| 4.2 | 必须是方案对比表 + 文案层级表 + 示例图，不得退回纯代码块 |
| 4.3 | 必须是五张主图分工表 + 每图执行卡 + 示例图 |
| 4.4 | 必须是详情页四屏信任链 + 长屏结构示意 |
| 图片引用 | Markdown 引用的图片必须存在 |
| 合规提醒 | 不得出现无证据的“第一、全网最、保护视力、防近视、零差评”等表达 |

可用以下命令辅助检查：

```powershell
rg -n "^# |^## |^### 4\.2|^### 4\.3|^### 4\.4|评价#[0-9]|问答Q[0-9]" shared\tasks\{taskId}\output\新品上架全案_{taskId}.md
```

检查图片是否存在：

```powershell
$md='shared\tasks\{taskId}\output\新品上架全案_{taskId}.md'
Select-String -LiteralPath $md -Pattern '!\[[^\]]+\]\(([^)]+)\)' | ForEach-Object {
  if ($_.Line -match '\(([^)]+)\)') {
    $p = Join-Path (Split-Path $md) $Matches[1]
    "{0} {1}" -f (Test-Path $p), $Matches[1]
  }
}
```

---

## 6. 正式发布前检查

每次改脚本或框架后运行：

```powershell
python -m py_compile scripts\parse_raw_data.py scripts\generate_raw_md.py scripts\compute_landscape.py scripts\render_launch_plan.py scripts\report_template.py scripts\upload_report_assets_to_r2.py scripts\upload_to_cloudflare.py scripts\task_paths.py scripts\task_state.py scripts\task_state_machine.py
python -m unittest tests.test_regression
```

结果必须满足：

- Python 编译无错误。
- 回归测试全部通过。
- `scripts/render_launch_plan.py` 不得残留具体历史任务的固定商品名、店铺名或商品 ID。
- 真实任务数据、报告、`.env`、API 密钥不得提交到公开仓库。

---

## 7. 常见问题

### 生成内容混入旧类目怎么办？

优先检查 `scripts/render_launch_plan.py` 是否残留历史任务硬编码，例如旧商品名、旧店铺名、旧竞品标签。修复后重新渲染当前任务。

### 评价/问答没有证据怎么办？

报告中必须明确“自家评价/问答样本不足”，不能编造用户反馈。可以引用竞品原始评价/问答作为市场顾虑证据。

### 图片挪位置后无法显示怎么办？

本地交付默认使用 `output/assets/` 相对路径。分享给外部同事时，应把 Markdown 和 `assets/` 一起打包；如需在线稳定访问，再执行 R2 上传流程。

### 什么时候生成 HTML？

如果用户要运营决策简报、投放复盘或飞书归档，才继续执行 Step 8/9/9.5/10/10.5/11。只要新品上架全案时，通常不需要 HTML。
