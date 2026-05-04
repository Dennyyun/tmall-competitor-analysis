# -*- coding: utf-8 -*-
"""
上传报表至 Cloudflare R2

使用方法:
    python scripts/upload_to_cloudflare.py <taskId>

环境变量配置 (.env 或系统环境变量):
    R2_ACCOUNT_ID=your_account_id
    R2_ACCESS_KEY_ID=your_access_key_id
    R2_SECRET_ACCESS_KEY=your_secret_access_key
    R2_BUCKET_NAME=reports
    R2_PUBLIC_DOMAIN=https://your-domain.com
"""

import json
import os
import sys
import uuid
import urllib.parse
from pathlib import Path


from dotenv import load_dotenv
from task_paths import ensure_task_dir, resolve_task_dir
from task_state import update_task_meta

load_dotenv()
# 从环境变量读取配置
R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'reports')
R2_PUBLIC_DOMAIN = os.environ.get('R2_PUBLIC_DOMAIN', '')


def upload_report(task_id, report_path):
    """
    上传报告文件到 R2
    :param task_id: 任务ID
    :param report_path: 报告文件本地路径
    :return: 文件的公共访问 URL
    """
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        return "Error: 请先安装 boto3: pip install boto3"

    if not os.path.exists(report_path):
        return f"Error: 文件不存在 {report_path}"

    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]):
        return "Error: 缺少 R2 配置，请设置环境变量 R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY"

    # 初始化 R2 客户端
    s3 = boto3.client(
        service_name='s3',
        endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version='s3v4')
    )

    # 读取文件内容
    with open(report_path, 'rb') as f:
        content = f.read()

    # 构造文件名
    file_name = f"report_{task_id}_{uuid.uuid4().hex[:6]}.html"
    object_key = f"reports/{task_id}/{file_name}"

    # 上传文件
    s3.put_object(
        Body=content,
        Bucket=R2_BUCKET_NAME,
        Key=object_key,
        ContentType='text/html; charset=utf-8'
    )

    # 返回访问链接
    safe_key = urllib.parse.quote(object_key)
    domain = R2_PUBLIC_DOMAIN.rstrip('/') or f"https://{R2_ACCOUNT_ID}.r2.dev"
    return f"{domain}/{safe_key}"


def main():
    if len(sys.argv) < 2:
        print('Usage: python scripts/upload_to_cloudflare.py <taskId> [report_path]')
        sys.exit(1)

    task_id = sys.argv[1]

    # 如果提供了第二个参数，直接使用作为文件路径
    if len(sys.argv) >= 3:
        report_path = sys.argv[2]
    else:
        task_dir = ensure_task_dir(task_id)
        report_path = os.path.join(task_dir, 'output', f'竞品分析报告_完整版_{task_id}.html')

    print(f'Uploading report for task: {task_id}...')

    url = upload_report(task_id, report_path)

    if url.startswith('Error'):
        update_task_meta(
            resolve_task_dir(task_id),
            status_text=f'失败：Step 10.5 Cloudflare 上传失败 - {url[:80]}',
            current_step='Step 10.5',
        )
        print(f'FAILED: {url}')
        sys.exit(1)
    else:
        print(f'SUCCESS: {url}')

        # 自动保存 URL 到文件
        url_file = os.path.join(os.path.dirname(report_path), 'cloudflare_url.txt')
        with open(url_file, 'w', encoding='utf-8') as f:
            f.write(url)
        update_task_meta(
            Path(report_path).parent.parent,
            status_text='Step 10.5 完成',
            current_step='Step 10.5',
            outputs=[url_file],
        )
        print(f'[INFO] URL 已保存到: {url_file}')


if __name__ == '__main__':
    main()
