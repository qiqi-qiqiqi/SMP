# gui_main.py
import tkinter as tk
import time
from pages.home_page import HomePage
from pages.face_page import FacePage
from pages.password_page import PasswordPage
from pages.admin_page import AdminPage
from pages.card_page import CardPage
from pages.fingerprint_page import FingerprintPage
from sensors import Sensors
from password_auth import PasswordManager
from face_recognizer import FaceRecognizer
from mqtt_client import MQTTClient

class SmartDoorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("智慧门禁系统")
        self.geometry("800x480")
        self.attributes("-fullscreen", True)

        self.sensors = Sensors()
        self.pwd_manager = PasswordManager()
        self.face_recognizer = FaceRecognizer()
        self.mqtt_client = MQTTClient(sensors=self.sensors, on_command_received=self.on_command_received)
        self.mqtt_client.connect()

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for PageClass in (HomePage, FacePage, PasswordPage, AdminPage, CardPage, FingerprintPage):
            page_name = PageClass.__name__
            frame = PageClass(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.current_page = None
        self.show_frame("HomePage")

        self.last_command = ""

    def show_frame(self, page_name):
        if self.current_page and hasattr(self.frames[self.current_page], 'stop'):
            self.frames[self.current_page].stop()
        
        self._show_frame_delayed(page_name)
    
    def _show_frame_delayed(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        self.current_page = page_name
        if hasattr(frame, 'on_show'):
            frame.on_show()

    def on_command_received(self, command_name, paras):
        self.last_command = f"{command_name}: {paras}"
        print(f"[CMD] 收到命令: {self.last_command}")

    def record_door_event(self, person, action):
        if self.mqtt_client:
            self.mqtt_client.update_door_event(person, action)

    def cleanup(self):
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        self.sensors.cleanup()
        self.face_recognizer.stop_camera()
        self.destroy()

if __name__ == "__main__":
    app = SmartDoorApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.cleanup()