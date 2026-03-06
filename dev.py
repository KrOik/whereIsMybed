import requests
import json
import time
import random
import os
import datetime


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
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


def get_room_info(floor_id, floor_name):
    """获取特定楼层的房源信息"""
    payload = {"seckillId": SECKILL_ID, "floorId": floor_id}

    response = requests.post(
        GET_ROOM_URL, headers=HEADERS, cookies={"cookie": COOKIES}, json=payload
    )
    result = response.json()

    # 将结果写入日志文件
    log_result(floor_name, result)

    return result


def log_result(floor_name, result):
    """将查询结果保存到日志文件"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{LOG_DIR}/{floor_name}_{current_time}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print(f"查询结果已保存到: {filename}")


def confirm_bed(bed_id):
    """提交床位预定请求"""
    payload = {"seckillId": SECKILL_ID, "bedId": bed_id}

    response = requests.post(
        CONFIRM_URL, headers=HEADERS, cookies={"cookie": COOKIES}, json=payload
    )
    result = response.json()

    # 将预定结果保存到日志
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{LOG_DIR}/confirm_{bed_id}_{current_time}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    return result


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


def main():
    """主函数：实现多楼层抢房流程"""
    print("开始自动抢房脚本...")

    attempt_count = 0
    while True:
        attempt_count += 1

        # 1. 随机等待4-8秒
        wait_time = random.uniform(4, 8)
        print(f"第 {attempt_count} 次尝试，等待 {wait_time:.2f} 秒...")
        time.sleep(wait_time)

        # 循环查询每个楼层
        has_available_bed = False
        for floor_name, floor_id in FLOOR_IDS.items():
            print(f"正在查询 {floor_name} 楼层...")

            try:
                # 2. 获取房源信息
                room_data = get_room_info(floor_id, floor_name)
                available_beds = find_available_beds(room_data)

                # 检查是否有可用床位
                if not available_beds:
                    print(f"{floor_name} 楼层当前没有可用床位")
                    continue

                has_available_bed = True

                # 3. 发现有可用床位，尝试预定
                for bed in available_beds:
                    print(
                        f"发现可用床位: {bed['building']} {bed['floor']} {bed['room']} 床位{bed['bed_name']}"
                    )

                    # 尝试预定两次，间隔200ms
                    for i in range(2):
                        try:
                            print(f"第 {i + 1} 次尝试预定...")
                            confirm_result = confirm_bed(bed["bed_id"])

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

                            # 等待200ms后再次尝试
                            if i == 0:  # 只在第一次尝试后等待
                                time.sleep(0.2)

                        except Exception as e:
                            print(f"预定过程中出错: {str(e)}")

            except Exception as e:
                print(f"查询 {floor_name} 楼层过程中出错: {str(e)}")
                print("1秒后继续下一个楼层...")
                time.sleep(1)

        # 4. 所有楼层都没有可用床位或尝试失败，继续循环
        if not has_available_bed:
            print("所有楼层当前没有可用床位，继续等待...")


if __name__ == "__main__":
    main()
