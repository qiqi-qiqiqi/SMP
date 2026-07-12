# pages/admin_page.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
from PIL import Image, ImageTk
from config import DB_FILE, NAME_FILE

class AdminPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#0f172a")
        self.controller = controller

        # ========== 登录界面 ==========
        self.login_frame = tk.Frame(self, bg="#0f172a")
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(self.login_frame, text="⚙️ 管理员登录", font=("Arial", 22, "bold"),
                 bg="#0f172a", fg="white").pack(pady=(0, 15))

        # 密码输入框
        entry_frame = tk.Frame(self.login_frame, bg="#1e293b", relief="solid", bd=2, padx=15, pady=10)
        entry_frame.pack(pady=5)
        tk.Label(entry_frame, text="请输入管理员密码", font=("Arial", 12),
                 bg="#1e293b", fg="#94a3b8").pack(anchor="w")
        self.pwd_var = tk.StringVar()
        self.pwd_entry = tk.Entry(entry_frame, textvariable=self.pwd_var, font=("Arial", 18),
                                  show="●", justify="center", width=12, bd=0, bg="#1e293b",
                                  fg="white", insertbackground="white")
        self.pwd_entry.pack(pady=8)

        # 数字键盘 (加大按钮)
        btn_frame = tk.Frame(self.login_frame, bg="#0f172a")
        btn_frame.pack(pady=10)

        buttons = [
            ('1',0,0), ('2',0,1), ('3',0,2),
            ('4',1,0), ('5',1,1), ('6',1,2),
            ('7',2,0), ('8',2,1), ('9',2,2),
            ('⌫',3,0), ('0',3,1), ('✓',3,2),
        ]
        btn_style = {"font": ("Arial", 14, "bold"), "bg": "#334155", "fg": "white",
                     "activebackground": "#475569", "activeforeground": "white",
                     "bd": 0, "padx": 12, "pady": 10, "width": 3}

        for (text, row, col) in buttons:
            if text == '✓':
                cmd = self.login
            elif text == '⌫':
                cmd = lambda: self.pwd_var.set(self.pwd_var.get()[:-1])
            else:
                cmd = lambda t=text: self.pwd_var.set(self.pwd_var.get() + t)
            tk.Button(btn_frame, text=text, **btn_style, command=cmd)\
                .grid(row=row, column=col, padx=4, pady=4)

        self.login_msg = tk.Label(self.login_frame, text="", fg="#ef4444", bg="#0f172a",
                                  font=("Arial", 12, "bold"))
        self.login_msg.pack(pady=5)

        tk.Button(self.login_frame, text="← 返回主页", font=("Arial", 12, "bold"),
                  bg="#475569", fg="white", bd=0, padx=20, pady=8,
                  activebackground="#64748b",
                  command=lambda: controller.show_frame("HomePage")).pack(pady=(10,0))

        # ========== 管理功能界面 ==========
        self.admin_frame = tk.Frame(self, bg="#0f172a")
        # 两列，权重分配左6右4（让控制区宽一些）
        self.admin_frame.columnconfigure(0, weight=3)
        self.admin_frame.columnconfigure(1, weight=2)
        self.admin_frame.rowconfigure(0, weight=1)
        self.admin_frame.rowconfigure(1, weight=1)
        self.admin_frame.rowconfigure(2, weight=0)

        # ----- 左侧：门锁控制 + 修改密码 (上下各占一行) -----
        # 门锁控制卡片
        lock_frame = tk.LabelFrame(self.admin_frame, text="🔒 门锁控制", font=("Arial", 14, "bold"),
                                   bg="#1e293b", fg="white", padx=15, pady=15,
                                   relief="solid", bd=1)
        lock_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.lock_status = tk.Label(lock_frame, text="当前状态：关闭", font=("Arial", 18, "bold"),
                                    bg="#1e293b", fg="#ef4444")
        self.lock_status.pack(pady=10)
        btn_lock_frame = tk.Frame(lock_frame, bg="#1e293b")
        btn_lock_frame.pack()
        tk.Button(btn_lock_frame, text="开 门", font=("Arial", 14, "bold"), bg="#10b981",
                  fg="white", bd=0, padx=20, pady=8, activebackground="#059669",
                  command=self.open_door).pack(side="left", padx=10)
        tk.Button(btn_lock_frame, text="关 门", font=("Arial", 14, "bold"), bg="#ef4444",
                  fg="white", bd=0, padx=20, pady=8, activebackground="#dc2626",
                  command=self.close_door).pack(side="left", padx=10)

        # 修改密码卡片
        pwd_frame = tk.LabelFrame(self.admin_frame, text="🔑 修改门锁密码", font=("Arial", 14, "bold"),
                                  bg="#1e293b", fg="white", padx=15, pady=15,
                                  relief="solid", bd=1)
        pwd_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        # 旧密码
        tk.Label(pwd_frame, text="旧密码", font=("Arial", 12), bg="#1e293b", fg="#94a3b8")\
            .grid(row=0, column=0, sticky="w", pady=5)
        self.old_pwd = tk.StringVar()
        tk.Entry(pwd_frame, textvariable=self.old_pwd, font=("Arial", 14), show="●",
                 width=16, bg="#334155", fg="white", insertbackground="white", bd=0)\
            .grid(row=0, column=1, padx=10, pady=5)
        # 新密码
        tk.Label(pwd_frame, text="新密码", font=("Arial", 12), bg="#1e293b", fg="#94a3b8")\
            .grid(row=1, column=0, sticky="w", pady=5)
        self.new_pwd = tk.StringVar()
        tk.Entry(pwd_frame, textvariable=self.new_pwd, font=("Arial", 14), show="●",
                 width=16, bg="#334155", fg="white", insertbackground="white", bd=0)\
            .grid(row=1, column=1, padx=10, pady=5)
        tk.Button(pwd_frame, text="确认修改", font=("Arial", 12, "bold"), bg="#3b82f6",
                  fg="white", bd=0, padx=15, pady=5, activebackground="#2563eb",
                  command=self.change_door_pwd)\
            .grid(row=2, column=0, columnspan=2, pady=15)
        self.change_msg = tk.Label(pwd_frame, text="", font=("Arial", 10), bg="#1e293b", fg="#ef4444")
        self.change_msg.grid(row=3, column=0, columnspan=2)

        # ----- 右侧：人脸管理 (跨上下两行) -----
        face_frame = tk.LabelFrame(self.admin_frame, text="📷 人脸库管理", font=("Arial", 14, "bold"),
                                   bg="#1e293b", fg="white", padx=15, pady=15,
                                   relief="solid", bd=1)
        face_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")

        # 人物选择行
        row_frame = tk.Frame(face_frame, bg="#1e293b")
        row_frame.pack(fill="x", pady=5)
        tk.Label(row_frame, text="人物", font=("Arial", 12), bg="#1e293b", fg="#94a3b8")\
            .pack(side="left")
        self.face_name_var = tk.StringVar()
        self.comb_face_name = ttk.Combobox(row_frame, textvariable=self.face_name_var,
                                           font=("Arial", 11), width=12, state="readonly")
        self.comb_face_name['values'] = self._get_existing_people()
        self.comb_face_name.pack(side="left", padx=5)
        tk.Button(row_frame, text="新增", font=("Arial", 10), bg="#10b981", fg="white",
                  bd=0, padx=10, pady=2, command=self.add_new_person).pack(side="left")

        # 四个功能按钮
        btn_frame_f = tk.Frame(face_frame, bg="#1e293b")
        btn_frame_f.pack(pady=15)
        btn_cfg = {"font": ("Arial", 11, "bold"), "bg": "#3b82f6", "fg": "white",
                   "activebackground": "#2563eb", "bd": 0, "padx": 10, "pady": 6, "width": 12}
        tk.Button(btn_frame_f, text="采集人脸", **btn_cfg, command=self.capture_face)\
            .grid(row=0, column=0, padx=4, pady=4)
        tk.Button(btn_frame_f, text="训练库", **btn_cfg, command=self.train_db)\
            .grid(row=0, column=1, padx=4, pady=4)
        tk.Button(btn_frame_f, text="实时检验", **btn_cfg, command=self.test_realtime)\
            .grid(row=1, column=0, padx=4, pady=4)
        tk.Button(btn_frame_f, text="图片检验", **btn_cfg, command=self.test_image)\
            .grid(row=1, column=1, padx=4, pady=4)

        btn_frame_f.columnconfigure(0, weight=1)
        btn_frame_f.columnconfigure(1, weight=1)

        self.face_msg = tk.Label(face_frame, text="", font=("Arial", 10), bg="#1e293b", fg="#22c55e")
        self.face_msg.pack(pady=5)

        # ----- 底部：退出登录按钮 -----
        tk.Button(self.admin_frame, text="退出登录", font=("Arial", 12, "bold"),
                  bg="#ef4444", fg="white", bd=0, padx=25, pady=8,
                  activebackground="#dc2626", command=self.logout)\
            .grid(row=2, column=0, columnspan=2, pady=10)

    # ---------- 登录管理 ----------
    def login(self):
        if self.controller.pwd_manager.check_admin_password(self.pwd_var.get()):
            self.login_frame.place_forget()
            self.admin_frame.pack(expand=True, fill="both", padx=10, pady=10)
            self.update_lock_status()
            self.comb_face_name['values'] = self._get_existing_people()
        else:
            self.login_msg.config(text="❌ 密码错误")

    def logout(self):
        self.admin_frame.pack_forget()
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.pwd_var.set("")
        self.login_msg.config(text="")

    # ---------- 门锁控制 ----------
    def update_lock_status(self):
        state = self.controller.sensors.get_relay_state()
        self.lock_status.config(text=f"当前状态：{'开启' if state else '关闭'}",
                                fg="#10b981" if state else "#ef4444")

    def open_door(self):
        self.controller.sensors.set_relay(True)
        self.update_lock_status()

    def close_door(self):
        self.controller.sensors.set_relay(False)
        self.update_lock_status()

    # ---------- 修改密码 ----------
    def change_door_pwd(self):
        old = self.old_pwd.get()
        new = self.new_pwd.get()
        if not new:
            self.change_msg.config(text="新密码不能为空")
            return
        if self.controller.pwd_manager.change_door_password(old, new):
            self.change_msg.config(text="✅ 密码修改成功", fg="#22c55e")
            self.old_pwd.set("")
            self.new_pwd.set("")
        else:
            self.change_msg.config(text="❌ 旧密码错误", fg="#ef4444")

    # ---------- 人脸管理辅助方法 ----------
    def _get_existing_people(self):
        dataset = "./dataset"
        if not os.path.exists(dataset):
            return []
        return [d for d in os.listdir(dataset) if os.path.isdir(os.path.join(dataset, d))]

    def add_new_person(self):
        name = simpledialog.askstring("新增人物", "输入人物名称（英文/拼音）:")
        if not name:
            return
        if any(c in name for c in [" ", "/", "\\", ":", "*", "?", "\"", "<", ">", "|"]):
            messagebox.showerror("错误", "名称包含非法字符")
            return
        folder = os.path.join("dataset", name)
        if os.path.exists(folder):
            messagebox.showinfo("提示", "该人物已存在")
            return
        os.makedirs(folder)
        self.comb_face_name['values'] = self._get_existing_people()
        self.face_name_var.set(name)
        self.face_msg.config(text=f"人物 {name} 已创建")

    def capture_face(self):
        name = self.face_name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请先选择或新增人物名称")
            return
        self.face_msg.config(text="采集人脸中，请在弹出的窗口中拍照...")
        self.update()
        ok = self.controller.face_recognizer.capture_faces(name)
        if ok:
            self.face_msg.config(text=f"采集完成，保存在 dataset/{name}/")
        else:
            self.face_msg.config(text="采集取消或失败")

    def train_db(self):
        self.face_msg.config(text="正在训练特征库...")
        self.update()
        ok = self.controller.face_recognizer.build_database()
        if ok:
            self.face_msg.config(text="✅ 特征库训练完成！")
        else:
            self.face_msg.config(text="训练失败，检查 dataset 文件夹")

    def test_realtime(self):
        if not os.path.exists(DB_FILE) or not os.path.exists(NAME_FILE):
            messagebox.showwarning("提示", "请先训练特征库！")
            return
        self.face_msg.config(text="启动实时识别窗口，ESC/关闭窗口返回")
        self.update()
        self.controller.face_recognizer.test_realtime()
        self.face_msg.config(text="实时识别已结束")

    def test_image(self):
        if not os.path.exists(DB_FILE) or not os.path.exists(NAME_FILE):
            messagebox.showwarning("提示", "请先训练特征库！")
            return
        test_path = "./test.jpg"
        if not os.path.exists(test_path):
            messagebox.showerror("错误", f"未找到 {test_path}")
            return
        output = self.controller.face_recognizer.recognize_image(test_path)
        if output:
            self.show_result_image(output)
            self.face_msg.config(text="图片检验完成")
        else:
            messagebox.showerror("错误", "识别失败")

    def show_result_image(self, path):
        result_win = tk.Toplevel(self)
        result_win.title("检验结果")
        result_win.geometry("700x550")
        result_win.configure(bg="#1e293b")
        try:
            img = Image.open(path)
            img.thumbnail((680, 500))
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(result_win, image=photo, bg="#1e293b")
            lbl.image = photo
            lbl.pack(pady=10)
        except Exception as e:
            messagebox.showerror("错误", f"无法显示图片：{e}")
            result_win.destroy()
            return
        tk.Button(result_win, text="关闭", command=result_win.destroy,
                  font=("Arial", 12), bg="#ef4444", fg="white").pack(pady=10)

    def on_show(self):
        self.admin_frame.pack_forget()
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")
        self.pwd_var.set("")
        self.login_msg.config(text="")
        self.face_msg.config(text="")