from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# Файл для хранения курса BTC
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
        
        # Получаем текущий курс
        rate = get_btc_rate()

        # Рассчитываем суммы
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

@app.route('/confirm', methods=['POST'])
def confirm():
    """Обрабатывает нажатие кнопок Оплачено/Отмена и выдает чистые переменные"""
    try:
        data = request.json
        content = data.get('content', '')

        # Если в данных от кнопки есть наш разделитель
        if "|" in content:
            parts = content.split("|")
            # Возвращаем результат в BotHunter
            return jsonify({
                "action": parts[0],    # pay или cancel
                "user_id": parts[1],   # ID клиента
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
    # Порт 5000 для локальной разработки, Render сам подставит нужный через переменные окружения
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
