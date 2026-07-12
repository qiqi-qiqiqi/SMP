import time
import board
import adafruit_dht
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# ---------- 配置 ----------
DHT_PIN = board.D4          # 对应BCM4，物理引脚7
I2C_PORT = 1                # 树莓派 I2C 端口号
OLED_ADDRESS = 0x3C         # OLED I2C 地址 (用 i2cdetect -y 1 确认)

# ---------- 初始化传感器与显示 ----------
dht11 = adafruit_dht.DHT11(DHT_PIN)

serial = i2c(port=I2C_PORT, address=OLED_ADDRESS)
device = ssd1306(serial)

font = ImageFont.load_default()

print("DHT11 + OLED 启动成功，按 Ctrl+C 退出...")

try:
    while True:
        # 读取温湿度
        try:
            temperature = dht11.temperature
            humidity = dht11.humidity
            if temperature is not None and humidity is not None:
                temp_str = f"Temp: {temperature:.1f} C"
                hum_str  = f"Humi: {humidity:.1f} %"
            else:
                temp_str = "Temp: --.- C"
                hum_str  = "Humi: --.- %"
        except RuntimeError as e:
            # DHT11读取偶尔失败（尤其刚上电后），忽略并重试
            print(f"读取错误: {e}")
            temp_str = "Temp: ERROR"
            hum_str  = "Humi: ERROR"

        # OLED 刷新显示
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((10, 10), "Smart Door", fill="white", font=font)
            draw.text((10, 25), temp_str, fill="white", font=font)
            draw.text((10, 40), hum_str, fill="white", font=font)

        time.sleep(2.0)  # DHT11最快采样周期约1~2秒

except KeyboardInterrupt:
    print("\n程序退出，清理资源...")
    device.clear()
    dht11.exit()