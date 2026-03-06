"""
Расширенные PIDs для автомобилей Jaguar / Land Rover
"""

import obd
import logging
from typing import List

logger = logging.getLogger(__name__)

JAGUAR_PIDS = [
    {
        "name":    "Давление масла Jaguar",
        "command": obd.OBDCommand("JAG_OIL_PRESSURE", "Jaguar oil pressure",
                                  b"220A1B", 6, lambda r: r, obd.ECU.ALL, False),
        "unit": "кПа", "range": (100, 600),
    },
    {
        "name":    "Температура масла Jaguar",
        "command": obd.OBDCommand("JAG_OIL_TEMP", "Jaguar oil temp",
                                  b"220B1A", 6, lambda r: r, obd.ECU.ALL, False),
        "unit": "°C", "range": (60, 140),
    },
    {
        "name":    "Лямбда Jaguar (Б1)",
        "command": obd.OBDCommand("JAG_LAMBDA_1", "Jaguar lambda bank1",
                                  b"221031", 6, lambda r: r, obd.ECU.ALL, False),
        "unit": "λ", "range": (0.85, 1.15),
    },
    {
        "name":    "Ток АКБ Jaguar",
        "command": obd.OBDCommand("JAG_BATT_CURRENT", "Jaguar battery current",
                                  b"228006", 6, lambda r: r, obd.ECU.ALL, False),
        "unit": "А", "range": (-100, 200),
    },
    {
        "name":    "Напряжение АКБ Jaguar",
        "command": obd.OBDCommand("JAG_BATT_VOLT", "Jaguar battery voltage",
                                  b"228005", 6, lambda r: r, obd.ECU.ALL, False),
        "unit": "В", "range": (11.5, 14.8),
    },
    {
        "name":    "Температура ОГ (перед ДК2)",
        "command": obd.OBDCommand("JAG_EGT_POST", "Jaguar EGT post-cat",
                                  b"221020", 6, lambda r: r, obd.ECU.ALL, False),
        "unit": "°C", "range": (100, 700),
    },
    {
        "name":    "Давление наддува Jaguar",
        "command": obd.OBDCommand("JAG_BOOST", "Jaguar boost pressure",
                                  b"220500", 6, lambda r: r, obd.ECU.ALL, False),
        "unit": "кПа", "range": (80, 230),
    },
    {
        "name":    "Уровень жидкости АКПП",
        "command": obd.OBDCommand("JAG_TRANS_FLUID", "Transmission fluid level",
                                  b"222140", 6, lambda r: r, obd.ECU.ALL, False),
        "unit": "%", "range": (40, 100),
    },
]


def read_jaguar_pids(connection) -> List:
    """Считывает Jaguar-специфичные PIDs."""
    from obd_reader import SensorReading
    results = []

    for pid_def in JAGUAR_PIDS:
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
            logger.debug("Jaguar PID %s ошибка: %s", pid_def["name"], e)

    logger.info("Jaguar протокол: считано %d показаний", len(results))
    return results
