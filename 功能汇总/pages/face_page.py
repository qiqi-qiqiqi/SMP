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
        self.last_recognized_name = None

        self.video_label = tk.Label(self, bg="black")
        self.video_label.pack(pady=10, expand=True, fill="both")

        self.result_label = tk.Label(self, text="识别结果: --", font=("Arial", 14),
                                     bg="white", fg="blue")
        self.result_label.pack(pady=5)

        self.status_label = tk.Label(self, text="", font=("Arial", 12),
                                     bg="white", fg="green")
        self.status_label.pack(pady=5)

        tk.Button(self, text="返回主页", width=10, height=2,
                  command=self.go_home, font=("Arial", 11)).pack(pady=10)

    def on_show(self):
        if not self.running:
            self.running = True
            self.last_recognized_name = None
            self.status_label.config(text="")
            self.recognizer.start_camera()
            self.update_frame()

    def stop(self):
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
                name, _ = self.recognizer.recognize(frame)
                self.result_label.config(text=f"识别结果: {name}")

                if name != "Unknown" and name != "No Face" and name != "No DB":
                    if name != self.last_recognized_name:
                        self.last_recognized_name = name
                        self.status_label.config(text=f"✅ 欢迎 {name}，门锁已打开")
                        self.controller.sensors.set_relay(True)
                        self.controller.record_door_event(name, "open")
                        self.after(3000, self.close_door)

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                img.thumbnail((780, 300))
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

            self.after_id = self.after(50, self.update_frame)

    def close_door(self):
        if self.running:
            self.controller.sensors.set_relay(False)
            self.status_label.config(text=f"🔒 门锁已关闭")