from flask import Flask, request, jsonify, render_template_string, redirect, url_for, flash
import sqlite3, os
from werkzeug.utils import secure_filename
from urllib.parse import quote
from datetime import datetime
import uuid
app = Flask(__name__)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    


init_db()


app.secret_key = "secret123"

STORE_NAME = "🏪 سوبر ماركت أولاد قايد محمد"
STORE_PHONE = "967771602370"

DB_FILE = "store.db"
UPLOAD_FOLDER = "static/images/"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

ADMIN_PASSWORD = "1111"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= قاعدة البيانات =================


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL
    )
    """)
    
    conn.commit()
    conn.close()

init_db()


def create_connection():
    return sqlite3.connect(DB_FILE)

def create_product_table():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        name TEXT PRIMARY KEY,
        price REAL NOT NULL,
        stock INTEGER NOT NULL,
        image_path TEXT DEFAULT '',
        discount REAL DEFAULT 0,
        category TEXT DEFAULT 'عام'
    )
    """)
    conn.commit()
    conn.close()

def create_sales_table():
    conn = create_connection()
    cur = conn.cursor()
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
    conn.commit()
    conn.close()

def create_category_table():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            name TEXT PRIMARY KEY
        )
    """)
    # إضافة فئة افتراضية
    try:
        cur.execute("INSERT INTO categories (name) VALUES (?)", ("عام",))
    except sqlite3.IntegrityError:
        pass
    conn.commit()
    conn.close()

# ================= دوال الفئات =================

def get_categories():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM categories ORDER BY name")
    cats = [r[0] for r in cur.fetchall()]
    conn.close()
    return cats

def add_category(name):
    conn = create_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# ================= دوال المنتجات =================

def get_products():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, price, stock, image_path, discount, category FROM products")
    data = cur.fetchall()
    conn.close()
    return data

def get_product(name):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, price, stock, image_path, discount, category FROM products WHERE name=?", (name,))
    data = cur.fetchone()
    conn.close()
    return data

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def insert_product(name, price, stock, image_file=None, discount=0, category="عام"):
    image_path = ""
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        filename = f"{uuid.uuid4().hex}_{filename}"
        image_path = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(image_path)

    conn = create_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO products (name, price, stock, image_path, discount, category) VALUES (?,?,?,?,?,?)",
            (name, price, stock, image_path, discount, category)
        )
        conn.commit()
        flash(f"✅ تم إضافة المنتج '{name}'", "success")
    except sqlite3.IntegrityError:
        flash(f"❌ المنتج '{name}' موجود مسبقًا", "error")
    finally:
        conn.close()

def set_stock(name, qty):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("UPDATE products SET stock=? WHERE name=?", (qty, name))
    conn.commit()
    conn.close()

def update_stock(name, qty):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("UPDATE products SET stock = stock - ? WHERE name=?", (qty, name))
    conn.commit()
    conn.close()

def update_product(name, price=None, discount=None, category=None):
    conn = create_connection()
    cur = conn.cursor()
    if price is not None:
        cur.execute("UPDATE products SET price=? WHERE name=?", (price, name))
    if discount is not None:
        cur.execute("UPDATE products SET discount=? WHERE name=?", (discount, name))
    if category is not None:
        cur.execute("UPDATE products SET category=? WHERE name=?", (category, name))
    conn.commit()
    conn.close()

def delete_product(name):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE name=?", (name,))
    conn.commit()
    conn.close()

# ================= مبيعات =================

def save_sale(customer_name, customer_phone, cart):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = create_connection()
    cur = conn.cursor()
    for n, q in cart.items():
        p = get_product(n)
        if not p: continue
        price = p[1] * (1 - p[4]/100)
        total = price * q
        cur.execute("""
            INSERT INTO sales (datetime, customer_name, customer_phone, product_name, quantity, price, total)
            VALUES (?,?,?,?,?,?,?)
        """, (now, customer_name, customer_phone, n, q, price, total))
    conn.commit()
    conn.close()

# ================= واجهة الزبون =================
@app.route("/")
def customer_page():
    products = get_products()
    categories = get_categories()

    html = """ 
<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="UTF-8">
<title>واجهة الزبون</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{direction:rtl;padding:15px;font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background:#f9f9f9;}
#categoryButtons button{margin:3px;}
.product-card{border:1px solid #ccc;padding:10px;margin:5px;text-align:center;border-radius:8px;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.1); transition:0.2s;}
.product-card:hover{transform:scale(1.03); box-shadow:0 4px 12px rgba(0,0,0,0.2);}
.product-card img{max-width:150px; max-height:150px; object-fit:contain;}
.product-price{font-weight:bold;margin-top:5px; color:#2c3e50;}
.header-store{font-size:28px;font-weight:bold; color:#e74c3c;}
.store-logo{display:block;margin:10px auto; max-width:200px;}
</style>
</head>
<body class="container">

<div class="text-center mb-4">
  <img src="https://ms.hsoubcdn.com/uploads/portfolios/1737137/63b1854f834e5/logo-13.png" class="store-logo" alt="شعار سوبر ماركت">
  <div class="header-store">{{store}}</div>
</div>

<a href="/admin" class="btn btn-warning mb-3">🔧 صفحة المدير</a>

<div class="mb-3">
  👤 الاسم: <input id="cname" class="form-control d-inline w-auto">
  📞 الهاتف: <input id="cphone" class="form-control d-inline w-auto">
</div>

<div class="mb-3">
  🔍 بحث عن منتج: <input id="searchInput" class="form-control d-inline w-auto" placeholder="اكتب اسم المنتج...">
</div>

<h3>🔘 تصنيفات المنتجات</h3>
<div id="categoryButtons" class="mb-3">
  <button class="btn btn-secondary" onclick="showAll()">كل المنتجات</button>
  {% for cat in categories %}
  <button class="btn btn-info" onclick="filterCategoryByName('{{cat}}')">{{cat}}</button>
  {% endfor %}
</div>

<div id="productsContainer" class="d-flex flex-wrap justify-content-start">
{% for n,p,s,img,d,cat in products %}
<div class="product-card" data-name="{{n}}" data-price="{{p}}" data-stock="{{s}}" data-discount="{{d}}" data-category="{{cat}}">
  {% if img %}
    <img src="{{ img }}" alt="{{n}}">
  {% else %}
    <img src="https://via.placeholder.com/150?text=No+Image" alt="No Image">
  {% endif %}
  <div>{{n}}</div>
  <div class="product-price">{{p}} {% if d>0 %}- خصم {{d}}%{% endif %}</div>
  <input type="number" value="1" min="1" max="{{s}}" class="form-control w-50 mx-auto my-1">
  <button class="btn btn-primary btn-sm" onclick="add(this)">➕ إضافة إلى السلة</button>
</div>
{% endfor %}
</div>

<h3 class="mt-4">🛒 سلة المشتريات</h3>
<table class="table table-bordered" id="cart">
<tr><th>المنتج</th><th>الكمية</th></tr>
</table>

<button class="btn btn-danger mb-2" onclick="clearCart()">🗑️ تفريغ السلة</button>
<button class="btn btn-info mb-2" onclick="makeBill()">🧾 عرض الفاتورة</button>
<button class="btn btn-success mb-2" id="whatsappBtn" onclick="sendWhats()">📱 إرسال واتساب</button>
<button class="btn btn-primary mb-2" id="confirmBtn" onclick="confirmSale()">✅ تأكيد البيع</button>

<div id="bill" class="mt-3"></div>

<script>
let cart = {};

function add(btn){
    let card = btn.parentElement;
    let name = card.dataset.name;
    let qty = parseInt(card.querySelector("input").value);
    if(qty > parseInt(card.dataset.stock)){
        alert("❌ الكمية المطلوبة أكبر من المخزون!");
        return;
    }
    cart[name] = (cart[name] || 0) + qty;
    drawCart();
}

function drawCart(){
    let t = document.getElementById("cart");
    t.innerHTML = "<tr><th>المنتج</th><th>الكمية</th></tr>";
    for(let k in cart){
        t.innerHTML += `<tr><td>${k}</td><td>${cart[k]}</td></tr>`;
    }
}

function clearCart(){
    if(confirm("هل تريد تفريغ السلة؟")){
        cart = {};
        drawCart();
        document.getElementById("bill").innerHTML = "";
        document.getElementById("confirmBtn").style.display = "inline";
    }
}

function makeBill(){
    fetch("/bill",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            customer_name: document.getElementById("cname").value,
            customer_phone: document.getElementById("cphone").value,
            cart: cart
        })
    }).then(r=>r.json()).then(d=>{
        document.getElementById("bill").innerHTML = d.bill_html;
        document.getElementById("bill").scrollIntoView({behavior:"smooth"});
    });
}

function sendWhats(){
    if(Object.keys(cart).length === 0){
        alert("❌ السلة فارغة!");
        return;
    }
    fetch("/bill",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            customer_name: document.getElementById("cname").value,
            customer_phone: document.getElementById("cphone").value,
            cart: cart
        })
    }).then(r=>r.json()).then(d=>{
        window.open(d.whatsapp_url,"_blank");
        document.getElementById("confirmBtn").style.display = "none";
    });
}

function confirmSale(){
    if(Object.keys(cart).length === 0){
        alert("❌ السلة فارغة!");
        return;
    }
    fetch("/confirm_sale",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            customer_name: document.getElementById("cname").value,
            customer_phone: document.getElementById("cphone").value,
            cart: cart
        })
    }).then(r=>r.json()).then(d=>{
        alert(d.message);
        location.reload();
    });
}

function showAll() {
    let cards = document.querySelectorAll(".product-card");
    cards.forEach(c => c.style.display = "block");
}

function filterCategoryByName(cat){
    let cards = document.querySelectorAll(".product-card");
    cards.forEach(c => {
        if(c.dataset.category === cat) c.style.display = "block";
        else c.style.display = "none";
    });
}

document.getElementById("searchInput").addEventListener("input", function(){
    let term = this.value.toLowerCase();
    let cards = document.querySelectorAll(".product-card");
    cards.forEach(c => {
        if(c.dataset.name.toLowerCase().includes(term)){
            c.style.display = "block";
        } else {
            c.style.display = "none";
        }
    });
});
</script>

</body>
</html>
"""
    return render_template_string(html, products=products, categories=categories, store=STORE_NAME)

# ================= متابعة مع الفاتورة =================
@app.route("/bill", methods=["POST"])
def bill():
    data = request.json
    cart = data["cart"]
    cname = data.get("customer_name","")
    cphone = data.get("customer_phone","")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = 0

    html = f"<h2>{STORE_NAME}</h2><p>🗓 {now}</p>"
    if cname or cphone:
        html += f"<p>👤 الزبون: {cname} {cphone}</p>"
    html += "<table class='table table-bordered'><tr><th>المنتج</th><th>السعر</th><th>الكمية</th><th>الإجمالي</th></tr>"

    text = f"{STORE_NAME}\nالتاريخ: {now}\n"
    if cname or cphone:
        text += f"الزبون: {cname} {cphone}\n"
    text += "-"*30 + "\n"

    for n,q in cart.items():
        p = get_product(n)
        if not p: continue
        price = p[1]
        discount = p[4]
        price_after_discount = price * (1 - discount/100)
        sub = price_after_discount * q
        total += sub
        html += f"<tr><td>{n}</td><td>{price_after_discount:.2f}</td><td>{q}</td><td>{sub:.2f}</td></tr>"
        text += f"{n:<15} {price_after_discount:<8.2f} {q:<5} {sub:<8.2f}\n"

    html += f"<tr><th colspan=3>الإجمالي الكلي</th><th>{total:.2f}</th></tr></table>"
    text += "-"*30 + f"\nالإجمالي الكلي: {total:.2f}\n"

    return jsonify({
        "bill_html": html,
        "whatsapp_url": f"https://wa.me/{STORE_PHONE}?text={quote(text)}"
    })

# ================= تأكيد البيع =================
@app.route("/confirm_sale", methods=["POST"])
def confirm_sale():
    data = request.json
    cart = data["cart"]
    cname = data.get("customer_name","زبون مجهول")
    cphone = data.get("customer_phone","")
    for n,q in cart.items():
        p = get_product(n)
        if not p or q > p[2]:
            return jsonify({"message":f"❌ كمية غير كافية للمنتج {n}"}),400
        update_stock(n,q)
    save_sale(cname, cphone, cart)
    return jsonify({"message":"✅ تم تأكيد البيع وخصم المخزون وحفظ الفاتورة"})

# ================= صفحة المدير =================
@app.route("/admin", methods=["GET","POST"])
def admin_page():
    if request.method == "POST":
        password = request.form.get("password")
        if password != ADMIN_PASSWORD:
            flash("❌ كلمة المرور غير صحيحة", "error")
            return redirect(url_for("admin_page"))

        action = request.form.get("action")

        if action=="add_category":
            category_name = request.form.get("category_name")
            if add_category(category_name):
                flash(f"✅ تم إضافة الفئة '{category_name}'", "success")
            else:
                flash(f"❌ الفئة '{category_name}' موجودة مسبقًا", "error")
            return redirect(url_for("admin_page"))

        elif action=="add":
            name = request.form.get("name")
            price = float(request.form.get("price"))
            stock = int(request.form.get("stock"))
            discount = float(request.form.get("discount",0))
            category = request.form.get("category","عام")
            insert_product(name, price, stock, request.files.get("image_file"), discount, category)

        elif action=="update":
            name = request.form.get("name")
            set_stock(name,int(request.form.get("stock")))
            price = request.form.get("price")
            discount = request.form.get("discount")
            category = request.form.get("category")
            if price: update_product(name, price=float(price))
            if discount: update_product(name, discount=float(discount))
            if category: update_product(name, category=category)
            flash(f"✅ تم تحديث المنتج {name}", "success")

        elif action=="delete":
            name = request.form.get("name")
            delete_product(name)
            flash(f"🗑 تم حذف المنتج {name}", "success")

        return redirect(url_for("admin_page"))

    products = get_products()
    categories = get_categories()
    html = """
<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="UTF-8">
<title>صفحة المدير</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{direction:rtl;padding:15px;font-family:Arial, sans-serif;} .flash{margin:10px 0;}</style>
</head>
<body class="container">
<h2>🔧 صفحة المدير</h2>

<form method="POST">
<label>كلمة المرور:</label>
<input type="password" name="password" required>
<button class="btn btn-primary">دخول</button>
</form>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    {% for category, msg in messages %}
      <div class="alert alert-{{'success' if category=='success' else 'danger'}} flash">{{ msg }}</div>
    {% endfor %}
  {% endif %}
{% endwith %}

<h3>📦 إضافة فئة جديدة</h3>
<form method="POST">
<input type="hidden" name="password" value="{{request.form.get('password','')}}">
<input type="hidden" name="action" value="add_category">
<input type="text" name="category_name" required>
<button class="btn btn-success">إضافة</button>
</form>

<h3>🛒 إدارة المنتجات</h3>
<table class="table table-bordered">
<tr><th>الاسم</th><th>السعر</th><th>الكمية</th><th>الفئة</th><th>خصم %</th><th>صورة</th><th>إجراءات</th></tr>
{% for n,p,s,img,d,cat in products %}
<tr>
<td>{{n}}</td>
<td>{{p}}</td>
<td>{{s}}</td>
<td>{{cat}}</td>
<td>{{d}}</td>
<td>{% if img %}<img src="{{ img }}" width="50">{% endif %}</td>
<td>
<form method="POST" style="display:inline">
<input type="hidden" name="password" value="{{request.form.get('password','')}}">
<input type="hidden" name="action" value="update">
<input type="hidden" name="name" value="{{n}}">
<input type="number" name="stock" value="{{s}}" style="width:60px">
<input type="number" name="price" value="{{p}}" step="0.01" style="width:80px">
<input type="number" name="discount" value="{{d}}" step="0.01" style="width:60px">
<select name="category">
{% for c in categories %}
<option value="{{c}}" {% if c==cat %}selected{% endif %}>{{c}}</option>
{% endfor %}
</select>
<button class="btn btn-info btn-sm">تحديث</button>
</form>

<form method="POST" style="display:inline">
<input type="hidden" name="password" value="{{request.form.get('password','')}}">
<input type="hidden" name="action" value="delete">
<input type="hidden" name="name" value="{{n}}">
<button class="btn btn-danger btn-sm">حذف</button>
</form>
</td>
</tr>
{% endfor %}
</table>

<h3>➕ إضافة منتج جديد</h3>
<form method="POST" enctype="multipart/form-data">
<input type="hidden" name="password" value="{{request.form.get('password','')}}">
<input type="hidden" name="action" value="add">
<input type="text" name="name" placeholder="اسم المنتج" required>
<input type="number" step="0.01" name="price" placeholder="السعر" required>
<input type="number" name="stock" placeholder="الكمية" required>
<input type="number" step="0.01" name="discount" placeholder="خصم %" value="0">
<select name="category">{% for c in categories %}<option value="{{c}}">{{c}}</option>{% endfor %}</select>
<input type="file" name="image_file">
<button class="btn btn-success">إضافة المنتج</button>
</form>

</body>
</html>
"""
    return render_template_string(html, products=products, categories=categories)

# ================= تشغيل =================
if __name__ == "__main__":
    create_product_table()
    create_sales_table()
    create_category_table()
    

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    





