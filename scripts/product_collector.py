import json
import os
import time
import uuid
import requests

from dotenv import load_dotenv
load_dotenv()

DOWNLOAD_RETRIES   = 3     # 下载结果最大重试次数（网络问题单独重试）
RETRY_DELAY_SEC    = 10.0  # 重试前等待时间（秒）
DOWNLOAD_RETRY_DELAY = 5.0 # 下载重试间隔（秒）
BETWEEN_JOBS_SEC   = 6.0   # 两个商品之间强制间隔（秒）
POLL_INTERVAL_SEC  = 10.0  # 影刀任务状态轮询间隔（秒）
JOB_TIMEOUT_MIN    = 10    # 单任务最长等待时间（分钟）


def _require_yingdao_config() -> tuple[str, str, str, str]:
    """Read and validate the Yingdao credentials only when the collector is used."""

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


def _read_json_response(response: requests.Response) -> dict:
    """Return a validated JSON payload from an HTTP response."""

    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("影刀接口返回了非字典 JSON")
    return data

def get_accesstoken()-> str:
    """获取凭证

    Returns:
        str: accessToken
        
    """
    base_url = 'https://api.yingdao.com/oapi/token/v2/token/create'
    access_key_id, access_key_secret, _, _ = _require_yingdao_config()

    params ={
        "accessKeyId":access_key_id,
        "accessKeySecret":access_key_secret,
        }

    response = requests.get(url=base_url, params=params, timeout=30)
    payload = _read_json_response(response)
    try:
        return payload['data']['accessToken']
    except KeyError as exc:
        raise RuntimeError(f"获取 accessToken 失败，响应缺少字段: {payload}") from exc


def run_application(accessToken,query_data)-> str:
    """启动应用

    Args:
        accessToken (_type_): _description_
        query_data (_type_): 商品链接/商品ID

    Returns:
        str: 应用运行uuid
    """
    _, _, account_name, robot_uuid = _require_yingdao_config()

    url = 'https://api.yingdao.com/oapi/dispatch/v2/job/start'
    headers = {
        "Authorization": f"Bearer {accessToken}",
        "Content-Type": "application/json"
    }

    body ={
        "accountName": account_name,
        "robotUuid": robot_uuid, 
        "idempotentUuid":str(uuid.uuid4()),
        "waitTimeout":"10m",
        "executeScope":"any",
        "priority": "middle", 
        "params":[
                {
                "name":"商品链接", 
                "value":query_data,
                "type":"str" 
                }
        ]
    }

    response = requests.post(url=url, headers=headers, json=body, timeout=30)
    payload = _read_json_response(response)
    print(payload)
    try:
        return payload['data']['jobUuid']
    except KeyError as exc:
        raise RuntimeError(f"启动影刀任务失败，响应缺少字段: {payload}") from exc


    

def query_applicaton_status(accessToken,jobUuid)-> str:
    url = 'https://api.yingdao.com/oapi/dispatch/v2/job/query'
    headers = {
        "Authorization": f"Bearer {accessToken}",
        "Content-Type": "application/json"
    }

    body ={
        "jobUuid": jobUuid
    }
    response = requests.post(url=url, headers=headers, json=body, timeout=30)
    payload = _read_json_response(response)
    try:
        return payload['data']
    except KeyError as exc:
        raise RuntimeError(f"查询影刀任务失败，响应缺少字段: {payload}") from exc
    

def download_json_from_url(url: str, timeout: int = 60) -> str:
    """从下载链接获取 JSON 内容（单次下载，无重试）

    Args:
        url: JSON 文件下载链接
        timeout: 下载超时时间（秒）

    Returns:
        str: JSON 字符串内容

    Raises:
        RuntimeError: 下载失败
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        # 验证是否为有效 JSON
        json.loads(response.text)
        return response.text
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"下载 JSON 文件失败: {e}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"下载内容不是有效 JSON: {e}")


def download_with_retry(download_url: str, max_retries: int = DOWNLOAD_RETRIES) -> str:
    """下载采集结果，支持独立重试（影刀任务已成功，只重试下载）

    Args:
        download_url: JSON 文件下载链接
        max_retries: 最大重试次数

    Returns:
        str: JSON 字符串内容

    Raises:
        RuntimeError: 达到重试上限仍下载失败
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[DOWNLOAD] 尝试下载 (第{attempt}/{max_retries}次)...", flush=True)
            json_content = download_json_from_url(download_url)
            print(f"[DOWNLOAD] 下载成功", flush=True)
            return json_content
        except Exception as e:
            last_error = e
            print(f"[DOWNLOAD] 第{attempt}次下载失败: {e}", flush=True)
            if attempt < max_retries:
                print(f"[DOWNLOAD] 等待 {DOWNLOAD_RETRY_DELAY} 秒后重试...", flush=True)
                time.sleep(DOWNLOAD_RETRY_DELAY)

    raise RuntimeError(f"下载失败，已重试 {max_retries} 次。最后错误：{last_error}")


def run_yingdao_job(goods: str) -> str:
    """执行影刀采集任务，返回下载链接（不下载结果）

    Args:
        goods: 商品链接或商品ID

    Returns:
        str: JSON 文件下载链接

    Raises:
        RuntimeError: 影刀任务执行失败或超时
    """
    access_token = get_accesstoken()
    job_uuid = run_application(access_token, goods)

    deadline = time.time() + JOB_TIMEOUT_MIN * 60
    while time.time() < deadline:
        result_data = query_applicaton_status(access_token, job_uuid)
        status = result_data["statusName"]

        if status == "完成":
            # 安全获取 outputs
            robot_params = result_data.get("robotParams", {})
            outputs = robot_params.get("outputs", [])

            if not outputs:
                raise RuntimeError("影刀返回的 outputs 为空")

            download_url = outputs[0].get("value")
            if not download_url:
                raise RuntimeError("影刀返回的下载链接为空")

            return download_url

        elif status == "异常":
            raise RuntimeError(f"影刀任务异常：{result_data}")

        time.sleep(POLL_INTERVAL_SEC)

    raise TimeoutError(f"任务超时，已等待 {JOB_TIMEOUT_MIN} 分钟")


def run(goods: str) -> str:
    """
    调用影刀采集单个商品数据。
    分离影刀任务执行和结果下载，下载失败可独立重试，不重新执行影刀任务。

    Returns:
        str: JSON 字符串
    Raises:
        RuntimeError: 达到重试上限或超时
    """
    last_error = None
    download_url = None

    try:
        # 第一步：执行影刀任务（只执行一次，失败才重试）
        print(f"[YINGDAO] 启动影刀任务...", flush=True)
        download_url = run_yingdao_job(goods)
        print(f"[YINGDAO] 影刀任务完成，获取下载链接", flush=True)

        # 第二步：下载结果（独立重试，不重新执行影刀任务）
        # 下载失败会抛出异常，被外层捕获后决定是否重试整个流程
        json_content = download_with_retry(download_url)
        return json_content

    except Exception as e:
        last_error = e
         # 失败后等待一段时间，给影刀服务恢复时间
        time.sleep(RETRY_DELAY_SEC)
           
    raise RuntimeError(f"采集失败：{last_error}")



def run_batch(goods_list: list, output_dir: str = None, reset_log: bool = True, attempt_label: str = "initial") -> dict:
    """
    批量采集入口。每个商品之间强制间隔 BETWEEN_JOBS_SEC 秒。
    调用方不得绕过此函数直接循环调用 run()。
    采集完成后立即写盘，验证 JSON 合法性，返回写入状态。

    Args:
        goods_list: [(品牌名, 商品链接), ...]
        output_dir: 输出文件目录，默认为脚本所在目录下的 raw/
        reset_log: 是否在本轮开始前清空错误日志
        attempt_label: 当前采集轮次标识
    Returns:
        dict: {品牌名: {"status": "success"/"failed", "file": "路径" or None, "error": None or "错误信息"}}
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")

    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "collection_errors.log")
    if reset_log and os.path.exists(log_path):
        os.remove(log_path)

    results = {}
    for i, (brand, url) in enumerate(goods_list):
        file_path = os.path.join(output_dir, f"{brand}.json")
        try:
            # 1. 采集数据
            json_content = run(url)

            # 2. 验证 JSON 合法性（二次确认）
            try:
                json.loads(json_content)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON 验证失败: {e}")

            # 3. 原子写入 + 强制同步，解决文件系统延迟问题
            temp_path = file_path + ".tmp"
            try:
                # 先写入临时文件
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(json_content)
                    f.flush()                      # 刷新 Python 缓冲区
                    os.fsync(f.fileno())           # 强制同步到操作系统磁盘
                
                # 原子重命名（确保文件完整性）
                # os.replace() 是原子操作，在 Windows 上会覆盖已存在的目标文件
                os.replace(temp_path, file_path)
                
                # 再次同步目录元数据（某些文件系统需要）
                # 注意：os.O_DIRECTORY 是 Linux 专用，Windows 不支持
                import platform
                if platform.system() != 'Windows':
                    dir_fd = os.open(output_dir, os.O_RDONLY | os.O_DIRECTORY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                    
            except Exception as e:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise RuntimeError(f"文件写入失败: {e}")

            # 4. 重试验证机制，解决文件系统延迟可见性问题
            max_verify_retries = 5
            verify_delay = 2  # 2秒
            file_verified = False
            
            for retry in range(max_verify_retries):
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    # 额外验证：尝试读取并解析 JSON
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            verify_content = f.read()
                            json.loads(verify_content)  # 验证可读且合法
                        file_verified = True
                        if retry > 0:
                            print(f"[DEBUG] {brand} 文件验证成功（第{retry+1}次重试）", flush=True)
                        break
                    except Exception as e:
                        print(f"[DEBUG] {brand} 文件验证失败（第{retry+1}次）: {e}", flush=True)
                
                if retry < max_verify_retries - 1:
                    time.sleep(verify_delay)
            
            if not file_verified:
                raise RuntimeError(f"文件写入验证失败（重试{max_verify_retries}次）: {file_path}")

            # 5. 返回写入状态而非原始数据
            results[brand] = {
                "status": "success",
                "file": file_path,
                "size": os.path.getsize(file_path),
                "error": None
            }
            print(f"[SUCCESS] {brand} -> {file_path} ({os.path.getsize(file_path)} bytes)", flush=True)

        except Exception as e:
            # 失败记录写入日志，不中断批量任务
            error_msg = str(e)
            results[brand] = {
                "status": "failed",
                "file": None,
                "size": 0,
                "error": error_msg
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{attempt_label}] [FAILED] {brand} | {url} | {error_msg}\n")
            print(f"[FAILED][{attempt_label}] {brand}: {error_msg}", flush=True)

        # 最后一个商品不需要等待
        if i < len(goods_list) - 1:
            time.sleep(BETWEEN_JOBS_SEC)

    # 6. 【新增】汇总报告
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    failed_count = len(results) - success_count
    print(f"[BATCH_COMPLETE] 成功: {success_count}, 失败: {failed_count}", flush=True)

    return results

if __name__ == "__main__":
    # 测试 run_batch 函数
    print(get_accesstoken())
    # goods_list = [
    #     ('self', 'https://detail.tmall.com/item.htm?id=766442618180'),
    #     ('p1', 'https://detail.tmall.com/item.htm?id=827012431671'),
    #     ('p2', 'https://detail.tmall.com/item.htm?id=895417183717'),
    #     ('p3', 'https://detail.tmall.com/item.htm?id=899979299425'),
    # ]
    # results = run_batch(goods_list)
    # print("\n=== 最终结果 ===")
    # for brand, result in results.items():
    #     print(f"{brand}: {result}")
    pass
