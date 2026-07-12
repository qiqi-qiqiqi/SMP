import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import platform

# ===================== 全局配置 =====================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_ROOT = os.path.join(SCRIPT_DIR, "dataset")

DET_MODEL_NAME = "face_detection_yunet_2023mar.onnx"
REC_MODEL_NAME = "face_recognition_sface_2021dec_int8.onnx"

DET_MODEL = os.path.join(SCRIPT_DIR, DET_MODEL_NAME)
REC_MODEL = os.path.join(SCRIPT_DIR, REC_MODEL_NAME)
DB_FILE = os.path.join(SCRIPT_DIR, "face_db.npy")
NAME_FILE = os.path.join(SCRIPT_DIR, "names.npy")
SIM_THRESHOLD = 0.65
CAM_W, CAM_H = 640, 480
TOP_K = 5
MIN_FACE_CONFIDENCE = 0.85
MIN_FACE_SIZE = 50

os.makedirs(DATASET_ROOT, exist_ok=True)

# ===================== 工具函数 =====================
def imread_cn(file_path):
    if not os.path.exists(file_path):
        return None
    buf = np.fromfile(file_path, dtype=np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)

def imwrite_cn(file_path, img):
    success, buf = cv2.imencode('.jpg', img)
    if not success:
        return False
    try:
        buf.tofile(file_path)
        return True
    except:
        return False

import shutil
import tempfile

_model_cache = {}

def get_model_path(model_name):
    global _model_cache
    if model_name in _model_cache:
        return _model_cache[model_name]
    
    base_path = os.path.join(SCRIPT_DIR, model_name)
    if not os.path.exists(base_path):
        return base_path
    
    if isinstance(base_path, str) and ('\\' in base_path or '/' in base_path):
        try:
            temp_dir = tempfile.mkdtemp(prefix="face_model_")
            temp_path = os.path.join(temp_dir, model_name)
            shutil.copy2(base_path, temp_path)
            _model_cache[model_name] = temp_path
            return temp_path
        except Exception as e:
            print(f"无法创建模型临时副本: {e}")
    
    return base_path

def get_camera(camera_id=0):
    sys = platform.system()
    cap = None
    if sys == "Windows":
        cap = cv2.VideoCapture(int(camera_id))
    else:
        cap = cv2.VideoCapture(f"/dev/video{camera_id}")
        if not cap.isOpened():
            cap = cv2.VideoCapture(int(camera_id))
    if cap.isOpened():
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
    return cap

def get_next_img_index(save_dir):
    max_idx = -1
    for fname in os.listdir(save_dir):
        if fname.endswith(".jpg") and fname[:-4].isdigit():
            idx = int(fname[:-4])
            if idx > max_idx:
                max_idx = idx
    return max_idx + 1

# ===================== 数据增强函数 =====================
def augment_image(img):
    augmented = [img]
    augmented.append(cv2.flip(img, 1))
    for alpha in [0.85, 1.15]:
        adjusted = cv2.convertScaleAbs(img, alpha=alpha, beta=0)
        augmented.append(adjusted)
    for beta in [-20, 20]:
        adjusted = cv2.convertScaleAbs(img, alpha=1.0, beta=beta)
        augmented.append(adjusted)
    rows, cols = img.shape[:2]
    for angle in [-10, 10]:
        M = cv2.getRotationMatrix2D((cols/2, rows/2), angle, 1)
        rotated = cv2.warpAffine(img, M, (cols, rows), borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))
        augmented.append(rotated)
    for alpha, beta in [(0.9, -10), (1.1, 10)]:
        adjusted = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
        augmented.append(adjusted)
    return augmented

# ===================== 训练建库函数 =====================
def build_face_database():
    det_model_path = get_model_path(DET_MODEL_NAME)
    rec_model_path = get_model_path(REC_MODEL_NAME)
    
    if not os.path.exists(det_model_path):
        messagebox.showerror("错误", f"检测模型文件不存在：{det_model_path}")
        return False
    if not os.path.exists(rec_model_path):
        messagebox.showerror("错误", f"识别模型文件不存在：{rec_model_path}")
        return False
    
    try:
        detector = cv2.FaceDetectorYN_create(det_model_path, "", (0,0), 0.7, 0.3, 10)
    except Exception as e:
        messagebox.showerror("错误", f"加载检测模型失败：{e}")
        return False
    
    try:
        recognizer = cv2.FaceRecognizerSF_create(rec_model_path, "")
    except Exception as e:
        messagebox.showerror("错误", f"加载识别模型失败：{e}")
        return False
    
    name_list = []
    feat_list = []

    people_folders = [f for f in os.listdir(DATASET_ROOT) if os.path.isdir(os.path.join(DATASET_ROOT, f))]
    if len(people_folders) == 0:
        messagebox.showwarning("提示", "dataset内暂无任何人脸文件夹，请先采集照片！")
        return False

    for name in people_folders:
        folder_path = os.path.join(DATASET_ROOT, name)
        all_feats = []
        img_files = [f for f in os.listdir(folder_path) if f.lower().endswith(("jpg","png","jpeg"))]
        if len(img_files) == 0:
            continue
        print(f"正在处理 {name}，共{len(img_files)}张照片，启用数据增强...")
        for img_name in img_files:
            img_path = os.path.join(folder_path, img_name)
            img = imread_cn(img_path)
            if img is None:
                continue
            h,w = img.shape[:2]
            detector.setInputSize((w,h))
            ret, faces = detector.detect(img)
            if faces is None or len(faces) != 1:
                continue
            face = faces[0]
            confidence = face[-1]
            if confidence < MIN_FACE_CONFIDENCE:
                print(f"  跳过低置信度图片 {img_name}, conf={confidence:.3f}")
                continue
            x,y,w_box,h_box = face[:4]
            if min(w_box, h_box) < MIN_FACE_SIZE:
                print(f"  跳过人脸过小图片 {img_name}, size={int(w_box)}x{int(h_box)}")
                continue
            augmented_imgs = augment_image(img)
            for aug_img in augmented_imgs:
                aug_h, aug_w = aug_img.shape[:2]
                detector.setInputSize((aug_w, aug_h))
                _, aug_faces = detector.detect(aug_img)
                if aug_faces is None or len(aug_faces) != 1:
                    continue
                aug_aligned = recognizer.alignCrop(aug_img, aug_faces[0])
                aug_feat = recognizer.feature(aug_aligned).flatten()
                aug_feat = aug_feat / np.linalg.norm(aug_feat)
                all_feats.append(aug_feat)
        if len(all_feats) == 0:
            print(f"{name} 无有效人脸照片，跳过")
            continue
        print(f"  {name} 生成特征数: {len(all_feats)} (原图{len(img_files)}张 × 增强)")
        name_list.append(name)
        feat_list.append(np.array(all_feats))
    
    print(f"=== 循环结束 ===")
    print(f"name_list长度: {len(name_list)}")
    print(f"feat_list长度: {len(feat_list)}")
    if len(feat_list) > 0:
        print(f"第一个人特征形状: {feat_list[0].shape}")
    
    if len(name_list) == 0:
        messagebox.showerror("错误", "未生成任何有效人脸特征库！")
        return False
    
    print(f"准备保存特征库，共 {len(name_list)} 人")
    print(f"特征库路径: {DB_FILE}")
    print(f"名称文件路径: {NAME_FILE}")
    
    try:
        np.save(DB_FILE, feat_list)
        print(f"特征库保存成功")
        if os.path.exists(DB_FILE):
            print(f"特征库文件大小: {os.path.getsize(DB_FILE)} 字节")
        else:
            print(f"特征库文件不存在！")
    except Exception as e:
        print(f"特征库保存失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("错误", f"保存特征库失败: {e}")
        return False
    
    try:
        np.save(NAME_FILE, np.array(name_list))
        print(f"名称文件保存成功")
        if os.path.exists(NAME_FILE):
            print(f"名称文件大小: {os.path.getsize(NAME_FILE)} 字节")
        else:
            print(f"名称文件不存在！")
    except Exception as e:
        print(f"名称文件保存失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        messagebox.showerror("错误", f"保存名称文件失败: {e}")
        return False
    
    messagebox.showinfo("完成", f"特征库训练完成！共录入 {len(name_list)} 人")
    return True

# ===================== 图片检验函数 =====================
def test_recognize_image(img_path=None):
    if not os.path.exists(DB_FILE) or not os.path.exists(NAME_FILE):
        messagebox.showwarning("提示", "请先生成人脸特征库！")
        return
    if img_path is None:
        img_path = filedialog.askopenfilename(title="选择待检测图片", filetypes=[("图片文件", "*.jpg;*.png;*.jpeg")])
        if not img_path:
            return
    det_model_path = get_model_path(DET_MODEL_NAME)
    rec_model_path = get_model_path(REC_MODEL_NAME)
    
    try:
        detector = cv2.FaceDetectorYN_create(det_model_path, "", (0,0), 0.7,0.3,10)
        recognizer = cv2.FaceRecognizerSF_create(rec_model_path, "")
    except Exception as e:
        messagebox.showerror("错误", f"加载模型失败：{e}")
        return
    
    db = np.load(DB_FILE, allow_pickle=True)
    names = np.load(NAME_FILE)
    img = imread_cn(img_path)
    if img is None:
        messagebox.showerror("错误", "图片读取失败")
        return
    h,w = img.shape[:2]
    detector.setInputSize((w,h))
    ret, faces = detector.detect(img)
    if faces is None:
        messagebox.showinfo("结果", "图片中未检测到人脸")
        return
    for face in faces:
        aligned = recognizer.alignCrop(img, face)
        feat = recognizer.feature(aligned).flatten()
        feat = feat / np.linalg.norm(feat)
        best_name = "未知"
        best_sim = 0.0
        for i, person_feats in enumerate(db):
            sims = np.dot(person_feats, feat)
            top_k_sims = np.sort(sims)[-TOP_K:]
            avg_sim = float(np.mean(top_k_sims))
            if avg_sim > best_sim:
                best_sim = avg_sim
                best_name = names[i]
        x,y,w_box,h_box = map(int, face[:4])
        if best_sim >= SIM_THRESHOLD:
            text = f"{best_name} {best_sim:.2f}"
            color = (0,255,0)
        else:
            text = f"未知 {best_sim:.2f}"
            color = (0,0,255)
        cv2.rectangle(img, (x,y), (x+w_box,y+h_box), color, 2)
        cv2.putText(img, text, (x,y-8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    save_path = os.path.join(SCRIPT_DIR, "test_output.jpg")
    if not imwrite_cn(save_path, img):
        messagebox.showwarning("提示", "保存结果图片失败")
    else:
        messagebox.showinfo("识别完成", f"结果已保存为 {save_path}，可打开查看")

# ===================== GUI主程序 =====================
class FaceTrainGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("人脸采集训练上位机（跨Windows/树莓派）")
        self.root.geometry("660x500")

        self.cap = None

        # ========== 1. 人物名称下拉框区域 ==========
        frame_name = tk.Frame(root, pady=8)
        frame_name.pack(fill="x", padx=20)
        tk.Label(frame_name, text="人物名称(英文/拼音):").pack(side="left")
        self.name_var = tk.StringVar()
        self.comb_name = ttk.Combobox(frame_name, textvariable=self.name_var, width=22)
        self.comb_name['values'] = self.get_exist_names()
        self.comb_name.pack(side="left", padx=10)
        tk.Button(frame_name, text="新增名称", command=self.add_new_name).pack(side="left")

        # ========== 2. 摄像头ID选择区域 ==========
        frame_cam = tk.Frame(root, pady=8)
        frame_cam.pack(fill="x", padx=20)
        tk.Label(frame_cam, text="摄像头ID:").pack(side="left")
        self.cam_id_var = tk.StringVar(value="0")
        self.spin_cam = ttk.Spinbox(frame_cam, from_=0, to=9, textvariable=self.cam_id_var, width=5)
        self.spin_cam.pack(side="left", padx=5)
        tk.Button(frame_cam, text="测试摄像头", command=self.test_camera).pack(side="left", padx=5)

        # ========== 3. 检测方式下拉选择框 ==========
        frame_mode = tk.Frame(root, pady=8)
        frame_mode.pack(fill="x", padx=20)
        tk.Label(frame_mode, text="识别检测方式：").pack(side="left")
        self.mode_var = tk.StringVar()
        self.comb_mode = ttk.Combobox(frame_mode, textvariable=self.mode_var, width=22, state="readonly")
        self.comb_mode['values'] = ["调用摄像头实时检测", "选择本地图片检测"]
        self.comb_mode.current(0)
        self.comb_mode.pack(side="left", padx=10)

        # ========== 4. 三大功能按钮 ==========
        frame_btn = tk.Frame(root, pady=12)
        frame_btn.pack(pady=5)
        self.btn_capture = tk.Button(frame_btn, text="1. 采集训练人脸", width=18, height=2, command=self.open_camera)
        self.btn_capture.grid(row=0, column=0, padx=6)
        self.btn_train = tk.Button(frame_btn, text="2. 一键训练生成特征库", width=18, height=2, command=build_face_database)
        self.btn_train.grid(row=0, column=1, padx=6)
        self.btn_test = tk.Button(frame_btn, text="3. 检验识别模型", width=18, height=2, command=self.run_test_by_mode)
        self.btn_test.grid(row=0, column=2, padx=6)

        # ========== 操作提示 ==========
        tip_text = """【采集人脸】：打开摄像头左键拍照，图片自动命名0/1/2...；ESC或窗口X关闭摄像头
【检验模型】：上方下拉框切换检测方式：摄像头实时识别 / 单张图片识别
【训练模型】：采集完所有人脸后点击，生成可在树莓派运行的人脸特征库（含数据增强）
【摄像头ID】：选择不同的USB摄像头，点击测试验证"""
        tk.Label(root, text=tip_text, fg="#222", wraplength=620).pack(pady=10)

    def get_exist_names(self):
        if not os.path.exists(DATASET_ROOT):
            return []
        dirs = []
        for d in os.listdir(DATASET_ROOT):
            full = os.path.join(DATASET_ROOT, d)
            if os.path.isdir(full):
                dirs.append(d)
        return dirs

    def add_new_name(self):
        new_name = simpledialog.askstring("新增人物", "输入英文/拼音名称（禁止中文、空格、特殊符号）:")
        if not new_name:
            return
        invalid_chars = [" ","/","\\",":","*","?","\"","<",">","|"]
        if any(c in new_name for c in invalid_chars):
            messagebox.showerror("错误", "名称不能包含空格、特殊符号！")
            return
        new_folder = os.path.join(DATASET_ROOT, new_name)
        if os.path.exists(new_folder):
            messagebox.showinfo("提示", "该人物文件夹已存在！")
            return
        os.makedirs(new_folder)
        self.comb_name['values'] = self.get_exist_names()
        self.name_var.set(new_name)
        messagebox.showinfo("成功", f"人物 {new_name} 创建完成")

    def test_camera(self):
        cam_id = self.cam_id_var.get()
        cap = get_camera(cam_id)
        if cap.isOpened():
            cap.release()
            messagebox.showinfo("成功", f"摄像头 ID {cam_id} 可以正常打开！")
        else:
            messagebox.showerror("失败", f"摄像头 ID {cam_id} 打开失败，请检查硬件连接！")

    def open_camera(self):
        target_name = self.name_var.get().strip()
        if not target_name:
            messagebox.showwarning("提示", "请先选择或新增人物名称！")
            return
        save_dir = os.path.join(DATASET_ROOT, target_name)
        os.makedirs(save_dir, exist_ok=True)

        current_idx = get_next_img_index(save_dir)
        cam_id = self.cam_id_var.get()
        self.cap = get_camera(cam_id)
        if not self.cap.isOpened():
            messagebox.showerror("错误", f"摄像头 ID {cam_id} 打开失败，请检查硬件！")
            return
        print("=== 人脸采集窗口 ===")
        print(f"当前保存起始序号: {current_idx}.jpg")
        print("左键点击画面拍照 | ESC / 窗口X 关闭摄像头")

        def mouse_click(event, x, y, flags, param):
            nonlocal current_idx, frame
            if event == cv2.EVENT_LBUTTONDOWN:
                save_path = os.path.join(save_dir, f"{current_idx}.jpg")
                success = imwrite_cn(save_path, frame)
                if success:
                    print(f"已保存：{save_path}")
                    current_idx += 1
                else:
                    print(f"保存失败：{save_path}")

        cv2.namedWindow("Capture Face | Click Shoot | ESC/X Close")
        cv2.setMouseCallback("Capture Face | Click Shoot | ESC/X Close", mouse_click)

        frame = None
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("摄像头画面读取中断，自动关闭")
                break
            cv2.imshow("Capture Face | Click Shoot | ESC/X Close", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break
            if cv2.getWindowProperty("Capture Face | Click Shoot | ESC/X Close", cv2.WND_PROP_VISIBLE) < 1:
                break

        self.cap.release()
        cv2.destroyAllWindows()
        messagebox.showinfo("采集结束", f"照片已保存在 {save_dir}/\n最后一张序号：{current_idx-1}.jpg")

    def run_test_by_mode(self):
        select_mode = self.mode_var.get()
        if select_mode == "选择本地图片检测":
            test_recognize_image()
        elif select_mode == "调用摄像头实时检测":
            self.camera_realtime_recognize()

    def camera_realtime_recognize(self):
        if not os.path.exists(DB_FILE) or not os.path.exists(NAME_FILE):
            messagebox.showwarning("提示", "请先生成人脸特征库！")
            return
        cam_id = self.cam_id_var.get()
        cap = get_camera(cam_id)
        if not cap.isOpened():
            messagebox.showerror("错误", f"摄像头 ID {cam_id} 打开失败！")
            return
        
        det_model_path = get_model_path(DET_MODEL_NAME)
        rec_model_path = get_model_path(REC_MODEL_NAME)
        
        try:
            detector = cv2.FaceDetectorYN_create(det_model_path, "", (0,0), 0.7,0.3,10)
            recognizer = cv2.FaceRecognizerSF_create(rec_model_path, "")
        except Exception as e:
            messagebox.showerror("错误", f"加载模型失败：{e}")
            cap.release()
            return
        
        db = np.load(DB_FILE, allow_pickle=True)
        names = np.load(NAME_FILE)
        print("实时识别启动，ESC/窗口X关闭")
        frame = None
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            h,w = frame.shape[:2]
            detector.setInputSize((w,h))
            _, faces = detector.detect(frame)
            if faces is not None:
                for face_info in faces:
                    aligned = recognizer.alignCrop(frame, face_info)
                    feat = recognizer.feature(aligned).flatten()
                    feat = feat / np.linalg.norm(feat)
                    best_name = "未知"
                    best_sim = 0.0
                    for i, person_feats in enumerate(db):
                        sims = np.dot(person_feats, feat)
                        top_k_sims = np.sort(sims)[-TOP_K:]
                        avg_sim = float(np.mean(top_k_sims))
                        if avg_sim > best_sim:
                            best_sim = avg_sim
                            best_name = names[i]
                    x,y,w_box,h_box = map(int, face_info[:4])
                    if best_sim >= SIM_THRESHOLD:
                        text = f"{best_name} {best_sim:.2f}"
                        color = (0,255,0)
                    else:
                        text = f"未知 {best_sim:.2f}"
                        color = (0,0,255)
                    cv2.rectangle(frame, (x,y), (x+w_box,y+h_box), color, 2)
                    cv2.putText(frame, text, (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
            cv2.imshow("RealTime Recognize | ESC/X Close", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:
                break
            if cv2.getWindowProperty("RealTime Recognize | ESC/X Close", cv2.WND_PROP_VISIBLE) < 1:
                break
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    root = tk.Tk()
    app = FaceTrainGUI(root)
    root.mainloop()