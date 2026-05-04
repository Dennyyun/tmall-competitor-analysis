# -*- coding: utf-8 -*-
"""
Step 7 — 生成原始数据 Markdown 文件（本地执行）
将 parse_result.json 格式化为固定命名的 step1_*.md 原始数据文件

优化：从子 Agent 改为本地脚本执行，耗时从 ~2分钟 → ~1秒
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from task_paths import ensure_task_dir
from task_state import update_task_meta


def load_parse_result(task_dir: str) -> dict:
    """加载 parse_result.json"""
    path = os.path.join(task_dir, 'raw', 'parse_result.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_raw_data(task_dir: str, brand: str) -> dict:
    """加载原始采集数据"""
    path = os.path.join(task_dir, 'raw', f'{brand}.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_price_data(price_data: dict) -> str:
    """格式化价格数据"""
    if not price_data:
        return "暂无数据"
    
    lines = []
    for key, value in price_data.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def format_shop_scores(scores: dict) -> str:
    """格式化店铺评分"""
    if not scores:
        return "暂无数据"
    
    lines = []
    for key, value in scores.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _truncate_json_value(value, max_string_length: int = 240, max_items: int = 5):
    """Return a JSON-serializable preview without breaking syntax."""

    if isinstance(value, dict):
        preview = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= max_items:
                preview["_truncated_keys"] = max(0, len(value) - max_items)
                break
            preview[key] = _truncate_json_value(item, max_string_length=max_string_length, max_items=max_items)
        return preview

    if isinstance(value, list):
        preview_items = [
            _truncate_json_value(item, max_string_length=max_string_length, max_items=max_items)
            for item in value[:max_items]
        ]
        if len(value) > max_items:
            preview_items.append(f"... 已截断 {len(value) - max_items} 项")
        return preview_items

    if isinstance(value, str) and len(value) > max_string_length:
        return value[:max_string_length] + "... [truncated]"

    return value


def build_json_preview(raw_data: dict, max_length: int = 3000) -> str:
    """Build a valid JSON preview that stays readable and syntactically correct."""

    full_text = json.dumps(raw_data, ensure_ascii=False, indent=2)
    if len(full_text) <= max_length:
        return full_text

    preview_payload = {
        "_note": f"原始 JSON 过长，以下为合法预览（长度限制 {max_length} 字符）",
        "preview": _truncate_json_value(raw_data),
    }
    return json.dumps(preview_payload, ensure_ascii=False, indent=2)


def generate_raw_md(brand: str, brand_name: str, parse_data: dict, raw_data: dict) -> str:
    """生成单个品牌的原始数据 Markdown"""
    
    # 提取关键数据
    title = parse_data.get('title', '暂无标题')
    price_sale = parse_data.get('price_sale', '暂无')
    price_ori = parse_data.get('price_ori', '暂无')
    sold = parse_data.get('sold', '暂无')
    reviews = parse_data.get('reviews', '暂无')
    shop_name = parse_data.get('shop_name', '暂无')
    shop_scores = parse_data.get('shop_scores', {})
    main_images_count = parse_data.get('main_images_count', 0)
    
    # 提取 feedback 和 question（限制长度）
    feedback = raw_data.get('feedback', '')[:2000] if raw_data.get('feedback') else '暂无评价数据'
    question = raw_data.get('question', '')[:1000] if raw_data.get('question') else '暂无问答数据'
    
    # 生成 Markdown
    md = f"""# 原始数据：{brand_name}

> 生成时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> 数据来源：天猫商品采集

---

## 基础信息

| 字段 | 数值 |
|------|------|
| 商品标题 | {title} |
| 店铺名称 | {shop_name} |
| 券后价 | {price_sale} 元 |
| 原价 | {price_ori} 元 |
| 已售数量 | {sold} |
| 评价总数 | {reviews} |
| 主图数量 | {main_images_count} 张 |

---

## 店铺评分

{format_shop_scores(shop_scores)}

---

## 评价反馈（前2000字）

```
{feedback}
```

---

## 问大家（前1000字）

```
{question}
```

---

## 原始 JSON 结构

```json
{build_json_preview(raw_data)}
```

> 注：为保证代码块中的 JSON 始终合法，超长内容会转换为结构化预览
"""
    
    return md


def main():
    """主入口"""
    if len(sys.argv) < 2:
        print("用法: python scripts/generate_raw_md.py <taskId>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    task_dir = str(ensure_task_dir(task_id))
    output_dir = os.path.join(task_dir, 'output')
    
    print("=" * 60)
    print("Step 7 — 生成原始数据 Markdown 文件")
    print("=" * 60)
    print(f"\nTask ID: {task_id}")
    print(f"Output Dir: {output_dir}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 加载数据
        parse_result = load_parse_result(task_dir)
        
        # 品牌映射
        brand_map = {
            'self': '自身',
            'p1': '竞品1',
            'p2': '竞品2',
            'p3': '竞品3'
        }
        
        generated_files = []
        
        for brand, brand_label in brand_map.items():
            if brand not in parse_result:
                print(f"\n[SKIP] {brand}: 数据不存在")
                continue
            
            # 加载原始数据
            raw_data = load_raw_data(task_dir, brand)
            
            # 生成 Markdown
            md_content = generate_raw_md(brand, brand_label, parse_result[brand], raw_data)
            
            # 写入文件
            output_path = os.path.join(output_dir, f'step1_{brand_label}_原始数据.md')
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            generated_files.append(output_path)
            print(f"\n[OK] {brand} -> {output_path}")
        
        print("\n" + "=" * 60)
        print(f"[SUCCESS] 生成完成，共 {len(generated_files)} 个文件")
        print("=" * 60)
        print("\n下一步: 执行 Step 8（子 Agent：视觉分析）")

        update_task_meta(
            Path(task_dir),
            status_text='Step 7 完成',
            current_step='Step 7',
            outputs=generated_files,
        )
        # 输出状态报告
        files_str = ', '.join([f"output/step1_{brand_map[b]}_原始数据.md" for b in brand_map if b in parse_result])
        print(f"\nSTATUS: SUCCESS | files=[{files_str}]")
        
        sys.exit(0)
        
    except Exception as e:
        update_task_meta(
            Path(task_dir),
            status_text=f'失败：Step 7 原始数据 Markdown 生成失败 - {str(e)[:80]}',
            current_step='Step 7',
        )
        print(f"\n[ERROR] 生成失败: {e}")
        import traceback
        traceback.print_exc()
        print(f"\nSTATUS: FAILED | reason={str(e)[:50]}")
        sys.exit(1)


if __name__ == '__main__':
    main()
