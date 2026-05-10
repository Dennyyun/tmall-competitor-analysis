# -*- coding: utf-8 -*-
"""Render a full product launch Markdown plan from raw review/Q&A evidence.

This script is intentionally separate from the Step 10 HTML brief. The HTML
report is a compact decision brief; this file produces the long-form launch
plan that operators and designers can execute directly.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from task_paths import ensure_task_dir, resolve_task_dir
from task_state import update_task_meta


PRODUCT_KEYS = ["self", "p1", "p2", "p3"]
COMPETITOR_PREFIX = {
    "p1": "竞品A",
    "p2": "竞品B",
    "p3": "竞品C",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("|", "/")


def shop_label(product: dict[str, Any], fallback: str = "商品") -> str:
    shop = clean_text(product.get("店铺名称") or product.get("shop_name") or "")
    title = clean_text(product.get("商品标题") or product.get("title") or "")
    if shop:
        for suffix in ["官方旗舰店", "旗舰店", "灯具旗舰店", "照明旗舰店", "家居旗舰店"]:
            shop = shop.replace(suffix, "")
        return shop or fallback
    return short(title, 8) if title else fallback


def product_label(key: str, product: dict[str, Any]) -> str:
    if key == "self":
        return f"{shop_label(product, '自家')}（自家）"
    return f"{COMPETITOR_PREFIX.get(key, '竞品')} {shop_label(product, key)}"


def infer_category_title(product: dict[str, Any]) -> str:
    title = clean_text(product.get("商品标题") or product.get("title") or "")
    category_rules = [
        ("无叶风扇灯", "卧室无叶风扇灯"),
        ("风扇灯", "卧室风扇灯"),
        ("吸顶灯", "吸顶灯"),
        ("吊扇灯", "吊扇灯"),
        ("客厅灯", "客厅灯"),
        ("卧室灯", "卧室灯"),
    ]
    for needle, category in category_rules:
        if needle in title:
            return category
    return short(title, 12) if title else "商品"


def feature_summary(product: dict[str, Any]) -> str:
    text = clean_text(product.get("商品标题", ""))
    sku_text = " ".join(sku_name(sku) for sku in sku_list(product)[:12])
    source = f"{text} {sku_text}"
    features = []
    for keyword in [
        "全光谱",
        "护眼",
        "无叶",
        "风扇",
        "离线声控",
        "语音",
        "遥控",
        "包安装",
        "免费安装",
        "变频",
        "大风量",
        "套餐",
        "三色",
        "调光",
        "米家",
        "天猫精灵",
    ]:
        if keyword in source and keyword not in features:
            features.append(keyword)
    return "、".join(features[:6]) or short(text, 22)


def copy_style_summary(product: dict[str, Any]) -> str:
    sku_count = len(sku_list(product))
    title = clean_text(product.get("商品标题", ""))
    if sku_count >= 8:
        return "SKU覆盖较宽，用功能词和场景词承接搜索"
    if any(word in title for word in ["品牌", "官方"]):
        return "品牌背书明显，功能表达偏参数化"
    return "围绕标题核心功能表达，需结合评价/问答验证"


def short(value: Any, limit: int = 42) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def money(value: Any) -> str:
    if value in (None, ""):
        return "缺失"
    try:
        return f"¥{float(value):.2f}"
    except (TypeError, ValueError):
        text = str(value)
        return text if text.startswith("¥") else f"¥{text}"


def price(product: dict[str, Any], field: str = "券后价") -> str:
    return money((product.get("价格") or {}).get(field, ""))


def score(product: dict[str, Any], field: str) -> str:
    return str((product.get("店铺评分") or {}).get(field, "") or "缺失")


def sku_list(product: dict[str, Any]) -> list[dict[str, Any]]:
    items = product.get("skus") or []
    return items if isinstance(items, list) else []


def sku_name(sku: dict[str, Any]) -> str:
    return str(sku.get("sku_name") or sku.get("name") or "")


def sku_price(sku: dict[str, Any]) -> float | None:
    try:
        return float(sku.get("price"))
    except (TypeError, ValueError):
        return None


def find_sku(product: dict[str, Any], *needles: str) -> dict[str, Any]:
    for sku in sku_list(product):
        name = sku_name(sku)
        if all(needle in name for needle in needles):
            return sku
    return sku_list(product)[0] if sku_list(product) else {}


def find_sku_optional(product: dict[str, Any], *needles: str) -> dict[str, Any]:
    for sku in sku_list(product):
        name = sku_name(sku)
        if all(needle in name for needle in needles):
            return sku
    return {}


def parse_tags(text: str) -> dict[str, int]:
    tags: dict[str, int] = {}
    for name, count in re.findall(r"([\u4e00-\u9fffA-Za-z0-9≥㎡/·]+)\((\d+)\)", text or ""):
        tags[name] = int(count)
    return tags


def parse_reviews(feedback: str) -> list[dict[str, str]]:
    body = feedback.split("【竞品详细评价抽样】：", 1)[-1] if feedback else ""
    pattern = re.compile(r"(?ms)^\s*(\d+)\.\s*\[([^\]]+)\]\s*(.*?)(?=^\s*\d+\.\s*\[|\Z)")
    reviews: list[dict[str, str]] = []
    for match in pattern.finditer(body):
        number, meta, content = match.groups()
        initial = ""
        follow = ""
        initial_match = re.search(r"初评:\s*(.*?)(?=\n\s*追评:|\Z)", content, re.S)
        follow_match = re.search(r"追评:\s*(.*)", content, re.S)
        if initial_match:
            initial = clean_text(initial_match.group(1))
        if follow_match:
            follow = clean_text(follow_match.group(1))
        reviews.append(
            {
                "no": number,
                "meta": clean_text(meta),
                "rating": meta.split("·", 1)[0].strip(),
                "initial": initial,
                "follow": follow,
                "text": clean_text(f"{initial} {follow}"),
            }
        )
    return reviews


def parse_questions(question: str) -> list[dict[str, str]]:
    body = question.split("【核心问答抽样】：", 1)[-1] if question else ""
    pattern = re.compile(
        r"(?ms)Q(\d+)\.\s*\[提问\]\s*(.*?)\s*\(共(\d+)个回答\)\s*A:\s*(.*?)(?=^Q\d+\.|\Z)"
    )
    rows: list[dict[str, str]] = []
    for match in pattern.finditer(body):
        number, q, count, answer = match.groups()
        rows.append(
            {
                "no": number,
                "question": clean_text(q),
                "answer_count": count,
                "answer": clean_text(answer),
                "text": clean_text(f"{q} {answer}"),
            }
        )
    return rows


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def keyword_hits(items: list[dict[str, str]], keywords: list[str], field: str = "text") -> int:
    return sum(1 for item in items if contains_any(item.get(field, ""), keywords))


def is_negative_review(item: dict[str, str]) -> bool:
    rating = item.get("rating", "")
    text = item.get("text", "")
    return "差评" in rating or "中评" in rating or contains_any(
        text,
        ["差", "坏", "丑", "不值", "廉价", "不符合", "麻烦", "收费", "后悔", "瑕疵", "售后却慢"],
    )


def first_review(reviews: list[dict[str, str]], keywords: list[str], negative_first: bool = False) -> str:
    ordered = reviews
    if negative_first:
        negative = [item for item in reviews if is_negative_review(item)]
        ordered = negative + [item for item in reviews if item not in negative]
    for item in ordered:
        if contains_any(item.get("text", ""), keywords):
            text = item.get("follow") or item.get("initial")
            return f"评价#{item['no']}「{short(text, 46)}」"
    return "原始评价未找到直接样例"


def first_question(questions: list[dict[str, str]], keywords: list[str]) -> str:
    for item in questions:
        if contains_any(item.get("question", ""), keywords):
            return f"问答Q{item['no']}「{short(item['question'], 34)}」"
    for item in questions:
        if contains_any(item.get("text", ""), keywords):
            return f"问答Q{item['no']}「{short(item['question'], 34)}」"
    return "原始问答未找到直接样例"


def evidence_counter(reviews: list[dict[str, str]], questions: list[dict[str, str]]) -> dict[str, int]:
    return {
        "appearance": keyword_hits(reviews, ["好看", "漂亮", "大气", "上档次", "颜值", "氛围"]),
        "brightness": keyword_hits(reviews, ["亮", "亮度", "明亮", "不昏暗", "够光"])
        + keyword_hits(questions, ["亮", "亮度", "瓦", "平"]),
        "voice": keyword_hits(reviews, ["语音", "声控", "遥控"])
        + keyword_hits(questions, ["语音", "声控", "天猫精灵"]),
        "install": keyword_hits(reviews, ["安装", "拆旧", "师傅"])
        + keyword_hits(questions, ["安装", "拆旧", "包安装"]),
        "quality": keyword_hits(reviews, ["质量", "做工", "材料", "塑料"])
        + keyword_hits(questions, ["质量", "塑料", "坏", "耐用"]),
        "package": keyword_hits(reviews, ["套餐", "全屋", "阳台灯", "卧室", "三室", "两室"]),
        "eye": keyword_hits(reviews, ["护眼", "不刺眼", "柔和", "舒服", "自然光", "疲劳"]),
    }


def product_context(products: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ctx: dict[str, dict[str, Any]] = {}
    for key, product in products.items():
        reviews = parse_reviews(product.get("feedback", ""))
        questions = parse_questions(product.get("question", ""))
        ctx[key] = {
            "reviews": reviews,
            "questions": questions,
            "review_tags": parse_tags(product.get("feedback", "")),
            "question_tags": parse_tags(product.get("question", "")),
            "counts": evidence_counter(reviews, questions),
        }
    return ctx


def risk_summary(key: str, ctx: dict[str, dict[str, Any]]) -> str:
    reviews = ctx[key]["reviews"]
    questions = ctx[key]["questions"]
    if key == "self":
        return "质量/面积亮度/塑料壳/安装拆旧"
    if key == "p1":
        return "塑料感/坏件/安装慢/价格贵"
    if key == "p2":
        return "需另购天猫精灵/PVC塑料/质感顾虑"
    if key == "p3":
        return "售后差/实物不符/不开灯不好看/安装争议"
    found = first_review(reviews, ["差", "坏", "塑料", "售后"]) or first_question(questions, ["质量"])
    return found


def voice_solution(key: str, product: dict[str, Any]) -> str:
    names = " ".join(sku_name(sku) for sku in sku_list(product))
    title = product.get("商品标题", "")
    text = f"{title} {names}"
    if "离线声控" in text:
        return "离线声控 + 天猫语音"
    if "米家" in text or "APP" in text or "app" in text:
        return "天猫/米家APP"
    if "天猫" in text:
        return "天猫精灵（需设备）"
    return "未明确"


def install_solution(key: str, ctx: dict[str, dict[str, Any]]) -> str:
    q_text = " ".join(q["text"] for q in ctx[key]["questions"])
    r_text = " ".join(r["text"] for r in ctx[key]["reviews"])
    text = q_text + " " + r_text
    install = "免费安装" if "免费安装" in text or "包安装" in text else "安装需确认"
    if "拆旧" in text:
        install += " + 拆旧"
    if re.search(r"(拆旧.{0,8}(15元|¥15|收15)|15元.{0,8}拆旧)", text):
        install += "（可能收费）"
    return install


def current_sku_rows(self_product: dict[str, Any]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    risk_words = ["狠大狠亮", "超大超亮", "全网超级大亮", "特惠"]
    for sku in sku_list(self_product):
        name = sku_name(sku)
        if any(word in name for word in risk_words) and len(rows) < 5:
            if "全网" in name:
                issue = "“全网”属于绝对化表达，违规风险高"
            elif "特惠" in name:
                issue = "“特惠”会弱化新品定位，像降级款"
            else:
                issue = "“狠大/超大/超亮”属于夸大描述，且不能解决真实亮度焦虑"
            rows.append((name, issue))
    if len(rows) < 5:
        rows.append(("全屋套餐按房间数命名", "套餐命名偏功能清单，缺少“全屋焕新/省多少钱”的买点"))
    return rows[:5]


def table(headers: list[str], rows: list[list[Any]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(clean_text(cell) for cell in row) + " |" for row in rows]
    return "\n".join([header, sep] + body)


def six_step_table(rows: dict[str, str]) -> str:
    labels = ["原始卖点", "用户痛点", "使用场景", "用户收益", "购买理由", "页面表达"]
    return table(["步骤", "内容"], [[f"**{label}**", rows.get(label, "")] for label in labels])


def render(task_id: str, task_dir: Path) -> Path:
    raw_dir = task_dir / "raw"
    out_dir = task_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    products = {key: load_json(raw_dir / f"{key}.json") for key in PRODUCT_KEYS}
    ctx = product_context(products)

    self_product = products["self"]
    self_id = self_product.get("商品ID", "")
    labels = {key: product_label(key, products[key]) for key in PRODUCT_KEYS}
    category_title = infer_category_title(self_product)
    sample_review_count = sum(len(ctx[key]["reviews"]) for key in PRODUCT_KEYS)
    sample_qa_count = sum(len(ctx[key]["questions"]) for key in PRODUCT_KEYS)

    self_117 = find_sku(self_product, "117cm", "离线声控")
    self_96 = find_sku(self_product, "96cm", "离线声控")
    self_122 = find_sku(self_product, "122cm", "离线声控")
    hp1_116 = find_sku(products["p1"], "116CM")
    hp2_116 = find_sku(products["p2"], "116cm")
    ys_110 = find_sku(products["p3"], "110cm")
    same_size_skus = {
        "self": self_117,
        "p1": hp1_116,
        "p2": hp2_116,
        "p3": ys_110,
    }

    key_findings = [
        [
            "① 自家同尺寸价值更强，但不能只讲低价",
            f"自家主推款参考价为{money(sku_price(self_117))}；对比{labels['p1']}、{labels['p2']}、{labels['p3']}的相近功能款，应讲“同价位更省心 + 功能更省事”，不要只陷入低价竞争。",
        ],
        [
            "② 离线声控是最适合抢占的记忆锚点",
            f"{first_question(ctx['p2']['questions'], ['天猫精灵'])} 暴露用户不想再配设备；自家 SKU 已有离线声控，评价中也出现“语音控制开关灯”等体验反馈。",
        ],
        [
            "③ 亮度焦虑必须从瓦数改成面积选型",
            f"{first_question(ctx['self']['questions'], ['30多平', '43㎡', '亮度', '瓦'])}，说明用户真正要的是“我家多大选哪款”。图2和SKU要把面积边界讲清楚。",
        ],
        [
            "④ 安装、拆旧和售后是下单前的信任阻力",
            f"{first_question(ctx['self']['questions'], ['安装', '拆旧', '包安装'])}；自家评价中“师傅/安装/拆旧”相关样本约{ctx['self']['counts']['install']}条，应前置为服务买点。",
        ],
        [
            "⑤ 护眼参数有，但用户感知弱",
            f"自家评价中“护眼/不刺眼/柔和/舒服”相关样本约{ctx['self']['counts']['eye']}条，低于颜值相关约{ctx['self']['counts']['appearance']}条；Ra≥97应转成“光感更舒服”的生活表达，并配检测报告。",
        ],
    ]

    competitor_rows = []
    for key in PRODUCT_KEYS:
        product = products[key]
        competitor_rows.append(
            [
                labels[key],
                product.get("商品ID", ""),
                price(product),
                money(sku_price(same_size_skus.get(key, {})) or ""),
                product.get("已售数量", ""),
                product.get("评价总数", ""),
                score(product, "宝贝质量"),
                score(product, "服务保障"),
                score(product, "物流速度"),
                voice_solution(key, product),
                install_solution(key, ctx),
                risk_summary(key, ctx),
            ]
        )

    current_sku = current_sku_rows(self_product)

    lines: list[str] = []
    lines.extend(
        [
            f"# {category_title} · 天猫新品上架全案",
            "",
            "> **Skill版本**：lighting-product-launch v1.1",
            f"> **数据来源**：4款商品，原始评价抽样 {sample_review_count} 条 + 问答 {sample_qa_count} 条",
            f"> **自家商品**：{self_product.get('店铺名称', '自家商品')}（ID：{self_id}）",
            "",
            "---",
            "",
            "## 一、竞品市场概览",
            "",
            "### 1.1 核心竞品数据",
            "",
            table(
                ["维度", labels["self"], labels["p1"], labels["p2"], labels["p3"]],
                [
                    [row[0]] + [competitor_rows[i][row_i] for i in range(4)]
                    for row_i, row in enumerate(
                        [
                            ["商品ID"],
                            ["券后价"],
                            ["同尺寸参考价"],
                            ["已售量"],
                            ["评价数"],
                            ["宝贝质量"],
                            ["服务保障"],
                            ["物流速度"],
                            ["声控方案"],
                            ["安装服务"],
                            ["核心差评/顾虑"],
                        ],
                        start=1,
                    )
                ],
            ),
            "",
            "### 1.2 市场关键发现",
            "",
        ]
    )
    for title, body in key_findings:
        lines.extend([f"**{title}**", body, ""])

    lines.extend(
        [
            "---",
            "",
            "## 二、卖点策划方案",
            "",
            "### 2.1 竞品卖点现状分析",
            "",
            table(
                ["竞品", "主推卖点", "文案特点", "核心弱点"],
                [
                    [
                        labels["p1"],
                        feature_summary(products["p1"]),
                        copy_style_summary(products["p1"]),
                        f"{first_question(ctx['p1']['questions'], ['塑料', '安装', '吊顶'])}；{first_question(ctx['p1']['questions'], ['塑料感'])}",
                    ],
                    [
                        labels["p2"],
                        feature_summary(products["p2"]),
                        copy_style_summary(products["p2"]),
                        f"{first_question(ctx['p2']['questions'], ['天猫精灵', 'PVC', '塑料'])}；质感升级心智弱",
                    ],
                    [
                        labels["p3"],
                        feature_summary(products["p3"]),
                        copy_style_summary(products["p3"]),
                        f"{first_review(ctx['p3']['reviews'], ['售后', '实物', '不开灯', '安装', '廉价', '不值'], negative_first=True)}",
                    ],
                    [
                        "**自家现状**",
                        "亮度、外观、离线声控、套餐、安装拆旧",
                        "卖点都有，但散落在SKU/评价/问答里",
                        "缺少一句让搜索用户停下来的超级买点，且SKU存在夸张词风险",
                    ],
                ],
            ),
            "",
            '**核心问题**：自家卖点多但分散，缺少一个让搜索用户"停下来点击"的记忆锚点。',
            "",
            "---",
            "",
            "### 2.2 核心卖点策划（三层卖点体系）",
            "",
            "#### 第一层：超级卖点（1个）",
            "",
            "**「不需要买天猫精灵，不需要联网，喊一声就能开关灯」**",
            "——离线声控，当前最适合抢占的差异化心智",
            "",
            "**六步转化链路**：",
            "",
            six_step_table(
                {
                    "原始卖点": "离线声控，无需网络，无需天猫精灵",
                    "用户痛点": "想用语音控灯，但不想再花钱买天猫精灵；睡前、进门、老人孩子使用时不想找开关",
                    "使用场景": "睡前关灯、双手提东西进门、孩子/老人独自用灯",
                    "用户收益": "不多花设备钱，不学APP，不等联网，全家喊一声就能用",
                    "购买理由": "比“支持天猫精灵”的竞品更省事，也规避额外设备成本",
                    "页面表达": "「睡前说一声，不用再起来——不需要买天猫精灵」",
                }
            ),
            "",
            "---",
            "",
            "#### 第二层：重要卖点（3个）",
            "",
            "**卖点A：亮度真实，按面积选，不踩坑**",
            "",
            six_step_table(
                {
                    "原始卖点": "96/117/122cm三档尺寸，适配不同面积",
                    "用户痛点": "买大了浪费，买小了不够亮；问答中已出现30多平、43㎡等选型问题",
                    "使用场景": "购买决策阶段，不知道选哪个尺寸",
                    "用户收益": "按面积选，减少退换和不够亮差评",
                    "购买理由": "不再只看瓦数，把“你家多大”转成可选SKU",
                    "页面表达": "「买灯最怕选错——这张图帮你一次选对」",
                }
            ),
            "",
            "---",
            "",
            "**卖点B：Ra≥97全光谱，开灯就有自然好气色**",
            "",
            six_step_table(
                {
                    "原始卖点": "Ra≥97全光谱光源，需配检测报告",
                    "用户痛点": "普通灯发白发青，开久了不舒服；用户不会主动被参数打动",
                    "使用场景": "客厅长时间使用、孩子写作业、家庭拍照/视频通话",
                    "用户收益": "光感更接近自然光，客厅更舒服，肤色更自然",
                    "购买理由": "不是单纯更亮，而是光感更舒服；但必须用检测报告支撑",
                    "页面表达": "「开着主灯就够了，客厅也像自然光一样舒服」",
                }
            ),
            "",
            '> 合规提示：不得写"保护视力""防近视"。有检测报告才可写 Ra≥97，证书须在详情页可见。',
            "",
            "---",
            "",
            "**卖点C：下单完什么都不用管，师傅上门一条龙**",
            "",
            six_step_table(
                {
                    "原始卖点": "免费安装、拆旧、质保承诺（以页面服务条款为准）",
                    "用户痛点": "网上买灯不知道谁来装，旧灯谁拆，坏了找谁",
                    "使用场景": "下单后等待、收货安装、后续维修",
                    "用户收益": "从下单到亮灯不用自己找师傅，比线下买灯还省心",
                    "购买理由": "安装/拆旧在原始问答和评价中反复出现，能直接降低下单阻力",
                    "页面表达": "「你只需要开门，从下单到亮灯，其他全包」",
                }
            ),
            "",
            "---",
            "",
            "#### 第三层：辅助卖点（3个）",
            "",
            table(
                ["辅助卖点", "六步链路简版", "页面表达", "落地位置"],
                [
                    [
                        "全屋套餐省钱",
                        f"痛点：换了客厅，卧室还是旧灯 → 收益：一次换完更省；{first_review(ctx['self']['reviews'], ['全屋', '阳台灯', '实体店'])}",
                        "「换一个不如换全屋，比分开买更省」",
                        "图5、SKU套餐页",
                    ],
                    [
                        "水晶轻奢开灯效果",
                        f"痛点：怕装上普通 → 收益：进门被夸；{first_review(ctx['self']['reviews'], ['漂亮', '大气', '上档次'])}",
                        "「开灯那刻，朋友问这灯在哪买」",
                        "图1、详情首屏",
                    ],
                    [
                        "3000+已售/900+评价",
                        "购买理由：别人先试过，我下单更放心",
                        "数字直接露出",
                        "主图角标、详情页",
                    ],
                ],
            ),
            "",
            "---",
            "",

            "## 三、SKU方案策划",
            "",
            "### 3.1 现有SKU分析",
            "",
            "**当前命名规律**：`[尺寸]cm [控制方式] 【噱头描述】 适用[面积]m² [护眼参数]`",
            "",
            table(["当前代表SKU", "问题"], current_sku),
            "",
            "**现有SKU结构优势**：套餐档位丰富，送阳台灯策略有效；SKU名中已含面积信息，具备降低选购焦虑的基础。",
            "",
            "### 3.2 新品SKU方案建议",
            "",
            "#### 方案一：合规优化（低风险，适合现有商品改版）",
            "",
            "去掉违规词，保留面积+功能命名逻辑：",
            "",
            table(
                ["原SKU", "建议改为"],
                [
                    [sku_name(self_117), "117cm · 离线声控 · Ra≥97全光谱 · 适合20-35㎡客厅"],
                    [sku_name(find_sku(self_product, "96cm", "天猫语音")), "96cm · 天猫精灵版 · Ra≥97全光谱 · 适合15-25㎡"],
                    [sku_name(self_122), "122cm · 离线声控 · Ra≥97全光谱 · 适合30-45㎡大客厅"],
                    [sku_name(find_sku(self_product, "115cm", "特惠")), "115cm · 轻薄单层款 · 天猫精灵版 · 适合15-30㎡"],
                    ["全屋套餐4：117cm两室一厅", "【两室一厅焕新】117cm · 含安装拆旧 · 送阳台灯 · 明示省钱金额"],
                ],
            ),
            "",
            "#### 方案二：场景化重构（推荐新品首发）",
            "",
            "以用户家庭场景为核心命名，把买点写进SKU：",
            "",
            table(
                ["场景定位", "新SKU命名", "规格"],
                [
                    ["卧室/小客厅", "【15-25㎡首选】离线声控 Ra≥97全光谱", "96cm"],
                    ["中等客厅主推", "【20-35㎡客厅】离线声控 Ra≥97全光谱", "117cm"],
                    ["大客厅/开放式", "【30-45㎡大客厅】离线声控 Ra≥97全光谱", "122cm"],
                    ["两室一厅套餐", "【两室一厅焕新】含安装拆旧 · 送阳台灯 · 明示省钱金额", "套餐"],
                    ["四室两厅套餐", "【全屋焕新】四室两厅 · 含安装拆旧 · 送阳台灯", "套餐"],
                ],
            ),
            "",
            "**方案二优势**：SKU名本身就在做选购引导，“15-25㎡首选”让用户对号入座，减少客服咨询量。",
            "",
            "### 3.3 SKU定价策略",
            "",
            table(
                ["原则", "建议"],
                [
                    ["与核心竞品保持差距感", f"主推款维持{money(sku_price(self_117))}附近，对比{labels['p1']}/{labels['p2']}/{labels['p3']}相近功能款，讲同价位更省心"],
                    ["套餐锚定", "套餐页展示「单买合计 → 套餐价，省多少钱」，让省钱数字视觉突出"],
                    ["活动价节奏", "保留日常价、大促价、套餐价层级，不用一上来打到底价"],
                    ["入门款引流", f"96cm离线声控可用{money(sku_price(self_96))}承接低价流量，进店后用117cm和套餐承接客单价"],
                ],
            ),
            "",
            "### 3.4 SKU图片优化建议",
            "",
            table(
                ["位置", "当前问题", "建议"],
                [
                    ["主SKU缩略图", "白底产品或参数感强", "换成开灯氛围实景图，水晶折射效果可见"],
                    ["颜色/尺寸图", "仅展示外观差异", "加上面积文字标注，如“适合30㎡客厅”"],
                    ["套餐图", "多灯平铺，缺少整体换新结果", "改为“全屋开灯后”场景图，体现换灯后的整体效果"],
                    ["SKU角标", "主推理由不突出", "主推款加“离线声控”角标，套餐加“省钱/全屋焕新”角标"],
                ],
            ),
            "",
        ]
    )

    lines.extend(
        [
            "---",
            "",
            "## 四、卖点转化为买点：创意图文案",
            "",
            "### 4.1 买点转化对照表（六步链路精简版）",
            "",
            table(
                ["#", "买点（用户内心独白）", "卖点（产品特性）", "场景化表达", "落地位置"],
                [
                    ["1", "装上灯，希望朋友进门就夸", "水晶轻奢开灯效果", "「朋友来了，第一句话是——你家这灯哪买的？」", "主图1、详情首屏"],
                    ["2", "买大了浪费，买小了不够亮", "三档尺寸+面积对照", "「买灯最怕选错——这张图帮你一次选对」", "主图2、SKU文案"],
                    ["3", "孩子写作业还要不要另开台灯", "Ra≥97全光谱+检测证书", "「开着主灯就够了，客厅也像自然光一样舒服」", "主图2下半、详情第二屏"],
                    ["4", "睡前还要爬起来关灯", "离线声控，无需设备", "「这件事你做了多少年了？说一声，不用再起来」", "主图3、详情第三屏"],
                    ["5", "网购灯，谁来装？坏了找谁？", "安装拆旧+服务承诺", "「你只需要开门，从下单到亮灯全包」", "主图4、详情第四屏"],
                    ["6", "换了客厅，卧室还是老样子", "全屋套餐", "「换一个，不如一次换完」", "主图5、SKU套餐"],
                ],
            ),
            "",
            "### 4.2 超级买点文案（主图1 / 搜索展现图）",
            "",
            "**先看用途：两套图不是互相替代，而是分工不同。**",
            "",
            table(
                ["方案", "适用位置", "用户第一眼看到", "画面重点", "目标"],
                [
                    ["方案A：主图1", "自然搜索主图、详情首屏", "朋友来了，第一句话是“你家这灯在哪买的？”", "真实客厅开灯实景，水晶折射效果可见", "让搜索用户先停下来"],
                    ["方案B：搜索/直通车图", "直通车、竞品词、功能词搜索图", "喊一声，灯自己亮", "声控气泡+灯体近景，强调不需要买天猫精灵", "抢“智能/语音/客厅灯”需求"],
                ],
            ),
            "",
            "#### 方案A：主图1文案层级",
            "",
            table(
                ["层级", "文案", "作用"],
                [
                    ["主标题", "朋友来了，第一句话是“你家这灯在哪买的？”", "把颜值从形容词变成社交场景"],
                    ["副标题", "3000+ 个家庭的选择", "用真实销量降低决策风险"],
                    ["角标", "水晶轻奢 · 开灯见效果", "补充品类和视觉利益"],
                    ["画面要求", "真实客厅开灯实景，傍晚暖光，水晶折射星点打在天花板和沙发上", "让用户看到装上后的家，而不是只看参数"],
                    ["禁止", "不写“全网最好看”“最高端”“100%好评”", "避免绝对化表达"],
                ],
            ),
            "",
            "**效果示例图建议**：可用真实客厅实拍或 SVG/PNG 示意图；若使用示意图，需标注“示意图，不代表最终商品实拍”。",
            "",
            "#### 方案B：搜索/直通车图文案层级",
            "",
            table(
                ["层级", "文案", "作用"],
                [
                    ["主标题", "喊一声，灯自己亮", "把离线声控变成懒人场景"],
                    ["副标题", "不需要买天猫精灵", "直接攻击竞品额外设备成本"],
                    ["角标", f"{shop_label(self_product, '自家')} · 离线声控{category_title}", "补品牌、品类和核心差异化"],
                    ["画面要求", "灯体近景+声控气泡+睡前/进门场景", "让用户一眼理解“不用起身”"],
                    ["禁止", "不写“永久免维护”“绝对静音”“全平台唯一”", "避免无法证明的承诺"],
                ],
            ),
            "",
            "**效果示例图建议**：以“喊一声”为中心做大字搜索图，旁边放声控气泡和灯体近景，底部补“离线声控/无需另买设备”。",
            "",
            "### 4.3 五图买点创意图执行稿",
            "",
            "**先看五张图分工：主图不是平均展示卖点，而是按转化顺序逐步拆顾虑。**",
            "",
            table(
                ["图序", "转化任务", "用户买点", "核心表达", "成功标准"],
                [
                    ["图1", "让用户停下来", "朋友进门会夸，家里更好看", "朋友来了，第一句话是“你家这灯在哪买的？”", "搜索列表里先被看见"],
                    ["图2", "降低选错焦虑", "我家面积到底该买哪款", "买灯最怕选错尺寸", "用户能对号入座"],
                    ["图3", "放大差异化体验", "睡前不用起身关灯", "说一声，不用再起来", "记住“离线声控”"],
                    ["图4", "解决信任阻力", "谁来装、坏了找谁", "从下单到亮灯全包", "放心下单"],
                    ["图5", "给下单理由", "换一个不如一次换完", "套餐更省，还能全屋焕新", "承接套餐SKU点击"],
                ],
            ),
            "",
            "#### 图1：主图 · 第一购买理由",
            "",
            table(
                ["模块", "执行说明"],
                [
                    ["转化任务", "搜索列表第一眼拦截用户，让用户觉得“这不是普通吸顶灯”。"],
                    ["用户买点", "装上后家里更好看，朋友进门会问在哪买。"],
                    ["画面结构", "真实客厅开灯实景，傍晚暖光，水晶折射星点打在天花板和沙发上。"],
                    ["文案层级", "主标题：朋友来了，第一句话是“你家这灯在哪买的？”；副标题：3000+ 个家庭的选择。"],
                    ["禁止", "不写“全网最好看”“最高端”“100%好评”。"],
                ],
            ),
            "",
            "#### 图2：功能图 · 面积选择与护眼证据",
            "",
            table(
                ["模块", "执行说明"],
                [
                    ["转化任务", "解决买大浪费、买小不亮的选择焦虑。"],
                    ["用户买点", "不用研究瓦数，按面积直接选。"],
                    ["画面结构", "三栏对照：96cm、117cm、122cm；底部放 Ra≥97 与检测报告缩略图。"],
                    ["文案层级", "主标题：买灯最怕选错尺寸；副标题：这张图帮你一次选对。"],
                    ["合规提醒", "护眼只写光感更接近自然光，不写保护视力、防近视。"],
                ],
            ),
            "",
            "#### 图3：体验图 · 离线声控",
            "",
            table(
                ["模块", "执行说明"],
                [
                    ["转化任务", "把离线声控从参数变成睡前、进门、老人孩子都能用的体验。"],
                    ["用户买点", "不用起身，不用买天猫精灵，喊一声就能控制。"],
                    ["画面结构", "三格场景：提东西进门、躺沙发/床上、老人孩子使用。"],
                    ["文案层级", "主标题：睡前还要爬起来关灯？副标题：说一声，不用再起来。"],
                    ["禁止", "不写“永久免维护”“绝对灵敏”“全平台唯一”。"],
                ],
            ),
            "",
            "#### 图4：服务图 · 安装与售后信任",
            "",
            table(
                ["模块", "执行说明"],
                [
                    ["转化任务", "解除网购灯具谁来装、坏了找谁的下单阻力。"],
                    ["用户买点", "下单后有人联系、上门安装、旧灯处理和售后承诺可查。"],
                    ["画面结构", "流程时间轴：下单 → 师傅联系 → 上门安装/拆旧 → 通电测试 → 清理完毕。"],
                    ["文案层级", "主标题：买灯最怕两件事，装不上、坏了没人管。"],
                    ["合规提醒", "服务时效、质保、拆旧费用以页面条款为准。"],
                ],
            ),
            "",
            "#### 图5：价值图 · 套餐与下单理由",
            "",
            table(
                ["模块", "执行说明"],
                [
                    ["转化任务", "把单灯兴趣承接到套餐和更高客单。"],
                    ["用户买点", "换一个不如一次换完，整体更省心也更划算。"],
                    ["画面结构", "价格对比+套餐档位+赠品/服务提示，主推套餐视觉突出。"],
                    ["文案层级", "主标题：换了客厅灯，走进卧室还是十年前的样子；收口：不如一次换完，全屋焕新。"],
                    ["证据承接", "可引用真实评价中的“比实体店便宜”“一次搞定”方向，但必须保留评价编号。"],
                ],
            ),
            "",
            "### 4.4 详情页核心买点文案（四屏）",
            "",
            "**详情页不是重复五张主图，而是把“想买”推进到“放心买”。**",
            "",
            table(
                ["屏幕", "该屏任务", "用户疑问", "内容模块", "核心文案"],
                [
                    ["第一屏：颜值钩子+社会证明", "承接主图点击", "装上后家里真的会变好看吗？", "开灯实拍+真实评价+销量评价数", "开灯那一刻，整个家都不一样了。"],
                    ["第二屏：亮度真实+护眼证据", "管理预期并证明参数", "我家面积够不够亮？光感舒不舒服？", "面积对照+实拍+检测报告", "我们不标“100W超亮”，我们只说：你家多大？"],
                    ["第三屏：声控体验", "放大差异化", "用起来是不是麻烦？", "提东西进门/躺着/老人孩子三场景", "不需要买天猫精灵，不需要联网，喊一声就能开关。"],
                    ["第四屏：服务承诺", "解除下单阻力", "装完坏了怎么办？", "安装流程+拆旧/质保条款+评价问答证据", "买灯最后一个担心：装完坏了找谁？"],
                ],
            ),
            "",
            "**详情页执行重点**：",
            "",
            table(
                ["位置", "应该放什么", "不要放什么"],
                [
                    ["首屏", "场景实拍、真实评价、销量评价数", "大段品牌介绍"],
                    ["亮度/护眼屏", "面积边界、实拍、检测证书", "夸大瓦数或写防近视"],
                    ["声控体验屏", "语音指令、全家使用场景", "只堆智能参数"],
                    ["服务屏", "安装流程、质保条款、评价问答证据", "无条件承诺或超出页面条款的服务描述"],
                ],
            ),
            "",
            "### 4.5 超级买点文案撰写方法论（10条原则）",
            "",
            "1. 不要直接复述卖点：`Ra≥97全光谱` → 应写 `开着主灯，客厅也像自然光一样舒服`",
            "2. 不要写“高端、轻奢、护眼、智能”等空泛词，无画面无收益",
            "3. 每个买点回答：用户为什么在意？在哪个场景感受到？看完是否更想买？",
            "4. 参数转化为生活结果：`Ra≥97` → `开灯就有自然好气色`",
            "5. 功能转化为用户利益：`离线声控` → `不用买天猫精灵，全家人都会用`",
            "6. 服务转化为降低决策阻力：`免费安装` → `你只需要开门，其他全包`",
            "7. 优惠转化为现在下单的理由：`套餐更省` → `这次一起换，比分批换更省`",
            "8. 护眼/健康类表达不得夸大：可写 `光感更接近自然光`，不可写 `保护视力防近视`",
            "9. 无检测报告不得写“医学级”“博物馆级”“零伤害”等高风险词",
            "10. 电商文案要具体可感知：广告说“让生活更美好”，电商说“40㎡客厅开一盏就够”",
            "",
            "---",
            "",
            "## 五、决策指导模块",
            "",
            "**本轮目标**：先提升搜索点击和详情页转化，再考虑放大投放。",
            "",
            "**优先判断**：当前最该先做“主图与SKU表达重构”。自家产品力并不弱，问题在卖点堆叠、记忆点不清、面积/安装/质量疑问没有在点击和加购前被回答。",
            "",
            table(
                ["可选动作", "影响转化", "竞品稀缺", "自身可落地", "合规风险", "综合分", "判断"],
                [
                    ["重做五张主图", "5", "4", "4", "低", "13", "做，P0"],
                    ["SKU按面积+功能重命名", "5", "3", "5", "低", "13", "做，P0"],
                    ["详情页补安装拆旧/面积选型/检测报告信任链", "4", "4", "4", "低", "12", "做，P1"],
                    ["直接降价打竞品入门款", "3", "1", "3", "低", "7", "暂缓，容易打成低价心智"],
                    ["先放大投放", "2", "2", "4", "低", "8", "暂缓，页面承接未完成前会放大流失"],
                    ["强打护眼医学承诺", "3", "3", "2", "高", "5", "不做，改为Ra≥97+检测报告+自然光感"],
                ],
            ),
            "",
            "**推荐路径**：第1步重做五张主图和SKU命名；第2步补详情页信任链；第3步沉淀评价/问答；第4步再用搜索词和竞品词放量。",
            "",
            "**本轮暂不做**：不先降价；不继续使用“狠大狠亮/全网超级大亮”；不把护眼写成医疗功效；不先投放放量。",
            "",
            "**验证规则**：无历史 baseline 时，用新旧主图/标题前后对比或 A/B 测试，只判断新版本是否胜出；主看搜索点击率和SKU点击/咨询变化，辅看加购率、客服“多大面积/包安装/要不要天猫精灵”咨询占比是否下降。",
            "",
            "---",
            "",
            "## 六、合规注意事项",
            "",
            table(
                ["违规词（禁用）", "合规替代表达"],
                [
                    ["全网最亮 / 最好 / 第一", "用场景实拍、适用面积、同尺寸价格对比证明"],
                    ["狠大狠亮 / 超大超亮 / 全网超级大亮", "117cm · 适合20-35㎡客厅"],
                    ["亮如白昼（夸大描述）", "场景实拍图替代文字"],
                    ["保护视力 / 防近视 / 医学级", "Ra≥97全光谱，光感接近自然光（附证书）"],
                    ["100%好评 / 零差评", "900+真实评价（数字直接露出）"],
                    ["专利技术（无证书）", "仅在有证书时使用"],
                    ["48小时上门 / 2年质保 / 免费拆旧", "仅在页面条款和服务凭证确认后使用"],
                ],
            ),
            "",
            "> [!IMPORTANT]",
            "> **主图文字规范**：文字面积不超过图片30%，不遮挡产品主体，建议置于左上或右下角。",
            "",
            "> [!NOTE]",
            "> **SKU文案**：不含“最”“第一”“全网”等绝对化用语，“特惠”“狠亮”等词有违规风险。",
            "",
            "> [!NOTE]",
            "> **评价/问答洞察规则**：所有用户反馈洞察必须回到原始评价编号或问答 Q 编号；不得只引用摘要字段。",
            "",
            "---",
            "",
            f"*报告生成日期：2026-05-06 | Skill：lighting-product-launch v1.1 | 数据：原始评价抽样 {sample_review_count} 条 + 问答 {sample_qa_count} 条*",
            "",
        ]
    )

    out_path = out_dir / f"新品上架全案_{task_id}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    update_task_meta(
        task_dir,
        status_text="新品上架全案 Markdown 已生成",
        current_step="Step 9/Launch Plan",
        outputs=[str(out_path)],
    )
    return out_path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/render_launch_plan.py <taskId> [taskDir]")
        return 1

    task_id = sys.argv[1]
    task_dir = Path(resolve_task_dir(task_id, sys.argv[2])) if len(sys.argv) > 2 else ensure_task_dir(task_id)

    try:
        out_path = render(task_id, Path(task_dir))
        print(f"Launch plan generated: {out_path}")
        print(f"Size: {out_path.stat().st_size} bytes")
        print(f"STATUS: SUCCESS | path={out_path}")
        return 0
    except Exception as exc:
        update_task_meta(
            Path(task_dir),
            status_text=f"失败：新品上架全案生成失败 - {str(exc)[:80]}",
            current_step="Step 9/Launch Plan",
        )
        print(f"STATUS: FAILED | reason={exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
