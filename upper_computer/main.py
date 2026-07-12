# main.py
from gui_main import SmartDoorApp

if __name__ == "__main__":
    app = SmartDoorApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.cleanup()