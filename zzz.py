from flask import Flask, request, render_template_string, redirect
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# =========================
# إعداد قاعدة البيانات
# =========================

DB_FILE = "store.db"

def create_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = create_connection()
    cur = conn.cursor()

    # جدول المنتجات
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            category TEXT DEFAULT 'عام'
        )
    """)

    # جدول الفئات
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            name TEXT PRIMARY KEY
        )
    """)

    # جدول المبيعات
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datetime TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            product_name TEXT,
            quantity INTEGER,
            price REAL,
            total REAL
        )
    """)

    # إضافة فئة افتراضية
    try:
        cur.execute("INSERT INTO categories (name) VALUES (?)", ("عام",))
    except:
        pass

    conn.commit()
    conn.close()

# إنشاء الجداول مباشرة عند تشغيل التطبيق
init_db()

# =========================
# دوال جلب البيانات
# =========================

def get_products():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    conn.close()
    return products

def get_categories():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM categories")
    categories = cur.fetchall()
    conn.close()
    return categories

# =========================
# واجهة الزبون
# =========================

@app.route("/")
def customer_page():
    products = get_products()
    categories = get_categories()

    html = """
    <h2>واجهة الزبون</h2>
    <a href="/admin">صفحة المدير</a>
    <hr>
    {% for p in products %}
        <div>
            <b>{{p[1]}}</b> - السعر: {{p[2]}}
        </div>
    {% endfor %}
    """

    return render_template_string(html, products=products, categories=categories)

# =========================
# صفحة المدير
# =========================

@app.route("/admin", methods=["GET", "POST"])
def admin_page():
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        stock = request.form["stock"]

        conn = create_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
            (name, price, stock)
        )
        conn.commit()
        conn.close()

        return redirect("/admin")

    products = get_products()

    html = """
    <h2>لوحة المدير</h2>
    <a href="/">رجوع للمتجر</a>
    <hr>
    <form method="post">
        اسم المنتج: <input name="name"><br>
        السعر: <input name="price"><br>
        الكمية: <input name="stock"><br>
        <button type="submit">إضافة</button>
    </form>
    <hr>
    {% for p in products %}
        <div>{{p[1]}} - {{p[2]}} - الكمية: {{p[3]}}</div>
    {% endfor %}
    """

    return render_template_string(html, products=products)

# =========================
# التشغيل
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
