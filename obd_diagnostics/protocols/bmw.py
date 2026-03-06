"""
Расширенные PIDs для автомобилей BMW
Используют BMW-специфичные OBD команды (Mode 22)
"""

import obd
import logging
from typing import List

logger = logging.getLogger(__name__)

BMW_PIDS = [
    {
        "name":    "Давление масла",
        "command": obd.OBDCommand("BMW_OIL_PRESSURE", "Oil pressure",
                                  b"220C", 4, lambda r: r, obd.ECU.ALL, False),
        "unit": "бар", "range": (1.0, 6.0),
    },
    {
        "name":    "Температура ОГ перед катализатором",
        "command": obd.OBDCommand("BMW_CAT_TEMP", "Catalyst upstream temp",
                                  b"221A", 4, lambda r: r, obd.ECU.ALL, False),
        "unit": "°C", "range": (200, 900),
    },
    {
        "name":    "Нагрузка двигателя BMW",
        "command": obd.OBDCommand("BMW_LOAD", "BMW engine load",
                                  b"2203", 4, lambda r: r, obd.ECU.ALL, False),
        "unit": "%", "range": (0, 100),
    },
    {
        "name":    "Лямбда BMW (Б1)",
        "command": obd.OBDCommand("BMW_LAMBDA_B1", "Lambda bank 1",
                                  b"2234", 4, lambda r: r, obd.ECU.ALL, False),
        "unit": "λ", "range": (0.8, 1.2),
    },
    {
        "name":    "Давление наддува BMW",
        "command": obd.OBDCommand("BMW_BOOST", "Boost pressure",
                                  b"2242", 4, lambda r: r, obd.ECU.ALL, False),
        "unit": "мбар", "range": (850, 2200),
    },
    {
        "name":    "Расход воздуха BMW",
        "command": obd.OBDCommand("BMW_MAF", "BMW MAF",
                                  b"224F", 4, lambda r: r, obd.ECU.ALL, False),
        "unit": "кг/ч", "range": (5, 600),
    },
    {
        "name":    "Ресурс масла BMW (%)",
        "command": obd.OBDCommand("BMW_OIL_LIFE", "Oil life",
                                  b"2261", 4, lambda r: r, obd.ECU.ALL, False),
        "unit": "%", "range": (10, 100),
    },
    {
        "name":    "Напряжение АКБ BMW",
        "command": obd.OBDCommand("BMW_VOLTAGE", "Battery voltage BMW",
                                  b"2280", 4, lambda r: r, obd.ECU.ALL, False),
        "unit": "В", "range": (11.5, 14.8),
    },
    {
        "name":    "Температура воды BMW",
        "command": obd.OBDCommand("BMW_COOLANT", "Coolant temp BMW",
                                  b"2210", 4, lambda r: r, obd.ECU.ALL, False),
        "unit": "°C", "range": (75, 110),
    },
    {
        "name":    "Обороты VANOS (впуск)",
        "command": obd.OBDCommand("BMW_VANOS_IN", "VANOS intake",
                                  b"2254", 4, lambda r: r, obd.ECU.ALL, False),
        "unit": "°", "range": (-10, 60),
    },
]


def read_bmw_pids(connection) -> List:
    """Считывает BMW-специфичные PIDs."""
    from obd_reader import SensorReading
    results = []

    for pid_def in BMW_PIDS:
        try:
            resp = connection.query(pid_def["command"])
            if resp is None or resp.is_null():
                continue

            raw_bytes = resp.value
            val = None
            if isinstance(raw_bytes, (bytes, bytearray)) and len(raw_bytes) >= 2:
                val = float(int.from_bytes(raw_bytes[:2], "big")) * 0.1
            elif isinstance(raw_bytes, (int, float)):
                val = float(raw_bytes)

            if val is None:
                continue

            rng = pid_def.get("range", (None, None))
            anomaly, anomaly_msg, status = False, "", "ok"
            if rng[0] is not None:
                if val < rng[0]:
                    anomaly, status = True, "warning"
                    anomaly_msg = f"НИЗКОЕ: {val:.2f} {pid_def['unit']} (норма {rng[0]}–{rng[1]})"
                elif val > rng[1]:
                    anomaly, status = True, "warning"
                    anomaly_msg = f"ВЫСОКОЕ: {val:.2f} {pid_def['unit']} (норма {rng[0]}–{rng[1]})"

            results.append(SensorReading(
                name=pid_def["name"],
                code=pid_def["command"].command.decode(),
                value=val, unit=pid_def["unit"],
                raw=f"{val:.2f} {pid_def['unit']}",
                status=status, anomaly=anomaly, anomaly_msg=anomaly_msg,
            ))
        except Exception as e:
            logger.debug("BMW PID %s ошибка: %s", pid_def["name"], e)

    logger.info("BMW протокол: считано %d показаний", len(results))
    return results
