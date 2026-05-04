import json
import os
import time
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = 'https://api.yingdao.com'


def require_config():
    access_key_id = os.environ.get('YINGDAO_ACCESS_KEY_ID')
    access_key_secret = os.environ.get('YINGDAO_ACCESS_KEY_SECRET')
    account_name = os.environ.get('YINGDAO_ACCOUNT_NAME')
    robot_uuid = os.environ.get('YINGDAO_ROBOT_UUID')

    if not all([access_key_id, access_key_secret, account_name, robot_uuid]):
        raise RuntimeError(
            "影刀配置缺失！请设置以下环境变量：\n"
            "  - YINGDAO_ACCESS_KEY_ID\n"
            "  - YINGDAO_ACCESS_KEY_SECRET\n"
            "  - YINGDAO_ACCOUNT_NAME\n"
            "  - YINGDAO_ROBOT_UUID"
        )

    return access_key_id, access_key_secret, account_name, robot_uuid


def get_token():
    access_key_id, access_key_secret, _, _ = require_config()
    r = requests.get(
        f'{BASE_URL}/oapi/token/v2/token/create',
        params={'accessKeyId': access_key_id, 'accessKeySecret': access_key_secret},
        timeout=30,
    )
    return r.json()['data']['accessToken']

def start_job(token, goods_url):
    import uuid
    _, _, account_name, robot_uuid = require_config()
    r = requests.post(f'{BASE_URL}/oapi/dispatch/v2/job/start',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={
            'accountName': account_name,
            'robotUuid': robot_uuid,
            'idempotentUuid': str(uuid.uuid4()),
            'waitTimeout': '10m',
            'executeScope': 'any',
            'priority': 'middle',
            'params': [{'name': '商品链接', 'value': goods_url, 'type': 'str'}]
        }, timeout=30)
    return r.json()['data']['jobUuid']

def query_job(token, jobUuid):
    r = requests.post(f'{BASE_URL}/oapi/dispatch/v2/job/query',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
        json={'jobUuid': jobUuid}, timeout=30)
    return r.json()

def download_json(url):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    # 验证是有效JSON
    json.loads(r.text)
    return r.text

def main():
    token = get_token()
    print(f'Token OK: {token[:20]}...', flush=True)

    goods_list = [
        ('self', os.environ.get('YINGDAO_CHECK_SELF_GOODS', 'https://detail.tmall.com/item.htm?id=YOUR_SELF_ITEM_ID')),
        ('p1', os.environ.get('YINGDAO_CHECK_P1_GOODS', 'https://detail.tmall.com/item.htm?id=YOUR_COMPETITOR_1_ITEM_ID')),
        ('p2', os.environ.get('YINGDAO_CHECK_P2_GOODS', 'https://detail.tmall.com/item.htm?id=YOUR_COMPETITOR_2_ITEM_ID')),
        ('p3', os.environ.get('YINGDAO_CHECK_P3_GOODS', 'https://detail.tmall.com/item.htm?id=YOUR_COMPETITOR_3_ITEM_ID')),
    ]

    task_base_dir = os.environ.get('TASK_BASE_DIR', os.path.join('shared', 'tasks'))
    log_dir = os.path.join(task_base_dir, 'yingdao-check', 'raw')
    os.makedirs(log_dir, exist_ok=True)

    for i, (brand, url) in enumerate(goods_list):
        print(f'\n[{brand}] Starting...', flush=True)
        job_uuid = start_job(token, url)
        print(f'[{brand}] Job: {job_uuid}', flush=True)

        deadline = time.time() + 10 * 60
        while time.time() < deadline:
            result = query_job(token, job_uuid)
            if 'data' not in result:
                print(f'[{brand}] Waiting... response: {result}', flush=True)
                time.sleep(10)
                continue
            status = result['data'].get('statusName')
            print(f'[{brand}] Status: {status}', flush=True)
            if status == '完成':
                outputs = result['data'].get('robotParams', {}).get('outputs', [])
                if not outputs:
                    print(f'[{brand}] No outputs!', flush=True)
                    break
                download_url = outputs[0].get('value')
                print(f'[{brand}] Downloading from: {download_url}', flush=True)
                json_str = download_json(download_url)
                out_path = os.path.join(log_dir, f'{brand}.json')
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                print(f'[{brand}] Saved {len(json_str)} bytes', flush=True)
                break
            elif status == '异常':
                print(f'[{brand}] 异常: {result}', flush=True)
                break
            time.sleep(10)
        else:
            print(f'[{brand}] TIMEOUT', flush=True)

        if i < len(goods_list) - 1:
            time.sleep(6)

    print('\n=== DONE ===', flush=True)
    for f in os.listdir(log_dir):
        size = os.path.getsize(os.path.join(log_dir, f))
        print(f'{f}: {size} bytes', flush=True)


if __name__ == '__main__':
    main()
