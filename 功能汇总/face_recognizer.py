# face_recognizer.py
import os
import cv2
import numpy as np
import platform
import time
from config import (MOCK_MODE, DATASET_ROOT, DB_FILE, NAME_FILE,
                    DET_MODEL, REC_MODEL, SIM_THRESHOLD, CAM_ID, CAM_W, CAM_H)

class FaceRecognizer:
    def __init__(self):
        self.mock = MOCK_MODE
        self.db_features = None
        self.db_names = None

        if not self.mock:
            # 加载特征库（若存在）
            self.load_database()
            # 初始化检测/识别模型（全局复用）
            self.detector = cv2.FaceDetectorYN_create(DET_MODEL, "", (0,0), 0.7, 0.3, 10)
            self.recognizer = cv2.FaceRecognizerSF_create(REC_MODEL, "")
        else:
            print("[模拟模式] 人脸识别使用随机数据")

    # ---------- 数据库加载 / 保存 ----------
    def load_database(self):
        if os.path.exists(DB_FILE) and os.path.exists(NAME_FILE):
            self.db_features = np.load(DB_FILE, allow_pickle=True)
            self.db_names = np.load(NAME_FILE)
        else:
            self.db_features = None
            self.db_names = None
    
    def _compute_similarity(self, feat):
        best_sim = 0.0
        best_idx = -1
        for i, person_feats in enumerate(self.db_features):
            if person_feats.ndim == 2:
                sims = np.dot(person_feats, feat)
                top_k = min(5, len(sims))
                avg_sim = float(np.mean(np.sort(sims)[-top_k:]))
            else:
                sim = float(np.dot(person_feats, feat))
                avg_sim = sim
            if avg_sim > best_sim:
                best_sim = avg_sim
                best_idx = i
        return best_idx, best_sim

    def save_database(self, feats, names):
        np.save(DB_FILE, np.array(feats))
        np.save(NAME_FILE, np.array(names))
        self.db_features = np.array(feats)
        self.db_names = np.array(names)

    # ---------- 工具函数 ----------
    def _imread_cn(self, path):
        if not os.path.exists(path):
            return None
        buf = np.fromfile(path, dtype=np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)

    def _get_camera(self, max_retries=5, retry_delay=1):
        if self.mock:
            return None
        sys = platform.system()
        cap = None
        
        backends = []
        if sys == "Windows":
            backends = [
                (CAM_ID, cv2.CAP_DSHOW),
                (CAM_ID, cv2.CAP_MSMF),
                (CAM_ID, cv2.CAP_ANY),
            ]
        else:
            backends = [
                (f"/dev/video{CAM_ID}", cv2.CAP_V4L2),
                (CAM_ID, cv2.CAP_V4L2),
                (CAM_ID, cv2.CAP_ANY),
                (f"/dev/video{CAM_ID}", cv2.CAP_ANY),
            ]
        
        for attempt in range(max_retries):
            for src, backend in backends:
                try:
                    cap = cv2.VideoCapture(src, backend)
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
                        actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                        actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        backend_name = cap.getBackendName() if hasattr(cap, 'getBackendName') else "unknown"
                        print(f"摄像头打开成功 (src={src}, backend={backend_name}, 分辨率={actual_w}x{actual_h}, 尝试 {attempt+1}/{max_retries})")
                        return cap
                    cap.release()
                except Exception as e:
                    print(f"尝试打开摄像头失败 (src={src}, backend={backend}): {e}")
                    if cap:
                        cap.release()
            
            print(f"摄像头打开失败 (尝试 {attempt+1}/{max_retries})，{retry_delay}秒后重试...")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        print(f"所有尝试均失败，请检查：")
        print(f"1. 摄像头设备是否存在: ls /dev/video*")
        print(f"2. 当前用户是否在video组: groups")
        print(f"3. 树莓派CSI摄像头是否启用: sudo raspi-config -> Interface Options -> Camera")
        print(f"4. 若使用libcamera，尝试用libcamerify运行: libcamerify python3 main.py")
        return None

    # ---------- 采集人脸（打开 OpenCV 窗口拍照） ----------
    def capture_faces(self, name):
        """为指定人物采集人脸照片，存入 dataset/name/ 文件夹"""
        if self.mock:
            print(f"[模拟] 已为 {name} 采集人脸")
            return True

        save_dir = os.path.join(DATASET_ROOT, name)
        os.makedirs(save_dir, exist_ok=True)

        max_idx = -1
        for f in os.listdir(save_dir):
            if f.endswith(".jpg") and f[:-4].isdigit():
                idx = int(f[:-4])
                if idx > max_idx:
                    max_idx = idx
        idx = max_idx + 1

        try:
            self.stop_camera()
            time.sleep(0.3)
            self.start_camera()
        except RuntimeError as e:
            print(f"摄像头打开失败: {e}")
            return False

        print(f"开始采集 {name} 的人脸，左键拍照，ESC 或关闭窗口结束")
        cv2.namedWindow("Collect Faces", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Collect Faces", 640, 480)

        frame = None
        def mouse_cb(event, x, y, flags, param):
            nonlocal idx, frame
            if event == cv2.EVENT_LBUTTONDOWN and frame is not None:
                save_path = os.path.join(save_dir, f"{idx}.jpg")
                cv2.imwrite(save_path, frame)
                print(f"已保存 {save_path}")
                idx += 1

        cv2.setMouseCallback("Collect Faces", mouse_cb)

        while True:
            ret, frame = self.get_frame()
            if not ret:
                break
            cv2.imshow("Collect Faces", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break
            if cv2.getWindowProperty("Collect Faces", cv2.WND_PROP_VISIBLE) < 1:
                break

        cv2.destroyAllWindows()
        self.stop_camera()
        return True

    # ---------- 训练建库 ----------
    def build_database(self):
        """从 dataset 文件夹生成特征库"""
        if self.mock:
            print("[模拟] 特征库训练完成")
            return True

        if not os.path.exists(DATASET_ROOT):
            print("dataset 文件夹不存在")
            return False

        people = [d for d in os.listdir(DATASET_ROOT)
                  if os.path.isdir(os.path.join(DATASET_ROOT, d))]
        if not people:
            print("dataset 内无人物文件夹")
            return False

        name_list = []
        feat_list = []

        for name in people:
            folder = os.path.join(DATASET_ROOT, name)
            img_files = [f for f in os.listdir(folder)
                         if f.lower().endswith((".jpg", ".png", ".jpeg"))]
            if not img_files:
                continue
            feats = []
            for img_name in img_files:
                img = self._imread_cn(os.path.join(folder, img_name))
                if img is None:
                    continue
                h, w = img.shape[:2]
                self.detector.setInputSize((w, h))
                _, faces = self.detector.detect(img)
                if faces is None or len(faces) != 1:
                    continue
                aligned = self.recognizer.alignCrop(img, faces[0])
                feat = self.recognizer.feature(aligned).flatten()
                feat = feat / np.linalg.norm(feat)
                feats.append(feat)
            if feats:
                avg = np.mean(feats, axis=0)
                avg = avg / np.linalg.norm(avg)
                name_list.append(name)
                feat_list.append(avg)

        if not name_list:
            print("未提取到有效人脸特征")
            return False

        self.save_database(feat_list, name_list)
        print(f"训练完成，共录入 {len(name_list)} 人")
        return True

    # ---------- 识别单张图片 ----------
    def recognize_image(self, img_path):
        """返回带标注的图片路径（保存为 test_output.jpg）"""
        if self.mock:
            # 模拟返回一张图
            img = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(img, "MOCK RECOGNIZE", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255),2)
            cv2.imwrite("test_output.jpg", img)
            return "test_output.jpg"

        if self.db_features is None:
            self.load_database()
        if self.db_features is None:
            print("特征库为空，请先训练")
            return None

        img = self._imread_cn(img_path)
        if img is None:
            return None
        h, w = img.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(img)
        if faces is None:
            cv2.imwrite("test_output.jpg", img)
            return "test_output.jpg"

        for face in faces:
            aligned = self.recognizer.alignCrop(img, face)
            feat = self.recognizer.feature(aligned).flatten()
            feat = feat / np.linalg.norm(feat)
            max_idx, max_sim = self._compute_similarity(feat)
            x, y, wb, hb = map(int, face[:4])
            if max_idx >= 0 and max_sim >= SIM_THRESHOLD:
                text = f"{self.db_names[max_idx]} {max_sim:.2f}"
                color = (0, 255, 0)
            else:
                text = f"Unknown {max_sim:.2f}"
                color = (0, 0, 255)
            cv2.rectangle(img, (x,y), (x+wb, y+hb), color, 2)
            cv2.putText(img, text, (x, y-8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.imwrite("test_output.jpg", img)
        return "test_output.jpg"

    # ---------- 实时识别循环（给 FacePage 使用） ----------
    def start_camera(self):
        self.cap = self._get_camera() if not self.mock else None
        if self.mock:
            print("[模拟] 摄像头已启动")
        elif self.cap is None or not self.cap.isOpened():
            raise RuntimeError("无法打开摄像头")

    def stop_camera(self):
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
            self.cap = None

    def get_frame(self):
        if self.mock:
            frame = np.zeros((CAM_H, CAM_W, 3), dtype=np.uint8)
            cv2.putText(frame, "MOCK CAM", (220, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            return True, frame
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            return ret, frame
        return False, None

    def recognize(self, frame):
        """识别一帧，返回 (name, face_locations)"""
        if self.mock:
            import random
            if random.random() > 0.5 and self.db_names is not None and len(self.db_names) > 0:
                return random.choice(self.db_names), [(100, 200, 200, 100)]
            return "Unknown", []
        if self.db_features is None:
            self.load_database()
        if self.db_features is None:
            return "No DB", []

        h, w = frame.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(frame)
        if faces is None:
            return "No Face", []
        results = []
        for face in faces:
            aligned = self.recognizer.alignCrop(frame, face)
            feat = self.recognizer.feature(aligned).flatten()
            feat = feat / np.linalg.norm(feat)
            max_idx, max_sim = self._compute_similarity(feat)
            name = self.db_names[max_idx] if max_idx >= 0 and max_sim >= SIM_THRESHOLD else "Unknown"
            loc = (int(face[1]), int(face[0]+face[2]), int(face[1]+face[3]), int(face[0]))
            results.append((name, loc))
        if results:
            # 返回第一个人脸的信息
            return results[0]
        return "No Face", []

    # ---------- 管理员实时检验（带画面显示） ----------
    def test_realtime(self):
        """打开摄像头进行实时识别检验（阻塞，直到关闭）"""
        if self.mock:
            print("[模拟] 实时识别检验已结束")
            return
        if self.db_features is None:
            self.load_database()
        if self.db_features is None:
            print("请先训练特征库")
            return

        try:
            self.stop_camera()
            time.sleep(0.3)
            self.start_camera()
        except RuntimeError as e:
            print(f"摄像头打开失败: {e}")
            return

        print("实时识别开始，ESC/关闭窗口退出")
        cv2.namedWindow("Realtime Recognize", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Realtime Recognize", 640, 480)

        while True:
            ret, frame = self.get_frame()
            if not ret:
                break
            h, w = frame.shape[:2]
            self.detector.setInputSize((w, h))
            _, faces = self.detector.detect(frame)
            if faces is not None:
                for face in faces:
                    aligned = self.recognizer.alignCrop(frame, face)
                    feat = self.recognizer.feature(aligned).flatten()
                    feat = feat / np.linalg.norm(feat)
                    max_idx, max_sim = self._compute_similarity(feat)
                    x, y, wb, hb = map(int, face[:4])
                    if max_idx >= 0 and max_sim >= SIM_THRESHOLD:
                        text = f"{self.db_names[max_idx]} {max_sim:.2f}"
                        color = (0,255,0)
                    else:
                        text = f"Unknown {max_sim:.2f}"
                        color = (0,0,255)
                    cv2.rectangle(frame, (x,y), (x+wb, y+hb), color, 2)
                    cv2.putText(frame, text, (x, y-8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            cv2.imshow("Realtime Recognize", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break
            if cv2.getWindowProperty("Realtime Recognize", cv2.WND_PROP_VISIBLE) < 1:
                break

        cv2.destroyAllWindows()
        self.stop_camera()