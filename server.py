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
            # 1. Базові операції та дроби
            "поділити на": "/", "розділити на": "/", "дріб": "",
            "в чисельнику": "(", "чисельник": "(",
            "в знаменнику": ")/(", "знаменник": ")/(",
            "кінець дробу": ")", 
            "плюс": "+", "додати": "+", 
            "мінус": "-", "відняти": "-", 
            "помножити на": "*", "помножити": "*",
            "дорівнює": "=", "це": "=",

            # 2. ФУНКЦІЇ та тригонометрія
            "синус від": "sin(", "синус": "sin(", 
            "косинус від": "cos(", "косинус": "cos(",
            "тангенс від": "tan(", "тангенс": "tan(", 
            "котангенс від": "cot(", "котангенс": "cot(",
            "натуральний логарифм від": "ln(", "натуральний логарифм": "ln(",
            "логарифм від": "log(", "логарифм": "log(",
            "квадратний корінь з": "sqrt(", "корінь квадратний з": "sqrt(", "корінь з": "sqrt(", "корінь": "sqrt(",
            
            # 3. Ступені та дужки
            "в квадраті": "**2", "у квадраті": "**2", 
            "в кубі": "**3", "у кубі": "**3",
            "в степені": "**(", "у степені": "**(",
            "відкрити дужку": "(", "відкрити дужки": "(", "в дужках": "(",
            "закрити дужку": ")", "закрити дужки": ")", "кінець": ")",

            # 4. ЗМІННІ та грецький алфавіт
            "а": "a", "бе": "b", "це": "c", "де": "d", "еф": "f",
            "ікс": "x", "ігрек": "y", "ігрик": "y", "зет": "z", "зєд": "z",
            "альфа": "alpha", "бета": "beta", "гамма": "gamma",
            "пі": "pi", "є": "E",

            # 5. ЦИФРИ: Одиниці (з урахуванням орфографії)
            "нуль": "0", "один": "1", "одна": "1", "два": "2", "дві": "2",
            "три": "3", "чотири": "4", "п'ять": "5", "пять": "5",
            "шість": "6", "сім": "7", "вісім": "8", "дев'ять": "9", "девять": "9",
            
            # 6. ЦИФРИ: Другий десяток
            "десять": "10", "одинадцять": "11", "дванадцять": "12", "тринадцять": "13",
            "чотирнадцять": "14", "п'ятнадцять": "15", "пятнадцять": "15", 
            "шістнадцять": "16", "сімнадцять": "17", "вісімнадцять": "18", 
            "дев'ятнадцять": "19", "девятнадцять": "19",
            
            # 7. ЦИФРИ: Десятки та сотні
            "двадцять": "20", "тридцять": "30", "сорок": "40", "п'ятдесят": "50", "пятдесят": "50",
            "шістдесят": "60", "сімдесят": "70", "вісімдесят": "80", "дев'яносто": "90", "девяносто": "90",
            "сто": "100", "двісті": "200", "триста": "300", "тисяча": "1000"
        }

        parsed_text = spoken_text.lower()
        # Сортуємо словник від найдовших фраз до найкоротших слів, щоб "помножити на" замінилося швидше ніж просто "на"
        sorted_keys = sorted(replacements.keys(), key=len, reverse=True)
        for ukr_word in sorted_keys:
            parsed_text = re.sub(rf'\b{ukr_word}\b', replacements[ukr_word], parsed_text)

        math_str = parsed_text.replace(" ", "")
        # Видаляємо зайві математичні знаки на початку (якщо мікрофон "зловив" шум)
        math_str = re.sub(r'^[\*\/\+\-\=]+', '', math_str)

        # Балансування дужок
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
        # 1. Якщо це РІВНЯННЯ (є знак дорівнює)
        if "=" in raw_math:
            left_part, right_part = raw_math.split("=", 1)
            
            # Обробляємо ліву і праву частини незалежно одна від одної
            left_expr = sp.sympify(left_part.replace("()", "(?)"), evaluate=False, locals={"?": sp.Symbol("?")})
            right_expr = sp.sympify(right_part.replace("()", "(?)"), evaluate=False, locals={"?": sp.Symbol("?")})
            
            # Збираємо ідеальний LaTeX з дорівнює по центру
            latex_formula = f"${sp.latex(left_expr)} = {sp.latex(right_expr)}$"
            plain_formula = f"{left_expr} = {right_expr}"
            
        # 2. Якщо це звичайний ВИРАЗ (без дорівнює)
        else:
            clean_string = raw_math.replace("()", "(?)")
            expr = sp.sympify(clean_string, evaluate=False, locals={"?": sp.Symbol("?")})
            
            latex_formula = f"${sp.latex(expr)}$"
            plain_formula = str(expr)

        # Робимо текстовий формат красивішим (для Miro)
        plain_formula = plain_formula.replace('**', '^').replace('sqrt', '√').replace('pi', 'π')
        plain_formula = plain_formula.replace('alpha', 'α').replace('beta', 'β').replace('gamma', 'γ')

    except Exception as e:
        print(f"Помилка SymPy: {e}")
        # Якщо SymPy все ж падає, робимо псевдо-LaTeX своїми руками, щоб не віддавати сирий Python-код
        fallback_latex = raw_math.replace('**', '^').replace('sqrt', '\\sqrt').replace('pi', '\\pi')
        fallback_latex = fallback_latex.replace('alpha', '\\alpha ').replace('beta', '\\beta ').replace('gamma', '\\gamma ')
        latex_formula = f"${fallback_latex}$"
        
        plain_formula = raw_math.replace('**', '^').replace('sqrt', '√').replace('pi', 'π')
        plain_formula = plain_formula.replace('alpha', 'α').replace('beta', 'β').replace('gamma', 'γ')

    return jsonify({
        "latex": latex_formula,
        "plain": plain_formula
    })


if __name__ == '__main__':
    print("🚀 Сервер працює! Чекаю на запити...")
    app.run(port=5000)
