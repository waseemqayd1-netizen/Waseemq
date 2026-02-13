from flask import Flask, request, redirect, render_template_string, send_file
import psycopg2
import os
from io import BytesIO

app = Flask(__name__)

def connect():
    # يقرأ DATABASE_URL من المتغيرات
    return psycopg2.connect(os.environ.get("DATABASE_URL"), sslmode="require")

def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id SERIAL PRIMARY KEY,
        name TEXT,
        price REAL,
        stock INTEGER,
        image BYTEA
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# صفحة الرئيسية
# =========================
@app.route("/")
def index():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, stock FROM products ORDER BY id")
    products = cur.fetchall()
    conn.close()

    return render_template_string("""
    <html dir="rtl">
    <head>
        <title>المتجر</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-dark text-white p-4">

    <h2 class="text-warning">المتجر</h2>
    <a href="/add" class="btn btn-success mb-3">➕ إضافة منتج</a>

    <div class="row">
    {% for p in products %}
        <div class="col-md-4">
            <div class="card bg-secondary mb-3">
                <div class="card-body text-center">
                    <h5>{{p[1]}}</h5>
                    <p>السعر: {{p[2]}}</p>
                    <p>المخزون: {{p[3]}}</p>
                    <img src="/image/{{p[0]}}" width="150"><br><br>

                    <a href="/edit/{{p[0]}}" class="btn btn-warning btn-sm">تعديل</a>
                    <a href="/delete/{{p[0]}}" onclick="return confirm('هل أنت متأكد؟')" class="btn btn-danger btn-sm">حذف</a>
                </div>
            </div>
        </div>
    {% endfor %}
    </div>

    </body>
    </html>
    """, products=products)

# =========================
# عرض الصورة
# =========================
@app.route("/image/<int:id>")
def image(id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT image FROM products WHERE id=%s", (id,))
    data = cur.fetchone()
    conn.close()

    if data and data[0]:
        return send_file(BytesIO(data[0]), mimetype="image/jpeg")
    return ""

# =========================
# إضافة منتج
# =========================
@app.route("/add", methods=["GET","POST"])
def add():
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        stock = request.form["stock"]
        image = request.files["image"].read()

        conn = connect()
        cur = conn.cursor()
        cur.execute("INSERT INTO products (name, price, stock, image) VALUES (%s, %s, %s, %s)",
                    (name, price, stock, image))
        conn.commit()
        conn.close()

        return redirect("/")

    return """
    <html dir="rtl"><body class="p-4">
    <h2>إضافة منتج</h2>
    <form method="POST" enctype="multipart/form-data">
        الاسم: <input name="name" required><br><br>
        السعر: <input name="price" required><br><br>
        المخزون: <input name="stock" required><br><br>
        الصورة: <input type="file" name="image" required><br><br>
        <button type="submit">حفظ</button>
    </form>
    </body></html>
    """

# =========================
# تعديل منتج
# =========================
@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit(id):
    conn = connect()
    cur = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        stock = request.form["stock"]

        image_file = request.files.get("image")
        if image_file and image_file.filename != "":
            image = image_file.read()
            cur.execute("""
                UPDATE products SET name=%s, price=%s, stock=%s, image=%s WHERE id=%s
            """, (name, price, stock, image, id))
        else:
            cur.execute("""
                UPDATE products SET name=%s, price=%s, stock=%s WHERE id=%s
            """, (name, price, stock, id))

        conn.commit()
        conn.close()
        return redirect("/")

    cur.execute("SELECT name, price, stock FROM products WHERE id=%s", (id,))
    product = cur.fetchone()
    conn.close()

    return f"""
    <html dir="rtl"><body class="p-4">
    <h2>تعديل منتج</h2>
    <form method="POST" enctype="multipart/form-data">
        الاسم: <input name="name" value="{product[0]}" required><br><br>
        السعر: <input name="price" value="{product[1]}" required><br><br>
        المخزون: <input name="stock" value="{product[2]}" required><br><br>
        تغيير الصورة: <input type="file" name="image"><br><br>
        <button type="submit">تحديث</button>
    </form>
    </body></html>
    """

# =========================
# حذف منتج
# =========================
@app.route("/delete/<int:id>")
def delete(id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run()
    
