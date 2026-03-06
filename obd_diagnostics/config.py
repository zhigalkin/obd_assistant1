"""
Конфигурация приложения OBD-II Диагностика
Настройте параметры подключения и API ключи здесь
"""

import os

# ─── OpenAI ───────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")  # Или вставьте ключ сюда
OPENAI_MODEL = "gpt-4o-mini"

# ─── OBD Подключение ──────────────────────────────────────────────────────────
OBD_PORT = os.environ.get("OBD_PORT", "")          # Например: "/dev/ttyUSB0" или "COM3"
OBD_BAUDRATE = 38400                                # Скорость соединения
OBD_TIMEOUT = 10                                    # Таймаут подключения (секунды)
OBD_FAST = False                                    # Быстрый режим (может пропускать PIDs)

# ─── Марка автомобиля ─────────────────────────────────────────────────────────
# Варианты: "generic", "audi_vag", "bmw", "jaguar"
CAR_BRAND = "generic"

# ─── База данных ──────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diagnostics_history.db")

# ─── Интерфейс ────────────────────────────────────────────────────────────────
LIVE_DATA_REFRESH_MS = 1000   # Интервал обновления живых данных (мс)
THEME_BG = "#1e1e2e"
THEME_FG = "#cdd6f4"
THEME_ACCENT = "#89b4fa"
THEME_OK = "#a6e3a1"
THEME_WARN = "#f9e2af"
THEME_ERROR = "#f38ba8"
THEME_PANEL = "#313244"
THEME_BORDER = "#45475a"

# ─── Экспорт отчётов ──────────────────────────────────────────────────────────
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")

# ─── Диапазоны нормальных значений (для обнаружения аномалий) ─────────────────
NORMAL_RANGES = {
    "coolant_temp":        (75, 105),     # °C
    "intake_temp":         (-20, 60),     # °C
    "oil_temp":            (80, 130),     # °C
    "rpm_idle":            (600, 1000),   # об/мин в режиме холостого хода
    "rpm_max":             (0, 7500),     # об/мин максимум
    "throttle":            (0, 100),      # %
    "battery_voltage":     (11.5, 14.8), # В
    "map_pressure":        (20, 105),     # кПа
    "maf":                 (2, 25),       # г/с на холостом ходу
    "fuel_pressure":       (300, 450),    # кПа
    "o2_voltage":          (0.1, 0.9),   # В
    "short_fuel_trim":     (-10, 10),    # %
    "long_fuel_trim":      (-10, 10),    # %
    "timing_advance":      (5, 35),       # градусов
    "engine_load":         (0, 100),      # %
    "boost_pressure":      (0, 250),      # кПа абсолютное
}
