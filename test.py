import requests
import json
import time
import random
import os
import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def load_config():
    config_file = "config.txt"

    if not os.path.exists(config_file):
        print(f"错误: 配置文件 {config_file} 不存在")
        print("请创建 config.txt 文件并添加以下内容:")
        print("ACCESS_TOKEN=你的JWT令牌")
        print("COOKIES=你的Cookies字符串")
        print("SECKILL_ID=秒杀活动ID")
        exit(1)

    config = {}
    with open(config_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

    required_keys = ["ACCESS_TOKEN", "COOKIES", "SECKILL_ID"]
    for key in required_keys:
        if key not in config:
            print(f"错误: 配置文件中缺少 {key}")
            exit(1)

    return config


config = load_config()

# 请求所需的认证信息和Headers
HEADERS = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "content-type": "application/json",
    "origin": "https://hive.xjtlu.edu.cn",
    "referer": "https://hive.xjtlu.edu.cn/pc/pages/student-party/get-room",
    "sec-ch-ua": '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
    "x-access-token": config["ACCESS_TOKEN"],
}

COOKIES = config["COOKIES"]

# 接口URL
GET_ROOM_URL = "https://hive.xjtlu.edu.cn/hive-api/client/seckill/getSeckillRooms"
CONFIRM_URL = "https://hive.xjtlu.edu.cn/hive-api/client/seckill/seckill"

# 请求参数
SECKILL_ID = config["SECKILL_ID"]
# 所有楼层ID列表
FLOOR_IDS = {
    "6F": "1921761822050402306",
    "7F": "1921761824462127105",
    "8F": "1921761824252411906",
    "9F": "1921761823778455553",
    "10F": "1921761823254167553",
}

# 创建日志目录
LOG_DIR = "log"


def setup_session():
    """设置和配置请求会话"""
    session = requests.Session()

    # 设置请求头
    session.headers.update(HEADERS)

    # 设置重试策略
    retry_strategy = Retry(
        total=3,  # 最大重试次数
        backoff_factor=0.5,  # 重试间隔
        status_forcelist=[500, 502, 503, 504],  # 需要重试的HTTP状态码
        allowed_methods=["GET", "POST"],  # 允许重试的请求方法
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # 设置Cookies (直接添加原始cookie字符串)
    session.headers.update({"Cookie": COOKIES})

    return session


def check_environment():
    """检查运行环境"""
    # 检查日志目录
    try:
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
            print(f"已创建日志目录: {LOG_DIR}")

        # 测试写入权限
        test_file = f"{LOG_DIR}/test_write.tmp"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)

    except PermissionError:
        print(f"错误: 没有权限创建或写入日志目录 {LOG_DIR}")
        print("请以管理员权限运行脚本或更改日志目录位置")
        return False
    except Exception as e:
        print(f"初始化日志目录时出错: {str(e)}")
        return False

    return True


def get_room_info(session, floor_id, floor_name):
    """获取特定楼层的房源信息"""
    payload = {"seckillId": SECKILL_ID, "floorId": floor_id}

    try:
        response = session.post(GET_ROOM_URL, json=payload, timeout=10)
        response.raise_for_status()  # 检查HTTP错误
        result = response.json()

        # 将结果写入日志文件
        log_result(floor_name, result)

        return result

    except requests.exceptions.Timeout:
        print(f"查询 {floor_name} 楼层时请求超时")
        return {"success": False, "message": "请求超时", "result": []}

    except requests.exceptions.HTTPError as e:
        print(f"查询 {floor_name} 楼层时HTTP错误: {e}")
        return {"success": False, "message": f"HTTP错误: {str(e)}", "result": []}

    except requests.exceptions.RequestException as e:
        print(f"查询 {floor_name} 楼层时请求错误: {e}")
        return {"success": False, "message": f"请求错误: {str(e)}", "result": []}

    except json.JSONDecodeError:
        print(f"查询 {floor_name} 楼层时返回的不是有效的JSON格式")
        return {"success": False, "message": "返回数据格式错误", "result": []}

    except Exception as e:
        print(f"查询 {floor_name} 楼层时发生未知错误: {str(e)}")
        return {"success": False, "message": f"未知错误: {str(e)}", "result": []}


def log_result(floor_name, result):
    """将查询结果保存到日志文件"""
    try:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{LOG_DIR}/{floor_name}_{current_time}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        print(f"查询结果已保存到: {filename}")
    except Exception as e:
        print(f"保存日志文件时出错: {str(e)}")


def confirm_bed(session, bed_id):
    """提交床位预定请求"""
    payload = {"seckillId": SECKILL_ID, "bedId": bed_id}

    try:
        response = session.post(CONFIRM_URL, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()

        # 将预定结果保存到日志
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{LOG_DIR}/confirm_{bed_id}_{current_time}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        return result

    except Exception as e:
        print(f"预定床位时出错: {str(e)}")
        return {"success": False, "message": f"预定请求错误: {str(e)}"}


def find_available_beds(room_data):
    """查找可用的床位（status=0）"""
    available_beds = []

    if room_data.get("success") and room_data.get("result"):
        for room in room_data["result"]:
            for bed in room["bedList"]:
                if bed["status"] == 0:
                    available_beds.append(
                        {
                            "room": room["roomName"],
                            "building": room["buildingName"],
                            "floor": room["floorName"],
                            "bed_name": bed["name"],
                            "bed_id": bed["id"],
                        }
                    )

    return available_beds


def is_token_expired(token):
    """检查JWT令牌是否过期"""
    import base64
    import json
    import time

    try:
        # 解析JWT中的载荷部分
        payload = token.split(".")[1]
        # 处理填充
        payload += "=" * (4 - len(payload) % 4)
        decoded = base64.b64decode(payload)
        claims = json.loads(decoded)

        # 获取过期时间
        exp_time = claims.get("exp", 0)
        current_time = time.time()

        return current_time > exp_time
    except Exception as e:
        print(f"检查令牌时出错: {str(e)}")
        return False


def main():
    """主函数：实现多楼层抢房流程"""
    print("开始自动抢房脚本...")

    # 检查环境
    if not check_environment():
        print("环境检查失败，脚本终止")
        return

    # 检查令牌是否过期
    token = HEADERS["x-access-token"]
    if is_token_expired(token):
        print("警告：认证令牌已过期，请重新登录获取新令牌！")
        print(
            "1. 打开浏览器访问：https://hive.xjtlu.edu.cn/pc/pages/student-party/get-room"
        )
        print("2. F12打开开发者工具，刷新页面")
        print("3. 查看任意请求的x-access-token值")
        print("4. 更新脚本中的HEADERS变量")
        return

    # 创建请求会话
    session = setup_session()

    attempt_count = 0
    request_count = 0

    while True:
        attempt_count += 1

        # 每100次请求后暂停一段时间，避免被判定为攻击
        if request_count >= 100:
            pause_time = random.uniform(20, 30)
            print(f"已发送大量请求，暂停 {pause_time:.2f} 秒...")
            time.sleep(pause_time)
            request_count = 0

        # 1. 随机等待8-12秒
        wait_time = random.uniform(8, 12)
        print(f"第 {attempt_count} 次尝试，等待 {wait_time:.2f} 秒...")
        time.sleep(wait_time)

        # 循环查询每个楼层
        has_available_bed = False
        for floor_name, floor_id in FLOOR_IDS.items():
            print(f"正在查询 {floor_name} 楼层...")

            # 2. 获取房源信息
            room_data = get_room_info(session, floor_id, floor_name)
            request_count += 1

            available_beds = find_available_beds(room_data)

            # 检查是否有可用床位
            if not available_beds:
                print(f"{floor_name} 楼层当前没有可用床位")
            else:
                has_available_bed = True

                # 3. 发现有可用床位，尝试预定
                for bed in available_beds:
                    print(
                        f"发现可用床位: {bed['building']} {bed['floor']} {bed['room']} 床位{bed['bed_name']}"
                    )

                    # 尝试预定两次，间隔1200ms
                    for i in range(2):
                        print(f"第 {i + 1} 次尝试预定...")
                        confirm_result = confirm_bed(session, bed["bed_id"])
                        request_count += 1

                        if confirm_result.get("success"):
                            print("恭喜！抢房成功！")
                            print(
                                f"成功预定: {bed['building']} {bed['floor']} {bed['room']} 床位{bed['bed_name']}"
                            )
                            return  # 成功预定，退出程序
                        else:
                            print(
                                f"预定失败: {confirm_result.get('message', '未知错误')}"
                            )

                        # 等待1200ms后再次尝试
                        if i == 0:  # 只在第一次尝试后等待
                            time.sleep(1.2)

            # 在楼层之间添加200-350ms的随机延迟
            floor_delay = random.uniform(0.2, 0.35)
            time.sleep(floor_delay)

        # 4. 所有楼层都没有可用床位或尝试失败，继续循环
        if not has_available_bed:
            print("所有楼层当前没有可用床位，继续等待...")


if __name__ == "__main__":
    main()
