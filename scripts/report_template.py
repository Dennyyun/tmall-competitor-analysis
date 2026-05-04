# -*- coding: utf-8 -*-
"""Step 10 - render the operations decision brief HTML report."""

from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from task_paths import ensure_task_dir, resolve_task_dir
from task_state import update_task_meta


if len(sys.argv) < 2:
    print("Usage: python scripts/report_template.py <taskId> [taskDir]")
    raise SystemExit(1)

TASK_ID = sys.argv[1]
TASK_DIR = str(resolve_task_dir(TASK_ID, sys.argv[2])) if len(sys.argv) > 2 else str(ensure_task_dir(TASK_ID))
RAW_DIR = os.path.join(TASK_DIR, "raw")
OUT_DIR = os.path.join(TASK_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)


def load_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def fail_exit(message: str):
    update_task_meta(
        TASK_DIR,
        status_text=f"失败：Step 10 HTML 报告生成失败 - {message[:80]}",
        current_step="Step 10",
    )
    print(f"ERROR: {message}")
    raise SystemExit(1)


products: dict[str, dict[str, Any]] = {}
for name in ["self", "p1", "p2", "p3"]:
    path = os.path.join(RAW_DIR, f"{name}.json")
    if not os.path.exists(path):
        fail_exit(f"{path} not found")
    products[name] = load_json(path)

analysis_path = os.path.join(OUT_DIR, "analysis.json")
if not os.path.exists(analysis_path):
    fail_exit(f"{analysis_path} not found")
A = load_json(analysis_path)


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=False)


def raw_field(product_key: str, field: str, default: str = "") -> str:
    return str(products.get(product_key, {}).get(field, default) or default)


def raw_price(product_key: str, field: str) -> str:
    value = products.get(product_key, {}).get("价格", {}).get(field, "")
    return str(value or "")


def shop_score(product_key: str, field: str) -> str:
    value = products.get(product_key, {}).get("店铺评分", {}).get(field, "")
    return str(value or "")


def img(product_key: str) -> str:
    images = products.get(product_key, {}).get("商品主图", []) or []
    return str(images[0]) if images else ""


def price_display(value: str) -> str:
    return f"¥{esc(value)}" if value else "缺失"


def score_display(product_key: str) -> str:
    scores = [shop_score(product_key, k) for k in ("宝贝质量", "服务保障", "物流速度")]
    return "/".join([s if s else "缺失" for s in scores])


def tags(product_key: str) -> list[tuple[str, str]]:
    return re.findall(r"([\u4e00-\u9fa5a-zA-Z]+)\((\d+)\)", raw_field(product_key, "feedback"))


def top_feedback(product_key: str, limit: int = 5) -> str:
    pairs = sorted(tags(product_key), key=lambda x: int(x[1]), reverse=True)[:limit]
    return " / ".join([f"{esc(k)}({esc(v)})" for k, v in pairs]) or "缺失"


def as_list(value: Any) -> list[Any]:
    if value in (None, "", {}, []):
        return []
    return value if isinstance(value, list) else [value]


def text_value(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        return "；".join([text_value(x) for x in value if text_value(x)])
    if isinstance(value, dict):
        parts = []
        for key, val in value.items():
            rendered = text_value(val)
            if rendered:
                parts.append(f"{key}: {rendered}")
        return "；".join(parts)
    return str(value)


def ul(items: Any, empty: str = "暂无") -> str:
    rows = [text_value(x) for x in as_list(items)]
    rows = [x for x in rows if x]
    if not rows:
        rows = [empty]
    return "<ul>" + "".join([f"<li>{esc(x)}</li>" for x in rows]) + "</ul>"


def pills(items: Any, empty: str = "暂无") -> str:
    rows = [text_value(x) for x in as_list(items)]
    rows = [x for x in rows if x]
    if not rows:
        rows = [empty]
    return '<div class="pill-list">' + "".join([f'<span class="pill">{esc(x)}</span>' for x in rows]) + "</div>"


def td(value: Any, cls: str = "") -> str:
    class_attr = f' class="{cls}"' if cls else ""
    return f"<td{class_attr}>{esc(value)}</td>"


def th(value: str) -> str:
    return f"<th>{esc(value)}</th>"


def tr(cells: list[str]) -> str:
    return "<tr>" + "".join(cells) + "</tr>"


def item_title(item: dict[str, Any]) -> str:
    return str(item.get("title") or item.get("blocker") or item.get("metric") or "事项")


def item_body(item: dict[str, Any]) -> str:
    return str(
        item.get("content")
        or item.get("description")
        or item.get("evidence")
        or item.get("business_interpretation")
        or item.get("reason")
        or ""
    )


def brand_label(product_key: str) -> str:
    name = raw_field(product_key, "店铺名称", product_key)
    return f"{name}（自家）" if product_key == "self" else f"竞品 {name}"


def map_lookup(mapping: Any, product_key: str) -> str:
    if not isinstance(mapping, dict):
        return "缺失"
    if product_key in mapping and mapping[product_key]:
        return str(mapping[product_key])
    shop_name = raw_field(product_key, "店铺名称")
    short = shop_name.replace("官方旗舰店", "").replace("照明", "").replace("灯饰", "").strip()
    for key, value in mapping.items():
        if key in (shop_name, short) or (short and short in str(key)):
            return str(value or "缺失")
    return "缺失"


def position_text(product_key: str) -> str:
    pos = A.get("positioning", {}).get(product_key, "")
    if isinstance(pos, dict):
        return str(pos.get("position") or pos.get("name") or text_value(pos))
    return str(pos or "缺失")


def render_metric_card(label: str, value: str) -> str:
    return f'<div class="metric-card"><span>{esc(label)}</span><strong>{esc(value)}</strong></div>'


def decision_type_label(value: Any) -> str:
    labels = {
        "execute": "直接执行",
        "experiment": "实验验证",
        "collect_data": "先补数据",
        "hold": "暂缓推进",
    }
    return labels.get(str(value or ""), "待判断")


def confidence_label(value: Any) -> str:
    labels = {
        "high": "高",
        "medium": "中等",
        "low": "低",
    }
    return labels.get(str(value or ""), "待判断")


def severity_label(value: Any) -> str:
    labels = {
        "high": "高严重度",
        "medium": "中严重度",
        "low": "低严重度",
    }
    return labels.get(str(value or ""), str(value or ""))


def scope_label(value: Any) -> str:
    text = str(value or "待判断")
    parts = [part.strip() for part in text.split("|") if part.strip()]
    return "、".join(parts) if parts else text


def recommendation_label(decision_type: Any, can_decide: Any) -> str:
    can_move = can_decide is True or str(can_decide).lower() == "true"
    dtype = str(decision_type or "")
    if can_move and dtype == "experiment":
        return "可以推进，按实验验证执行"
    if can_move and dtype == "execute":
        return "可以推进，直接执行"
    if dtype == "collect_data":
        return "先补关键数据，再决策"
    if dtype == "hold":
        return "暂缓推进"
    return "待判断"


def limit_summary(gate: dict[str, Any], confidence: dict[str, Any]) -> str:
    limits = as_list(gate.get("missing_critical_data")) + as_list(gate.get("weak_data_points"))
    joined = "；".join([text_value(x) for x in limits])
    if "点击率" in joined and "SKU" in joined:
        return "缺少点击率与SKU转化数据"
    if "主图" in joined:
        return "主图内容未完整核验"
    if limits:
        return text_value(limits[0])[:26]
    return str(confidence.get("reason") or "暂无关键限制")[:26]


def render_decision_header() -> str:
    summary = A.get("decision_summary", {}) if isinstance(A.get("decision_summary"), dict) else {}
    mode = A.get("decision_mode", {}) if isinstance(A.get("decision_mode"), dict) else {}
    gate = A.get("data_quality_gate", {}) if isinstance(A.get("data_quality_gate"), dict) else {}
    confidence = summary.get("confidence_level", {}) if isinstance(summary.get("confidence_level"), dict) else {}

    final_decision = summary.get("final_decision") or A.get("hero_title") or "本轮主决策未生成"
    decision_type = mode.get("decision_type")
    decision_scope = mode.get("decision_scope")
    confidence_level = confidence.get("level")
    can_decide = gate.get("can_make_final_decision", "待判断")

    return f"""
    <section class="hero" id="top">
      <div class="eyebrow">竞品分析决策简报 · {esc(raw_field("self", "店铺名称", "自家商品"))}</div>
      <h1>{esc(final_decision)}</h1>
      <p class="subtitle">Task ID: {esc(TASK_ID)} · 生成日期: {esc(A.get("analysis_date", ""))}</p>
      <div class="metric-grid">
        {render_metric_card("本轮建议", recommendation_label(decision_type, can_decide))}
        {render_metric_card("重点范围", scope_label(decision_scope))}
        {render_metric_card("置信度", f"{confidence_label(confidence_level)}置信")}
        {render_metric_card("关键限制", limit_summary(gate, confidence))}
      </div>
    </section>
    """


def render_section_1() -> str:
    summary = A.get("decision_summary", {}) if isinstance(A.get("decision_summary"), dict) else {}
    mode = A.get("decision_mode", {}) if isinstance(A.get("decision_mode"), dict) else {}
    gate = A.get("data_quality_gate", {}) if isinstance(A.get("data_quality_gate"), dict) else {}
    confidence = summary.get("confidence_level", {}) if isinstance(summary.get("confidence_level"), dict) else {}
    limits = as_list(gate.get("missing_critical_data")) + as_list(gate.get("weak_data_points"))

    return f"""
    <section class="section" id="decision">
      <div class="section-kicker">01</div>
      <h2>本轮主决策</h2>
      <div class="decision-copy">
        <p><strong>为什么：</strong>{esc(summary.get("why_this") or mode.get("reason") or "暂无")}</p>
        <p><strong>暂缓其他方向：</strong>{esc(summary.get("why_not_others") or "暂无")}</p>
        <p><strong>预期影响：</strong>{esc(summary.get("expected_impact") or "暂无")}</p>
      </div>
      <div class="grid-2">
        <div class="panel">
          <h3>本轮不做</h3>
          {ul([f'{x.get("item", "暂缓事项")}：{x.get("reason", "")}' if isinstance(x, dict) else x for x in as_list(summary.get("not_do_now"))])}
        </div>
        <div class="panel">
          <h3>数据质量限制</h3>
          <p>{esc(gate.get("decision_limitation") or confidence.get("reason") or "暂无")}</p>
          {pills(limits)}
        </div>
      </div>
    </section>
    """


def render_blockers() -> str:
    blockers = as_list(A.get("conversion_blockers"))[:5]
    if not blockers:
        blockers = [
            {"blocker": item_title(x), "severity": "", "evidence": item_body(x), "priority": ""}
            for x in as_list(A.get("opportunity_1")) + as_list(A.get("threat_1"))
        ]
    cards = []
    for item in blockers:
        if not isinstance(item, dict):
            cards.append(f'<div class="mini-card"><h3>阻力</h3><p>{esc(item)}</p></div>')
            continue
        meta = " · ".join([str(x) for x in [severity_label(item.get("severity")), item.get("priority"), item.get("affected_stage")] if x])
        cards.append(
            f"""
            <div class="mini-card">
              <h3>{esc(item.get("blocker") or item.get("title") or "转化阻力")}</h3>
              <p class="muted">{esc(meta)}</p>
              <p>{esc(item.get("evidence") or item_body(item) or "暂无证据")}</p>
            </div>
            """
        )
    return "".join(cards)


def render_evidence() -> str:
    evidence = as_list(A.get("evidence_chain"))[:5]
    if not evidence:
        evidence = [{"evidence": x, "source": "关键发现", "business_interpretation": ""} for x in as_list(A.get("key_findings"))[:5]]
    rows = []
    for item in evidence:
        if isinstance(item, dict):
            rows.append(
                tr(
                    [
                        td(item.get("evidence", "")),
                        td(item.get("source", "")),
                        td(item.get("business_interpretation", "")),
                        td(item.get("supports_decision", "")),
                    ]
                )
            )
        else:
            rows.append(tr([td(item), td(""), td(""), td("")]))
    return (
        "<table>"
        + tr([th("原始证据"), th("来源"), th("运营解释"), th("支持的判断")])
        + "".join(rows)
        + "</table>"
    )


def render_opportunity_risk() -> str:
    items = [
        ("机会", "good", A.get("opportunity_1")),
        ("机会", "good", A.get("opportunity_2")),
        ("风险", "bad", A.get("threat_1")),
        ("风险", "bad", A.get("threat_2")),
    ]
    cards = []
    for label, cls, item in items:
        if not isinstance(item, dict) or not item:
            continue
        cards.append(
            f"""
            <div class="signal {cls}">
              <span>{esc(label)}</span>
              <h3>{esc(item_title(item))}</h3>
              <p>{esc(item_body(item) or "暂无")}</p>
            </div>
            """
        )
    return '<div class="signal-grid">' + "".join(cards) + "</div>" if cards else ""


def render_section_2() -> str:
    return f"""
    <section class="section" id="why">
      <div class="section-kicker">02</div>
      <h2>为什么这样做</h2>
      <h3 class="subhead">Top 转化阻力</h3>
      <div class="card-grid">{render_blockers()}</div>
      <h3 class="subhead">关键证据链</h3>
      {render_evidence()}
      {render_opportunity_risk()}
    </section>
    """


def render_actions() -> str:
    summary = A.get("decision_summary", {}) if isinstance(A.get("decision_summary"), dict) else {}
    actions = as_list(summary.get("top3_actions"))[:3]

    cards = []
    for index, action in enumerate(actions, start=1):
        if isinstance(action, dict):
            title = action.get("action_type") or f"动作{index}"
            body = action.get("action") or ""
            owner = action.get("owner") or "待定"
            deadline = action.get("deadline") or "待定"
            criteria = action.get("acceptance_criteria") or "待定"
            priority = action.get("priority") or f"P{index - 1}"
        else:
            title = f"动作{index}"
            body = str(action)
            owner = "待定"
            deadline = "待定"
            criteria = "待定"
            priority = f"P{index - 1}"
        cards.append(
            f"""
            <div class="action-card">
              <div class="priority">{esc(priority)}</div>
              <h3>{esc(title)}</h3>
              <p>{esc(body)}</p>
              <dl>
                <dt>负责人</dt><dd>{esc(owner)}</dd>
                <dt>截止</dt><dd>{esc(deadline)}</dd>
                <dt>验收</dt><dd>{esc(criteria)}</dd>
              </dl>
            </div>
            """
        )
    return "".join(cards) or '<div class="panel"><p>暂无 Top3 动作。</p></div>'


def render_section_3() -> str:
    return f"""
    <section class="section" id="actions">
      <div class="section-kicker">03</div>
      <h2>Top3 执行动作</h2>
      <div class="action-grid">{render_actions()}</div>
    </section>
    """


def render_section_4() -> str:
    validation = A.get("validation_plan", {}) if isinstance(A.get("validation_plan"), dict) else {}
    kpis = as_list(A.get("kpi_table"))[:5]
    kpi_rows = "".join(
        [
            tr([td(x.get("metric", "")), td(x.get("current", "")), td(x.get("target", "")), td(x.get("action", ""))])
            for x in kpis
            if isinstance(x, dict)
        ]
    )
    kpi_table = (
        "<table>"
        + tr([th("指标"), th("当前基准"), th("目标"), th("关键行动")])
        + kpi_rows
        + "</table>"
        if kpi_rows
        else "<p class=\"muted\">暂无 KPI 表。</p>"
    )
    return f"""
    <section class="section" id="validation">
      <div class="section-kicker">04</div>
      <h2>验证方案</h2>
      <div class="validation-grid">
        <div class="panel hero-panel">
          <h3>{esc(validation.get("method") or "待定")}</h3>
          <p><strong>主指标：</strong>{esc(validation.get("primary_metric") or "待定")}</p>
          <p><strong>辅指标：</strong>{esc(text_value(validation.get("secondary_metric")) or "待定")}</p>
          <p><strong>无 baseline 规则：</strong>{esc(validation.get("no_baseline_rule") or "没有baseline时，只判断新旧版本胜负，不编造精确增长比例。")}</p>
        </div>
        <div class="panel">{kpi_table}</div>
      </div>
    </section>
    """


def render_competitor_table() -> str:
    rows = [tr([th("品牌"), th("券后价"), th("原价"), th("销量"), th("评价数"), th("店铺评分"), th("核心定位")])]
    for key, cls in [("self", "self-row"), ("p1", ""), ("p2", ""), ("p3", "")]:
        rows.append(
            tr(
                [
                    td(brand_label(key), cls),
                    td(price_display(raw_price(key, "券后价"))),
                    td(price_display(raw_price(key, "原价"))),
                    td(raw_field(key, "已售数量") or "缺失"),
                    td(raw_field(key, "评价总数") or "缺失"),
                    td(score_display(key)),
                    td(position_text(key)),
                ]
            )
        )
    return "<table>" + "".join(rows) + "</table>"


def render_title_support() -> str:
    title_data = A.get("title_analysis", {}) if isinstance(A.get("title_analysis"), dict) else {}
    optimized = as_list(title_data.get("optimized_titles"))[:2]
    title_rows = ""
    for item in optimized:
        if isinstance(item, dict):
            title_rows += tr([td(item.get("title", "")), td(item.get("intent", ""))])
        else:
            title_rows += tr([td(item), td("")])
    if not title_rows:
        title_rows = tr([td("暂无"), td("暂无")])
    return f"""
    <div class="panel">
      <h3>标题关键词</h3>
      <p><strong>当前标题：</strong>{esc(title_data.get("current_title") or raw_field("self", "商品标题") or "缺失")}</p>
      <p><strong>缺失关键词：</strong></p>
      {pills(title_data.get("missing_keywords"))}
      <table>{tr([th("建议标题"), th("对应意图")])}{title_rows}</table>
    </div>
    """


def render_feedback_support() -> str:
    feedback_pain = A.get("feedback_pain_points", {})
    feedback_eye = A.get("feedback_eye_rate", {})
    rows = [tr([th("品牌"), th("正向热词Top5"), th("痛点关键词"), th("护眼提及/判断")])]
    for key, cls in [("self", "self-row"), ("p1", ""), ("p2", ""), ("p3", "")]:
        rows.append(
            tr(
                [
                    td(brand_label(key), cls),
                    td(top_feedback(key)),
                    td(map_lookup(feedback_pain, key)),
                    td(map_lookup(feedback_eye, key)),
                ]
            )
        )
    review = A.get("review_qa_insights", {}) if isinstance(A.get("review_qa_insights"), dict) else {}
    return f"""
    <div class="panel">
      <h3>用户反馈洞察</h3>
      <table>{''.join(rows)}</table>
      <div class="grid-2">
        <div>
          <h4>购买理由</h4>
          {pills(review.get("purchase_reasons") or A.get("feedback_insights"))}
        </div>
        <div>
          <h4>下单顾虑</h4>
          {pills(review.get("conversion_blockers"))}
        </div>
      </div>
    </div>
    """


def render_price_support() -> str:
    pricing = A.get("pricing_strategy", {}) if isinstance(A.get("pricing_strategy"), dict) else {}
    return f"""
    <div class="panel">
      <h3>价格与促销判断</h3>
      <p>{esc(pricing.get("price_position") or text_value(A.get("price_matrix")) or "暂无")}</p>
      {pills(pricing.get("promotion"))}
    </div>
    """


def render_section_5() -> str:
    return f"""
    <section class="section" id="support">
      <div class="section-kicker">05</div>
      <h2>关键支撑数据</h2>
      <h3 class="subhead">关键竞品对比</h3>
      {render_competitor_table()}
      <div class="support-grid">
        {render_title_support()}
        {render_price_support()}
      </div>
      {render_feedback_support()}
    </section>
    """


CSS = """
<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f5f7fb;
  color: #172033;
  line-height: 1.65;
  font-size: 15px;
}
.container { max-width: 1180px; margin: 0 auto; padding: 28px; }
.hero, .section {
  background: #fff;
  border: 1px solid #e5e9f2;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(23, 32, 51, 0.06);
}
.hero { padding: 34px; margin-bottom: 18px; border-top: 5px solid #3157d5; }
.eyebrow { color: #3157d5; font-weight: 800; letter-spacing: .08em; font-size: 12px; margin-bottom: 12px; }
h1 { margin: 0 0 12px; font-size: 28px; line-height: 1.35; color: #101827; letter-spacing: 0; }
.subtitle, .muted { color: #6b7280; }
.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 24px; }
.metric-card { background: #f7f9fe; border: 1px solid #e8edf7; border-radius: 10px; padding: 14px; }
.metric-card span { display: block; color: #667085; font-size: 12px; margin-bottom: 4px; }
.metric-card strong { display: block; color: #172033; font-size: 15px; }
.toc { display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0; }
.toc a { color: #3157d5; background: #fff; border: 1px solid #dce3f2; border-radius: 999px; padding: 6px 12px; text-decoration: none; font-size: 13px; }
.section { padding: 28px; margin-bottom: 18px; }
.section-kicker { color: #3157d5; font-size: 12px; font-weight: 900; letter-spacing: .14em; margin-bottom: 4px; }
h2 { margin: 0 0 18px; font-size: 22px; color: #101827; letter-spacing: 0; }
h3 { margin: 0 0 10px; font-size: 16px; color: #172033; }
h4 { margin: 12px 0 8px; font-size: 14px; color: #344054; }
.subhead { margin-top: 18px; border-left: 4px solid #3157d5; padding-left: 10px; }
.decision-copy { background: #f7f9fe; border: 1px solid #e8edf7; border-radius: 10px; padding: 18px; margin-bottom: 16px; }
.decision-copy p { margin: 8px 0; }
.grid-2, .support-grid, .validation-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.panel, .mini-card, .action-card, .signal {
  border: 1px solid #e5e9f2;
  background: #fff;
  border-radius: 10px;
  padding: 18px;
}
.hero-panel { background: #f7f9fe; }
.card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.mini-card { background: #fbfcff; }
.mini-card p { margin: 6px 0; }
.signal-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-top: 16px; }
.signal span, .priority { display: inline-block; font-size: 12px; font-weight: 900; border-radius: 999px; padding: 3px 9px; margin-bottom: 10px; }
.signal.good { background: #f0fdf4; border-color: #bbf7d0; }
.signal.good span { background: #dcfce7; color: #15803d; }
.signal.bad { background: #fff7ed; border-color: #fed7aa; }
.signal.bad span { background: #ffedd5; color: #c2410c; }
.action-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.action-card { position: relative; padding-top: 42px; }
.priority { position: absolute; top: 14px; left: 18px; background: #e8efff; color: #3157d5; }
dl { display: grid; grid-template-columns: 58px 1fr; gap: 6px 10px; margin: 14px 0 0; }
dt { color: #667085; font-weight: 700; }
dd { margin: 0; color: #344054; }
table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13.5px; }
th { background: #eef3ff; color: #3157d5; text-align: left; padding: 10px; border: 1px solid #dce3f2; white-space: nowrap; }
td { padding: 10px; border: 1px solid #e5e9f2; vertical-align: top; }
.self-row { color: #3157d5; font-weight: 800; }
ul { margin: 8px 0 0; padding-left: 18px; }
li { margin: 4px 0; }
.pill-list { display: flex; flex-wrap: wrap; gap: 7px; margin: 8px 0; }
.pill { background: #eef3ff; color: #3157d5; border: 1px solid #dce3f2; border-radius: 999px; padding: 4px 10px; font-size: 12px; }
.footer { text-align: center; color: #667085; font-size: 12px; padding: 24px 0; }
@media (max-width: 900px) {
  .metric-grid, .grid-2, .support-grid, .validation-grid, .card-grid, .signal-grid, .action-grid { grid-template-columns: 1fr; }
  .container { padding: 16px; }
  h1 { font-size: 22px; }
}
</style>
"""


toc_html = """
<nav class="toc">
  <a href="#decision">01 本轮主决策</a>
  <a href="#why">02 为什么这样做</a>
  <a href="#actions">03 Top3动作</a>
  <a href="#validation">04 验证方案</a>
  <a href="#support">05 关键支撑数据</a>
</nav>
"""

html_parts = [
    "<!DOCTYPE html>",
    '<html lang="zh-CN">',
    "<head>",
    '<meta charset="UTF-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    f"<title>竞品分析决策简报_{esc(TASK_ID)}</title>",
    CSS,
    "</head>",
    "<body>",
    '<div class="container">',
    render_decision_header(),
    toc_html,
    render_section_1(),
    render_section_2(),
    render_section_3(),
    render_section_4(),
    render_section_5(),
    '<div class="footer">',
    f"<p>竞品分析决策简报 | Task ID: {esc(TASK_ID)} · 生成时间: {esc(A.get('analysis_date', ''))}</p>",
    "<p>数据来源：天猫商品 JSON · 只保留关键决策证据</p>",
    "</div>",
    "</div>",
    "</body>",
    "</html>",
]

html_output = "\n".join(html_parts)

html_file = os.path.join(OUT_DIR, f"竞品分析报告_完整版_{TASK_ID}.html")
try:
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_output)
    update_task_meta(
        TASK_DIR,
        status_text="Step 10 完成",
        current_step="Step 10",
        outputs=[html_file],
    )
    print(f"HTML report generated: {html_file}")
    print(f"Size: {os.path.getsize(html_file)} bytes")
    print(f"STATUS: SUCCESS | path={html_file}")
except Exception as exc:
    fail_exit(str(exc))
