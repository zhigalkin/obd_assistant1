"""
OBD-II Диагностика — Современный интерфейс (CustomTkinter)
Запуск: python main.py
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🚗 OBD-II Диагностика")
        self.geometry("1200x750")
        self.minsize(1000, 600)

        # Состояние
        self.connection = None
        self.live_running = False
        self.live_thread = None
        self.car_brand = ctk.StringVar(value=config.CAR_BRAND)
        self.port_var = ctk.StringVar(value=config.OBD_PORT or "COM3")
        self.api_key_var = ctk.StringVar(value=config.OPENAI_API_KEY)

        self._build_ui()

    def _build_ui(self):
        # Grid layout: sidebar + content
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar (левая панель навигации)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(self.sidebar, text="🚗 OBD Диагностика", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, padx=20, pady=20)

        self.nav_buttons = {}
        nav_items = [
            ("📡 Живые данные", self._show_live),
            ("🔍 Сканирование", self._show_scan),
            ("⚠️ Коды ошибок", self._show_dtc),
            ("📚 История", self._show_history),
            ("⚙️ Настройки", self._show_settings),
        ]
        for idx, (text, cmd) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(self.sidebar, text=text, command=cmd, font=("Segoe UI", 14), anchor="w")
            btn.grid(row=idx, column=0, padx=10, pady=5, sticky="ew")
            self.nav_buttons[text] = btn

        # Статус подключения
        ctk.CTkLabel(self.sidebar, text="Статус:", font=("Segoe UI", 12)).grid(row=7, column=0, padx=20, pady=(20, 5), sticky="w")
        self.status_label = ctk.CTkLabel(self.sidebar, text="● Не подключено", font=("Segoe UI", 12, "bold"), text_color="#e74c3c")
        self.status_label.grid(row=8, column=0, padx=20, pady=(0, 10), sticky="w")

        # Правая панель контента
        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.content.grid_rowconfigure(1, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        # Top bar (подключение)
        self.topbar = ctk.CTkFrame(self.content)
        self.topbar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(self.topbar, text="Порт:", font=("Segoe UI", 12)).pack(side="left", padx=(5, 2))
        ctk.CTkEntry(self.topbar, textvariable=self.port_var, width=100).pack(side="left", padx=5)

        ctk.CTkLabel(self.topbar, text="Марка:", font=("Segoe UI", 12)).pack(side="left", padx=(10, 2))
        ctk.CTkComboBox(self.topbar, variable=self.car_brand, values=["generic", "audi_vag", "bmw", "jaguar"], width=120).pack(side="left", padx=5)

        ctk.CTkButton(self.topbar, text="🔌 Подключиться", command=self._connect, fg_color="#2ecc71", hover_color="#27ae60").pack(side="left", padx=5)
        ctk.CTkButton(self.topbar, text="⛔ Отключить", command=self._disconnect, fg_color="#e74c3c", hover_color="#c0392b").pack(side="left", padx=5)

        # Frames для контента
        self.frames = {}
        self._create_frames()
        self._show_live()

    def _create_frames(self):
        self.frames['live'] = LiveFrame(self.content, self)
        self.frames['scan'] = ScanFrame(self.content, self)
        self.frames['dtc'] = DTCFrame(self.content, self)
        self.frames['history'] = HistoryFrame(self.content, self)
        self.frames['settings'] = SettingsFrame(self.content, self)

    def _show_frame(self, name):
        for f in self.frames.values():
            f.grid_forget()
        self.frames[name].grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def _show_live(self): self._show_frame('live')
    def _show_scan(self): self._show_frame('scan')
    def _show_dtc(self): self._show_frame('dtc')
    def _show_history(self): self._show_frame('history')
    def _show_settings(self): self._show_frame('settings')

    def _connect(self):
        def _do():
            try:
                from obd_reader import OBDReader
                self.reader = OBDReader(port=self.port_var.get(), car_brand=self.car_brand.get())
                ok = self.reader.connect()
                if ok:
                    self.after(0, lambda: self.status_label.configure(text="● Подключено", text_color="#2ecc71"))
                else:
                    self.after(0, lambda: self.status_label.configure(text="● Ошибка", text_color="#e74c3c"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        threading.Thread(target=_do, daemon=True).start()

    def _disconnect(self):
        if hasattr(self, 'reader') and self.reader:
            self.reader.disconnect()
        self.status_label.configure(text="● Не подключено", text_color="#e74c3c")


# ─── FRAMES ──────────────────────────────────────────────────────────────────

class LiveFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(top, text="▶ Запустить", command=self._start, fg_color="#2ecc71").pack(side="left", padx=5)
        ctk.CTkButton(top, text="⏹ Остановить", command=self._stop, fg_color="#e74c3c").pack(side="left", padx=5)

        self.text = ctk.CTkTextbox(self, font=("Consolas", 11))
        self.text.grid(row=1, column=0, sticky="nsew")

    def _start(self):
        if not hasattr(self.app, 'reader') or not self.app.reader.is_connected():
            messagebox.showwarning("Нет подключения", "Сначала подключитесь")
            return
        self.app.live_running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _stop(self):
        self.app.live_running = False

    def _loop(self):
        while self.app.live_running:
            try:
                readings = self.app.reader.read_all_standard()
                output = ""
                for r in readings:
                    status = f"⚠ {r.anomaly_msg}" if r.anomaly else "✓"
                    output += f"{r.name}: {r.display_value} {r.unit}  {status}\n"
                self.app.after(0, lambda o=output: self._update(o))
            except Exception as e:
                logger.error("Live error: %s", e)
            time.sleep(1)

    def _update(self, text):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)


class ScanFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._last_scan = None

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(top, text="🔍 Сканировать", command=self._scan, fg_color="#3498db").pack(side="left", padx=5)
        ctk.CTkButton(top, text="🤖 AI Анализ", command=self._ai, fg_color="#9b59b6").pack(side="left", padx=5)
        ctk.CTkButton(top, text="💾 Экспорт", command=self._export, fg_color="#2ecc71").pack(side="left", padx=5)

        self.text = ctk.CTkTextbox(self, font=("Consolas", 11))
        self.text.grid(row=1, column=0, sticky="nsew")

    def _scan(self):
        if not hasattr(self.app, 'reader') or not self.app.reader.is_connected():
            messagebox.showwarning("Нет подключения", "Подключитесь к адаптеру")
            return

        def _do():
            self.app.after(0, lambda: self._log("\n=== СКАНИРОВАНИЕ ===\n"))
            try:
                scan_data = self.app.reader.full_scan()
                self._last_scan = scan_data
                from database import Database
                db = Database(config.DB_PATH)
                db.save_session(scan_data)
                self.app.after(0, lambda: self._display(scan_data))
            except Exception as e:
                self.app.after(0, lambda: self._log(f"❌ Ошибка: {e}\n"))
        threading.Thread(target=_do, daemon=True).start()

    def _display(self, data):
        self.text.delete("1.0", "end")
        self._log(f"=== ОТЧЁТ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} ===\n\n")
        if data.get('vin'):
            self._log(f"VIN: {data['vin']}\n")
        if data.get('battery_voltage'):
            self._log(f"АКБ: {data['battery_voltage']:.2f} В\n")
        self._log("\n--- ДАТЧИКИ ---\n")
        for r in data.get('readings', []):
            if hasattr(r, 'anomaly'):
                line = f"{r.name}: {r.display_value} {r.unit}"
                if r.anomaly:
                    line += f"  ⚠ {r.anomaly_msg}"
                self._log(line + "\n")

    def _ai(self):
        if not self._last_scan:
            messagebox.showwarning("Нет данных", "Сначала выполните сканирование")
            return

        def _do():
            self.app.after(0, lambda: self._log("\n🤖 AI анализ...\n"))
            from analyzer import analyze_scan
            result = analyze_scan(self._last_scan, api_key=self.app.api_key_var.get())
            self.app.after(0, lambda: self._log(f"\n=== AI ===\n{result}\n"))
        threading.Thread(target=_do, daemon=True).start()

    def _export(self):
        content = self.text.get("1.0", "end")
        os.makedirs(config.REPORTS_DIR, exist_ok=True)
        fname = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=fname, filetypes=[("Text", "*.txt")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Сохранено", f"Отчёт: {path}")

    def _log(self, text):
        self.text.insert("end", text)
        self.text.see("end")


class DTCFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._dtc = []

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(top, text="📋 Считать", command=self._read, fg_color="#3498db").pack(side="left", padx=5)
        ctk.CTkButton(top, text="🤖 AI", command=self._ai, fg_color="#9b59b6").pack(side="left", padx=5)
        ctk.CTkButton(top, text="🗑 Сбросить", command=self._clear, fg_color="#e74c3c").pack(side="left", padx=5)

        self.text = ctk.CTkTextbox(self, font=("Consolas", 11))
        self.text.grid(row=1, column=0, sticky="nsew")

    def _read(self):
        if not hasattr(self.app, 'reader') or not self.app.reader.is_connected():
            messagebox.showwarning("Нет подключения", "Подключитесь")
            return

        def _do():
            dtc = self.app.reader.read_dtc()
            self._dtc = dtc
            self.app.after(0, lambda: self._display(dtc))
        threading.Thread(target=_do, daemon=True).start()

    def _display(self, dtc_list):
        self.text.delete("1.0", "end")
        if not dtc_list:
            self.text.insert("1.0", "✅ Ошибок не найдено\n")
            return
        for d in dtc_list:
            self.text.insert("end", f"{d.get('code', '?')}: {d.get('description', '?')} ({d.get('type', '?')})\n")

    def _ai(self):
        if not self._dtc:
            messagebox.showwarning("Нет данных", "Сначала считайте ошибки")
            return

        def _do():
            from analyzer import analyze_dtc_only
            result = analyze_dtc_only(self._dtc, api_key=self.app.api_key_var.get())
            self.app.after(0, lambda: self.text.insert("end", f"\n=== AI ===\n{result}\n"))
        threading.Thread(target=_do, daemon=True).start()

    def _clear(self):
        if messagebox.askyesno("Подтверждение", "Сбросить коды ошибок?"):
            self.app.reader.clear_dtc()
            self.text.delete("1.0", "end")
            messagebox.showinfo("Готово", "Коды сброшены")


class HistoryFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(top, text="🔄 Обновить", command=self._load, fg_color="#3498db").pack(side="left", padx=5)

        self.text = ctk.CTkTextbox(self, font=("Consolas", 11))
        self.text.grid(row=1, column=0, sticky="nsew")

    def _load(self):
        try:
            from database import Database
            db = Database(config.DB_PATH)
            sessions = db.get_sessions(limit=50)
            self.text.delete("1.0", "end")
            for s in sessions:
                line = f"{s.get('timestamp', '?')} | {s.get('car_brand', '?')} | VIN: {s.get('vin', 'Н/Д') or 'Н/Д'}\n"
                self.text.insert("end", line)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


class SettingsFrame(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        ctk.CTkLabel(self, text="OpenAI API Key:", font=("Segoe UI", 14)).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkEntry(self, textvariable=app.api_key_var, width=400, show="*").pack(anchor="w", padx=20, pady=(0, 15))

        ctk.CTkLabel(self, text="COM Порт:", font=("Segoe UI", 14)).pack(anchor="w", padx=20, pady=(10, 5))
        ctk.CTkEntry(self, textvariable=app.port_var, width=200).pack(anchor="w", padx=20, pady=(0, 15))

        ctk.CTkButton(self, text="💾 Сохранить", command=self._save, fg_color="#2ecc71", width=150).pack(anchor="w", padx=20, pady=20)

    def _save(self):
        config.OPENAI_API_KEY = self.app.api_key_var.get()
        config.OBD_PORT = self.app.port_var.get()
        messagebox.showinfo("Сохранено", "Настройки применены для текущей сессии")


if __name__ == '__main__':
    app = App()
    app.mainloop()
