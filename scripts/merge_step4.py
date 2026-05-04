# -*- coding: utf-8 -*-
"""
Step 4d - 合并 Step 4a/4b/4c 输出到 analysis.json

合并来源：
  - output/step4a_landscape.json (Python 计算)
  - output/step4b_jtbd.json (子 Agent LLM)
  - output/step4c_insights.json (子 Agent LLM)

写入 output/analysis.json（通过 analysis_manager 原子写入）
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from task_paths import ensure_task_dir, resolve_task_dir
from task_state import update_task_meta
from analysis_manager import AnalysisManager
from consolidate_json import extract_json_from_text


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_load_agent_output(path):
    """Load JSON from a file that may contain LLM text wrapping."""
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Try direct JSON parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code blocks
    extracted = extract_json_from_text(text)
    if extracted:
        return extracted

    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python merge_step4.py <taskId> [taskDir]")
        raise SystemExit(1)

    task_id = sys.argv[1]
    task_dir = str(resolve_task_dir(task_id, sys.argv[2])) if len(sys.argv) > 2 else str(ensure_task_dir(task_id))
    out_dir = os.path.join(task_dir, "output")

    # Load all sub-step outputs
    step4a_path = os.path.join(out_dir, "step4a_landscape.json")
    step4b_path = os.path.join(out_dir, "step4b_jtbd.json")
    step4c_path = os.path.join(out_dir, "step4c_insights.json")

    errors = []

    # Step 4a (required - pure Python, should always exist)
    if not os.path.exists(step4a_path):
        errors.append(f"step4a_landscape.json not found at {step4a_path}")
    step4a = load_json(step4a_path) if os.path.exists(step4a_path) else {}

    # Step 4b (required - LLM output)
    step4b = safe_load_agent_output(step4b_path)
    if step4b is None:
        errors.append(f"step4b_jtbd.json not found or unparseable at {step4b_path}")
        step4b = {}

    # Step 4c (required - LLM output)
    step4c = safe_load_agent_output(step4c_path)
    if step4c is None:
        errors.append(f"step4c_insights.json not found or unparseable at {step4c_path}")
        step4c = {}

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print("STATUS: FAILED | reason=missing sub-step outputs")
        raise SystemExit(1)

    # Merge all fields into analysis.json
    merged = {}

    # From Step 4a (Python computed)
    for field in ["key_findings", "price_matrix", "positioning", "hero_exec_cards",
                   "analysis_date", "hero_badge", "hero_title"]:
        if field in step4a:
            merged[field] = step4a[field]

    # From Step 4b (JTBD + decision factors)
    for field in ["decision_factors", "jtbd_functional", "jtbd_emotional"]:
        if field in step4b:
            merged[field] = step4b[field]

    # From Step 4c (opportunities, threats, feedback)
    for field in ["opportunity_1", "opportunity_2", "threat_1", "threat_2",
                   "feedback_insights", "feedback_pain_points", "feedback_eye_rate"]:
        if field in step4c:
            merged[field] = step4c[field]

    # Patch hero_exec_cards with LLM-generated content from 4b/4c
    if "hero_exec_cards" in merged and isinstance(merged["hero_exec_cards"], list):
        cards = merged["hero_exec_cards"]
        # Update JTBD card
        jtbd_funcs = step4b.get("jtbd_functional", [])
        if jtbd_funcs:
            for c in cards:
                if c.get("label") == "核心JTBD":
                    c["value"] = jtbd_funcs[0][:40] if jtbd_funcs else ""
        # Update opportunity card
        opp1 = step4c.get("opportunity_1", {})
        if opp1:
            for c in cards:
                if c.get("label") == "最大机会点":
                    c["value"] = opp1.get("title", "")[:50]
        # Update threat card
        threat1 = step4c.get("threat_1", {})
        if threat1:
            for c in cards:
                if c.get("label") == "最需规避陷阱":
                    c["value"] = threat1.get("title", "")[:50]

    # Write via analysis_manager (atomic)
    mgr = AnalysisManager(task_dir)
    success = mgr.write(merged, merge=False)  # Fresh write for Step 4

    if not success:
        print("ERROR: Failed to write analysis.json")
        print("STATUS: FAILED | reason=write_error")
        raise SystemExit(1)

    # Validate required fields
    required = [
        "analysis_date", "hero_badge", "hero_title", "hero_exec_cards",
        "positioning", "key_findings", "price_matrix",
        "decision_factors", "jtbd_functional", "jtbd_emotional",
        "opportunity_1", "opportunity_2", "threat_1", "threat_2",
        "feedback_insights", "feedback_pain_points", "feedback_eye_rate",
    ]
    missing = [f for f in required if f not in merged or not merged[f]]
    if missing:
        print(f"WARN: Missing fields after merge: {', '.join(missing)}")

    update_task_meta(
        task_dir,
        status_text="Step 4d 合并完成",
        current_step="Step 4",
        outputs=[os.path.join(out_dir, "analysis.json")],
    )

    print(f"Step 4d merge complete: {len(merged)} fields written to analysis.json")
    print(f"  From 4a: {len([k for k in merged if k in step4a])} fields")
    print(f"  From 4b: {len([k for k in merged if k in step4b])} fields")
    print(f"  From 4c: {len([k for k in merged if k in step4c])} fields")
    if missing:
        print(f"  Missing: {', '.join(missing)}")
    print(f"STATUS: SUCCESS | path={os.path.join(out_dir, 'analysis.json')}")


if __name__ == "__main__":
    main()
