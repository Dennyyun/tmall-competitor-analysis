# -*- coding: utf-8 -*-
"""
Step 3 - 解析原始数据（本地执行脚本）
读取 raw/*.json，解析关键字段，生成 parse_result.json

【修复】改为本地直接执行，避免子 Agent 超时问题
"""
import json
import os
import sys
import re
from pathlib import Path

from task_paths import ensure_task_dir, resolve_task_dir
from task_state import update_task_meta


def load_json(path):
    """加载 JSON 文件"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_price(price_data):
    """解析价格数据"""
    if isinstance(price_data, dict):
        return {
            'price_sale': price_data.get('券后价', ''),
            'price_ori': price_data.get('原价', '')
        }
    return {'price_sale': '', 'price_ori': ''}


def parse_shop_scores(scores_data):
    """解析店铺评分"""
    if isinstance(scores_data, dict):
        return {
            '宝贝质量': scores_data.get('宝贝质量', ''),
            '服务保障': scores_data.get('服务保障', ''),
            '物流速度': scores_data.get('物流速度', '')
        }
    return {'宝贝质量': '', '服务保障': '', '物流速度': ''}


def extract_main_images(images_list):
    """提取主图数量"""
    if isinstance(images_list, list):
        return len(images_list)
    return 0


def check_feedback_nonempty(feedback_str):
    """检查 feedback 是否非空"""
    if not feedback_str:
        return False
    # 检查是否包含评价内容
    return len(feedback_str) > 100  # 至少有100个字符


def check_question_nonempty(question_str):
    """检查 question 是否非空"""
    if not question_str:
        return False
    return len(question_str) > 10


def parse_product(brand, raw_data):
    """解析单个商品数据"""
    # 价格
    price_info = parse_price(raw_data.get('价格', {}))
    
    # 店铺评分
    shop_scores = parse_shop_scores(raw_data.get('店铺评分', {}))
    
    # 主图数量
    main_images = raw_data.get('商品主图', [])
    main_images_count = extract_main_images(main_images)
    
    # 详情图
    detail_image = raw_data.get('详情图', '')
    
    # feedback 和 question
    feedback = raw_data.get('feedback', '')
    question = raw_data.get('question', '')
    
    return {
        'title': raw_data.get('商品标题', ''),
        'price_sale': str(price_info['price_sale']),
        'price_ori': str(price_info['price_ori']),
        'sold': raw_data.get('已售数量', ''),
        'reviews': raw_data.get('评价总数', ''),
        'shop_name': raw_data.get('店铺名称', ''),
        'shop_scores': shop_scores,
        'main_images_count': main_images_count,
        'detail_image': detail_image,
        'feedback_nonempty': check_feedback_nonempty(feedback),
        'question_nonempty': check_question_nonempty(question)
    }


def parse_all_products(task_dir):
    """解析所有商品数据"""
    raw_dir = os.path.join(task_dir, 'raw')
    
    # 检查目录存在
    if not os.path.exists(raw_dir):
        raise RuntimeError(f"raw/ 目录不存在: {raw_dir}")
    
    brands = ['self', 'p1', 'p2', 'p3']
    result = {}
    errors = []
    
    for brand in brands:
        file_path = os.path.join(raw_dir, f'{brand}.json')
        
        # 检查文件存在
        if not os.path.exists(file_path):
            errors.append(f"{brand}.json 不存在")
            continue
        
        # 检查文件非空
        if os.path.getsize(file_path) == 0:
            errors.append(f"{brand}.json 为空文件")
            continue
        
        try:
            # 加载并解析
            raw_data = load_json(file_path)
            parsed = parse_product(brand, raw_data)
            result[brand] = parsed
            print(f"[PARSED] {brand}: {parsed['title'][:50]}...", flush=True)
        except Exception as e:
            errors.append(f"{brand}.json 解析失败: {e}")
            print(f"[ERROR] {brand}: {e}", flush=True)
    
    if errors:
        raise RuntimeError(f"解析失败: {'; '.join(errors)}")
    
    return result


def verify_parse_result(parse_result, raw_dir):
    """验证 parse_result 与 raw 文件的一致性"""
    print("[VERIFY] 开始验证 parse_result 与 raw 文件一致性...", flush=True)
    
    for brand in ['self', 'p1', 'p2', 'p3']:
        raw_path = os.path.join(raw_dir, f'{brand}.json')
        raw_data = load_json(raw_path)
        parsed = parse_result[brand]
        
        # 验证标题
        raw_title = raw_data.get('商品标题', '')
        parsed_title = parsed['title']
        if raw_title != parsed_title:
            raise RuntimeError(f"{brand} 标题不匹配: raw='{raw_title[:50]}...' vs parsed='{parsed_title[:50]}...'")
        
        # 验证店铺
        raw_shop = raw_data.get('店铺名称', '')
        parsed_shop = parsed['shop_name']
        if raw_shop != parsed_shop:
            raise RuntimeError(f"{brand} 店铺不匹配: raw='{raw_shop}' vs parsed='{parsed_shop}'")
        
        print(f"[VERIFY] {brand} 验证通过", flush=True)
    
    print("[VERIFY] 全部验证通过！", flush=True)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print('Usage: python scripts/parse_raw_data.py <taskId> [taskDir]', file=sys.stderr)
        return 1
    
    task_id = sys.argv[1]
    
    # 确定任务目录
    if len(sys.argv) > 2:
        task_dir = str(resolve_task_dir(task_id, sys.argv[2]))
    else:
        task_dir = str(ensure_task_dir(task_id))
    
    raw_dir = os.path.join(task_dir, 'raw')
    output_path = os.path.join(raw_dir, 'parse_result.json')
    
    print(f"[INFO] Task ID: {task_id}", flush=True)
    print(f"[INFO] Task Dir: {task_dir}", flush=True)
    print(f"[INFO] Raw Dir: {raw_dir}", flush=True)
    
    try:
        # 1. 解析所有商品
        result = parse_all_products(task_dir)
        
        # 2. 验证一致性（防止数据篡改）
        verify_parse_result(result, raw_dir)
        
        # 3. 写入结果
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 4. 验证写入成功
        if not os.path.exists(output_path):
            raise RuntimeError(f"写入失败: {output_path}")
        
        file_size = os.path.getsize(output_path)
        print(f"[SUCCESS] parse_result.json 生成成功: {output_path} ({file_size} bytes)", flush=True)
        update_task_meta(
            Path(task_dir),
            status_text='Step 3 完成',
            current_step='Step 3',
            outputs=[output_path],
        )
        
        # 5. 输出状态报告
        print(f"STATUS: SUCCESS | path={output_path} | brands=self,p1,p2,p3", flush=True)
        return 0
        
    except Exception as e:
        error_msg = str(e)
        update_task_meta(
            Path(task_dir),
            status_text=f'失败：Step 3 解析失败 - {error_msg[:80]}',
            current_step='Step 3',
        )
        print(f"[FAILED] {error_msg}", flush=True)
        print(f"STATUS: FAILED | reason={error_msg}", flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
