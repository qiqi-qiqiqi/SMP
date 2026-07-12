# gui_main.py
import tkinter as tk
from pages.home_page import HomePage
from pages.password_page import PasswordPage
from pages.fingerprint_page import FingerprintPage
from pages.card_page import CardPage
from pages.admin_page import AdminPage
from sensors import Sensors
from password_auth import PasswordManager
from face_recognizer import FaceRecognizer

class SmartDoorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("智慧门禁系统")
        self.geometry("800x480")
        # 非全屏，便于调试，树莓派上可开启全屏
        self.attributes("-fullscreen", True)

        self.sensors = Sensors()
        self.pwd_manager = PasswordManager()
        self.face_recognizer = FaceRecognizer()

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for PageClass in (HomePage, PasswordPage, FingerprintPage, CardPage, AdminPage):
            page_name = PageClass.__name__
            frame = PageClass(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.current_page = None
        self.show_frame("HomePage")

    def show_frame(self, page_name):
        # 停止当前页面的摄像头（如果有）
        if self.current_page and hasattr(self.frames[self.current_page], 'stop_camera'):
            self.frames[self.current_page].stop_camera()
        frame = self.frames[page_name]
        frame.tkraise()
        self.current_page = page_name
        if hasattr(frame, 'on_show'):
            frame.on_show()

    def cleanup(self):
        self.sensors.cleanup()
        self.face_recognizer.stop_camera()
        self.destroy()

if __name__ == "__main__":
    app = SmartDoorApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.cleanup()