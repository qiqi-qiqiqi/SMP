import time
import RPi.GPIO as GPIO
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# ---------- 配置 ----------
RAIN_DO_PIN = 17            # BCM17，物理引脚11
I2C_PORT = 1
OLED_ADDRESS = 0x3C

# ---------- GPIO初始化 ----------
GPIO.setmode(GPIO.BCM)
GPIO.setup(RAIN_DO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # 内部上拉，稳定状态

# ---------- OLED初始化 ----------
serial = i2c(port=I2C_PORT, address=OLED_ADDRESS)
device = ssd1306(serial)
font = ImageFont.load_default()

print("雨滴传感器(D0) + OLED 启动成功，按 Ctrl+C 退出...")

try:
    while True:
        # 读取数字输出：0表示检测到雨滴（有水），1表示干燥
        # 根据传感器实际输出逻辑，可在此调整
        sensor_value = GPIO.input(RAIN_DO_PIN)
        
        if sensor_value == 0:
            status = "Rain: YES"
            rain_state = "Wet (Raining)"
        else:
            status = "Rain: NO"
            rain_state = "Dry (No Rain)"

        # 在OLED上绘制
        with canvas(device) as draw:
            draw.rectangle(device.bounding_box, outline="white", fill="black")
            draw.text((10, 10), "Smart Door", fill="white", font=font)
            draw.text((10, 25), status, fill="white", font=font)
            draw.text((10, 40), rain_state, fill="white", font=font)

        time.sleep(0.5)  # 每0.5秒刷新

except KeyboardInterrupt:
    print("\n程序退出，清理资源...")
    device.clear()
    GPIO.cleanup()