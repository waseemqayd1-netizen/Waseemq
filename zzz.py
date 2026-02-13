from flask import Flask, request, render_template_string, redirect, url_for, flash
import sqlite3, os, uuid
from werkzeug.utils import secure_filename
from urllib.parse import quote
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

STORE_NAME = "🏪 سوبر ماركت أولاد قايد محمد"
WHATSAPP_NUMBER = "967770295876"

DB_FILE = "supermarket.db"
UPLOAD_FOLDER = "static/images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
ADMIN_PASSWORD = "1111"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= قاعدة البيانات =================
def connect():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        name TEXT PRIMARY KEY,
        price REAL,
        stock INTEGER,
        image TEXT,
        discount REAL DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= دوال المنتجات =================
def get_products():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    data = cur.fetchall()
    conn.close()
    return data

def get_product(name):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE name=?", (name,))
    data = cur.fetchone()
    conn.close()
    return data

def add_product(name, price, stock, image):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO products VALUES(?,?,?,?,0)", (name, price, stock, image))
    conn.commit()
    conn.close()

def update_stock(name, qty):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE products SET stock = stock - ? WHERE name=?", (qty, name))
    conn.commit()
    conn.close()

# ================= واجهة الزبون =================
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
            body{direction:rtl;background:#f8f9fa;padding:20px}
            .card{margin:10px;padding:10px;text-align:center}
        </style>
    </head>
    <body class="container">

    <h2 class="text-center">{{store}}</h2>
    <a href="/admin" class="btn btn-warning mb-3">🔧 صفحة المدير</a>

    <div class="row">
    {% for p in products %}
        <div class="col-md-3">
            <div class="card">
                {% if p[3] %}
                    <img src="{{p[3]}}" height="120">
                {% endif %}
                <h5>{{p[0]}}</h5>
                <p>{{p[1]}} ريال</p>
                <input type="number" min="1" max="{{p[2]}}" value="1" id="qty{{loop.index}}" class="form-control mb-2">
                <button onclick="add('{{p[0]}}', {{p[1]}}, {{loop.index}})" class="btn btn-primary btn-sm">إضافة</button>
            </div>
        </div>
    {% endfor %}
    </div>

    <h3 class="mt-4">🛒 السلة</h3>
    <table class="table table-bordered" id="cart">
        <tr><th>المنتج</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>
    </table>

    <button onclick="makeBill()" class="btn btn-info">🧾 عرض الفاتورة</button>
    <button onclick="sendWhats()" class="btn btn-success">📱 إرسال واتساب</button>

    <div id="bill" class="mt-3"></div>

<script>
let cart = {};

function add(name, price, index){
    let qty = parseInt(document.getElementById("qty"+index).value);
    if(!cart[name]) cart[name] = {price:price, qty:0};
    cart[name].qty += qty;
    renderCart();
}

function renderCart(){
    let table = document.getElementById("cart");
    table.innerHTML = "<tr><th>المنتج</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>";
    for(let n in cart){
        let row = table.insertRow();
        row.insertCell(0).innerText = n;
        row.insertCell(1).innerText = cart[n].qty;
        row.insertCell(2).innerText = cart[n].price;
        row.insertCell(3).innerText = cart[n].price * cart[n].qty;
    }
}

function makeBill(){
    let total = 0;
    let billHTML = "<h4>فاتورة شراء</h4>";
    billHTML += "<table class='table table-bordered'>";
    billHTML += "<tr><th>المنتج</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>";

    for(let n in cart){
        let t = cart[n].price * cart[n].qty;
        total += t;
        billHTML += "<tr><td>"+n+"</td><td>"+cart[n].qty+"</td><td>"+cart[n].price+"</td><td>"+t+"</td></tr>";
    }

    billHTML += "<tr><th colspan='3'>المجموع</th><th>"+total+"</th></tr>";
    billHTML += "</table>";

    document.getElementById("bill").innerHTML = billHTML;
}

function sendWhats(){
    let msg = "فاتورة شراء%0A";
    let total = 0;

    for(let n in cart){
        let t = cart[n].price * cart[n].qty;
        total += t;
        msg += n+" - "+cart[n].qty+" = "+t+"%0A";
    }

    msg += "المجموع: "+total;

    window.open("https://wa.me/{{phone}}?text="+msg, "_blank");
}
</script>

    </body>
    </html>
    """

    return render_template_string(html, products=products, store=STORE_NAME, phone=WHATSAPP_NUMBER)

# ================= صفحة المدير =================
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") != ADMIN_PASSWORD:
            flash("كلمة المرور خطأ")
            return redirect("/admin")

        name = request.form["name"]
        price = float(request.form["price"])
        stock = int(request.form["stock"])

        image_path = ""
        file = request.files["image"]
        if file and file.filename:
            filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)
            image_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(image_path)

        add_product(name, price, stock, image_path)
        return redirect("/admin")

    products = get_products()

    return render_template_string("""
    <h2>صفحة المدير</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="password" name="password" placeholder="كلمة المرور" required><br><br>
        <input name="name" placeholder="اسم المنتج" required><br>
        <input name="price" type="number" step="0.01" placeholder="السعر" required><br>
        <input name="stock" type="number" placeholder="الكمية" required><br>
        <input type="file" name="image"><br><br>
        <button>إضافة</button>
    </form>
    <hr>
    {% for p in products %}
        {{p[0]}} - {{p[1]}} ريال - كمية {{p[2]}} <br>
    {% endfor %}
    """, products=products)

# ================= تشغيل =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
