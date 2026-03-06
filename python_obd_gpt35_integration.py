import obd
import time
import openai
import os
import json

# OpenAI ключ из переменой окружения
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise Exception('OPENAI_API_KEY not set')

openai.api_key = OPENAI_API_KEY

# Подключение к OBD адаптеру
connection = obd.OBD()

# Команды для считывания
commands = [obd.commands.RPM, obd.commands.SPEED, obd.commands.COOLANT_TEMP]

# Функция запроса к OpenAI GPT-3.5

def analyze_data(data):
    prompt = f"Анализ данных с датчиков автомобиля и диагностика:\n{json.dumps(data, indent=2)}\n\nОбъясни возможные причины неисправностей и предупреждения:" 
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.3,
    )
    return response['choices'][0]['message']['content']

# Основной цикл считывания и анализа

try:
    while True:
        readings = {}
        for cmd in commands:
            response = connection.query(cmd)
            readings[cmd.name] = str(response.value) if response.value else 'N/A'
        print(f"Считывания: {readings}")

        # Анализ данных через ИИ
        analysis = analyze_data(readings)
        print(f"Анализ ИИ:\n{analysis}\n")

        time.sleep(10)  # пауза 10 с

except KeyboardInterrupt:
    print("Завершение работы")
