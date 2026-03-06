"""
Модуль AI-анализа данных диагностики через OpenAI gpt-4o-mini
"""

import logging
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — опытный автомобильный диагност с 20-летним стажем работы в сервисе.
Ты специализируешься на диагностике автомобилей по данным OBD-II адаптера.
Ты хорошо знаешь автомобили Audi, VW, BMW, Jaguar и другие марки.

При анализе данных:
1. Оцени каждый показатель — в норме ли он
2. Выяви все аномалии и их возможные причины
3. Оцени серьёзность проблем (критично / важно / рекомендуется проверить)
4. Дай конкретные рекомендации по ремонту или обслуживанию
5. Составь приоритетный список действий для владельца
6. Если есть коды ошибок — расшифруй их по-русски и объясни что это значит

Отвечай на русском языке. Будь конкретным и практичным.
Используй технические термины, но объясняй их понятно для обычного водителя."""


def build_scan_summary(scan_data: Dict[str, Any]) -> str:
    """Формирует текстовое резюме данных сканирования для отправки в AI."""
    lines = []

    lines.append("=== ДАННЫЕ ДИАГНОСТИКИ АВТОМОБИЛЯ ===\n")

    if scan_data.get("vin"):
        lines.append(f"VIN: {scan_data['vin']}")

    if scan_data.get("battery_voltage") is not None:
        lines.append(f"Напряжение АКБ: {scan_data['battery_voltage']:.2f} В")

    # Показания датчиков
    readings = scan_data.get("readings", [])
    if readings:
        lines.append("\n--- ПОКАЗАНИЯ ДАТЧИКОВ ---")
        for r in readings:
            if hasattr(r, 'name'):
                # SensorReading объект
                line = f"{r.name}: {r.raw}"
                if r.anomaly:
                    line += f"  ⚠️ АНОМАЛИЯ: {r.anomaly_msg}"
                lines.append(line)
            elif isinstance(r, dict):
                line = f"{r.get('name', '?')}: {r.get('raw', r.get('value', '?'))} {r.get('unit', '')}"
                if r.get('anomaly'):
                    line += f"  ⚠️ АНОМАЛИЯ: {r.get('anomaly_msg', '')}"
                lines.append(line)

    # Коды ошибок
    dtc_confirmed = scan_data.get("dtc_confirmed", [])
    if dtc_confirmed:
        lines.append("\n--- КОДЫ ОШИБОК (ПОДТВЕРЖДЁННЫЕ) ---")
        for dtc in dtc_confirmed:
            lines.append(f"  {dtc['code']}: {dtc.get('description', 'нет описания')}")

    dtc_pending = scan_data.get("dtc_pending", [])
    if dtc_pending:
        lines.append("\n--- КОДЫ ОШИБОК (ОЖИДАЮЩИЕ) ---")
        for dtc in dtc_pending:
            lines.append(f"  {dtc['code']}: {dtc.get('description', 'нет описания')}")

    # Аномалии
    anomalies = scan_data.get("anomalies", [])
    if anomalies:
        lines.append("\n--- ОБНАРУЖЕННЫЕ АНОМАЛИИ ---")
        for a in anomalies:
            lines.append(
                f"  {a.get('pid_name', '?')}: {a.get('value', '?')} {a.get('unit', '')} "
                f"— {a.get('message', a.get('anomaly_msg', ''))}"
            )

    if not dtc_confirmed and not dtc_pending and not anomalies:
        lines.append("\nКодов ошибок и явных аномалий не обнаружено.")

    return "\n".join(lines)


def analyze_scan(scan_data: Dict[str, Any],
                 api_key: Optional[str] = None,
                 model: str = "gpt-4o-mini",
                 extra_context: str = "") -> str:
    """
    Анализирует данные сканирования через OpenAI.
    Возвращает текст отчёта.
    """
    import config

    key = api_key or config.OPENAI_API_KEY
    if not key:
        return ("❌ API ключ OpenAI не настроен.\n"
                "Укажите OPENAI_API_KEY в переменных окружения или в настройках приложения.")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
    except ImportError:
        return "❌ Библиотека openai не установлена. Выполните: pip install openai"

    summary = build_scan_summary(scan_data)

    user_message = summary
    if extra_context:
        user_message += f"\n\nДополнительная информация от пользователя:\n{extra_context}"

    user_message += "\n\nПожалуйста, проведи полный анализ данных диагностики и дай рекомендации."

    logger.info("Отправка данных в OpenAI (%s)...", model)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        report = response.choices[0].message.content
        logger.info("AI анализ получен (%d символов)", len(report))
        return report

    except Exception as e:
        logger.error("Ошибка OpenAI API: %s", e)
        return f"❌ Ошибка при обращении к OpenAI API:\n{e}"


def analyze_dtc_only(dtc_codes: List[Dict], api_key: Optional[str] = None,
                     model: str = "gpt-4o-mini") -> str:
    """Анализирует только коды ошибок."""
    if not dtc_codes:
        return "Коды ошибок отсутствуют."

    import config
    key = api_key or config.OPENAI_API_KEY
    if not key:
        return "❌ API ключ OpenAI не настроен."

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
    except ImportError:
        return "❌ Библиотека openai не установлена."

    codes_text = "\n".join(
        f"- {c['code']}: {c.get('description', 'нет описания')} (тип: {c.get('type', '?')})"
        for c in dtc_codes
    )

    prompt = (f"Расшифруй следующие коды ошибок OBD-II и дай рекомендации:\n\n{codes_text}\n\n"
              "Для каждого кода: что означает, возможные причины, что делать.")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка OpenAI API: {e}"
