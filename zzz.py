from flask import Flask, request, render_template_string, redirect, session, send_file
import psycopg2
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from io import BytesIO

app = Flask(__name__)
app.secret_key = "your-secret-key"

def connect():
    return psycopg2.connect(os.environ.get("DATABASE_URL"), sslmode="require")

# ================================
# الصفحة الرئيسية
# ================================
@app.route("/")
def index():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price FROM products ORDER BY id")
    products = cur.fetchall()
    conn.close()

    return render_template_string("""
<html dir="rtl">
<head>
    <title>المتجر</title>
    <style>
        body { background: black; color: gold; font-family: Arial, sans-serif;}
        .grid { display: flex; flex-wrap: wrap; gap: 20px; }
        .card {
            background: #1a1a1a;
            border: 2px solid gold;
            border-radius: 8px;
            width: 200px; padding: 10px;
            text-align: center;
        }
        .btn {
            background: gold; color: black;
            padding: 8px 12px; text-decoration: none;
            font-weight: bold; display: inline-block;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <h1>🌟 متجر أولاد قايد 🌟</h1>
    <a class="btn" href="/cart">🛒 سلة المشتريات</a>
    <div class="grid">
        {% for p in products %}
        <div class="card">
            <img src="/image/{{p[0]}}" width="150"><br><br>
            <h3>{{p[1]}}</h3>
            <p>السعر: {{p[2]}}</p>
            <a class="btn" href="/add_to_cart/{{p[0]}}">➕ أضف للسلة</a>
        </div>
        {% endfor %}
    </div>
</body>
</html>
""", products=products)

# ================================
# أضف للسلة
# ================================
@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):
    cart = session.get("cart", {})
    cart[str(id)] = cart.get(str(id), 0) + 1
    session["cart"] = cart
    return redirect("/cart")

# ================================
# عرض السلة
# ================================
@app.route("/cart")
def cart():
    cart = session.get("cart", {})
    items = []
    total = 0

    conn = connect()
    cur = conn.cursor()

    for pid, qty in cart.items():
        cur.execute("SELECT name, price FROM products WHERE id=%s", (pid,))
        p = cur.fetchone()
        cur.execute("SELECT image FROM products WHERE id=%s", (pid,))
        img = cur.fetchone()[0]
        items.append((pid, p[0], p[1], qty, img))
        total += p[1] * qty

    conn.close()

    return render_template_string("""
<html dir="rtl">
<head>
    <title>السلة</title>
    <style>
        body { background: black; color: gold; font-family: Arial, sans-serif;}
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid gold; padding: 10px; }
        .btn { background: gold; color: black; padding: 8px 12px; text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🛒 سلة مشترياتك</h1>
    <table>
        <tr>
            <th>الصورة</th><th>المنتج</th><th>السعر</th><th>الكمية</th><th>الإجمالي</th><th></th>
        </tr>
        {% for i in items %}
        <tr>
            <td><img src="/image/{{i[0]}}" width="80"></td>
            <td>{{i[1]}}</td>
            <td>{{i[2]}}</td>
            <td>{{i[3]}}</td>
            <td>{{i[2]*i[3]}}</td>
            <td><a class="btn" href="/remove_from_cart/{{i[0]}}">❌ حذف</a></td>
        </tr>
        {% endfor %}
    </table>
    <h2>الإجمالي: {{total}}</h2>
    <a class="btn" href="/checkout">📦 إتمام الطلب</a>
</body>
</html>
""", items=items, total=total)

# ================================
# حذف من السلة
# ================================
@app.route("/remove_from_cart/<int:id>")
def remove_from_cart(id):
    cart = session.get("cart", {})
    cart.pop(str(id), None)
    session["cart"] = cart
    return redirect("/cart")

# ================================
# Checkout + عرض الفاتورة
# ================================
@app.route("/checkout", methods=["GET","POST"])
def checkout():
    cart = session.get("cart", {})
    if not cart:
        return redirect("/cart")

    if request.method == "POST":
        customer_name = request.form["customer_name"]
        customer_phone = request.form["customer_phone"]

        conn = connect()
        cur = conn.cursor()

        cur.execute("INSERT INTO orders (created_at, customer_name, customer_phone) VALUES (%s, %s, %s) RETURNING id",
                    (datetime.now(), customer_name, customer_phone))
        order_id = cur.fetchone()[0]

        items = []
        total = 0

        for pid, qty in cart.items():
            cur.execute("SELECT name, price FROM products WHERE id=%s", (pid,))
            p = cur.fetchone()
            cur.execute("SELECT image FROM products WHERE id=%s", (pid,))
            img = cur.fetchone()[0]
            items.append((pid, p[0], p[1], qty, img))
            total += p[1] * qty

            cur.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, pid, qty, p[1]))

        conn.commit()
        conn.close()

        session["cart"] = {}

        return render_template_string("""
<html dir="rtl">
<head><title>فاتورتك</title></head>
<body style="background:black;color:gold;font-family:Arial;">
    <h1>📄 فاتورة طلبك</h1>
    <p><strong style="color:blue;">سوبر ماركت أولاد قايد للتجارة العامة</strong></p>
    <p><strong style="color:blue;">موعد حماده</strong></p>
    <p><strong>اسم الزبون:</strong> {{ customer_name }}</p>
    <p><strong>رقم الهاتف:</strong> {{ customer_phone }}</p>
    <hr color="gold">
    <table border="1" width="100%" style="border-collapse:collapse;color:gold;">
        <tr><th>الصورة</th><th>المنتج</th><th>السعر</th><th>الكمية</th><th>الإجمالي</th></tr>
        {% for i in items %}
        <tr>
            <td><img src="/image/{{i[0]}}" width="60"></td>
            <td>{{i[1]}}</td>
            <td>{{i[2]}}</td>
            <td>{{i[3]}}</td>
            <td>{{i[2]*i[3]}}</td>
        </tr>
        {% endfor %}
    </table>
    <h2>💰 الإجمالي الكلّي: {{ total }}</h2>
    <a style="background:gold;color:black;padding:10px;font-weight:bold;text-decoration:none;" href="/download_invoice/{{order_id}}">⬇️ تحميل PDF</a><br><br>
    <a style="background:gold;color:black;padding:10px;font-weight:bold;text-decoration:none;" href="/">🏠 العودة للمتجر</a>
</body>
</html>
""", items=items, total=total, order_id=order_id,
   customer_name=customer_name, customer_phone=customer_phone)

    return render_template_string("""
<html dir="rtl">
<head><title>إتمام الطلب</title></head>
<body style="background:black;color:gold;font-family:Arial;">
    <h1>📦 بيانات الزبون</h1>
    <form method="POST">
        الاسم الكامل:<br><input type="text" name="customer_name" required><br><br>
        رقم الجوال:<br><input type="text" name="customer_phone" required><br><br>
        <button style="background:gold;color:black;padding:10px;font-weight:bold;" type="submit">📄 عرض الفاتورة</button>
    </form>
</body>
</html>
""")

# ================================
# تحميل الفاتورة PDF
# ================================
@app.route("/download_invoice/<int:order_id>")
def download_invoice(order_id):
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT customer_name, customer_phone FROM orders WHERE id=%s", (order_id,))
    customer = cur.fetchone()

    cur.execute("""
        SELECT products.name, order_items.price, order_items.quantity
        FROM order_items JOIN products
        ON order_items.product_id = products.id
        WHERE order_items.order_id=%s
    """, (order_id,))
    items = cur.fetchall()

    conn.close()

    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    # عنوان المتجر باللون الأزرق
    p.setFont("Helvetica-Bold", 18)
    p.setFillColorRGB(0, 0, 0.8)
    p.drawString(50, 820, "سوبر ماركت أولاد قايد للتجارة العامة")
    p.drawString(50, 800, "موعد حماده")

    p.setFont("Helvetica", 12)
    p.setFillColorRGB(0, 0, 0)
    p.drawString(50, 780, f"اسم الزبون: {customer[0]}")
    p.drawString(50, 765, f"رقم الجوال: {customer[1]}")

    y = 740
    p.drawString(50, y, "----------------------------------------------")
    y -= 20

    total_price = 0
    for name, price, qty in items:
        p.drawString(50, y, f"{name} x{qty} - {price*qty}")
        total_price += price*qty
        y -= 20

    p.drawString(50, y-10, "----------------------------------------------")
    p.drawString(50, y-30, f"الإجمالي الكلّي: {total_price}")

    y -= 60
    p.drawString(50, y, "إعداد وتصميم")
    y -= 20
    p.drawString(50, y, "«م. / وسيم العامري.»")

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"فاتورة_{order_id}.pdf",
                     mimetype="application/pdf")

if __name__ == "__main__":
    app.run()
    
