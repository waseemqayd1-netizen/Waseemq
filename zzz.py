from flask import Flask, request, render_template_string, redirect, url_for, flash
import sqlite3, os, uuid
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ================= إعدادات =================
STORE_NAME = "🏪 سوبر ماركت أولاد قايد محمد"
ADMIN_PASSWORD = "1111"

# مهم لريندر (لو فعلت Disk استخدم /var/data/)
DB_FILE = os.path.join(os.getcwd(), "supermarket.db")

UPLOAD_FOLDER = os.path.join("static", "images")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= قاعدة البيانات =================
def get_db():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        name TEXT PRIMARY KEY,
        price REAL,
        stock INTEGER,
        image TEXT,
        discount REAL DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datetime TEXT,
        product TEXT,
        qty INTEGER,
        total REAL
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= أدوات =================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def get_products():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    data = cur.fetchall()
    conn.close()
    return data

def get_product(name):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE name=?", (name,))
    data = cur.fetchone()
    conn.close()
    return data

# ================= صفحة الزبون =================
@app.route("/")
def home():
    products = get_products()

    html = """
    <!DOCTYPE html>
    <html lang="ar">
    <head>
        <meta charset="UTF-8">
        <title>واجهة الزبون</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body{direction:rtl;padding:20px;background:#f8f9fa;}
            .card{margin:10px;padding:10px;text-align:center}
            img{max-width:120px;height:120px;object-fit:contain}
        </style>
    </head>
    <body class="container">

    <h2 class="text-center mb-4">{{store}}</h2>

    <a href="/admin" class="btn btn-warning mb-3">🔧 صفحة المدير</a>

    <div class="row">
    {% for n,p,s,img,d in products %}
        <div class="col-md-3">
            <div class="card">
                {% if img %}
                    <img src="/{{img}}">
                {% else %}
                    <img src="https://via.placeholder.com/120">
                {% endif %}
                <h5>{{n}}</h5>
                <div>السعر: {{p}}</div>
                <div>المخزون: {{s}}</div>
            </div>
        </div>
    {% endfor %}
    </div>

    </body>
    </html>
    """

    return render_template_string(html, products=products, store=STORE_NAME)

# ================= صفحة المدير =================
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password")
        if password != ADMIN_PASSWORD:
            flash("كلمة المرور خطأ")
            return redirect(url_for("admin"))

        action = request.form.get("action")

        if action == "add":
            name = request.form.get("name")
            price = float(request.form.get("price"))
            stock = int(request.form.get("stock"))
            discount = float(request.form.get("discount",0))
            image_file = request.files.get("image")

            image_path = ""
            if image_file and allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                filename = f"{uuid.uuid4().hex}_{filename}"
                path = os.path.join(UPLOAD_FOLDER, filename)
                image_file.save(path)
                image_path = path.replace("\\","/")

            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute("INSERT INTO products VALUES (?,?,?,?,?)",
                            (name, price, stock, image_path, discount))
                conn.commit()
            except:
                flash("المنتج موجود مسبقاً")
            conn.close()

        elif action == "delete":
            name = request.form.get("name")
            conn = get_db()
            cur = conn.cursor()
            cur.execute("DELETE FROM products WHERE name=?", (name,))
            conn.commit()
            conn.close()

        return redirect(url_for("admin"))

    products = get_products()

    html = """
    <!DOCTYPE html>
    <html lang="ar">
    <head>
        <meta charset="UTF-8">
        <title>صفحة المدير</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>body{direction:rtl;padding:20px}</style>
    </head>
    <body class="container">

    <h2>🔧 صفحة المدير</h2>

    <form method="POST" enctype="multipart/form-data">
        <input type="hidden" name="action" value="add">
        كلمة المرور: <input type="password" name="password" required><br><br>
        اسم المنتج: <input type="text" name="name" required><br><br>
        السعر: <input type="number" step="0.01" name="price" required><br><br>
        الكمية: <input type="number" name="stock" required><br><br>
        الخصم %: <input type="number" step="0.01" name="discount" value="0"><br><br>
        صورة: <input type="file" name="image"><br><br>
        <button class="btn btn-success">إضافة المنتج</button>
    </form>

    <hr>

    <h3>المنتجات</h3>
    <table class="table table-bordered">
    <tr><th>الاسم</th><th>السعر</th><th>المخزون</th><th>حذف</th></tr>
    {% for n,p,s,img,d in products %}
        <tr>
            <td>{{n}}</td>
            <td>{{p}}</td>
            <td>{{s}}</td>
            <td>
                <form method="POST">
                    <input type="hidden" name="action" value="delete">
                    <input type="hidden" name="password" value="1111">
                    <input type="hidden" name="name" value="{{n}}">
                    <button class="btn btn-danger btn-sm">حذف</button>
                </form>
            </td>
        </tr>
    {% endfor %}
    </table>

    </body>
    </html>
    """

    return render_template_string(html, products=products)

# ================= تشغيل =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
