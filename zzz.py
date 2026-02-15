from flask import Flask, request, render_template_string, redirect, url_for, session, flash
import sqlite3, os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super_secret_key_2026"

# ================== إعدادات ==================
STORE_NAME = "🏪 سوبر ماركت أولاد قايد محمد"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("1111")

# لريندر (لو فعلت disk استخدم /var/data/)

DB_FILE = "/var/data/supermarket.db"


# ================== قاعدة البيانات ==================
def get_db():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        price REAL,
        stock INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT,
        qty INTEGER,
        total REAL,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================== أدوات ==================
def admin_required():
    return session.get("admin")

# ================== صفحة الزبون ==================
@app.route("/")
def home():
    search = request.args.get("search","")
    conn = get_db()
    cur = conn.cursor()

    if search:
        cur.execute("SELECT * FROM products WHERE name LIKE ?", ('%'+search+'%',))
    else:
        cur.execute("SELECT * FROM products")

    products = cur.fetchall()
    conn.close()

    html = """
    <html dir="rtl">
    <head>
    <title>الواجهة</title>
    <style>
    body{background:#111;color:#fff;font-family:tahoma;padding:20px}
    .card{background:#1e1e1e;padding:15px;margin:10px;border-radius:10px}
    .gold{color:gold}
    button{background:gold;border:none;padding:5px 10px}
    input{padding:5px}
    </style>
    </head>
    <body>

    <h2 class="gold">{{store}}</h2>

    <form>
        <input name="search" placeholder="بحث منتج">
        <button>بحث</button>
    </form>

    <br>
    <a href="/admin_login" style="color:gold">🔐 دخول المدير</a>
    <hr>

    {% for p in products %}
    <div class="card">
        <h3>{{p[1]}}</h3>
        <div>السعر: {{p[2]}}</div>
        <div>المخزون: {{p[3]}}</div>

        <form method="POST" action="/buy">
            <input type="hidden" name="id" value="{{p[0]}}">
            <input type="number" name="qty" min="1" value="1">
            <button>شراء</button>
        </form>
    </div>
    {% endfor %}

    </body>
    </html>
    """

    return render_template_string(html, products=products, store=STORE_NAME)

# ================== شراء ==================
@app.route("/buy", methods=["POST"])
def buy():
    pid = request.form["id"]
    qty = int(request.form["qty"])

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT name, price, stock FROM products WHERE id=?", (pid,))
    product = cur.fetchone()

    if not product:
        return "المنتج غير موجود"

    name, price, stock = product

    if qty > stock:
        return "الكمية غير متوفرة"

    total = price * qty
    new_stock = stock - qty

    cur.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, pid))
    cur.execute("INSERT INTO sales (product, qty, total, date) VALUES (?,?,?,?)",
                (name, qty, total, datetime.now().strftime("%Y-%m-%d")))

    conn.commit()
    conn.close()

    return redirect("/")

# ================== تسجيل دخول المدير ==================
@app.route("/admin_login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session["admin"] = True
            return redirect("/admin")
        else:
            flash("بيانات غير صحيحة")

    return """
    <body style="background:#111;color:white;text-align:center;padding:50px">
    <h2>دخول المدير</h2>
    <form method="POST">
    <input name="username" placeholder="اسم المستخدم"><br><br>
    <input type="password" name="password" placeholder="كلمة المرور"><br><br>
    <button style="background:gold">دخول</button>
    </form>
    </body>
    """

# ================== لوحة المدير ==================
@app.route("/admin", methods=["GET","POST"])
def admin():
    if not admin_required():
        return redirect("/admin_login")

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        stock = request.form["stock"]

        try:
            cur.execute("INSERT INTO products (name,price,stock) VALUES (?,?,?)",
                        (name, price, stock))
            conn.commit()
        except:
            pass

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    cur.execute("SELECT SUM(total) FROM sales WHERE date=?", 
                (datetime.now().strftime("%Y-%m-%d"),))
    today_sales = cur.fetchone()[0] or 0

    conn.close()

    html = """
    <html dir="rtl">
    <body style="background:#111;color:white;padding:20px">

    <h2 style="color:gold">لوحة التحكم</h2>

    <h3>💰 أرباح اليوم: {{today}}</h3>

    <h3>➕ إضافة منتج</h3>
    <form method="POST">
    الاسم:<input name="name"><br><br>
    السعر:<input name="price"><br><br>
    المخزون:<input name="stock"><br><br>
    <button style="background:gold">إضافة</button>
    </form>

    <hr>

    <h3>📦 المنتجات</h3>
    {% for p in products %}
        <div>
        {{p[1]}} | السعر: {{p[2]}} | المخزون: {{p[3]}}
        </div>
    {% endfor %}

    <br><br>
    <a href="/logout" style="color:gold">تسجيل خروج</a>

    </body>
    </html>
    """

    return render_template_string(html, products=products, today=today_sales)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================== تشغيل ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    

