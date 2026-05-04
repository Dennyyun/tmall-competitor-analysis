import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def load_module(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RegressionTests(unittest.TestCase):
    def test_product_collector_import_without_env(self):
        original = {key: os.environ.get(key) for key in (
            "YINGDAO_ACCESS_KEY_ID",
            "YINGDAO_ACCESS_KEY_SECRET",
            "YINGDAO_ACCOUNT_NAME",
            "YINGDAO_ROBOT_UUID",
        )}
        try:
            for key in original:
                os.environ[key] = ""

            module = load_module("product_collector_test", "product_collector.py")
            self.assertTrue(hasattr(module, "run_batch"))
            with self.assertRaises(RuntimeError):
                module._require_yingdao_config()
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_check_yingdao_import_without_env(self):
        original = {key: os.environ.get(key) for key in (
            "YINGDAO_ACCESS_KEY_ID",
            "YINGDAO_ACCESS_KEY_SECRET",
            "YINGDAO_ACCOUNT_NAME",
            "YINGDAO_ROBOT_UUID",
        )}
        try:
            for key in original:
                os.environ[key] = ""

            module = load_module("check_yingdao_test", "check_yingdao.py")
            self.assertTrue(hasattr(module, "get_token"))
            with self.assertRaises(RuntimeError):
                module.require_config()
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_generate_raw_md_json_preview_is_valid(self):
        module = load_module("generate_raw_md_test", "generate_raw_md.py")
        raw_data = {
            "商品标题": "测试商品",
            "feedback": "x" * 5000,
            "商品主图": [f"https://example.com/{i}.jpg" for i in range(10)],
            "nested": {"long": "y" * 5000, "items": list(range(20))},
        }

        preview = module.build_json_preview(raw_data, max_length=600)
        parsed = json.loads(preview)

        self.assertIn("preview", parsed)
        self.assertIn("_note", parsed)

    def test_upload_to_cloudflare_uses_ascii_object_key(self):
        module = load_module("upload_to_cloudflare_test", "upload_to_cloudflare.py")

        class FakeS3:
            def __init__(self):
                self.key = None

            def put_object(self, **kwargs):
                self.key = kwargs["Key"]

        fake_s3 = FakeS3()

        class FakeBoto3:
            @staticmethod
            def client(**kwargs):
                return fake_s3

        class FakeConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        botocore_module = type(sys)("botocore")
        config_module = type(sys)("botocore.config")
        config_module.Config = FakeConfig
        boto3_module = type(sys)("boto3")
        boto3_module.client = FakeBoto3.client

        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = Path(tmp_dir) / "report.html"
            report_path.write_text("<html></html>", encoding="utf-8")

            old_modules = {
                "boto3": sys.modules.get("boto3"),
                "botocore": sys.modules.get("botocore"),
                "botocore.config": sys.modules.get("botocore.config"),
            }
            old_env = {key: os.environ.get(key) for key in (
                "R2_ACCOUNT_ID",
                "R2_ACCESS_KEY_ID",
                "R2_SECRET_ACCESS_KEY",
            )}

            try:
                sys.modules["boto3"] = boto3_module
                sys.modules["botocore"] = botocore_module
                sys.modules["botocore.config"] = config_module
                os.environ["R2_ACCOUNT_ID"] = "acct"
                os.environ["R2_ACCESS_KEY_ID"] = "key"
                os.environ["R2_SECRET_ACCESS_KEY"] = "secret"
                module.R2_ACCOUNT_ID = "acct"
                module.R2_ACCESS_KEY_ID = "key"
                module.R2_SECRET_ACCESS_KEY = "secret"
                module.R2_PUBLIC_DOMAIN = ""

                url = module.upload_report("task-1", str(report_path))

                self.assertIn("reports/task-1/", fake_s3.key)
                self.assertNotIn("报表数据", fake_s3.key)
                self.assertIn("reports/task-1/", url)
            finally:
                for key, value in old_modules.items():
                    if value is None:
                        sys.modules.pop(key, None)
                    else:
                        sys.modules[key] = value
                for key, value in old_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
