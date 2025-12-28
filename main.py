from flask import Flask, request, jsonify
import json
import os
import requests  # Обязательно добавь в requirements.txt на Render

app = Flask(__name__)

# --- КОНФИГ ---
# Замени на свои реальные данные
BOT_TOKEN = "8507683894:AAE3aYcTZ7kuvy2-mhDdzd8YAwfVe1LblG0" 
MANAGER_GROUP_ID = "-1003636379042"  # ID чата, где сидят менеджеры
RATES_FILE = "rates.json"

def get_btc_rate():
    """Получает курс BTC из файла или возвращает значение по умолчанию"""
    if os.path.exists(RATES_FILE):
        with open(RATES_FILE) as f:
            data = json.load(f)
            return data.get("BTC", 7000000)
    return 7000000

def save_btc_rate(rate):
    """Сохраняет курс BTC в файл"""
    with open(RATES_FILE, "w") as f:
        json.dump({"BTC": rate}, f)

@app.route('/calculate', methods=['POST'])
def calculate():
    """Рассчитывает сумму для пользователя"""
    try:
        data = request.json
        amount = float(data['amount'])
        
        rate = get_btc_rate()
        sum_moment = amount * rate * 1.2
        sum_delay = amount * rate * 1.1

        return jsonify({
            "sum_moment": round(sum_moment),
            "sum_delay": round(sum_delay),
            "rate": rate,
            "success": True
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 400

@app.route('/take_order', methods=['POST'])
def take_order():
    """
    Логика ЗАХВАТА заявки:
    1. Получает данные из BotHunter.
    2. Удаляет кнопки в общей группе через API Telegram.
    3. Возвращает чистые данные для записи в таблицу.
    """
    try:
        data = request.json
        callback_data = data.get('callback_data', '')  # Строка типа take|username|sum
        message_id = data.get('message_id')            # ID сообщения в группе
        manager_name = data.get('manager_name')        # Имя менеджера, нажавшего кнопку

        if ":" in callback_data:
            parts = callback_data.split(":")
            # Если это наш захват
            if parts[0] == "take":
                client_username = parts[1]
                amount = parts[2]

                # --- 1. Удаляем кнопку в группе, чтобы никто другой не нажал ---
                tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup"
                tg_payload = {
                    "chat_id": MANAGER_GROUP_ID,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []}  # Очищаем кнопки
                }
                requests.post(tg_url, json=tg_payload)

                # --- 2. Возвращаем результат в BotHunter для записи в таблицу ---
                return jsonify({
                    "success": True,
                    "client_username": client_username,
                    "amount": amount,
                    "manager_confirm": manager_name,
                    "message": f"Заявка клиента @{client_username} на {amount} руб. захвачена вами!"
                })

        return jsonify({"success": False, "error": "Invalid data format"}), 400

    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 400

@app.route('/confirm', methods=['POST'])
def confirm():
    """Обрабатывает нажатие кнопок Оплачено/Отмена в личке менеджера"""
    try:
        data = request.json
        content = data.get('content', '')

        if "|" in content:
            parts = content.split("|")
            return jsonify({
                "action": parts[0],
                "user_id": parts[1],
                "amount": parts[2] if len(parts) > 2 else "0",
                "success": True
            })
        
        return jsonify({"success": False, "error": "Invalid format"}), 400
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 400

@app.route('/set_rate', methods=['GET'])
def set_rate():
    """Обновляет курс BTC (админка)"""
    try:
        new_rate = float(request.args.get('rate'))
        save_btc_rate(new_rate)
        return jsonify({
            "status": "ok",
            "rate": new_rate,
            "message": "Курс успешно обновлён"
        })
    except Exception as e:
        return jsonify({"error": str(e), "status": "fail"}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

