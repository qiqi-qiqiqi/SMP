import json
import time
import random
import ssl
from datetime import datetime
import paho.mqtt.client as mqtt

# ========== 华为云MQTT连接参数 ==========
CONFIG = {
    "username": "6a50aec2cbb0cf6bb96dc3dc_1234",
    "password": "aa2b5c56eda497169650fb75ef755e64f13f6f5036a1b9b7bed267c51544e81a",
    "clientId": "6a50aec2cbb0cf6bb96dc3dc_1234_0_0_2026071008",
    "hostname": "e201e15730.st1.iotda-device.cn-north-4.myhuaweicloud.com",
    "port": 8883,
    "protocol": "MQTTS"
}

# 设备ID
DEVICE_ID = CONFIG["username"].split("_")[0]

# 属性上报 topic
TOPIC_PROPERTY_REPORT = f"$oc/devices/{DEVICE_ID}/sys/properties/report"

# 服务ID（需与华为云产品模型一致）
SERVICE_ID = "1234"

# 上报间隔（秒）
REPORT_INTERVAL = 5

# ========== MQTT回调 ==========
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ 华为云MQTT连接成功")
    else:
        print(f"❌ 连接失败，返回码：{rc}")

def on_publish(client, userdata, mid):
    print(f"📤 数据上报成功 (mid={mid})")

def on_disconnect(client, userdata, rc):
    print("🔌 连接断开")
    if rc != 0:
        print("⚠️ 异常断开，尝试重连...")

# ========== 虚拟数据生成 ==========
# 随机英文名列表
NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]
DOOR_ACTIONS = ["open", "close"]

def get_virtual_data():
    """生成所有属性的虚拟数据"""
    temperature = round(random.uniform(20.0, 30.0), 1)      # 小数
    humidity = round(random.uniform(40.0, 70.0), 1)         # 小数
    beep = random.choice([0, 1])                            # 整型
    relay = random.choice([0, 1])                           # 整型
    rain = random.choice([0, 1])                            # 整型
    # person: "人名-动作-时间" 英文字符串
    name = random.choice(NAMES)
    action = random.choice(DOOR_ACTIONS)
    now = datetime.now().strftime("%H:%M:%S")               # 例如 14:30:05
    person = f"{name}-{action}-{now}"
    return temperature, humidity, beep, relay, rain, person

# ========== 构造上报消息 ==========
def build_payload(temp, humi, beep, relay, rain, person):
    payload = {
        "services": [
            {
                "service_id": SERVICE_ID,
                "properties": {
                    "temp": temp,
                    "humi": humi,
                    "beep": beep,
                    "relay": relay,
                    "rain": rain,
                    "person": person
                }
            }
        ]
    }
    return json.dumps(payload)

# ========== 主程序 ==========
def main():
    client = mqtt.Client(client_id=CONFIG["clientId"])
    client.username_pw_set(CONFIG["username"], CONFIG["password"])

    # MQTTS TLS 配置
    client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                   cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    # client.tls_insecure_set(True)  # 若证书问题临时测试可取消注释

    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_disconnect = on_disconnect

    print("正在连接华为云IoT平台...")
    try:
        client.connect(CONFIG["hostname"], CONFIG["port"], keepalive=60)
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        return

    client.loop_start()

    try:
        while True:
            temp, humi, beep, relay, rain, person = get_virtual_data()
            payload = build_payload(temp, humi, beep, relay, rain, person)
            print(f"上报 -> 温度:{temp}°C 湿度:{humi}% 蜂鸣器:{beep} 继电器:{relay} 雨滴:{rain} 人员:{person}")
            client.publish(TOPIC_PROPERTY_REPORT, payload, qos=1)
            time.sleep(REPORT_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 程序手动停止")
    finally:
        client.loop_stop()
        client.disconnect()
        print("已断开连接")

if __name__ == "__main__":
    main()