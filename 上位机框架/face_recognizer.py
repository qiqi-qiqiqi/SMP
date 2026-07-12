# face_recognizer.py
import cv2
import numpy as np
import os
import time
from config import FACE_MATCH_THRESHOLD, KNOWN_FACES_DIR

try:
    import face_recognition
    FACE_RECOG_AVAILABLE = True
except ImportError:
    FACE_RECOG_AVAILABLE = False

class FaceRecognizer:
    def __init__(self, known_faces_dir=KNOWN_FACES_DIR):
        self.known_encodings = []
        self.known_names = []
        self.cap = None
        self.mock = (not FACE_RECOG_AVAILABLE)   # 根据库是否可用自动选择模拟

        if not self.mock:
            self.load_known_faces(known_faces_dir)

    def load_known_faces(self, directory):
        """从目录加载已知人脸"""
        self.known_encodings = []
        self.known_names = []
        if not os.path.exists(directory):
            os.makedirs(directory)
        for filename in os.listdir(directory):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                path = os.path.join(directory, filename)
                image = face_recognition.load_image_file(path)
                encodings = face_recognition.face_encodings(image)
                if encodings:
                    self.known_encodings.append(encodings[0])
                    self.known_names.append(os.path.splitext(filename)[0])

    def add_face_from_camera(self, name):
        """打开摄像头拍照，提取人脸保存到已知库"""
        if self.mock:
            print(f"[模拟] 已为 {name} 添加人脸")
            return True
        temp_cap = cv2.VideoCapture(0)
        if not temp_cap.isOpened():
            return False
        time.sleep(0.5)  # 摄像头预热
        ret, frame = temp_cap.read()
        temp_cap.release()
        if not ret:
            return False

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb)
        if not boxes:
            return False

        # 保存图片
        save_dir = KNOWN_FACES_DIR
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        filename = f"{name}.jpg"
        save_path = os.path.join(save_dir, filename)
        cv2.imwrite(save_path, frame)
        # 重新加载所有人脸
        self.load_known_faces(save_dir)
        return True

    def start_camera(self):
        if not self.mock:
            if self.cap is None:
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    raise RuntimeError("无法打开摄像头")
        else:
            print("[模拟] 摄像头已启动")

    def stop_camera(self):
        if self.cap:
            self.cap.release()
            self.cap = None

    def get_frame(self):
        if self.mock:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "MOCK CAMERA", (200, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            return True, frame
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            return ret, frame
        return False, None

    def recognize(self, frame):
        if self.mock:
            import random
            if random.random() > 0.5 and self.known_names:
                return random.choice(self.known_names), [(100, 200, 200, 100)]
            return "Unknown", []
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb)
        if not locations:
            return "No Face", []
        encodings = face_recognition.face_encodings(rgb, locations)
        for encoding, loc in zip(encodings, locations):
            matches = face_recognition.compare_faces(self.known_encodings, encoding, tolerance=FACE_MATCH_THRESHOLD)
            if True in matches:
                idx = matches.index(True)
                return self.known_names[idx], locations
        return "Unknown", locations