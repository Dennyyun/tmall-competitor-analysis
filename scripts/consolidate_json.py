# -*- coding: utf-8 -*-
"""
Step 9.5 — JSON 数据合并（v7.0 沿用容错版）

【核心逻辑】
1. Step 8 默认直接写入 analysis.json.visual_analysis（子 Agent 执行）
2. Step 9 输出 step9_plan.json（子 Agent 执行）
3. 本脚本合并 Step 9 输出，并兼容额外的 step8_visual_analysis.json 调试文件

【容错机制】
- 自动提取 ```json 代码块
- 自动剥离前后自然语言
- 支持多种 JSON 格式变体
"""
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any

from analysis_manager import AnalysisManager
from task_paths import ensure_task_dir
from task_state import update_task_meta


def extract_json_from_text(text: str) -> Dict:
    """
    从 LLM 输出中提取 JSON（容错处理）
    
    尝试顺序：
    1. 直接解析
    2. 提取 ```json 代码块
    3. 提取第一个 { 到最后一个 }
    """
    text = text.strip()
    
    # 尝试1：直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试2：提取 ```json 代码块
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
        r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            json_str = match.group(1).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
    
    # 尝试3：找到第一个 { 和最后一个 }
    start = text.find('{')
    end = text.rfind('}')
    
    if start != -1 and end != -1 and end > start:
        json_str = text[start:end+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # 所有尝试都失败
    raise ValueError(f"无法从文本中提取有效 JSON（文本长度: {len(text)} 字符）")


def load_json_with_fallback(path: str) -> Dict:
    """加载 JSON 文件，支持容错处理"""
    with open(path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    
    # 先尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # 如果失败，使用容错提取
        return extract_json_from_text(content)


def consolidate(task_dir: str) -> bool:
    """
    合并 Step 8 和 Step 9 的 JSON 数据到 analysis.json
    
    Args:
        task_dir: 任务目录路径
        
    Returns:
        bool: 是否成功
    """
    print("=" * 60)
    print("Step 9.5 — JSON 数据合并（v7.0 沿用容错版）")
    print("=" * 60)
    
    output_dir = os.path.join(task_dir, 'output')
    
    # 检查输入文件
    step8_file = os.path.join(output_dir, 'step8_visual_analysis.json')
    step9_file = os.path.join(output_dir, 'step9_plan.json')
    analysis_path = os.path.join(output_dir, 'analysis.json')
    
    print(f"\n[1/3] 检查输入文件...")
    
    step8_exists = os.path.exists(step8_file)
    step9_exists = os.path.exists(step9_file)
    
    if not step9_exists:
        print(f"  [ERROR] 未找到: {step9_file}")
        print(f"  [ERROR] 请先执行 Step 9")
        return False

    print(f"  [OK] Step 8: {'找到独立文件' if step8_exists else '使用 analysis.json 中的 visual_analysis'}")
    print(f"  [OK] Step 9: {'找到' if step9_exists else '缺失'}")
    
    # 加载并合并数据
    print(f"\n[2/3] 加载并合并数据...")
    
    manager = AnalysisManager(task_dir)
    merged_count = 0
    
    # 合并 Step 8
    if step8_exists:
        try:
            step8_data = load_json_with_fallback(step8_file)
            print(f"  [OK] Step 8 数据加载成功，{len(step8_data)} 个顶级字段")
            
            success = manager.write(step8_data, merge=True)
            if success:
                print(f"  [OK] Step 8 数据已合并")
                merged_count += 1
            else:
                print(f"  [ERROR] Step 8 数据合并失败")
                return False
        except Exception as e:
            print(f"  [ERROR] Step 8 处理失败: {e}")
            return False
    else:
        existing_analysis = manager.read() if os.path.exists(analysis_path) else {}
        if not existing_analysis.get('visual_analysis'):
            print("  [ERROR] analysis.json 中缺少 visual_analysis，无法跳过 Step 8 独立文件")
            return False
        print("  [OK] 已验证 analysis.json 中存在 visual_analysis")
    
    # 合并 Step 9
    try:
        step9_data = load_json_with_fallback(step9_file)
        print(f"  [OK] Step 9 数据加载成功，{len(step9_data)} 个顶级字段")
        
        success = manager.write(step9_data, merge=True)
        if success:
            print(f"  [OK] Step 9 数据已合并")
            merged_count += 1
        else:
            print(f"  [ERROR] Step 9 数据合并失败")
            return False
    except Exception as e:
        print(f"  [ERROR] Step 9 处理失败: {e}")
        return False
    
    # 验证结果
    print(f"\n[3/3] 验证合并结果...")
    
    final_data = manager.read()
    
    # 检查运营决策简报关键字段
    required_fields = {
        'visual_analysis': 'Step 8 输出',
        'decision_mode': 'Step 9 决策模式输出',
        'data_quality_gate': 'Step 9 数据门槛输出',
        'conversion_blockers': 'Step 9 转化阻力输出',
        'evidence_chain': 'Step 9 证据链输出',
        'decision_summary': 'Step 9 决策摘要输出',
        'validation_plan': 'Step 9 验证闭环输出'
    }

    recommended_fields = {
        'title_analysis': 'Step 9 标题支撑输出',
        'pricing_strategy': 'Step 9 价格支撑输出',
        'review_qa_insights': 'Step 9 评价问答支撑输出',
        'kpi_table': 'Step 9 验证指标输出',
    }
    
    missing_fields = []
    for field, source in required_fields.items():
        if field not in final_data or not final_data[field]:
            missing_fields.append(f"{field}（{source}）")
    
    if missing_fields:
        print(f"  [WARN] 以下关键字段缺失: {', '.join(missing_fields)}")
        print(f"  [NOTE] 继续执行，但可能影响 HTML 报告生成")
    else:
        print(f"  [OK] 所有关键字段已验证通过")

    missing_recommended = []
    for field, source in recommended_fields.items():
        if field not in final_data or not final_data[field]:
            missing_recommended.append(f"{field}（{source}）")

    if missing_recommended:
        print(f"  [WARN] 以下决策简报支撑字段缺失: {', '.join(missing_recommended)}")
        print("  [NOTE] 报告仍会生成，但关键支撑数据会减少；如需完整简报，请重新执行 Step 9")
    else:
        print("  [OK] 决策简报支撑字段已验证通过")
    
    print(f"\n" + "=" * 60)
    print(f"[SUCCESS] 合并完成！")
    print(f"          analysis.json 共 {len(final_data)} 个字段")
    print(f"          合并文件数: {merged_count}")
    print(f"          visual_analysis: {'OK' if 'visual_analysis' in final_data else 'MISSING'}")
    print(f"          decision_summary: {'OK' if 'decision_summary' in final_data else 'MISSING'}")
    print(f"          validation_plan: {'OK' if 'validation_plan' in final_data else 'MISSING'}")
    print(f"          brief_support_fields: {'OK' if all(f in final_data for f in recommended_fields) else 'PARTIAL'}")
    print("=" * 60)
    
    return True


def main():
    """主入口"""
    if len(sys.argv) < 2:
        print("用法: python scripts/consolidate_json.py <taskId>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    task_dir = str(ensure_task_dir(task_id))
    
    print(f"\nTask ID: {task_id}")
    print(f"Task Dir: {task_dir}")
    
    success = consolidate(task_dir)

    if success:
        update_task_meta(
            Path(task_dir),
            status_text='Step 9.5 完成',
            current_step='Step 9.5',
            outputs=[os.path.join(task_dir, 'output', 'analysis.json')],
        )
        print(f"\nSTATUS: SUCCESS")
        sys.exit(0)
    else:
        update_task_meta(
            Path(task_dir),
            status_text='失败：Step 9.5 合并失败',
            current_step='Step 9.5',
        )
        print(f"\nSTATUS: FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
