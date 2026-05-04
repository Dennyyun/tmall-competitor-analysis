# -*- coding: utf-8 -*-
"""
Step 4a - 竞争格局数值计算（纯 Python，零 LLM 调用）

从 parse_result.json 和 raw/*.json 直接计算：
  - key_findings: 关键发现（价格/销量/评分对比）
  - price_matrix: 价格定位矩阵（按价格带归类）
  - positioning: 基础定位框架（品牌名 + 价格带 + 销量级别）
  - hero_exec_cards: 首屏速览卡片基础数据

输出写入 output/step4a_landscape.json
"""
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from task_paths import ensure_task_dir, resolve_task_dir


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_float(val, default=0.0):
    """Extract numeric value from strings like '¥264.71', '3000+', '1万+'."""
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace("¥", "").replace(",", "").replace("+", "").strip()
    if not s:
        return default
    # Handle Chinese units
    if "万" in s:
        s = s.replace("万", "")
        try:
            return float(s) * 10000
        except ValueError:
            return default
    try:
        return float(s)
    except ValueError:
        return default


def compute_key_findings(products: dict, labels: dict) -> list[str]:
    """Generate key findings from raw product data comparison."""
    findings = []

    # Price comparison
    prices = {}
    for key in ["self", "p1", "p2", "p3"]:
        p = products[key]
        price_data = p.get("价格", {})
        prices[key] = safe_float(price_data.get("券后价", ""))

    sorted_by_price = sorted(prices.items(), key=lambda x: x[1])
    cheapest = sorted_by_price[0]
    most_expensive = sorted_by_price[-1]
    findings.append(
        f"{labels[cheapest[0]]}：最低价¥{cheapest[1]:.0f}，"
        f"{labels[most_expensive[0]]}：最高价¥{most_expensive[1]:.0f}"
    )

    # Sales comparison
    sales = {}
    for key in ["self", "p1", "p2", "p3"]:
        sales[key] = safe_float(products[key].get("已售数量", "0"))
    top_seller = max(sales.items(), key=lambda x: x[1])
    self_sales = sales["self"]
    if top_seller[0] != "self":
        ratio = top_seller[1] / self_sales if self_sales > 0 else 0
        findings.append(
            f"{labels[top_seller[0]]}销量{products[top_seller[0]].get('已售数量', '')}最高，"
            f"是{labels['self']}{ratio:.0f}倍"
        )

    # Review count comparison
    reviews = {}
    for key in ["self", "p1", "p2", "p3"]:
        reviews[key] = safe_float(products[key].get("评价总数", "0"))
    top_reviews = max(reviews.items(), key=lambda x: x[1])
    if top_reviews[0] != "self":
        findings.append(
            f"{labels[top_reviews[0]]}评价{products[top_reviews[0]].get('评价总数', '')}碾压，"
            f"形成流量护城河"
        )

    # Shop score comparison
    for key in ["p1", "p2", "p3"]:
        scores = products[key].get("店铺评分", {})
        all_5 = all(
            safe_float(scores.get(f, "0")) >= 5.0
            for f in ["宝贝质量", "服务保障", "物流速度"]
            if scores.get(f)
        )
        if all_5 and scores:
            findings.append(f"{labels[key]}店铺评分全5.0，信任背书极强")

    return findings[:4]  # Cap at 4 findings


def compute_price_matrix(products: dict, labels: dict) -> list[str]:
    """Classify brands into price bands."""
    price_bands = []

    brands_by_band = {"性价比区": [], "中端区": [], "高端蓝海": []}
    for key in ["self", "p1", "p2", "p3"]:
        price = safe_float(products[key].get("价格", {}).get("券后价", ""))
        name = labels[key]
        if price <= 300:
            brands_by_band["性价比区"].append(name)
        elif price <= 600:
            brands_by_band["中端区"].append(name)
        else:
            brands_by_band["高端蓝海"].append(name)

    band_config = [
        ("¥200-300 性价比区", "性价比区"),
        ("¥300-600 中端区", "中端区"),
        ("¥800+ 高端护眼蓝海", "高端蓝海"),
    ]

    for label, band_key in band_config:
        brands = brands_by_band[band_key]
        if not brands:
            continue
        note = ""
        if len(brands) >= 2:
            note = " — 竞争最激烈，红海肉搏"
        elif band_key == "高端蓝海":
            note = " — 独占护眼心智，定价权最强"
        elif band_key == "中端区":
            note = " — 设计溢价路线"
        brand_str = " vs ".join(brands)
        price_bands.append(f"{label}：{brand_str}{note}")

    return price_bands


def compute_positioning(products: dict, labels: dict) -> dict:
    """Generate basic positioning framework for each brand."""
    positioning = {}
    for key in ["self", "p1", "p2", "p3"]:
        p = products[key]
        price = safe_float(p.get("价格", {}).get("券后价", ""))
        sales = p.get("已售数量", "")
        shop = p.get("店铺名称", "")

        # Price band
        if price <= 300:
            band = "性价比"
        elif price <= 600:
            band = "中端"
        else:
            band = "高端"

        positioning[key] = {
            "name": labels[key],
            "position": f"{band}·{sales}销量",
            "price_band": band,
        }
    return positioning


def compute_hero_exec_cards(products: dict, labels: dict, key_findings: list, price_matrix: list) -> list[dict]:
    """Generate hero section executive summary cards."""
    cards = [
        {"label": "竞品数量", "value": "3个核心竞品<br>+ 1个自家商品"},
    ]

    # The remaining cards (JTBD, opportunity, threat, traffic) require LLM insight
    # Provide placeholder structure that Step 4b/4c will fill
    cards.append({"label": "核心JTBD", "value": "（待 Step 4b 填充）"})
    cards.append({"label": "最大机会点", "value": "（待 Step 4c 填充）"})
    cards.append({"label": "最需规避陷阱", "value": "（待 Step 4c 填充）"})

    # Traffic landscape can be derived from price matrix
    if price_matrix:
        cards.append({"label": "流量格局", "value": price_matrix[0].split("：", 1)[-1][:40] if price_matrix else ""})

    return cards


def main():
    if len(sys.argv) < 2:
        print("Usage: python compute_landscape.py <taskId> [taskDir]")
        raise SystemExit(1)

    task_id = sys.argv[1]
    task_dir = str(resolve_task_dir(task_id, sys.argv[2])) if len(sys.argv) > 2 else str(ensure_task_dir(task_id))
    raw_dir = os.path.join(task_dir, "raw")
    out_dir = os.path.join(task_dir, "output")
    os.makedirs(out_dir, exist_ok=True)

    # Load all raw product data
    products = {}
    for name in ["self", "p1", "p2", "p3"]:
        path = os.path.join(raw_dir, f"{name}.json")
        if not os.path.exists(path):
            print(f"ERROR: {path} not found")
            raise SystemExit(1)
        products[name] = load_json(path)

    # Build brand labels
    brand_name = products["self"].get("店铺名称", "自家品牌")
    labels = {
        "self": f"{brand_name}（自家）",
        "p1": products["p1"].get("店铺名称", "竞品1"),
        "p2": products["p2"].get("店铺名称", "竞品2"),
        "p3": products["p3"].get("店铺名称", "竞品3"),
    }

    # Compute all deterministic fields
    key_findings = compute_key_findings(products, labels)
    price_matrix = compute_price_matrix(products, labels)
    positioning = compute_positioning(products, labels)
    hero_exec_cards = compute_hero_exec_cards(products, labels, key_findings, price_matrix)

    result = {
        "key_findings": key_findings,
        "price_matrix": price_matrix,
        "positioning": positioning,
        "hero_exec_cards": hero_exec_cards,
        "analysis_date": task_id.split("-")[0][:4] + "-" + task_id.split("-")[0][4:6] + "-" + task_id.split("-")[0][6:8] if len(task_id) >= 8 else "",
        "hero_badge": f"{brand_name} · 竞品分析报告",
        "hero_title": f"{products['self'].get('商品标题', '')[:10]}竞品全景分析",
    }

    # Write output
    out_path = os.path.join(out_dir, "step4a_landscape.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Step 4a landscape computed: {out_path}")
    print(f"  key_findings: {len(key_findings)} items")
    print(f"  price_matrix: {len(price_matrix)} bands")
    print(f"  positioning: {len(positioning)} brands")
    print(f"STATUS: SUCCESS | path={out_path}")


if __name__ == "__main__":
    main()
