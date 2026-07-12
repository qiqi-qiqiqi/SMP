# config.py

# 运行模式
MOCK_MODE = False               # True: 模拟模式；False: 真实硬件


# ========== 引脚分配 BCM ==========
DHT_PIN = 4      # DHT11 数据脚
RAIN_SENSOR_PIN = 17     # 雨量传感器 D0数字输出
RELAY_PIN = 18     # 继电器控制
BUZZER_PIN = 27     # 有源蜂鸣器
# OLED I2C：固定占用 SDA=BCM2, SCL=BCM3，不需要额外配置

# 密码
DOOR_PASSWORD = "8"
ADMIN_PASSWORD = "8"

# 人脸识别阈值（相似度 0~1，越大越严格）
SIM_THRESHOLD = 0.65

# 已知人脸照片存放目录（用于训练）
DATASET_ROOT = "./dataset"

# 人脸特征库文件
DB_FILE = "face_db.npy"
NAME_FILE = "names.npy"

# OpenCV 人脸模型文件（放在项目根目录）
DET_MODEL = "face_detection_yunet_2023mar.onnx"
REC_MODEL = "face_recognition_sface_2021dec_int8.onnx"

# 摄像头配置
CAM_ID = 0           # 摄像头ID，0表示第一个摄像头，1表示第二个摄像头...
CAM_W, CAM_H = 640, 480


# ========== 华为云IoT平台配置 ==========
MQTT_CONFIG = {
    "username": "6a50aec2cbb0cf6bb96dc3dc_1234",
    "password": "aa2b5c56eda497169650fb75ef755e64f13f6f5036a1b9b7bed267c51544e81a",
    "clientId": "6a50aec2cbb0cf6bb96dc3dc_1234_0_0_2026071008",
    "hostname": "e201e15730.st1.iotda-device.cn-north-4.myhuaweicloud.com",
    "port": 8883,
}

DEVICE_ID = MQTT_CONFIG["username"].split("_")[0]
SERVICE_ID = "1234"

# 数据上报间隔（秒）
REPORT_INTERVAL = 30

# 命令响应超时（秒）
COMMAND_TIMEOUT = 5