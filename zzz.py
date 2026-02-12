from flask import Flask, request, render_template_string, redirect, session
import sqlite3, os
from werkzeug.utils import secure_filename
from urllib.parse import quote
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secretkey123"

DB_FILE = "store.db"
UPLOAD_FOLDER = "static/uploads"
STORE_PHONE = "967771602370"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =========================
# Database
# =========================

def connect():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            stock INTEGER,
            discount REAL DEFAULT 0,
            image TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total REAL,
            date TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# Helper
# =========================

def get_products():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    data = cur.fetchall()
    conn.close()
    return data

# =========================
# Store
# =========================

@app.route("/")
def store():
    products = get_products()

    html = """
<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="UTF-8">
<title>متجر وسيم</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{direction:rtl;background:#f8f9fa;padding:20px}
.card:hover{transform:scale(1.05);transition:0.3s}
</style>
</head>
<body>

<h2 class="text-center mb-4">🛒 متجر وسيم</h2>
<a href="/login" class="btn btn-warning mb-3">لوحة المدير</a>

<div class="row">
{% for p in products %}
<div class="col-md-4">
<div class="card shadow mb-4">
<img src="/{{p[5]}}" class="card-img-top" style="height:200px;object-fit:cover">
<div class="card-body text-center">
<h5>{{p[1]}}</h5>

{% if p[4] > 0 %}
<p><del>{{p[2]}}</del>
<span class="text-danger">{{p[2] - (p[2]*p[4]/100)}}</span> ريال</p>
{% else %}
<p class="text-danger">{{p[2]}} ريال</p>
{% endif %}

<p>المخزون: {{p[3]}}</p>

<button onclick="addToCart('{{p[1]}}', {{p[2] - (p[2]*p[4]/100)}})" class="btn btn-success" {% if p[3] <= 0 %}disabled{% endif %}>
أضف للسلة
</button>
</div>
</div>
</div>
{% endfor %}
</div>

<hr>
<h4>🧾 السلة</h4>
<ul id="cart"></ul>
<h5 id="total"></h5>

<button onclick="sendWhatsApp()" class="btn btn-primary">إرسال الطلب</button>

<script>
let cart=[];
function addToCart(n,p){
cart.push({name:n,price:p});
render();
}
function render(){
let total=0;
document.getElementById("cart").innerHTML="";
cart.forEach(i=>{
document.getElementById("cart").innerHTML+=`<li>${i.name} - ${i.price}</li>`;
total+=i.price;
});
document.getElementById("total").innerHTML="الإجمالي: "+total+" ريال";
}
function sendWhatsApp(){
let msg="طلب جديد:%0A";
let total=0;
cart.forEach(i=>{
msg+=i.name+" - "+i.price+" ريال%0A";
total+=i.price;
});
msg+="%0Aالإجمالي: "+total+" ريال";
window.open("https://wa.me/""" + STORE_PHONE + """?text="+msg);
}
</script>

</body>
</html>
"""
    return render_template_string(html, products=products)

# =========================
# Login
# =========================

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == os.environ.get("ADMIN_PASSWORD"):
            session["admin"]=True
            return redirect("/admin")
    return """
    <h3>تسجيل دخول المدير</h3>
    <form method="post">
    كلمة المرور: <input type="password" name="password">
    <button type="submit">دخول</button>
    </form>
    """

# =========================
# Admin
# =========================

@app.route("/admin", methods=["GET","POST"])
def admin():
    if not session.get("admin"):
        return redirect("/login")

    if request.method=="POST":
        name=request.form["name"]
        price=float(request.form["price"])
        stock=int(request.form["stock"])
        discount=float(request.form["discount"])

        file=request.files["image"]
        filename=secure_filename(file.filename)
        path=os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        conn=connect()
        cur=conn.cursor()
        cur.execute("INSERT INTO products (name,price,stock,discount,image) VALUES (?,?,?,?,?)",
                    (name,price,stock,discount,path))
        conn.commit()
        conn.close()
        return redirect("/admin")

    products=get_products()

    return render_template_string("""
<h2>لوحة المدير</h2>
<a href="/">رجوع للمتجر</a>
<hr>
<form method="post" enctype="multipart/form-data">
اسم: <input name="name"><br><br>
السعر: <input name="price"><br><br>
المخزون: <input name="stock"><br><br>
الخصم %: <input name="discount"><br><br>
الصورة: <input type="file" name="image"><br><br>
<button type="submit">إضافة</button>
</form>
<hr>
{% for p in products %}
<div>{{p[1]}} - المخزون: {{p[3]}}</div>
{% endfor %}
""", products=products)

# =========================
# Stats
# =========================

@app.route("/stats")
def stats():
    conn=connect()
    cur=conn.cursor()
    cur.execute("SELECT SUM(total) FROM sales")
    total=cur.fetchone()[0]
    conn.close()
    return f"<h2>إجمالي المبيعات: {total}</h2>"

# =========================

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
