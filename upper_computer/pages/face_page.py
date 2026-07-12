# pages/face_page.py
import tkinter as tk
from PIL import Image, ImageTk
import cv2

class FacePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        self.controller = controller
        self.recognizer = controller.face_recognizer
        self.running = False
        self.after_id = None

        # 视频显示区
        self.video_label = tk.Label(self, bg="black")
        self.video_label.pack(pady=10, expand=True, fill="both")

        # 识别结果
        self.result_label = tk.Label(self, text="识别结果: --", font=("Arial", 14),
                                     bg="white", fg="blue")
        self.result_label.pack(pady=5)

        # 按钮
        tk.Button(self, text="返回主页", width=10, height=2,
                  command=self.go_home, font=("Arial", 11)).pack(pady=10)

    def on_show(self):
        """页面显示时自动启动识别"""
        if not self.running:
            self.running = True
            self.recognizer.start_camera()
            self.update_frame()

    def stop(self):
        """停止摄像头和定时器，供外部调用"""
        self.running = False
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.recognizer.stop_camera()
        self.video_label.config(image='')

    def go_home(self):
        self.stop()
        self.controller.show_frame("HomePage")

    def update_frame(self):
        if self.running:
            ret, frame = self.recognizer.get_frame()
            if ret:
                # 识别（隔帧识别可减轻 CPU 负担，这里每帧识别，树莓派可能需降帧）
                name, _ = self.recognizer.recognize(frame)
                self.result_label.config(text=f"识别结果: {name}")

                # 转换并显示
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                # 保持比例缩放到适合显示区域（宽度780，高度约300）
                img.thumbnail((780, 300))
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

            self.after_id = self.after(30, self.update_frame)