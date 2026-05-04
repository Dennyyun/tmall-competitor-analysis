import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, SCRIPT_DIR)

from product_collector import run_batch
from task_paths import ensure_task_dir
from task_state import update_task_meta


SELECTIVE_RETRY_ROUNDS = 1


def verify_collected_file(file_path: str) -> tuple[bool, str | None]:
    if not file_path or not os.path.exists(file_path):
        return False, f"文件不存在: {file_path}"
    if os.path.getsize(file_path) == 0:
        return False, f"文件为空: {file_path}"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
    except Exception as exc:
        return False, f"JSON 校验失败: {exc}"

    return True, None


def append_retry_log(log_path: str, brand: str, url: str, error_msg: str, phase: str) -> None:
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{phase}] [FAILED] {brand} | {url} | {error_msg}\n")


def normalize_results(results: dict, goods_map: dict[str, str], log_path: str, phase: str) -> dict:
    normalized = {}
    for brand, result in results.items():
        if result['status'] == 'success':
            is_valid, error_msg = verify_collected_file(result['file'])
            if is_valid:
                normalized[brand] = result
                continue

            append_retry_log(log_path, brand, goods_map[brand], error_msg, f'{phase}-verify')
            normalized[brand] = {
                'status': 'failed',
                'file': result.get('file'),
                'size': 0,
                'error': error_msg,
            }
            continue

        normalized[brand] = result

    return normalized


def collect_brand_status(results: dict) -> tuple[list[str], list[str]]:
    success_list = []
    fail_list = []
    for brand, result in results.items():
        if result['status'] == 'success':
            success_list.append(brand)
        else:
            fail_list.append(brand)
    return success_list, fail_list


def main() -> int:
    if len(sys.argv) < 6:
        print('Usage: python scripts/run_collect.py <taskId> <self_url> <p1_url> <p2_url> <p3_url>')
        return 1

    task_id = sys.argv[1]
    goods_list = [
        ('self', sys.argv[2]),
        ('p1', sys.argv[3]),
        ('p2', sys.argv[4]),
        ('p3', sys.argv[5]),
    ]
    goods_map = dict(goods_list)

    task_dir = ensure_task_dir(task_id)
    raw_dir = os.path.join(task_dir, 'raw')
    os.makedirs(raw_dir, exist_ok=True)
    log_path = os.path.join(raw_dir, 'collection_errors.log')

    # 过滤已经采集成功的商品，避免 OpenClaw 超时重试时重复采集
    needs_collection = []
    results = {}
    for brand, url in goods_list:
        file_path = os.path.join(raw_dir, f'{brand}.json')
        is_valid, _ = verify_collected_file(file_path)
        if is_valid:
            print(f"[SKIP] {brand} 已存在有效数据，跳过采集")
            results[brand] = {
                "status": "success",
                "file": file_path,
                "size": os.path.getsize(file_path),
                "error": None
            }
        else:
            needs_collection.append((brand, url))

    if needs_collection:
        print(f"\n[START] 本轮需要采集的品牌: {[b for b, _ in needs_collection]}")
        new_results = run_batch(needs_collection, output_dir=raw_dir, reset_log=True, attempt_label='initial')
        new_results = normalize_results(new_results, goods_map, log_path, 'initial')
        results.update(new_results)
    else:
        print("\n[START] 所有品牌均已存在有效数据，直接跳过采集环节。")

    success_list, fail_list = collect_brand_status(results)

    for retry_round in range(1, SELECTIVE_RETRY_ROUNDS + 1):
        if not fail_list:
            break

        retry_goods = [(brand, goods_map[brand]) for brand in fail_list]
        print(f'\n[RETRY] 第 {retry_round} 轮定点补采: {fail_list}')
        retry_results = run_batch(
            retry_goods,
            output_dir=raw_dir,
            reset_log=False,
            attempt_label=f'retry-{retry_round}',
        )
        retry_results = normalize_results(retry_results, goods_map, log_path, f'retry-{retry_round}')
        results.update(retry_results)
        success_list, fail_list = collect_brand_status(results)

    print('=== COLLECTION RESULT ===')
    print(f'TASK_DIR: {task_dir}')
    print(f'SUCCESS: {success_list}')
    print(f'FAILED: {fail_list}')

    if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
        with open(log_path, 'r', encoding='utf-8') as f:
            errors = f.read()
        level = 'WARNING' if fail_list else 'INFO'
        print(f'\n[{level}] 采集过程中有失败/补采记录:')
        print(errors)
        if not fail_list:
            print('[INFO] 所有品牌最终均已成功，以上日志仅保留失败尝试轨迹。')

    if fail_list:
        update_task_meta(
            task_dir,
            status_text=f'失败：采集失败品牌 {", ".join(fail_list)}',
            current_step='Step 2',
            outputs=[log_path] if os.path.exists(log_path) else None,
        )
        print(f'STATUS: FAILED | reason=采集失败品牌: {", ".join(fail_list)}')
        return 1

    update_task_meta(
        task_dir,
        status_text='Step 2 完成',
        current_step='Step 2',
        outputs=[os.path.join(raw_dir, f'{brand}.json') for brand in success_list],
        note='失败商品已按品牌定点补采',
    )
    print(f'STATUS: SUCCESS | path={raw_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
