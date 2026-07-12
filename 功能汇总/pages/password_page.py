# pages/password_page.py
import tkinter as tk

class PasswordPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        self.controller = controller
        self.input_var = tk.StringVar()

        container = tk.Frame(self, bg="white")
        container.pack(expand=True, fill="both", padx=40, pady=40)

        tk.Label(container, text="🔐 密码开锁", font=("Microsoft YaHei", 22, "bold"),
                 bg="white", fg="#1e293b").pack(pady=(0, 20))

        entry_frame = tk.Frame(container, bg="#f8fafc", relief="solid", bd=2, padx=20, pady=15)
        entry_frame.pack(pady=10)
        tk.Label(entry_frame, text="请输入密码", font=("Microsoft YaHei", 12), bg="#f8fafc", fg="#64748b").pack(anchor="w")
        self.entry = tk.Entry(entry_frame, textvariable=self.input_var, font=("Microsoft YaHei", 18),
                              show="●", justify="center", width=14, bd=0, bg="#f8fafc")
        self.entry.pack(pady=10)

        btn_frame = tk.Frame(container, bg="white")
        btn_frame.pack(pady=20)

        buttons = [
            ('1',0,0), ('2',0,1), ('3',0,2),
            ('4',1,0), ('5',1,1), ('6',1,2),
            ('7',2,0), ('8',2,1), ('9',2,2),
            ('⌫',3,0), ('0',3,1), ('✓',3,2),
        ]
        btn_style = {"font": ("Microsoft YaHei", 14, "bold"), "bg": "#e2e8f0",
                     "activebackground": "#cbd5e1", "bd": 0, "padx": 15, "pady": 10,
                     "width": 3, "height": 1}

        for (text, row, col) in buttons:
            if text == '✓':
                cmd = self.verify_password
            elif text == '⌫':
                cmd = lambda: self.input_var.set(self.input_var.get()[:-1])
            else:
                cmd = lambda t=text: self.input_var.set(self.input_var.get() + t)
            tk.Button(btn_frame, text=text, **btn_style, command=cmd)\
                .grid(row=row, column=col, padx=5, pady=5)

        self.message = tk.Label(container, text="", font=("Microsoft YaHei", 12, "bold"), bg="white")
        self.message.pack(pady=(10, 15))

        tk.Button(container, text="← 返回主页", font=("Microsoft YaHei", 12),
                  bg="#94a3b8", fg="white", bd=0, padx=15, pady=6,
                  activebackground="#64748b",
                  command=lambda: controller.show_frame("HomePage")).pack()

    def verify_password(self):
        pwd = self.input_var.get()
        if not pwd:
            self.message.config(text="请输入密码！", fg="red")
            return
        if self.controller.pwd_manager.check_door_password(pwd):
            self.message.config(text="✅ 密码正确，开锁成功！", fg="green")
            self.controller.sensors.set_relay(True)
            self.controller.record_door_event("Password_User", "open")
            self.after(3000, self.return_home)
        else:
            self.message.config(text="❌ 密码错误，请重试", fg="red")
            self.input_var.set("")

    def return_home(self):
        self.controller.sensors.set_relay(False)
        self.controller.show_frame("HomePage")

    def on_show(self):
        self.input_var.set("")
        self.message.config(text="")