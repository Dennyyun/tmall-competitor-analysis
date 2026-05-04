# -*- coding: utf-8 -*-
"""Helpers for keeping task metadata in sync with generated outputs."""

from __future__ import annotations

import ast
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable


STEP_LABELS = [
    "Step 1",
    "Step 2",
    "Step 3",
    "Step 4a",
    "Step 4b",
    "Step 4c",
    "Step 4d",
    "Step 7",
    "Step 8",
    "Step 9",
    "Step 9.5",
    "Step 10",
    "Step 10.5",
    "Step 11",
]


def _extract_created_time(existing_text: str) -> str | None:
    match = re.search(r"- \*\*创建时间:\*\* (.+)", existing_text)
    if match:
        return match.group(1).strip()
    return None


def _extract_goods_from_collect(task_dir: Path) -> list[tuple[str, str]]:
    collect_path = task_dir / "collect.py"
    if not collect_path.exists():
        return []

    text = collect_path.read_text(encoding="utf-8")
    match = re.search(r"goods_list\s*=\s*(\[[\s\S]*?\])", text)
    if not match:
        return []

    try:
        goods = ast.literal_eval(match.group(1))
    except (SyntaxError, ValueError):
        return []

    normalized: list[tuple[str, str]] = []
    for item in goods:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            normalized.append((str(item[0]), str(item[1])))
    return normalized


def _extract_ids_from_goods(goods: Iterable[tuple[str, str]]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for brand, value in goods:
        match = re.search(r"(?:^|[?&])id=(\d+)", value)
        item_id = match.group(1) if match else value.strip()
        rows.append((brand, item_id, value))
    return rows


def _step_status(task_dir: Path) -> dict[str, str]:
    raw_dir = task_dir / "raw"
    output_dir = task_dir / "output"
    analysis_path = output_dir / "analysis.json"

    statuses = {label: "⬜" for label in STEP_LABELS}
    statuses["Step 1"] = "✅" if task_dir.exists() else "⬜"
    if all((raw_dir / f"{brand}.json").exists() for brand in ("self", "p1", "p2", "p3")):
        statuses["Step 2"] = "✅"
    if (raw_dir / "parse_result.json").exists():
        statuses["Step 3"] = "✅"
    # Step 4 sub-steps
    if (output_dir / "step4a_landscape.json").exists():
        statuses["Step 4a"] = "✅"
    if (output_dir / "step4b_jtbd.json").exists():
        statuses["Step 4b"] = "✅"
    if (output_dir / "step4c_insights.json").exists():
        statuses["Step 4c"] = "✅"
    if analysis_path.exists():
        try:
            import json
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        except Exception:
            analysis = {}
        if analysis.get("positioning") and analysis.get("decision_factors"):
            statuses["Step 4d"] = "✅"
        if analysis.get("visual_analysis"):
            statuses["Step 8"] = "✅"
        if analysis.get("decision_summary") and analysis.get("validation_plan"):
            statuses["Step 9.5"] = "✅"
    if len(list(output_dir.glob("step1_*_原始数据.md"))) >= 4:
        statuses["Step 7"] = "✅"
    if (output_dir / "step9_plan.json").exists():
        statuses["Step 9"] = "✅"
    if (output_dir / f"竞品分析报告_完整版_{task_dir.name}.html").exists():
        statuses["Step 10"] = "✅"
    if (output_dir / "cloudflare_url.txt").exists():
        statuses["Step 10.5"] = "✅"
    return statuses


def _current_step_label(statuses: dict[str, str]) -> str:
    pending = [label for label in STEP_LABELS if statuses.get(label) != "✅"]
    return pending[0] if pending else "Done"


def update_task_meta(
    task_dir: Path,
    *,
    status_text: str,
    current_step: str,
    outputs: Iterable[str] | None = None,
    note: str | None = None,
) -> None:
    """Rewrite ``meta.md`` with a reliable current-state snapshot."""

    task_dir = Path(task_dir)
    meta_path = task_dir / "meta.md"
    existing_text = meta_path.read_text(encoding="utf-8") if meta_path.exists() else ""
    created_time = _extract_created_time(existing_text) or datetime.now().strftime("%Y-%m-%d %H:%M")
    updated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    goods = _extract_ids_from_goods(_extract_goods_from_collect(task_dir))
    statuses = _step_status(task_dir)
    current_step_label = _current_step_label(statuses)

    lines = [
        "# Task Meta - 竞品分析",
        "",
        "## 任务信息",
        "",
        f"- **taskId:** {task_dir.name}",
        f"- **创建时间:** {created_time}",
        f"- **最近更新:** {updated_time}",
        f"- **当前步骤:** {current_step_label}",
        f"- **状态:** {status_text}",
        f"- **触发更新:** {current_step}",
    ]

    if note:
        lines.append(f"- **备注:** {note}")

    lines.extend(["", "## 商品清单", ""])
    if goods:
        lines.extend(
            [
                "| 角色 | 商品ID | 链接 |",
                "|------|--------|------|",
            ]
        )
        for brand, item_id, value in goods:
            lines.append(f"| {brand} | {item_id} | {value} |")
    else:
        lines.append("- 暂无商品清单")

    lines.extend(["", "## 执行状态", ""])
    for label in STEP_LABELS:
        lines.append(f"- {label}: {statuses.get(label, '⬜')}")

    if outputs:
        lines.extend(["", "## 关键产物", ""])
        for output in outputs:
            lines.append(f"- {output}")

    meta_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

