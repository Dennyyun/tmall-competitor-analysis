import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

# Add project directory to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from scripts.task_state_machine import TaskStateMachine, StepStatus, STEP_SEQUENCE

def run_test():
    task_id = "test_v7_e2e"
    task_base_dir = Path(os.environ.get("TASK_BASE_DIR", project_root / ".tmp" / "tasks"))
    task_dir = task_base_dir / task_id
    source_raw = Path(os.environ.get("TMALL_E2E_RAW_FIXTURE", project_root / "tests" / "fixtures" / "raw"))

    if not source_raw.exists():
        print(f"SKIP: E2E raw fixture not found: {source_raw}")
        return
    
    # 1. Setup mock task
    print(f"--- Setting up test task: {task_id} ---")
    if task_dir.exists():
        shutil.rmtree(task_dir)
    task_dir.mkdir(parents=True)
    
    shutil.copytree(source_raw, task_dir / "raw")
    output_dir = task_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    sm = TaskStateMachine(str(task_dir))
    
    # helper to run command
    def run_cmd(cmd):
        print(f"Running: {cmd}")
        env = {**os.environ, "TASK_BASE_DIR": str(task_base_dir)}
        res = subprocess.run(cmd, shell=True, cwd=project_root, capture_output=True, text=True, env=env)
        if res.returncode != 0:
            print(f"STDOUT: {res.stdout}")
            print(f"STDERR: {res.stderr}")
            raise RuntimeError(f"Command failed: {cmd}")
        return res.stdout
        
    # Step 1 & 2: Init and Collect (Already done by copying raw data)
    sm.mark("step_1", StepStatus.SUCCESS)
    sm.mark("step_2", StepStatus.SUCCESS)
    
    # Step 3: Parse
    print("\n--- Step 3: Parse ---")
    assert sm.can_proceed("step_3")[0], sm.can_proceed("step_3")[1]
    sm.mark("step_3", StepStatus.RUNNING)
    run_cmd(f"python scripts/parse_raw_data.py {task_id}")
    sm.mark("step_3", StepStatus.SUCCESS)
    
    # Step 4a: Landscape (Python)
    print("\n--- Step 4a: Landscape ---")
    assert sm.can_proceed("step_4a")[0]
    sm.mark("step_4a", StepStatus.RUNNING)
    run_cmd(f"python scripts/compute_landscape.py {task_id}")
    sm.mark("step_4a", StepStatus.SUCCESS)
    
    # Step 4b: JTBD (Mock LLM)
    print("\n--- Step 4b: JTBD (Mock) ---")
    assert sm.can_proceed("step_4b")[0]
    sm.mark("step_4b", StepStatus.RUNNING)
    mock_4b = {
        "decision_factors": [{"factor": "护眼", "weight": 80, "self_score": 8, "competitor_avg": 7}],
        "jtbd_functional": ["提供充足照明"],
        "jtbd_emotional": ["保护视力焦虑"]
    }
    with open(output_dir / "step4b_jtbd.json", "w", encoding="utf-8") as f:
        json.dump(mock_4b, f, ensure_ascii=False)
    sm.mark("step_4b", StepStatus.SUCCESS)
    
    # Step 4c: Insights (Mock LLM)
    print("\n--- Step 4c: Insights (Mock) ---")
    assert sm.can_proceed("step_4c")[0]
    sm.mark("step_4c", StepStatus.RUNNING)
    mock_4c = {
        "opportunity_1": {"icon": "🚀", "title": "O1", "content": "D1"},
        "opportunity_2": {"icon": "🌟", "title": "O2", "content": "D2"},
        "threat_1": {"icon": "⚠️", "title": "T1", "content": "D1"},
        "threat_2": {"icon": "🔒", "title": "T2", "content": "D2"},
        "feedback_insights": ["Insight 1"],
        "feedback_pain_points": {
            "self": "P1", "p1": "P2", "p2": "P3", "p3": "P4"
        },
        "feedback_eye_rate": {
            "self": "R1", "p1": "R2", "p2": "R3", "p3": "R4"
        }
    }
    with open(output_dir / "step4c_insights.json", "w", encoding="utf-8") as f:
        json.dump(mock_4c, f, ensure_ascii=False)
    sm.mark("step_4c", StepStatus.SUCCESS)
    
    # Step 4d: Merge
    print("\n--- Step 4d: Merge ---")
    assert sm.can_proceed("step_4d")[0]
    sm.mark("step_4d", StepStatus.RUNNING)
    run_cmd(f"python scripts/merge_step4.py {task_id}")
    sm.mark("step_4d", StepStatus.SUCCESS)
    
    # Step 7: Raw MD
    print("\n--- Step 7: Raw MD ---")
    assert sm.can_proceed("step_7")[0]
    sm.mark("step_7", StepStatus.RUNNING)
    run_cmd(f"python scripts/generate_raw_md.py {task_id}")
    sm.mark("step_7", StepStatus.SUCCESS)
    
    # Step 8: Visual (Mock LLM)
    print("\n--- Step 8: Visual (Mock) ---")
    assert sm.can_proceed("step_8")[0]
    sm.mark("step_8", StepStatus.RUNNING)
    run_cmd(f"python scripts/generate_visual_input.py {task_id}")
    
    # Read analysis.json, inject visual, save
    with open(output_dir / "analysis.json", "r", encoding="utf-8") as f:
        analysis = json.load(f)
    analysis["visual_analysis"] = {
        "self": {"desc": "self desc", "score": 8, "score_reason": "ok"},
        "p1": {"desc": "p1 desc", "score": 9, "score_reason": "good"},
        "p2": {"desc": "p2 desc", "score": 6, "score_reason": "bad"},
        "p3": {"desc": "p3 desc", "score": 7, "score_reason": "avg"}
    }
    with open(output_dir / "analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False)
    sm.mark("step_8", StepStatus.SUCCESS)
    
    # Step 9: Plan (Mock LLM)
    print("\n--- Step 9: Plan (Mock) ---")
    assert sm.can_proceed("step_9")[0]
    sm.mark("step_9", StepStatus.RUNNING)
    mock_9 = {
        "decision_mode": {
            "business_goal": "Improve conversion",
            "decision_type": "experiment",
            "decision_scope": "title, hero image, SKU, PDP",
            "reason": "Evidence is enough for experiment, not enough for final pricing decision"
        },
        "data_quality_gate": {
            "can_make_final_decision": False,
            "missing_critical_data": ["CTR", "SKU conversion"],
            "weak_data_points": ["review sample is limited"],
            "decision_limitation": "Use experiment validation before scaling"
        },
        "conversion_blockers": [
            {
                "blocker": "Core eye-protection value is not visible enough",
                "severity": "high",
                "evidence": "Reviews and Q&A mention lighting comfort",
                "affected_stage": "click and conversion",
                "priority": 1
            }
        ],
        "evidence_chain": [
            {
                "evidence": "Competitors emphasize eye protection and installation",
                "source": "title/review/Q&A",
                "business_interpretation": "The product should surface these claims earlier",
                "supports_decision": "Run title and hero-image experiment"
            }
        ],
        "decision_summary": {
            "final_decision": "Do not cut price first; run a positioning and content experiment",
            "why_this": "Current data points to communication friction before price friction",
            "why_not_others": "No baseline SKU conversion data supports an immediate price cut",
            "expected_impact": "Improve click quality and detail-page conversion",
            "top3_actions": [
                {
                    "priority": 1,
                    "action_type": "content",
                    "owner": "ops",
                    "action": "Update title and hero image around eye protection",
                    "acceptance_criteria": "New version is live and tracked",
                    "deadline": "D+3",
                    "risk": "CTR may not improve",
                    "dependent_data": ["CTR"]
                }
            ],
            "not_do_now": ["Do not cut price first"],
            "decision_risks": ["No baseline conversion"],
            "confidence_level": {
                "level": "medium",
                "reason": "Enough qualitative evidence, missing conversion baseline",
                "what_would_increase_confidence": ["CTR", "SKU conversion"]
            }
        },
        "validation_plan": {
            "method": "A/B experiment",
            "primary_metric": "detail-page conversion",
            "secondary_metric": ["CTR", "add-to-cart rate"],
            "no_baseline_rule": "Run A/A or use first 3 days as baseline"
        },
        "kpi_table": [{"metric": "M", "current": "C", "target": "T", "target_cls": "green", "action": "A"}]
    }
    with open(output_dir / "step9_plan.json", "w", encoding="utf-8") as f:
        json.dump(mock_9, f, ensure_ascii=False)
    sm.mark("step_9", StepStatus.SUCCESS)
    
    # Step 9.5: Consolidate
    print("\n--- Step 9.5: Consolidate ---")
    assert sm.can_proceed("step_9_5")[0]
    sm.mark("step_9_5", StepStatus.RUNNING)
    run_cmd(f"python scripts/consolidate_json.py {task_id}")
    sm.mark("step_9_5", StepStatus.SUCCESS)
    
    # Step 10: HTML
    print("\n--- Step 10: HTML ---")
    assert sm.can_proceed("step_10")[0]
    sm.mark("step_10", StepStatus.RUNNING)
    run_cmd(f"python scripts/report_template.py {task_id}")
    sm.mark("step_10", StepStatus.SUCCESS)
    
    print("\n=== E2E Test Passed ===")
    print(f"Report generated at: {output_dir}/竞品分析报告_完整版_{task_id}.html")
    print(f"Task state history:")
    with open(task_dir / "task_state.json", "r", encoding="utf-8") as f:
        print(f.read())

if __name__ == "__main__":
    run_test()
