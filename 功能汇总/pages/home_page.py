# pages/home_page.py
import tkinter as tk
from PIL import Image, ImageTk
import cv2
import subprocess
import threading
import time
from tkinter import messagebox
import sys
from config import CAM_ID

class HomePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#0f172a")
        self.controller = controller

        for i in range(10):
            self.columnconfigure(i, weight=1)
        for i in range(6):
            self.rowconfigure(i, weight=1)

        self.video_label = tk.Label(self, bg="black", relief="solid", bd=2)
        self.video_label.grid(row=0, column=0, rowspan=5, columnspan=6,
                             padx=5, pady=5, sticky="nsew")

        btn_style = {"font": ("Arial", 20, "bold"), "bg": "#3b82f6", "fg": "white",
                     "activebackground": "#2563eb", "activeforeground": "white",
                     "bd": 0, "padx": 10, "pady": 8, "cursor": "hand2"}

        self.face_btn = tk.Button(self, text="人脸验证", **btn_style,
                                  command=self.trigger_face_detection)
        self.face_btn.grid(row=0, column=7, columnspan=3, padx=5, pady=5, sticky="nsew")
        tk.Button(self, text="密码开锁", **btn_style,
                  command=lambda: controller.show_frame("PasswordPage"))\
            .grid(row=1, column=7, columnspan=3, padx=5, pady=5, sticky="nsew")
        tk.Button(self, text="指纹开锁", **btn_style,
                  command=lambda: controller.show_frame("FingerprintPage"))\
            .grid(row=2, column=7, columnspan=3, padx=5, pady=5, sticky="nsew")
        tk.Button(self, text="卡片开锁", **btn_style,
                  command=lambda: controller.show_frame("CardPage"))\
            .grid(row=3, column=7, columnspan=3, padx=5, pady=5, sticky="nsew")
        tk.Button(self, text="管理员", **btn_style,
                  command=lambda: controller.show_frame("AdminPage"))\
            .grid(row=4, column=7, columnspan=3, padx=5, pady=5, sticky="nsew")

        status_frame = tk.Frame(self, bg="#1e293b", relief="groove", bd=2)
        status_frame.grid(row=5, column=0, columnspan=7, padx=5, pady=5, sticky="nsew")
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=1)

        env_frame = tk.Frame(status_frame, bg="#1e293b")
        env_frame.grid(row=0, column=0, sticky="w", padx=10)
        self.temp_label = tk.Label(env_frame, text="🌡 25.0℃", font=("Arial", 20, "bold"),
                                   fg="white", bg="#1e293b")
        self.temp_label.pack(side="left", padx=5)
        self.hum_label = tk.Label(env_frame, text="💧 60%", font=("Arial", 20, "bold"),
                                  fg="white", bg="#1e293b")
        self.hum_label.pack(side="left", padx=5)
        self.light_label = tk.Label(env_frame, text="☀ 500", font=("Arial", 20, "bold"),
                                    fg="white", bg="#1e293b")
        self.light_label.pack(side="left", padx=5)
        self.rain_label = tk.Label(env_frame, text="🌧 无雨", font=("Arial", 20, "bold"),
                                   fg="#22c55e", bg="#1e293b")
        self.rain_label.pack(side="left", padx=5)
        
        self.refresh_btn = tk.Button(env_frame, text="🔄 刷新", font=("Arial", 14, "bold"),
                                     bg="#2563eb", fg="white", activebackground="#1d4ed8",
                                     bd=0, padx=10, pady=2, command=self.refresh_camera)
        self.refresh_btn.pack(side="left", padx=5)

        dev_frame = tk.Frame(status_frame, bg="#1e293b")
        dev_frame.grid(row=0, column=1, sticky="e", padx=10)
        self.relay_label = tk.Label(dev_frame, text="🔌 继电器:关", font=("Arial", 20, "bold"),
                                    fg="white", bg="#1e293b")
        self.relay_label.pack(side="left", padx=5)
        self.buzzer_label = tk.Label(dev_frame, text="🔊 蜂鸣器:关", font=("Arial", 20, "bold"),
                                     fg="white", bg="#1e293b")
        self.buzzer_label.pack(side="left", padx=5)

        tk.Button(self, text="⏻ 关机", font=("Arial", 20, "bold"),
                  bg="#dc2626", fg="white", activebackground="#b91c1c", bd=0,
                  command=self.shutdown_system)\
            .grid(row=5, column=7, columnspan=3, padx=5, pady=5, sticky="nsew")

        self.cap = None
        self.camera_running = False
        self.after_id = None
        self.detecting = False
        self.last_detection_frame = None

        self.update_status()

    def on_show(self):
        self.refresh_camera()

    def refresh_camera(self):
        self.stop_camera()
        time.sleep(0.3)
        self.start_camera()

    def stop_camera(self):
        self.camera_running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
        self.video_label.config(image='')

    def start_camera(self):
        import platform
        sys_platform = platform.system()
        if sys_platform == "Windows":
            self.cap = cv2.VideoCapture(CAM_ID, cv2.CAP_DSHOW)
        else:
            device_path = f"/dev/video{CAM_ID}"
            self.cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(CAM_ID, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            print(f"摄像头打开失败 (ID={CAM_ID})")
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.camera_running = True
        self.update_video()

    def update_video(self):
        if not self.camera_running:
            return
        try:
            ret, frame = self.cap.read()
            if ret:
                self.video_label.update_idletasks()
                target_width = self.video_label.winfo_width()
                target_height = self.video_label.winfo_height()
                
                if target_width > 0 and target_height > 0:
                    frame_resized = cv2.resize(frame, (target_width, target_height))
                    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.video_label.imgtk = imgtk
                    self.video_label.configure(image=imgtk)
        except Exception as e:
            print(f"[ERR] 更新视频帧失败: {e}")
        self.after_id = self.after(50, self.update_video)

    def trigger_face_detection(self):
        if self.detecting:
            return
        
        self.detecting = True
        self.face_btn.config(text="检测中...", bg="#f59e0b", state="disabled")
        
        ret, frame = self.cap.read()
        if ret:
            t = threading.Thread(target=self._do_face_detection, args=(frame.copy(),), daemon=True)
            t.start()
        else:
            self.detecting = False
            self.face_btn.config(text="人脸验证", bg="#3b82f6", state="normal")

    def _do_face_detection(self, frame):
        try:
            name, face_locations = self.controller.face_recognizer.recognize(frame)
            
            if face_locations:
                top, right, bottom, left = face_locations
                cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
                cv2.putText(frame, name, (left, top-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
            
            if name != "Unknown" and name != "No Face" and name != "No DB":
                self.controller.sensors.set_relay(True)
                self.controller.record_door_event(name, "open")
                self.after(3000, lambda: self.controller.sensors.set_relay(False))
        except Exception as e:
            print(f"[ERR] 人脸检测失败: {e}")
        
        self.after(0, self._update_detection_result, frame)

    def _update_detection_result(self, frame):
        try:
            self.video_label.update_idletasks()
            target_width = self.video_label.winfo_width()
            target_height = self.video_label.winfo_height()
            
            if target_width > 0 and target_height > 0:
                frame_resized = cv2.resize(frame, (target_width, target_height))
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
        except Exception as e:
            print(f"[ERR] 更新检测结果失败: {e}")
        
        self.detecting = False
        self.face_btn.config(text="人脸验证", bg="#3b82f6", state="normal")

    def stop(self):
        self.stop_camera()

    def update_status(self):
        sensors = self.controller.sensors
        temp, hum = sensors.read_temperature_humidity()
        light = sensors.read_light()
        relay = sensors.get_relay_state()
        buzzer = sensors.get_buzzer_state()
        self.temp_label.config(text=f"🌡 {temp}℃")
        self.hum_label.config(text=f"💧 {hum}%")
        self.light_label.config(text=f"☀ {light}")
        self.relay_label.config(text=f"🔌 继电器:{'开' if relay else '关'}",
                                fg="green" if relay else "white")
        self.buzzer_label.config(text=f"🔊 蜂鸣器:{'开' if buzzer else '关'}",
                                fg="orange" if buzzer else "white")
        self.after(2000, self.update_status)

    def shutdown_system(self):
        if messagebox.askyesno("确认关机", "确定要关闭系统吗？"):
            top_win = self.winfo_toplevel()
            top_win.destroy()
            sys.exit(0)