from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import sympy as sp

app = Flask(__name__)
CORS(app)


class MathParser:
    def parse(self, spoken_text: str) -> str:
        if not spoken_text:
            return ""

        replacements = {
            # Базові
            "поділити на": "/", "розділити на": "/", "дріб": "",
            "в чисельнику": "(", "чисельник": "(",
            "в знаменнику": ")/(", "знаменник": ")/(",
            "кінець дробу": ")", "плюс": "+", "мінус": "-", "помножити на": "*",

            # ФУНКЦІЇ
            "синус від": "sin(", "синус": "sin(", "косинус від": "cos(", "косинус": "cos(",
            "тангенс від": "tan(", "тангенс": "tan(", "котангенс від": "cot(", "котангенс": "cot(",
            "натуральний логарифм від": "ln(", "натуральний логарифм": "ln(",
            "логарифм від": "log(", "логарифм": "log(",
            "корінь квадратний з": "sqrt(", "корінь з": "sqrt(", "корінь": "sqrt(",
            "в квадраті": "**2", "у квадраті": "**2", "в кубі": "**3", "у кубі": "**3",
            "в степені": "**(", "у степені": "**(",
            "відкрити дужку": "(", "закрити дужку": ")", "кінець": ")",

            # ЗМІННІ
            "а": "a", "бе": "b", "це": "c", "де": "d", "еф": "f",
            "ікс": "x", "ігрек": "y", "зет": "z", "пі": "pi", "є": "E",

            # ЦИФРИ (Словами)
            "нуль": "0", "один": "1", "одна": "1", "два": "2", "дві": "2",
            "три": "3", "чотири": "4", "п'ять": "5", "пять": "5",
            "шість": "6", "сім": "7", "вісім": "8", "дев'ять": "9", "девять": "9",
            "десять": "10"
        }

        parsed_text = spoken_text.lower()
        sorted_keys = sorted(replacements.keys(), key=len, reverse=True)
        for ukr_word in sorted_keys:
            parsed_text = re.sub(rf'\b{ukr_word}\b', replacements[ukr_word], parsed_text)

        math_str = parsed_text.replace(" ", "")
        math_str = re.sub(r'^[\*\/\+\-\=]+', '', math_str)

        open_brackets = math_str.count('(')
        close_brackets = math_str.count(')')
        if open_brackets > close_brackets:
            math_str += ')' * (open_brackets - close_brackets)

        return math_str


parser = MathParser()


@app.route('/parse', methods=['POST'])
def parse_math():
    data = request.json
    text = data.get('text', '')

    raw_math = parser.parse(text)

    try:
        clean_string = raw_math.replace("()", "(?)")
        custom_symbols = {"?": sp.Symbol("?")}
        expr = sp.sympify(clean_string, evaluate=False, locals=custom_symbols)

        # Формат 1: Складний LaTeX (для Moodle/Docs)
        latex_formula = f"${sp.latex(expr)}$"

        # Формат 2: Звичайний текст (для Miro, чатів)
        # Додаємо заміну sqrt на √ та pi на π
        plain_formula = str(expr).replace('**', '^').replace('sqrt', '√').replace('pi', 'π')

    except Exception as e:
        print(f"Помилка SymPy: {e}")
        latex_formula = raw_math
        # Також робимо заміну, якщо вираз обірвався і SymPy видав помилку
        plain_formula = raw_math.replace('sqrt', '√').replace('pi', 'π')

    # Відправляємо браузеру обидва формати
    return jsonify({
        "latex": latex_formula,
        "plain": plain_formula
    })


if __name__ == '__main__':
    print("🚀 Сервер працює! Чекаю на запити...")
    app.run(port=5000)