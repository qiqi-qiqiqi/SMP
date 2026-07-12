# config.py
MOCK_MODE = True               # True: 模拟模式，PC调试；False: 真实硬件
# GPIO 引脚
DHT_PIN = 4
LIGHT_SPI_CHANNEL = 0
RAIN_SENSOR_PIN = 17
RELAY_PIN = 18
BUZZER_PIN = 27

DOOR_PASSWORD = "8"
ADMIN_PASSWORD = "8"

DB_FILE = "face_db.npy"
NAME_FILE = "names.npy"

FACE_MATCH_THRESHOLD = 0.6
REFRESH_INTERVAL = 2000

# 已知人脸图片存放目录
KNOWN_FACES_DIR = "known_faces"