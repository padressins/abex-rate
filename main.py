from flask import Flask, request, jsonify
import json
import os
import requests

app = Flask(__name__)

# --- КОНФИГ ---
BOT_TOKEN = "8507683894:AAE3aYcTZ7kuvy2-mhDdzd8YAwfVe1LblG0" 
MANAGER_GROUP_ID = "-1003636379042" 
RATES_FILE = "rates.json"
PROMOS_FILE = "promos.json"

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def load_data(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_btc_rate():
    data = load_data(RATES_FILE, {"BTC": 7000000})
    return data.get("BTC", 7000000)

# --- ЛОГИКА ПРОМОКОДОВ (Массовые + Анти-дюп) ---

@app.route('/add_promo', methods=['POST'])
def add_promo():
    """Админка: создание промокода (массовый, один код на много юзеров)"""
    try:
        data = request.json
        code = str(data.get('promo_name', '')).strip().upper()
        discount = int(data.get('promo_sum', 0))
        
        if not code:
            return jsonify({"success": False, "error": "Название кода пустое"}), 400

        promos = load_data(PROMOS_FILE, {})
        # Инициализируем структуру, если кода еще нет, сохраняя старых юзеров если есть
        promos[code] = {
            "discount": discount,
            "used_by_users": promos.get(code, {}).get("used_by_users", [])
        }
        save_data(PROMOS_FILE, promos)
        return jsonify({"success": True, "message": f"Промокод {code} активен"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/check_promo', methods=['POST'])
def check_promo():
    """Клиент: Проверка кода. ВСЕГДА возвращает discount (число), чтобы не ломать бота"""
    try:
        data = request.json
        user_code = str(data.get('code', '')).strip().upper()
        user_id = str(data.get('user_id', ''))

        promos = load_data(PROMOS_FILE, {})

        # Если код не найден
        if user_code not in promos:
            return jsonify({
                "success": False, 
                "discount": 0, 
                "message": "Промокод не найден"
            })

        promo = promos[user_code]

        # Анти-дюп: проверка повторного использования
        if user_id in promo['used_by_users']:
            return jsonify({
                "success": False, 
                "discount": 0, 
                "message": "Вы уже использовали этот код"
            })

        # Если всё честно — возвращаем сумму скидки
        # ВАЖНО: Мы НЕ записываем юзера здесь, чтобы он мог пересчитать сумму 
        # до момента финального подтверждения (или записываем сразу, если логика жесткая)
        # Для твоей схемы запишем сразу:
        promo['used_by_users'].append(user_id)
        save_data(PROMOS_FILE, promos)

        return jsonify({
            "success": True, 
            "discount": promo['discount'],
            "message": "Скидка применена!"
        })
    except Exception as e:
        # Страховка: если что-то пошло не так, бот получит 0 и не "зависнет"
        return jsonify({"success": False, "discount": 0, "error": str(e)})

# --- РАСЧЕТ И ЗАКАЗ ---

@app.route('/calculate', methods=['POST'])
def calculate():
    """Финальный расчет сумм. Защищен от пустых полей discount"""
    try:
        data = request.json
        amount = float(data.get('amount', 0))
        
        # Получаем скидку. Если пришла пустота или ошибка — ставим 0
        raw_discount = data.get('discount', 0)
        try:
            discount = float(raw_discount) if raw_discount else 0
        except:
            discount = 0
        
        rate = get_btc_rate()
        
        # Основная формула
        sum_moment = (amount * rate * 1.22) - discount
        sum_delay = (amount * rate * 1.18) - discount

        return jsonify({
            "sum_moment": round(max(0, sum_moment)),
            "sum_delay": round(max(0, sum_delay)),
            "rate": rate,
            "success": True
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/take_order', methods=['POST'])
def take_order():
    """Захват заявки менеджером"""
    try:
        data = request.json
        callback_data = data.get('callback_data', '')
        message_id = data.get('message_id')
        manager_name = data.get('manager_name')

        if ":" in callback_data:
            parts = callback_data.split(":")
            if parts[0] == "take":
                client_username = parts[1]
                amount = parts[2]

                tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup"
                tg_payload = {
                    "chat_id": MANAGER_GROUP_ID,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []}
                }
                requests.post(tg_url, json=tg_payload)

                return jsonify({
                    "success": True,
                    "client_username": client_username,
                    "amount": amount,
                    "manager_confirm": manager_name
                })
        return jsonify({"success": False}), 400
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 400

@app.route('/confirm', methods=['POST'])
def confirm():
    """Парсинг кнопок подтверждения"""
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
        return jsonify({"success": False}), 400
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 400

@app.route('/set_rate', methods=['GET'])
def set_rate():
    """Установка курса BTC"""
    try:
        new_rate = float(request.args.get('rate'))
        save_data(RATES_FILE, {"BTC": new_rate})
        return jsonify({"status": "ok", "rate": new_rate})
    except Exception as e:
        return jsonify({"error": str(e), "status": "fail"}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
