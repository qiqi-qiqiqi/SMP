import random
import time
from config import MOCK_MODE, DHT_PIN, RAIN_SENSOR_PIN, RELAY_PIN, BUZZER_PIN

# 非模拟模式下才导入真实硬件库
if not MOCK_MODE:
    try:
        import RPi.GPIO as GPIO
        import adafruit_dht
        import board
    except ImportError:
        print("缺少硬件支持库，请安装 RPi.GPIO / adafruit-circuitpython-dht")
        MOCK_MODE = True   # 自动回退模拟模式


class Sensors:
    def __init__(self):
        self.mock = MOCK_MODE
        self.relay_state = False
        self.buzzer_state = False
        self.dht_device = None
        self.last_temp = 25.0
        self.last_hum = 60.0

        if not self.mock:
            GPIO.setmode(GPIO.BCM)
            # 输出引脚
            GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)
            # 输入引脚：雨量传感器
            GPIO.setup(RAIN_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            # DHT11初始化
            try:
                self.dht_device = adafruit_dht.DHT11(getattr(board, f"D{DHT_PIN}"))
            except Exception as e:
                print(f"DHT11初始化失败: {e}")

    # ---------- 温度与湿度 ----------
    def read_temperature_humidity(self):
        if self.mock:
            temp = 25.0 + random.uniform(-2, 2)
            hum = 60.0 + random.uniform(-5, 5)
            self.last_temp = round(temp, 1)
            self.last_hum = round(hum, 1)
            return self.last_temp, self.last_hum
        else:
            try:
                temperature = self.dht_device.temperature
                humidity = self.dht_device.humidity
                if temperature is not None and humidity is not None:
                    self.last_temp = temperature
                    self.last_hum = humidity
                return self.last_temp, self.last_hum
            except RuntimeError:
                return self.last_temp, self.last_hum
            except Exception as e:
                print(f"DHT11读取错误: {e}")
                return self.last_temp, self.last_hum

    # ---------- 是否下雨（雨量传感器D0） ----------
    def read_rain(self):
        if self.mock:
            return random.choice([True, False])
        else:
            pin_state = GPIO.input(RAIN_SENSOR_PIN)
            print(f"[DEBUG] 雨量传感器引脚 {RAIN_SENSOR_PIN}: {'高电平' if pin_state else '低电平'}")
            return pin_state

    # ---------- 光照强度（模拟值） ----------
    def read_light(self):
        if self.mock:
            return random.randint(200, 800)
        else:
            return random.randint(200, 800)

    # ---------- 继电器控制 ----------
    def set_relay(self, state):
        self.relay_state = state
        if not self.mock:
            GPIO.output(RELAY_PIN, GPIO.HIGH if state else GPIO.LOW)

    def get_relay_state(self):
        return self.relay_state

    # ---------- 蜂鸣器控制 ----------
    def set_buzzer(self, state):
        self.buzzer_state = state
        if not self.mock:
            GPIO.output(BUZZER_PIN, GPIO.HIGH if state else GPIO.LOW)

    def get_buzzer_state(self):
        return self.buzzer_state

    # ---------- 获取所有传感器状态 ----------
    def get_all_status(self):
        temp, hum = self.read_temperature_humidity()
        return {
            "temperature": temp,
            "humidity": hum,
            "rain": 1 if self.read_rain() else 0,
            "relay": 1 if self.get_relay_state() else 0,
            "beep": 1 if self.get_buzzer_state() else 0
        }

    # ---------- 资源释放 ----------
    def cleanup(self):
        if not self.mock:
            GPIO.cleanup()
            if self.dht_device:
                try:
                    self.dht_device.exit()
                except Exception:
                    pass

