"""Simple Windows UI for AnkiRead."""

from __future__ import annotations

import datetime as dt
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from anki_read_app import find_anki
from anki_today import local_collection, read_cards, render_period_report, render_report


class AnkiReadWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("AnkiRead - Anki 学习记录")
        root.geometry("620x430")
        root.minsize(560, 380)
        self.days = tk.StringVar(value="5")
        self.profile = tk.StringVar()
        self.deck = tk.StringVar()
        self.anki_path = tk.StringVar(value=r"D:\Anki\anki.exe")
        self.wait = tk.StringVar(value="45")
        self.output = tk.StringVar(value="last_5_days.md")
        self.status = tk.StringVar(value="准备就绪")
        self.build()

    def build(self):
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="AnkiRead", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="手机同步到 AnkiWeb 后，启动 Anki 并生成学习报告").grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 16))
        fields = [
            ("统计天数", self.days), ("Anki 配置", self.profile),
            ("牌组（留空=全部）", self.deck), ("等待同步秒数", self.wait),
            ("输出文件", self.output),
        ]
        for row, (label, variable) in enumerate(fields, start=2):
            ttk.Label(frame, text=label, width=20).grid(row=row, column=0, sticky="w", pady=5)
            ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, columnspan=2, sticky="ew", pady=5)
        ttk.Label(frame, text="anki.exe 路径", width=20).grid(row=7, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.anki_path).grid(row=7, column=1, sticky="ew", pady=5)
        ttk.Button(frame, text="浏览", command=self.choose_anki).grid(row=7, column=2, padx=(8, 0))
        self.run_button = ttk.Button(frame, text="启动 Anki、同步并生成报告", command=self.run)
        self.run_button.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(18, 8))
        ttk.Label(frame, textvariable=self.status, foreground="#555").grid(row=9, column=0, columnspan=3, sticky="w")
        frame.columnconfigure(1, weight=1)

    def choose_anki(self):
        path = filedialog.askopenfilename(title="选择 anki.exe", filetypes=[("Anki", "anki.exe"), ("程序", "*.exe")])
        if path:
            self.anki_path.set(path)

    def run(self):
        try:
            days = int(self.days.get())
            wait = int(self.wait.get())
            if days < 1 or wait < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "统计天数必须为正整数，等待秒数不能为负数。")
            return
        self.run_button.configure(state="disabled")
        threading.Thread(target=self.worker, args=(days, wait), daemon=True).start()

    def worker(self, days: int, wait: int):
        try:
            self.set_status("检查 Anki 进程……")
            tasklist = subprocess.run(["tasklist", "/FI", "IMAGENAME eq anki.exe"], capture_output=True, text=True)
            if "anki.exe" in tasklist.stdout.lower():
                raise RuntimeError("Anki 已经在运行，请先关闭 Anki 后再点击按钮。")
            anki = find_anki(self.anki_path.get().strip() or None)
            process = subprocess.Popen([str(anki)])
            self.set_status(f"已启动 Anki，等待 {wait} 秒同步……")
            import time
            time.sleep(wait)
            close_script = "$p=Get-Process -Id %d -ErrorAction SilentlyContinue; if ($p) { $p.CloseMainWindow() | Out-Null; if (-not $p.WaitForExit(120000)) { exit 2 } }" % process.pid
            if subprocess.run(["powershell", "-NoProfile", "-Command", close_script]).returncode != 0:
                raise RuntimeError("Anki 未能正常关闭，数据库可能仍被占用。")
            source = local_collection(self.profile.get().strip() or None)
            today = dt.date.today()
            reports = [(today - dt.timedelta(days=i), []) for i in range(days - 1, -1, -1)]
            reports = [(day, read_cards(source, day, self.deck.get().strip() or None)) for day, _ in reports]
            output = Path(self.output.get().strip() or f"last_{days}_days.md")
            if days == 1:
                content = render_report(reports[0][1], today, source)
            else:
                content = render_period_report(reports, source)
            output.write_text(content, encoding="utf-8")
            self.set_status(f"完成：{output}，共 {sum(len(c) for _, c in reports)} 张卡片记录")
            self.root.after(0, lambda: messagebox.showinfo("完成", f"报告已生成：\n{output}"))
        except Exception as error:
            self.set_status("执行失败")
            self.root.after(0, lambda: messagebox.showerror("执行失败", str(error)))
        finally:
            self.root.after(0, lambda: self.run_button.configure(state="normal"))

    def set_status(self, text: str):
        self.root.after(0, lambda: self.status.set(text))


if __name__ == "__main__":
    app = tk.Tk()
    AnkiReadWindow(app)
    app.mainloop()

