## Step 3 — 解析数据（本地执行）

> **本地直接执行，避免子 Agent 超时导致数据篡改问题**

### 执行方式

```bash
python scripts/parse_raw_data.py {taskId}
```

脚本会自动：

1. 读取 `raw/self.json`, `raw/p1.json`, `raw/p2.json`, `raw/p3.json`
2. 解析关键字段（标题、价格、销量、店铺、评分等）
3. **验证解析结果与原始数据的一致性**（防止数据篡改）
4. 生成 `raw/parse_result.json`

### 3.1 影刀 JSON 字段说明

| 字段名        | 类型   | 说明                            | 示例值                                             |
| ---------- | ---- | ----------------------------- | ----------------------------------------------- |
| `商品ID`     | str  | 天猫商品 ID                       | `"709926868838"`                                |
| `商品标题`     | str  | 商品主标题                         | `"欧普照明智慧光..."`                                  |
| `价格`       | dict | 含两个子字段                        | `{"券后价": "1963.47", "原价": "2924"}`              |
| `已售数量`     | str  | 销量显示值                         | `"1万+"`                                         |
| `评价总数`     | str  | 评价数显示值                        | `"1000+"`                                       |
| `店铺名称`     | str  | 店铺名                           | `"欧普照明官方旗舰店"`                                   |
| `店铺ID`     | str  | 店铺 ID                         | `"57301501"`                                    |
| `店铺评分`     | dict | 三项评分，**值为字符串需 float() 转换后比较** | `{"宝贝质量": "4.5", "服务保障": "4.6", "物流速度": "4.8"}` |
| `商品主图`     | list | 5 张主图 URL，顺序对应主图 1-5          | `["https://...", ...]`                          |
| `详情图`      | str  | 详情页合并长图 URL（单张）               | `"https://i.ibb.co/..."`                        |
| `feedback` | str  | 影刀预分析的评价文本，直接用于分析             | 见 3.3                                           |
| `question` | str  | 影刀预分析的问大家文本，直接用于分析            | 见 3.4                                           |

### 3.2 解析输出格式

生成的 `parse_result.json` 结构：

```json
{
  "self": {
    "title": "商品标题",
    "price_sale": "券后价",
    "price_ori": "原价",
    "sold": "已售数量",
    "reviews": "评价总数",
    "shop_name": "店铺名称",
    "shop_scores": {"宝贝质量": "4.5", "服务保障": "4.6", "物流速度": "4.8"},
    "main_images_count": 5,
    "detail_image": "详情图URL",
    "feedback_nonempty": true,
    "question_nonempty": true
  },
  "p1": { ... },
  "p2": { ... },
  "p3": { ... }
}
```

### 3.3 feedback 字段结构

```
【竞品全局印象标签】：
外观很好看(157), 安装效率高(141), 价格实惠(69), ...

【竞品详细评价抽样】：
1. [好评 · 有图 · 回头客 · SKU名称]
   初评: ...（用户原文）
   追评: ...（如有）
2. [中评 · SKU名称]
   初评: ...
3. [差评 · SKU名称]
   初评: ...
```

### 3.4 question 字段结构

```
【买家售前顾虑标签（提问焦点）】：
质量(40), 好用(5), 价格(4), 效果(3), 售后(2), ...

【核心问答抽样】：
Q1. [提问] ...（问题原文）
   A: ...（最佳答案）[已购 · SKU名称]
```

### 3.5 一致性验证机制

脚本内置验证，确保 parse\_result 与 raw/\*.json 一致：

```python
# 验证每个品牌的标题和店铺是否匹配
for brand in ['self', 'p1', 'p2', 'p3']:
    raw_title = raw_data['商品标题']
    parsed_title = parse_result[brand]['title']
    if raw_title != parsed_title:
        raise Error(f"{brand} 标题不匹配！")
```

**验证失败时**：脚本会报错并返回 `STATUS: FAILED`，不会生成错误的 parse\_result.json

### 完成后上报

```
STATUS: SUCCESS | path=raw/parse_result.json | brands=self,p1,p2,p3
```

或失败时：

```
STATUS: FAILED | reason=self.json 标题不匹配: raw='2026新款...' vs parsed='简顿无缝...'
```

***

