# -*- coding: utf-8 -*-
"""
Upload report assets to Cloudflare R2 and rewrite Markdown image links.

Usage:
    python scripts/upload_report_assets_to_r2.py <taskId> [taskDir]

Required environment variables:
    R2_ACCOUNT_ID
    R2_ACCESS_KEY_ID
    R2_SECRET_ACCESS_KEY
    R2_BUCKET_NAME or R2_BUCKET
    R2_PUBLIC_DOMAIN

Optional environment variables:
    R2_ASSET_PREFIX  default: img
"""

from __future__ import annotations

import mimetypes
import os
import re
import sys
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv

from task_paths import ensure_task_dir, resolve_task_dir

load_dotenv()


IMAGE_LINK_RE = re.compile(r"!\[([^\]]*)\]\((assets/[^)]+)\)")


def _env(name: str, fallback: str = "") -> str:
    return os.environ.get(name, fallback).strip()


def _r2_config() -> dict[str, str]:
    return {
        "account_id": _env("R2_ACCOUNT_ID"),
        "access_key_id": _env("R2_ACCESS_KEY_ID"),
        "secret_access_key": _env("R2_SECRET_ACCESS_KEY"),
        "bucket_name": _env("R2_BUCKET_NAME") or _env("R2_BUCKET"),
        "public_domain": _env("R2_PUBLIC_DOMAIN"),
        "asset_prefix": (_env("R2_ASSET_PREFIX", "img") or "img").strip("/"),
    }


def _require_config(config: dict[str, str]) -> None:
    missing = [
        key
        for key in ("account_id", "access_key_id", "secret_access_key", "bucket_name", "public_domain")
        if not config[key]
    ]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing R2 config: {names}")


def _client(config: dict[str, str]):
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError("Please install boto3 first: pip install boto3") from exc

    return boto3.client(
        service_name="s3",
        endpoint_url=f"https://{config['account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=config["access_key_id"],
        aws_secret_access_key=config["secret_access_key"],
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def _content_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if path.suffix.lower() == ".svg":
        return "image/svg+xml; charset=utf-8"
    return guessed or "application/octet-stream"


def _asset_url(config: dict[str, str], object_key: str) -> str:
    domain = config["public_domain"].rstrip("/")
    return f"{domain}/{urllib.parse.quote(object_key, safe='/')}"


def upload_assets(task_id: str, task_dir: Path) -> dict[str, str]:
    config = _r2_config()
    _require_config(config)

    assets_dir = task_dir / "output" / "assets"
    if not assets_dir.exists():
        raise RuntimeError(f"Assets directory not found: {assets_dir}")

    assets = sorted(path for path in assets_dir.iterdir() if path.is_file())
    if not assets:
        raise RuntimeError(f"No assets found in: {assets_dir}")

    s3 = _client(config)
    urls: dict[str, str] = {}

    for path in assets:
        object_key = f"{config['asset_prefix']}/{task_id}/{path.name}"
        s3.put_object(
            Body=path.read_bytes(),
            Bucket=config["bucket_name"],
            Key=object_key,
            ContentType=_content_type(path),
        )
        urls[f"assets/{path.name}"] = _asset_url(config, object_key)

    return urls


def rewrite_markdown(task_id: str, task_dir: Path, urls: dict[str, str]) -> Path:
    output_dir = task_dir / "output"
    markdown_path = output_dir / f"新品上架全案_{task_id}.md"
    if not markdown_path.exists():
        candidates = sorted(output_dir.glob("新品上架全案_*.md"))
        if not candidates:
            raise RuntimeError(f"Markdown report not found in: {output_dir}")
        markdown_path = candidates[-1]

    text = markdown_path.read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        alt, asset_path = match.group(1), match.group(2)
        return f"![{alt}]({urls.get(asset_path, asset_path)})"

    new_text = IMAGE_LINK_RE.sub(replace, text)
    markdown_path.write_text(new_text, encoding="utf-8", newline="\n")

    url_map_path = output_dir / "r2_asset_urls.txt"
    url_map_path.write_text(
        "\n".join(f"{local}\t{remote}" for local, remote in sorted(urls.items())) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return markdown_path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/upload_report_assets_to_r2.py <taskId> [taskDir]", file=sys.stderr)
        return 2

    task_id = sys.argv[1]
    task_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else ensure_task_dir(task_id)
    task_dir = resolve_task_dir(task_id) if str(task_dir) == task_id else task_dir

    urls = upload_assets(task_id, task_dir)
    markdown_path = rewrite_markdown(task_id, task_dir, urls)

    print(f"Uploaded {len(urls)} assets.")
    print(f"Updated Markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
