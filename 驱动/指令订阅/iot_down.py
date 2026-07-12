#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为云IoT智慧门禁 - 树莓派端（OLED显示）
功能：订阅命令Topic，接收beep/relay命令并更新OLED显示开关状态
"""

import json
from paho.mqtt import client as mqtt_client
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# ==================== 华为云MQTT配置 ====================
DEVICE_ID = "6a50aec2cbb0cf6bb96dc3dc_1234"
USERNAME = "6a50aec2cbb0cf6bb96dc3dc_1234"
PASSWORD = "b051a0a8ad08504f1122a589d1a8b40d95f0a7253cbaf6eec13c92d7c970b68a"
CLIENT_ID = "6a50aec2cbb0cf6bb96dc3dc_1234_0_0_2026071010"
MQTT_HOST = "e201e15730.st1.iotda-device.cn-north-4.myhuaweicloud.com"
MQTT_PORT = 8883

COMMAND_TOPIC = f"$oc/devices/{DEVICE_ID}/sys/commands/#"
RESPONSE_TOPIC_TEMPLATE = f"$oc/devices/{DEVICE_ID}/sys/commands/response/"
PROPERTIES_SET_TOPIC = f"$oc/devices/{DEVICE_ID}/sys/properties/set"

# ==================== OLED 初始化 ====================
I2C_PORT = 1
OLED_ADDRESS = 0x3C

serial = i2c(port=I2C_PORT, address=OLED_ADDRESS)
device = ssd1306(serial)
font = ImageFont.load_default()

# 设备状态（初始关闭）
beep_state = 0
relay_state = 0

def update_oled():
    """刷新OLED显示蜂鸣器和继电器状态"""
    beep_text = "ON" if beep_state == 1 else "OFF"
    relay_text = "ON" if relay_state == 1 else "OFF"

    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="black")
        draw.text((10, 10), "Smart Door", fill="white", font=font)
        draw.text((10, 25), f"Buzzer: {beep_text}", fill="white", font=font)
        draw.text((10, 40), f"Relay : {relay_text}", fill="white", font=font)

# 首次清屏并显示初始状态
device.clear()
update_oled()

# ==================== MQTT回调 ====================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[OK] 设备 {DEVICE_ID} 连接成功")
        client.subscribe(COMMAND_TOPIC, qos=1)
        print(f"[SUB] 已订阅命令Topic: {COMMAND_TOPIC}")
        client.subscribe(PROPERTIES_SET_TOPIC, qos=1)
        print(f"[SUB] 已订阅属性设置Topic: {PROPERTIES_SET_TOPIC}")
    else:
        print(f"[ERR] 连接失败，错误码: {rc}")

def on_message(client, userdata, msg):
    global beep_state, relay_state
    topic = msg.topic
    payload = msg.payload.decode('utf-8')

    print(f"\n[MSG] 收到消息: {topic}")
    print(f"   内容: {payload}")

    try:
        if "commands" in topic:
            handle_command(client, topic, payload)
        elif "properties/set" in topic:
            handle_properties_set(client, topic, payload)
    except Exception as e:
        print(f"[ERR] 处理消息失败: {e}")

def handle_command(client, topic, payload):
    global beep_state, relay_state

    # 提取请求ID
    topic_parts = topic.split('/')
    request_id = ""
    for part in topic_parts:
        if part.startswith('request_id='):
            request_id = part.split('=')[1]
            break
    if not request_id:
        request_id = topic_parts[-1]

    data = json.loads(payload)
    command_name = data.get('command_name', '')
    paras = data.get('paras', {})

    print(f"   命令: {command_name}, 参数: {paras}")

    # 更新状态
    if command_name == "beep":
        beep_state = paras.get('beep', 0)
        print(f"[BEEP] 蜂鸣器 -> {'ON' if beep_state else 'OFF'}")
    elif command_name == "relay":
        relay_state = paras.get('relay', 0)
        print(f"[RELAY] 继电器 -> {'ON' if relay_state else 'OFF'}")

    # 刷新OLED
    update_oled()

    # 构造响应
    response = {
        "result_code": 0,
        "result_desc": "success"
    }
    response_topic = f"{RESPONSE_TOPIC_TEMPLATE}request_id={request_id}"
    client.publish(response_topic, json.dumps(response), qos=1)
    print(f"[RSP] 已回复命令响应")

def handle_properties_set(client, topic, payload):
    global beep_state, relay_state

    data = json.loads(payload)
    print(f"[PROP] 收到属性设置")

    if 'services' in data:
        for service in data['services']:
            properties = service.get('properties', {})
            for prop_name, prop_value in properties.items():
                if prop_name == 'beep':
                    beep_state = prop_value
                    print(f"[BEEP] 状态更新 -> {'ON' if beep_state else 'OFF'}")
                elif prop_name == 'relay':
                    relay_state = prop_value
                    print(f"[RELAY] 状态更新 -> {'ON' if relay_state else 'OFF'}")
                else:
                    print(f"[INFO] 忽略属性: {prop_name} = {prop_value}")

        # 刷新OLED
        update_oled()

    # 回复属性设置响应
    response_topic = f"$oc/devices/{DEVICE_ID}/sys/properties/set/response"
    response = {"result_code": 0, "result_desc": "success"}
    client.publish(response_topic, json.dumps(response), qos=1)
    print("[RSP] 属性设置响应已发送")

# ==================== MQTT连接 ====================
def connect_mqtt():
    client = mqtt_client.Client(client_id=CLIENT_ID, protocol=mqtt_client.MQTTv311)
    client.tls_set()
    client.username_pw_set(USERNAME, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[CONN] 正在连接华为云IoT平台...")
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        return client
    except Exception as e:
        print(f"[ERR] 连接失败: {e}")
        return None

# ==================== 主程序 ====================
def main():
    print("========================================")
    print("  华为云IoT门禁 - 树莓派OLED显示")
    print("  订阅命令，显示蜂鸣器/继电器状态")
    print("========================================")

    client = connect_mqtt()
    if not client:
        return

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n👋 退出程序...")
        client.disconnect()
        device.clear()
        print("✅ 已断开连接，OLED已清屏")

if __name__ == "__main__":
    main()