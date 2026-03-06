"""
Модуль чтения данных OBD-II
Поддерживает стандартные SAE J1979 PIDs и обнаружение аномалий
"""

import obd
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

import config

logger = logging.getLogger(__name__)


@dataclass
class SensorReading:
    """Результат чтения одного датчика."""
    name: str                          # Название датчика
    code: str                          # PID код
    value: Optional[float]             # Числовое значение
    unit: str                          # Единица измерения
    raw: str                           # Строковое представление
    status: str = "ok"                 # ok / warning / error
    anomaly: bool = False              # Флаг аномалии
    anomaly_msg: str = ""              # Описание аномалии


# ─── Описания стандартных OBD-II PIDs ────────────────────────────────────────
STANDARD_PIDS = [
    # (obd_command, human_name, config_key_for_range)
    (obd.commands.ENGINE_LOAD,        "Нагрузка двигателя",        "engine_load"),
    (obd.commands.COOLANT_TEMP,       "Температура охлаждающей жидкости", "coolant_temp"),
    (obd.commands.SHORT_FUEL_TRIM_1,  "Кратк. коррекция топлива б.1", "short_fuel_trim"),
    (obd.commands.LONG_FUEL_TRIM_1,   "Долг. коррекция топлива б.1",  "long_fuel_trim"),
    (obd.commands.SHORT_FUEL_TRIM_2,  "Кратк. коррекция топлива б.2", "short_fuel_trim"),
    (obd.commands.LONG_FUEL_TRIM_2,   "Долг. коррекция топлива б.2",  "long_fuel_trim"),
    (obd.commands.FUEL_PRESSURE,      "Давление топлива",           None),
    (obd.commands.INTAKE_PRESSURE,    "Давление во впускном коллекторе", "map_pressure"),
    (obd.commands.RPM,                "Обороты двигателя",          "rpm_max"),
    (obd.commands.SPEED,              "Скорость",                   None),
    (obd.commands.TIMING_ADVANCE,     "Угол опережения зажигания",  "timing_advance"),
    (obd.commands.INTAKE_TEMP,        "Температура воздуха на впуске", "intake_temp"),
    (obd.commands.MAF,                "Расход воздуха (MAF)",       "maf"),
    (obd.commands.THROTTLE_POS,       "Положение дросселя",         "throttle"),
    (obd.commands.O2_B1S1,            "Лямбда-зонд Б1 С1",          "o2_voltage"),
    (obd.commands.O2_B1S2,            "Лямбда-зонд Б1 С2",          "o2_voltage"),
    (obd.commands.O2_B2S1,            "Лямбда-зонд Б2 С1",          "o2_voltage"),
    (obd.commands.O2_B2S2,            "Лямбда-зонд Б2 С2",          "o2_voltage"),
    (obd.commands.OBD_COMPLIANCE,     "Стандарт OBD",               None),
    (obd.commands.ELM_VOLTAGE,        "Напряжение АКБ (ELM)",       "battery_voltage"),
    (obd.commands.RUN_TIME,           "Время работы двигателя",     None),
    (obd.commands.DISTANCE_W_MIL,     "Пробег с MIL",               None),
    (obd.commands.FUEL_RAIL_PRESSURE_VAC, "Давление топливн. рампы (вак)", None),
    (obd.commands.FUEL_RAIL_PRESSURE_DIRECT, "Давление топливн. рампы (прямое)", None),
    (obd.commands.COMMANDED_EGR,      "Управляемый EGR",            None),
    (obd.commands.EGR_ERROR,          "Ошибка EGR",                 None),
    (obd.commands.EVAPORATIVE_PURGE,  "Продувка EVAP",              None),
    (obd.commands.FUEL_LEVEL,         "Уровень топлива",            None),
    (obd.commands.WARMUPS_SINCE_DTC_CLEAR, "Прогревы после сброса ошибок", None),
    (obd.commands.DISTANCE_SINCE_DTC_CLEAR, "Пробег после сброса ошибок", None),
    (obd.commands.BAROMETRIC_PRESSURE, "Атмосферное давление",      None),
    (obd.commands.O2_S1_WR_CURRENT,   "Ток широкополосн. зонда Б1С1", None),
    (obd.commands.CATALYST_TEMP_B1S1, "Температура катализатора Б1С1", None),
    (obd.commands.CATALYST_TEMP_B2S1, "Температура катализатора Б2С1", None),
    (obd.commands.CONTROL_MODULE_VOLTAGE, "Напряжение модуля управления", "battery_voltage"),
    (obd.commands.ABSOLUTE_LOAD,      "Абсолютная нагрузка",        "engine_load"),
    (obd.commands.COMMANDED_EQUIV_RATIO, "Коэффициент Lambda",      None),
    (obd.commands.RELATIVE_THROTTLE_POS, "Относительное положение дросселя", None),
    (obd.commands.AMBIANT_AIR_TEMP,   "Температура окружающей среды", None),
    (obd.commands.THROTTLE_ACTUATOR,  "Привод дросселя",            None),
    (obd.commands.TIME_WITH_MIL,      "Время с MIL",                None),
    (obd.commands.TIME_SINCE_DTC_CLEARED, "Время после сброса ошибок", None),
    (obd.commands.MAX_MAF,            "Максимальный MAF",           None),
    (obd.commands.FUEL_TYPE,          "Тип топлива",                None),
    (obd.commands.ETHANOL_PERCENT,    "Содержание этанола",         None),
    (obd.commands.ACCELERATOR_POS_D,  "Педаль газа D",              None),
    (obd.commands.ACCELERATOR_POS_E,  "Педаль газа E",              None),
    (obd.commands.THROTTLE_POS_B,     "Дроссель B",                 None),
    (obd.commands.THROTTLE_POS_C,     "Дроссель C",                 None),
    (obd.commands.OIL_TEMP,           "Температура масла",          "oil_temp"),
    (obd.commands.FUEL_INJECT_TIMING, "Момент впрыска топлива",     None),
    (obd.commands.FUEL_RATE,          "Расход топлива",             None),
    (obd.commands.VIN,                "VIN номер",                  None),
    (obd.commands.ECU_NAME,           "Название ЭБУ",               None),
]


class OBDReader:
    """Основной класс для работы с OBD адаптером."""

    def __init__(self):
        self.connection: Optional[obd.OBD] = None
        self.connected = False
        self.vin: Optional[str] = None
        self._supported_pids: List = []

    def connect(self, port: str = "", baudrate: int = 38400,
                timeout: int = 10, fast: bool = False) -> Tuple[bool, str]:
        """
        Подключается к OBD адаптеру.
        Возвращает (успех, сообщение).
        """
        try:
            # Используем порт из конфига если не указан явно
            if not port:
                port = config.OBD_PORT

            logger.info("Подключение к OBD на порту: %s", port or "авто")

            if port:
                self.connection = obd.OBD(
                    portstr=port,
                    baudrate=baudrate,
                    timeout=timeout,
                    fast=fast
                )
            else:
                # Автоопределение порта
                self.connection = obd.OBD(
                    timeout=timeout,
                    fast=fast
                )

            if self.connection.is_connected():
                self.connected = True
                self._supported_pids = self.connection.supported_commands
                logger.info("OBD подключён. Поддерживаемых команд: %d", len(self._supported_pids))
                return True, f"Подключено успешно. Команд: {len(self._supported_pids)}"
            else:
                return False, "Не удалось установить соединение с адаптером"

        except Exception as e:
            logger.error("Ошибка подключения OBD: %s", e)
            return False, f"Ошибка: {e}"

    def disconnect(self):
        """Закрывает соединение."""
        if self.connection:
            self.connection.close()
            self.connected = False
            self.connection = None
            logger.info("OBD отключён")

    def is_connected(self) -> bool:
        """Проверяет статус соединения."""
        return self.connected and self.connection is not None and self.connection.is_connected()

    def _query(self, command) -> Optional[obd.OBDResponse]:
        """Безопасный запрос к OBD."""
        try:
            if not self.is_connected():
                return None
            response = self.connection.query(command)
            if response.is_null():
                return None
            return response
        except Exception as e:
            logger.debug("Ошибка запроса %s: %s", command.name, e)
            return None

    def _check_anomaly(self, name: str, value: float, range_key: str) -> Tuple[bool, str]:
        """Проверяет значение на аномалию по известным диапазонам."""
        if range_key not in config.NORMAL_RANGES:
            return False, ""
        lo, hi = config.NORMAL_RANGES[range_key]
        if value < lo:
            return True, f"НИЗКОЕ: {value:.1f} (норма {lo}–{hi})"
        if value > hi:
            return True, f"ВЫСОКОЕ: {value:.1f} (норма {lo}–{hi})"
        return False, ""

    def read_standard_pids(self) -> List[SensorReading]:
        """Считывает все стандартные OBD-II PIDs."""
        results = []
        for cmd, human_name, range_key in STANDARD_PIDS:
            resp = self._query(cmd)
            if resp is None:
                continue

            try:
                mag = resp.value
                if hasattr(mag, 'magnitude'):
                    val = float(mag.magnitude)
                    unit = str(mag.units)
                    raw = f"{val:.2f} {unit}"
                elif isinstance(mag, (int, float)):
                    val = float(mag)
                    unit = ""
                    raw = str(val)
                else:
                    val = None
                    unit = ""
                    raw = str(mag)

                status = "ok"
                anomaly = False
                anomaly_msg = ""

                if val is not None and range_key:
                    anomaly, anomaly_msg = self._check_anomaly(human_name, val, range_key)
                    if anomaly:
                        status = "warning"

                results.append(SensorReading(
                    name=human_name,
                    code=cmd.command.decode() if hasattr(cmd.command, 'decode') else str(cmd.command),
                    value=val,
                    unit=unit,
                    raw=raw,
                    status=status,
                    anomaly=anomaly,
                    anomaly_msg=anomaly_msg,
                ))
            except Exception as e:
                logger.debug("Ошибка парсинга %s: %s", human_name, e)

        return results

    def read_dtc_codes(self) -> List[Dict[str, Any]]:
        """Считывает подтверждённые коды неисправностей."""
        dtcs = []
        resp = self._query(obd.commands.GET_DTC)
        if resp and resp.value:
            for code, desc in resp.value:
                dtcs.append({
                    "code": str(code),
                    "description": str(desc) if desc else "Нет описания",
                    "type": "confirmed",
                    "severity": self._dtc_severity(str(code)),
                })
        return dtcs

    def read_pending_dtc_codes(self) -> List[Dict[str, Any]]:
        """Считывает ожидающие (pending) коды неисправностей."""
        dtcs = []
        resp = self._query(obd.commands.GET_CURRENT_DTC)
        if resp and resp.value:
            for code, desc in resp.value:
                dtcs.append({
                    "code": str(code),
                    "description": str(desc) if desc else "Нет описания",
                    "type": "pending",
                    "severity": self._dtc_severity(str(code)),
                })
        return dtcs

    def read_vin(self) -> Optional[str]:
        """Считывает VIN номер автомобиля."""
        resp = self._query(obd.commands.VIN)
        if resp and resp.value:
            self.vin = str(resp.value).strip()
            return self.vin
        return None

    def read_battery_voltage(self) -> Optional[float]:
        """Считывает напряжение АКБ через ELM адаптер."""
        resp = self._query(obd.commands.ELM_VOLTAGE)
        if resp and resp.value:
            try:
                return float(resp.value.magnitude)
            except Exception:
                pass
        return None

    def full_scan(self, extra_readings: Optional[List[SensorReading]] = None) -> Dict[str, Any]:
        """
        Полное сканирование: все PIDs + DTC коды + аномалии.
        extra_readings — показания от производителя-специфичных протоколов.
        """
        result: Dict[str, Any] = {
            "vin": self.read_vin(),
            "battery_voltage": self.read_battery_voltage(),
            "readings": [],
            "dtc_confirmed": [],
            "dtc_pending": [],
            "anomalies": [],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Стандартные PIDs
        readings = self.read_standard_pids()

        # Добавляем производитель-специфичные
        if extra_readings:
            readings.extend(extra_readings)

        result["readings"] = readings

        # DTC коды
        result["dtc_confirmed"] = self.read_dtc_codes()
        result["dtc_pending"] = self.read_pending_dtc_codes()

        # Собираем аномалии
        for r in readings:
            if r.anomaly:
                result["anomalies"].append({
                    "pid_name": r.name,
                    "value": r.value,
                    "unit": r.unit,
                    "message": r.anomaly_msg,
                    "severity": "warning",
                    "expected_min": config.NORMAL_RANGES.get(
                        self._find_range_key(r.name), (None, None))[0],
                    "expected_max": config.NORMAL_RANGES.get(
                        self._find_range_key(r.name), (None, None))[1],
                })

        # Аномалия напряжения АКБ
        if result["battery_voltage"] is not None:
            v = result["battery_voltage"]
            lo, hi = config.NORMAL_RANGES["battery_voltage"]
            if v < lo or v > hi:
                result["anomalies"].append({
                    "pid_name": "Напряжение АКБ",
                    "value": v,
                    "unit": "В",
                    "message": f"{'НИЗКОЕ' if v < lo else 'ВЫСОКОЕ'}: {v:.1f}В (норма {lo}–{hi}В)",
                    "severity": "error" if v < 11.0 else "warning",
                    "expected_min": lo,
                    "expected_max": hi,
                })

        return result

    @staticmethod
    def _dtc_severity(code: str) -> str:
        """Определяет серьёзность кода ошибки по первой букве."""
        if not code:
            return "unknown"
        prefix = code[0].upper()
        # P0xxx — общие, P1xxx — производитель, P2xxx — общие расш.
        if code.startswith("P0") or code.startswith("P2"):
            return "high"
        if code.startswith("P1") or code.startswith("P3"):
            return "medium"
        if prefix in ("C", "B", "U"):
            return "medium"
        return "low"

    @staticmethod
    def _find_range_key(pid_name: str) -> str:
        """Вспомогательный метод поиска ключа диапазона по имени датчика."""
        mapping = {
            "Температура охлаждающей жидкости": "coolant_temp",
            "Обороты двигателя": "rpm_max",
            "Нагрузка двигателя": "engine_load",
            "Напряжение АКБ (ELM)": "battery_voltage",
            "Напряжение модуля управления": "battery_voltage",
            "Расход воздуха (MAF)": "maf",
            "Положение дросселя": "throttle",
            "Температура воздуха на впуске": "intake_temp",
            "Температура масла": "oil_temp",
        }
        return mapping.get(pid_name, "")


# ─── Демо-режим (без реального адаптера) ─────────────────────────────────────

class DemoOBDReader(OBDReader):
    """
    Режим демонстрации — возвращает синтетические данные
    для тестирования интерфейса без адаптера.
    """
    import random as _rand

    def connect(self, port="", baudrate=38400, timeout=10, fast=False):
        self.connected = True
        self.vin = "WAUZZZ8K9BA123456"
        logger.info("ДЕМО-РЕЖИМ: симуляция OBD подключения")
        return True, "ДЕМО-РЕЖИМ: виртуальное подключение активно"

    def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    def read_vin(self):
        return self.vin

    def read_battery_voltage(self):
        import random
        return round(13.8 + random.uniform(-0.5, 0.5), 2)

    def read_standard_pids(self):
        import random
        demo_data = [
            ("Обороты двигателя",              "rpm_max",        lambda: round(800 + random.gauss(0, 30)), "об/мин"),
            ("Нагрузка двигателя",             "engine_load",    lambda: round(25 + random.gauss(0, 3), 1), "%"),
            ("Температура охлаждающей жидкости", "coolant_temp", lambda: round(90 + random.gauss(0, 2), 1), "°C"),
            ("Скорость",                        None,             lambda: 0, "км/ч"),
            ("Расход воздуха (MAF)",            "maf",            lambda: round(8.5 + random.gauss(0, 0.5), 2), "г/с"),
            ("Положение дросселя",              "throttle",       lambda: round(14.9 + random.gauss(0, 0.5), 1), "%"),
            ("Угол опережения зажигания",       "timing_advance", lambda: round(12 + random.gauss(0, 1), 1), "°"),
            ("Температура воздуха на впуске",   "intake_temp",    lambda: round(28 + random.gauss(0, 2), 1), "°C"),
            ("Температура масла",               "oil_temp",       lambda: round(95 + random.gauss(0, 3), 1), "°C"),
            ("Давление во впускном коллекторе", "map_pressure",   lambda: round(35 + random.gauss(0, 2), 1), "кПа"),
            ("Кратк. коррекция топлива б.1",    "short_fuel_trim", lambda: round(random.gauss(0, 2), 2), "%"),
            ("Долг. коррекция топлива б.1",     "long_fuel_trim", lambda: round(random.gauss(1, 1.5), 2), "%"),
            ("Лямбда-зонд Б1 С1",               "o2_voltage",     lambda: round(0.45 + random.gauss(0, 0.15), 3), "В"),
            ("Лямбда-зонд Б1 С2",               "o2_voltage",     lambda: round(0.75 + random.gauss(0, 0.05), 3), "В"),
            ("Уровень топлива",                 None,             lambda: round(65 + random.uniform(-1, 1), 1), "%"),
            ("Атмосферное давление",            None,             lambda: 101, "кПа"),
            ("Напряжение АКБ (ELM)",            "battery_voltage", lambda: round(13.8 + random.uniform(-0.3, 0.3), 2), "В"),
        ]
        results = []
        for name, range_key, gen, unit in demo_data:
            val = gen()
            anomaly, msg = False, ""
            if range_key and range_key in config.NORMAL_RANGES:
                lo, hi = config.NORMAL_RANGES[range_key]
                if val < lo or val > hi:
                    anomaly = True
                    msg = f"{'НИЗКОЕ' if val < lo else 'ВЫСОКОЕ'}: {val} (норма {lo}–{hi})"
            results.append(SensorReading(
                name=name, code="DEMO", value=val, unit=unit,
                raw=f"{val} {unit}", status="warning" if anomaly else "ok",
                anomaly=anomaly, anomaly_msg=msg
            ))
        return results

    def read_dtc_codes(self):
        return []

    def read_pending_dtc_codes(self):
        return []
