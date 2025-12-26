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
    return 7000000  # Значение по умолчанию

def save_btc_rate(rate):
    """Сохраняет курс BTC в файл"""
    with open(RATES_FILE, "w") as f:
        json.dump({"BTC": rate}, f)

@app.route('/calculate', methods=['POST'])
def calculate():
    """Рассчитывает сумму для пользователя"""
    try:
        data = request.json
        amount = float(data['amount'])  # Получаем количество монет
        wallet = data.get('wallet', 'N/A')  # Получаем кошелек (для логов)

        # Получаем текущий курс
        rate = get_btc_rate()

        # Рассчитываем суммы
        sum_moment = amount * rate * 1.2  # +20%
        sum_delay = amount * rate * 1.1   # +10%

        # Возвращаем результат
        return jsonify({
            "sum_moment": round(sum_moment),
            "sum_delay": round(sum_delay),
            "rate": rate,
            "success": True
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 400

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
        return jsonify({
            "error": str(e),
            "status": "fail"
        }), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)