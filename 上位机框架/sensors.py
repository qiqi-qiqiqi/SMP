# sensors.py
import random
import time
from config import MOCK_MODE, DHT_PIN, LIGHT_SPI_CHANNEL, RAIN_SENSOR_PIN, RELAY_PIN, BUZZER_PIN

# 非模拟模式下才导入真实硬件库
if not MOCK_MODE:
    try:
        import RPi.GPIO as GPIO
        import Adafruit_DHT
        import spidev
    except ImportError:
        print("缺少硬件支持库，请安装 RPi.GPIO / Adafruit_DHT / spidev")
        MOCK_MODE = True   # 回退到模拟模式

class Sensors:
    def __init__(self):
        self.mock = MOCK_MODE
        self.relay_state = False
        self.buzzer_state = False

        if not self.mock:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(RAIN_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            # 初始化 SPI（用于光照传感器）
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)
            self.spi.max_speed_hz = 1350000

    # ---------- 温度与湿度 ----------
    def read_temperature_humidity(self):
        if self.mock:
            temp = 25.0 + random.uniform(-2, 2)
            hum = 60.0 + random.uniform(-5, 5)
            return round(temp, 1), round(hum, 1)
        else:
            humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, DHT_PIN)
            return temperature, humidity

    # ---------- 光照强度（0 - 1023 或 lux） ----------
    def read_light(self):
        if self.mock:
            return random.randint(200, 800)
        else:
            # 从 MCP3008 读取模拟值
            adc = self.spi.xfer2([1, (8 + LIGHT_SPI_CHANNEL) << 4, 0])
            value = ((adc[1] & 3) << 8) + adc[2]
            return value

    # ---------- 是否下雨 ----------
    def read_rain(self):
        if self.mock:
            return random.choice([True, False])
        else:
            # 雨滴传感器：低电平表示检测到雨滴（根据实际接线调整）
            return not GPIO.input(RAIN_SENSOR_PIN)

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

    # ---------- 清理资源 ----------
    def cleanup(self):
        if not self.mock:
            GPIO.cleanup()
            self.spi.close()