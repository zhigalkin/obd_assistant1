"""
Расширенные PIDs для автомобилей Audi/Volkswagen/SEAT/Skoda (VAG Group)
Используют Mode 21 и другие VAG-специфичные команды
"""

import obd
import logging
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from obd_reader import SensorReading, OBDReader

logger = logging.getLogger(__name__)


# ─── VAG-специфичные PID определения ─────────────────────────────────────────
# Формат: (name, mode_byte, pid_byte, description, unit, scale, offset, min_val, max_val)
VAG_CUSTOM_PIDS = [
    # Наддув и впуск
    {
        "name":    "Давление наддува (факт.)",
        "command": obd.OBDCommand("VAG_BOOST_ACTUAL",   "Boost pressure actual",
                                  b"2101", 4, lambda r: r, obd.ECU.ALL, False),
        "unit":    "мбар",
        "range":   (900, 2500),
        "note":    "Фактическое давление наддува",
    },
    {
        "name":    "Давление наддува (целев.)",
        "command": obd.OBDCommand("VAG_BOOST_TARGET",   "Boost pressure target",
                                  b"2102", 4, lambda r: r, obd.ECU.ALL, False),
        "unit":    "мбар",
        "range":   (900, 2500),
        "note":    "Целевое давление наддува",
    },
    # Лямбда
    {
        "name":    "Лямбда (широкополосный)",
        "command": obd.OBDCommand("VAG_LAMBDA_WB",  "Wideband lambda",
                                  b"2131", 4, lambda r: r, obd.ECU.ALL, False),
        "unit":    "λ",
        "range":   (0.85, 1.15),
        "note":    "Широкополосный лямбда-зонд",
    },
    # Момент впрыска
    {
        "name":    "Момент начала впрыска",
        "command": obd.OBDCommand("VAG_INJ_TIMING",  "Injection timing",
                                  b"2142", 4, lambda r: r, obd.ECU.ALL, False),
        "unit":    "°BTDC",
        "range":   (-10, 25),
        "note":    "Угол начала впрыска топлива",
    },
    # Давление топлива (Common Rail)
    {
        "name":    "Давление в топливной рампе",
        "command": obd.OBDCommand("VAG_FUEL_RAIL",  "Fuel rail pressure",
                                  b"2180", 4, lambda r: r, obd.ECU.ALL, False),
        "unit":    "бар",
        "range":   (200, 1800),
        "note":    "Common Rail давление",
    },
    # Температура ОГ
    {
        "name":    "Темп. отработ. газов перед турбиной",
        "command": obd.OBDCommand("VAG_EGT_PRE",  "EGT pre-turbo",
                                  b"2112", 4, lambda r: r, obd.ECU.ALL, False),
        "unit":    "°C",
        "range":   (200, 850),
        "note":    "Температура ОГ перед турбиной",
    },
    # Потребляемый ток
    {
        "name":    "Ток генератора",
        "command": obd.OBDCommand("VAG_ALT_CURRENT",  "Alternator current",
                                  b"2161", 4, lambda r: r, obd.ECU.ALL, False),
        "unit":    "А",
        "range":   (-50, 150),
        "note":    "Ток зарядки/нагрузки генератора",
    },
    # Позиция педали газа
    {
        "name":    "Педаль газа (VAG)",
        "command": obd.OBDCommand("VAG_ACCEL",  "Accelerator position VAG",
                                  b"2125", 4, lambda r: r, obd.ECU.ALL, False),
        "unit":    "%",
        "range":   (0, 100),
        "note":    "Положение педали акселератора",
    },
]


def read_vag_pids(connection) -> List["SensorReading"]:
    """
    Считывает VAG-специфичные PIDs через переданное OBD соединение.
    Возвращает список SensorReading.
    """
    from obd_reader import SensorReading
    results = []

    for pid_def in VAG_CUSTOM_PIDS:
        try:
            resp = connection.query(pid_def["command"])
            if resp is None or resp.is_null():
                continue

            raw_bytes = resp.value
            # Попытка декодировать как число из байт
            val = None
            if isinstance(raw_bytes, (bytes, bytearray)) and len(raw_bytes) >= 2:
                val = float(int.from_bytes(raw_bytes[:2], "big")) * 0.1
            elif isinstance(raw_bytes, (int, float)):
                val = float(raw_bytes)

            if val is None:
                continue

            rng = pid_def.get("range", (None, None))
            anomaly = False
            anomaly_msg = ""
            status = "ok"

            if rng[0] is not None and val < rng[0]:
                anomaly = True
                anomaly_msg = f"НИЗКОЕ: {val:.2f} {pid_def['unit']} (норма {rng[0]}–{rng[1]})"
                status = "warning"
            elif rng[1] is not None and val > rng[1]:
                anomaly = True
                anomaly_msg = f"ВЫСОКОЕ: {val:.2f} {pid_def['unit']} (норма {rng[0]}–{rng[1]})"
                status = "warning"

            results.append(SensorReading(
                name=pid_def["name"],
                code=pid_def["command"].command.decode(),
                value=val,
                unit=pid_def["unit"],
                raw=f"{val:.2f} {pid_def['unit']}",
                status=status,
                anomaly=anomaly,
                anomaly_msg=anomaly_msg,
            ))

        except Exception as e:
            logger.debug("VAG PID %s ошибка: %s", pid_def["name"], e)

    logger.info("VAG протокол: считано %d показаний", len(results))
    return results
