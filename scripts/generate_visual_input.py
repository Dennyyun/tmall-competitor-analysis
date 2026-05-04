# -*- coding: utf-8 -*-
"""
Step 8 前置 - 生成视觉分析精简输入

从 raw/*.json 提取仅视觉分析所需字段，剔除 feedback/question 等无关文本。
输出 step8_visual_input.json，上下文从 ~38KB 降至 ~2KB。
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from task_paths import ensure_task_dir, resolve_task_dir


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_visual_input.py <taskId> [taskDir]")
        raise SystemExit(1)

    task_id = sys.argv[1]
    task_dir = str(resolve_task_dir(task_id, sys.argv[2])) if len(sys.argv) > 2 else str(ensure_task_dir(task_id))
    raw_dir = os.path.join(task_dir, "raw")
    out_dir = os.path.join(task_dir, "output")
    os.makedirs(out_dir, exist_ok=True)

    # First try to read positioning from step4a_landscape.json (so Step 8 can run parallel to 4b/4c)
    # Fallback to analysis.json if step4a is merged
    step4a_path = os.path.join(out_dir, "step4a_landscape.json")
    analysis_path = os.path.join(out_dir, "analysis.json")
    
    positioning = {}
    if os.path.exists(step4a_path):
        try:
            step4a_data = load_json(step4a_path)
            positioning = step4a_data.get("positioning", {})
        except Exception:
            pass
            
    if not positioning and os.path.exists(analysis_path):
        try:
            analysis = load_json(analysis_path)
            positioning = analysis.get("positioning", {})
        except Exception:
            pass

    visual_input = {}
    for brand in ["self", "p1", "p2", "p3"]:
        raw_path = os.path.join(raw_dir, f"{brand}.json")
        if not os.path.exists(raw_path):
            print(f"WARN: {raw_path} not found, skipping")
            continue

        raw = load_json(raw_path)
        main_images = raw.get("商品主图", [])
        detail_image = raw.get("详情图", "")
        title = raw.get("商品标题", "")
        shop_name = raw.get("店铺名称", "")
        price = raw.get("价格", {}).get("券后价", "")

        # Get positioning summary if available
        pos = positioning.get(brand, {})
        pos_text = pos.get("position", "") if isinstance(pos, dict) else str(pos)

        visual_input[brand] = {
            "shop_name": shop_name,
            "title": title,
            "price": price,
            "main_images": main_images[:5],  # Cap at 5
            "detail_image": detail_image if isinstance(detail_image, str) else "",
            "positioning": pos_text,
        }

    out_path = os.path.join(out_dir, "step8_visual_input.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(visual_input, f, ensure_ascii=False, indent=2)

    total_size = os.path.getsize(out_path)
    print(f"Visual input generated: {out_path}")
    print(f"  Size: {total_size} bytes ({total_size/1024:.1f} KB)")
    print(f"  Brands: {len(visual_input)}")
    for brand, data in visual_input.items():
        print(f"    {brand}: {len(data['main_images'])} main images, title={data['title'][:30]}...")
    print(f"STATUS: SUCCESS | path={out_path}")


if __name__ == "__main__":
    main()
