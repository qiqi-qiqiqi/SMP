import json
import ssl
import time
from datetime import datetime
import paho.mqtt.client as mqtt
from config import MQTT_CONFIG, DEVICE_ID, SERVICE_ID, REPORT_INTERVAL, MOCK_MODE

TOPIC_PROPERTY_REPORT = f"$oc/devices/{DEVICE_ID}/sys/properties/report"
TOPIC_COMMAND = f"$oc/devices/{DEVICE_ID}/sys/commands/#"
TOPIC_PROPERTIES_SET = f"$oc/devices/{DEVICE_ID}/sys/properties/set"
TOPIC_RESPONSE_TEMPLATE = f"$oc/devices/{DEVICE_ID}/sys/commands/response/"


class MQTTClient:
    def __init__(self, sensors=None, on_command_received=None):
        self.sensors = sensors
        self.on_command_received = on_command_received
        self.client = None
        self.connected = False
        self.report_timer = None
        self.last_door_event = {"person": "Unknown", "time": "", "action": "close"}

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print("✅ 华为云MQTT连接成功")
            client.subscribe(TOPIC_COMMAND, qos=1)
            print(f"[SUB] 已订阅命令Topic: {TOPIC_COMMAND}")
            client.subscribe(TOPIC_PROPERTIES_SET, qos=1)
            print(f"[SUB] 已订阅属性设置Topic: {TOPIC_PROPERTIES_SET}")
            self.start_report_loop()
        else:
            self.connected = False
            print(f"❌ 连接失败，错误码: {rc}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        print("🔌 连接断开")
        if rc != 0:
            print("⚠️ 异常断开，尝试重连...")
            self.reconnect()

    def on_publish(self, client, userdata, mid):
        print(f"📤 数据上报成功 (mid={mid})")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        print(f"\n[MSG] 收到消息: {topic}")
        print(f"   内容: {payload}")

        try:
            if "commands" in topic:
                self.handle_command(topic, payload)
            elif "properties/set" in topic:
                self.handle_properties_set(topic, payload)
        except Exception as e:
            print(f"[ERR] 处理消息失败: {e}")

    def handle_command(self, topic, payload):
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

        result_code = 0
        result_desc = "success"

        if command_name == "beep":
            beep_state = paras.get('beep', 0)
            if self.sensors:
                self.sensors.set_buzzer(bool(beep_state))
            print(f"[BEEP] 蜂鸣器 -> {'ON' if beep_state else 'OFF'}")
        elif command_name == "relay":
            relay_state = paras.get('relay', 0)
            if self.sensors:
                self.sensors.set_relay(bool(relay_state))
            print(f"[RELAY] 继电器 -> {'ON' if relay_state else 'OFF'}")
        else:
            result_desc = f"unknown command: {command_name}"

        if self.on_command_received:
            try:
                self.on_command_received(command_name, paras)
            except Exception as e:
                print(f"[ERR] 命令回调失败: {e}")

        response = {
            "result_code": result_code,
            "result_desc": result_desc
        }
        response_topic = f"{TOPIC_RESPONSE_TEMPLATE}request_id={request_id}"
        self.client.publish(response_topic, json.dumps(response), qos=1)
        print(f"[RSP] 已回复命令响应")

    def handle_properties_set(self, topic, payload):
        data = json.loads(payload)
        print(f"[PROP] 收到属性设置")

        if 'services' in data:
            for service in data['services']:
                properties = service.get('properties', {})
                for prop_name, prop_value in properties.items():
                    if prop_name == 'beep':
                        if self.sensors:
                            self.sensors.set_buzzer(bool(prop_value))
                        print(f"[BEEP] 状态更新 -> {'ON' if prop_value else 'OFF'}")
                    elif prop_name == 'relay':
                        if self.sensors:
                            self.sensors.set_relay(bool(prop_value))
                        print(f"[RELAY] 状态更新 -> {'ON' if prop_value else 'OFF'}")
                    else:
                        print(f"[INFO] 忽略属性: {prop_name} = {prop_value}")

            if self.on_command_received:
                try:
                    self.on_command_received("properties_set", properties)
                except Exception as e:
                    print(f"[ERR] 属性设置回调失败: {e}")

        response_topic = f"$oc/devices/{DEVICE_ID}/sys/properties/set/response"
        response = {"result_code": 0, "result_desc": "success"}
        self.client.publish(response_topic, json.dumps(response), qos=1)
        print("[RSP] 属性设置响应已发送")

    def build_payload(self, include_control=False):
        status = {}
        if self.sensors:
            status = self.sensors.get_all_status()

        person = f"{self.last_door_event['person']}-{self.last_door_event['action']}-{self.last_door_event['time']}"

        properties = {
            "temp": status.get("temperature", 25.0),
            "humi": status.get("humidity", 60.0),
            "rain": status.get("rain", 0),
            "person": person
        }

        if include_control:
            properties["beep"] = status.get("beep", 0)
            properties["relay"] = status.get("relay", 0)

        payload = {
            "services": [
                {
                    "service_id": SERVICE_ID,
                    "properties": properties
                }
            ]
        }
        return json.dumps(payload)

    def report_data(self):
        if not self.connected:
            return
        try:
            payload = self.build_payload(include_control=False)
            print(f"上报 -> {payload}")
            self.client.publish(TOPIC_PROPERTY_REPORT, payload, qos=1)
        except Exception as e:
            print(f"[ERR] 数据上报失败: {e}")

    def report_relay_status(self):
        if not self.connected:
            return
        try:
            payload = self.build_payload(include_control=True)
            print(f"上报继电器状态 -> {payload}")
            self.client.publish(TOPIC_PROPERTY_REPORT, payload, qos=1)
        except Exception as e:
            print(f"[ERR] 继电器状态上报失败: {e}")

    def start_report_loop(self):
        def loop():
            if self.connected:
                self.report_data()
            self.report_timer = time.sleep(REPORT_INTERVAL)
            loop()

        import threading
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def update_door_event(self, person, action):
        now = datetime.now().strftime("%H:%M:%S")
        self.last_door_event = {
            "person": person,
            "action": action,
            "time": now
        }
        print(f"[DOOR] 记录事件: {person} - {action} - {now}")
        self.report_data()

    def connect(self):
        if MOCK_MODE:
            print("[模拟模式] MQTT连接跳过")
            self.connected = True
            return True

        self.client = mqtt.Client(client_id=MQTT_CONFIG["clientId"])
        self.client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])

        self.client.tls_set(ca_certs=None, certfile=None, keyfile=None,
                           cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        self.client.on_message = self.on_message

        print("[CONN] 正在连接华为云IoT平台...")
        try:
            self.client.connect(MQTT_CONFIG["hostname"], MQTT_CONFIG["port"], keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[ERR] 连接失败: {e}")
            return False

    def reconnect(self):
        if self.client:
            try:
                self.client.reconnect()
            except Exception as e:
                print(f"[ERR] 重连失败: {e}")
                time.sleep(5)
                self.reconnect()

    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            print("已断开MQTT连接")