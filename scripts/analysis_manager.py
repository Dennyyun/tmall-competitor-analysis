# -*- coding: utf-8 -*-
"""Safe read/write helpers for task output/analysis.json."""

import json
import os
import time
from typing import Any, Dict


class AnalysisManager:
    """Manage analysis.json with atomic writes and focused schema checks."""

    def __init__(self, task_dir: str, timeout: int = 30):
        self.task_dir = task_dir
        self.output_dir = os.path.join(task_dir, "output")
        self.analysis_path = os.path.join(self.output_dir, "analysis.json")
        os.makedirs(self.output_dir, exist_ok=True)

    def read(self) -> Dict[str, Any]:
        """Read analysis.json. Return an empty dict when it does not exist."""
        if not os.path.exists(self.analysis_path):
            return {}

        try:
            with open(self.analysis_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            backup_path = self.analysis_path + ".corrupted." + str(int(time.time()))
            os.rename(self.analysis_path, backup_path)
            raise RuntimeError(
                f"analysis.json is corrupted ({e}); backed up to {backup_path}. "
                "Check the last write or restore from backup."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to read analysis.json: {e}")

    def write(self, data: Dict[str, Any], merge: bool = True) -> bool:
        """Write analysis.json atomically."""
        temp_path = self.analysis_path + ".tmp"

        try:
            data = self._normalize_data(data)

            if merge and os.path.exists(self.analysis_path):
                existing = self.read()
                data = self._deep_merge(self._normalize_data(existing), data)

            if not self._validate_data(data):
                print("[ERROR] analysis.json validation failed; write rejected", flush=True)
                return False

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_path, self.analysis_path)
            print(f"[SUCCESS] analysis.json written ({len(data)} fields)", flush=True)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to write analysis.json: {e}", flush=True)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

    def _deep_merge(self, existing: Dict, new: Dict) -> Dict:
        result = existing.copy()

        for key, value in new.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_data(self, data: Dict) -> bool:
        if not isinstance(data, dict):
            print("[ERROR] analysis payload must be a dict", flush=True)
            return False

        empty_dict_fields = [k for k, v in data.items() if isinstance(v, dict) and not v]
        if empty_dict_fields:
            print(f"[ERROR] Empty dict fields: {', '.join(empty_dict_fields)}", flush=True)
            return False

        critical_fields = ["positioning", "decision_factors", "key_findings"]
        empty_critical = [k for k in critical_fields if k in data and self._is_empty(data[k])]
        if empty_critical:
            print(f"[ERROR] Empty critical fields: {', '.join(empty_critical)}", flush=True)
            return False

        if "positioning" in data and not self._validate_brand_mapping(data["positioning"]):
            print("[ERROR] positioning requires non-empty self/p1/p2/p3 mappings", flush=True)
            return False

        if "visual_analysis" in data and not self._validate_visual_analysis(data["visual_analysis"]):
            print("[ERROR] visual_analysis requires self/p1/p2/p3 desc and score", flush=True)
            return False

        if "kpi_table" in data and data["kpi_table"] and not self._validate_kpi_table(data["kpi_table"]):
            print("[ERROR] kpi_table rows require metric/current/target/action", flush=True)
            return False

        if "decision_mode" in data and not self._validate_decision_mode(data["decision_mode"]):
            print("[ERROR] decision_mode is incomplete", flush=True)
            return False

        if "data_quality_gate" in data and not self._validate_data_quality_gate(data["data_quality_gate"]):
            print("[ERROR] data_quality_gate is incomplete", flush=True)
            return False

        if "conversion_blockers" in data and not self._validate_conversion_blockers(data["conversion_blockers"]):
            print("[ERROR] conversion_blockers is incomplete", flush=True)
            return False

        if "evidence_chain" in data and not self._validate_evidence_chain(data["evidence_chain"]):
            print("[ERROR] evidence_chain is incomplete", flush=True)
            return False

        if "decision_summary" in data and not self._validate_decision_summary(data["decision_summary"]):
            print("[ERROR] decision_summary is incomplete", flush=True)
            return False

        if "validation_plan" in data and not self._validate_validation_plan(data["validation_plan"]):
            print("[ERROR] validation_plan is incomplete", flush=True)
            return False

        empty_fields = [k for k, v in data.items() if k not in critical_fields and self._is_empty(v)]
        if empty_fields:
            print(f"[WARNING] Empty fields: {', '.join(empty_fields)}", flush=True)

        return True

    def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict):
            return data
        return self._deep_merge({}, data)

    def _is_empty(self, value: Any) -> bool:
        if value is None or value == "" or value == []:
            return True
        if isinstance(value, dict):
            return len(value) == 0
        return False

    def _validate_required_keys(self, payload: Any, keys: list[str]) -> bool:
        if not isinstance(payload, dict):
            return False
        return all(not self._is_empty(payload.get(key)) for key in keys)

    def _validate_brand_mapping(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        return all(not self._is_empty(payload.get(brand)) for brand in ("self", "p1", "p2", "p3"))

    def _validate_visual_analysis(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        for brand in ("self", "p1", "p2", "p3"):
            item = payload.get(brand)
            if not isinstance(item, dict):
                return False
            if self._is_empty(item.get("desc")) or self._is_empty(item.get("score")):
                return False
        return True

    def _validate_kpi_table(self, payload: Any) -> bool:
        if not isinstance(payload, list):
            return False
        required = ["metric", "current", "target", "action"]
        for row in payload:
            if not isinstance(row, dict):
                return False
            if any(self._is_empty(row.get(key)) for key in required):
                return False
        return True

    def _validate_decision_mode(self, payload: Any) -> bool:
        if not self._validate_required_keys(payload, ["business_goal", "decision_type", "decision_scope", "reason"]):
            return False
        return payload.get("decision_type") in ("execute", "experiment", "collect_data", "hold")

    def _validate_data_quality_gate(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        required = ["can_make_final_decision", "missing_critical_data", "weak_data_points", "decision_limitation"]
        if not all(key in payload for key in required):
            return False
        return isinstance(payload.get("missing_critical_data"), list) and isinstance(payload.get("weak_data_points"), list)

    def _validate_conversion_blockers(self, payload: Any) -> bool:
        if not isinstance(payload, list) or not payload:
            return False
        for row in payload:
            if not self._validate_required_keys(row, ["blocker", "severity", "evidence", "affected_stage", "priority"]):
                return False
        return True

    def _validate_evidence_chain(self, payload: Any) -> bool:
        if not isinstance(payload, list) or not payload:
            return False
        for row in payload:
            if not self._validate_required_keys(row, ["evidence", "source", "business_interpretation", "supports_decision"]):
                return False
        return True

    def _validate_decision_summary(self, payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        if not self._validate_required_keys(payload, ["final_decision", "why_this", "why_not_others", "expected_impact"]):
            return False

        top3 = payload.get("top3_actions")
        if not isinstance(top3, list) or not top3:
            return False
        for action in top3:
            required = ["priority", "action_type", "owner", "action", "acceptance_criteria", "deadline", "risk"]
            if not self._validate_required_keys(action, required):
                return False
            if not isinstance(action.get("dependent_data"), list):
                return False

        confidence = payload.get("confidence_level")
        if not self._validate_required_keys(confidence, ["level", "reason"]):
            return False
        return (
            isinstance(payload.get("not_do_now"), list)
            and isinstance(payload.get("decision_risks"), list)
            and isinstance(confidence.get("what_would_increase_confidence"), list)
        )

    def _validate_validation_plan(self, payload: Any) -> bool:
        if not self._validate_required_keys(payload, ["method", "primary_metric", "no_baseline_rule"]):
            return False
        return isinstance(payload.get("secondary_metric"), list)

    def get_field(self, field_path: str, default=None):
        data = self.read()
        keys = field_path.split(".")

        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default

        return data

    def check_step_completion(self, step_number: int | float) -> bool:
        data = self.read()

        step_fields = {
            4: [
                "positioning",
                "hero_exec_cards",
                "analysis_date",
                "hero_badge",
                "hero_title",
                "decision_factors",
                "jtbd_functional",
                "jtbd_emotional",
                "feedback_insights",
                "feedback_pain_points",
                "feedback_eye_rate",
                "key_findings",
                "price_matrix",
                "opportunity_1",
                "opportunity_2",
                "threat_1",
                "threat_2",
            ],
            7: [],
            8: [],
            9: [
                "decision_mode",
                "data_quality_gate",
                "conversion_blockers",
                "evidence_chain",
                "decision_summary",
                "validation_plan",
            ],
            9.5: [
                "visual_analysis",
                "decision_mode",
                "data_quality_gate",
                "conversion_blockers",
                "evidence_chain",
                "decision_summary",
                "validation_plan",
            ],
        }

        if step_number not in step_fields:
            print(f"[WARNING] Unknown step number: {step_number}", flush=True)
            return False

        required = step_fields[step_number]
        if not required:
            return True

        missing = [field for field in required if field not in data or not data[field]]
        if missing:
            print(f"[WARNING] Step {step_number} missing fields: {', '.join(missing)}", flush=True)
            return False

        print(f"[INFO] Step {step_number} fields complete", flush=True)
        return True


def get_manager(task_dir: str) -> AnalysisManager:
    return AnalysisManager(task_dir)


def safe_write_analysis(task_dir: str, data: Dict[str, Any], merge: bool = True) -> bool:
    manager = AnalysisManager(task_dir)
    return manager.write(data, merge=merge)


def safe_read_analysis(task_dir: str) -> Dict[str, Any]:
    manager = AnalysisManager(task_dir)
    return manager.read()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python analysis_manager.py <task_dir>")
        sys.exit(1)

    manager = AnalysisManager(sys.argv[1])
    current = manager.read()
    print(f"Current analysis.json field count: {len(current)}")
