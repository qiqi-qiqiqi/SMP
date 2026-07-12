# pages/card_page.py
import tkinter as tk

class CardPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        self.controller = controller
        container = tk.Frame(self, bg="white")
        container.pack(expand=True)
        tk.Label(container, text="💳 卡片开锁", font=("Microsoft YaHei", 20, "bold"),
                 bg="white", fg="#1e293b").pack(pady=20)
        tk.Label(container, text="请刷卡...", font=("Microsoft YaHei", 14),
                 bg="white", fg="#64748b").pack(pady=10)
        tk.Button(container, text="← 返回主页", font=("Microsoft YaHei", 12),
                  bg="#94a3b8", fg="white", bd=0, padx=15, pady=6,
                  command=lambda: controller.show_frame("HomePage")).pack(pady=20)