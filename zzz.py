from flask import Flask, request, redirect, render_template_string, session
import psycopg2
import os
from datetime import datetime
from urllib.parse import quote_plus

app = Flask(__name__)
app.secret_key = "your-secret-key"

def connect():
    return psycopg2.connect(os.environ.get("DATABASE_URL"), sslmode="require")

def init_db():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT,
        price REAL,
        stock INTEGER,
        image BYTEA
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMP,
        customer_name TEXT,
        customer_phone TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id SERIAL PRIMARY KEY,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price REAL
    );
    """)
    conn.commit()
    conn.close()

init_db()

# ----------------------------
# Admin Login
# ----------------------------
ADMIN_PASS = "080808"

@app.route("/admin-login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        if request.form["password"] == ADMIN_PASS:
            session["admin"] = True
            return redirect("/admin")
        else:
            return "<h3>كلمة المرور خطأ</h3><a href='/admin-login'>رجوع</a>"
    return """
    <div style="background:black;color:gold;padding:20px;font-family:Arial;">
    <h2>🔐 دخول المدير</h2>
    <form method='POST'>
      كلمة المرور: <input name='password' type='password' style='padding:5px;'><br><br>
      <button style='background:gold;color:black;padding:8px;'>دخول</button>
    </form>
    </div>
    """

# ----------------------------
# Admin Panel
# ----------------------------
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/admin-login")

    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, stock, image FROM products")
    products = cur.fetchall()

    cur.execute("""
    SELECT o.id, o.customer_name, o.customer_phone, SUM(oi.price*oi.quantity) 
    FROM orders o JOIN order_items oi ON oi.order_id=o.id
    GROUP BY o.id ORDER BY o.id DESC
    """)
    orders = cur.fetchall()
    conn.close()

    return render_template_string("""
<html dir="rtl">
<head><title>لوحة المدير</title>
<style>
body { background:black;color:gold;font-family:Arial;}
table { width:100%; border-collapse:collapse;}
th,td { border:1px solid gold; padding:8px;}
img { width:60px;}
.btn { background:gold;color:black;padding:6px 10px;text-decoration:none;font-weight:bold;}
</style>
</head>
<body>
<h1>📋 لوحة المدير</h1>

<h2>📦 المنتجات</h2>
<a class="btn" href="/admin-add-product">➕ إضافة منتج</a>
<table>
<tr><th>صورة</th><th>اسم</th><th>السعر</th><th>المخزون</th><th>تعديل</th><th>حذف</th></tr>
{% for p in products %}
<tr>
<td><img src="/image/{{p[0]}}"></td>
<td>{{p[1]}}</td><td>{{p[2]}}</td><td>{{p[3]}}</td>
<td><a class="btn" href="/admin-edit-product/{{p[0]}}">✏️</a></td>
<td><a class="btn" href="/admin-delete-product/{{p[0]}}">🗑️</a></td>
</tr>
{% endfor %}
</table>

<h2>📊 الطلبات</h2>
<table>
<tr><th>رقم الطلب</th><th>اسم الزبون</th><th>رقم الجوال</th><th>الإجمالي</th></tr>
{% for o in orders %}
<tr>
<td>{{o[0]}}</td><td>{{o[1]}}</td><td>{{o[2]}}</td><td>{{o[3]}}</td>
</tr>
{% endfor %}
</table>
</body>
</html>
""", products=products, orders=orders)

# ----------------------------
# Admin - Add Product
# ----------------------------
@app.route("/admin-add-product", methods=["GET","POST"])
def admin_add_product():
    if not session.get("admin"):
        return redirect("/admin-login")
    if request.method=="POST":
        name=request.form["name"]
        price=request.form["price"]
        stock=request.form["stock"]
        image=request.files["image"].read()
        conn=connect()
        cur=conn.cursor()
        cur.execute("INSERT INTO products (name,price,stock,image) VALUES (%s,%s,%s,%s)",
                    (name,price,stock,image))
        conn.commit()
        conn.close()
        return redirect("/admin")
    return """
    <div style='background:black;color:gold;font-family:Arial;padding:20px;'>
    <h2>📥 إضافة منتج جديد</h2>
    <form method='POST' enctype='multipart/form-data'>
      الاسم:<br><input name='name'><br><br>
      السعر:<br><input name='price'><br><br>
      المخزون:<br><input name='stock'><br><br>
      الصورة:<br><input type='file' name='image'><br><br>
      <button style='background:gold;color:black;padding:8px;'>حفظ</button>
    </form></div>
    """

# ----------------------------
# Admin - Edit Product
# ----------------------------
@app.route("/admin-edit-product/<int:id>", methods=["GET","POST"])
def admin_edit_product(id):
    if not session.get("admin"):
        return redirect("/admin-login")
    conn=connect()
    cur=conn.cursor()
    if request.method=="POST":
        name=request.form["name"]
        price=request.form["price"]
        stock=request.form["stock"]
        img_file=request.files.get("image")
        if img_file and img_file.filename!="":
            image=img_file.read()
            cur.execute("UPDATE products SET name=%s,price=%s,stock=%s,image=%s WHERE id=%s",
                        (name,price,stock,image,id))
        else:
            cur.execute("UPDATE products SET name=%s,price=%s,stock=%s WHERE id=%s",
                        (name,price,stock,id))
        conn.commit()
        conn.close()
        return redirect("/admin")
    cur.execute("SELECT name,price,stock FROM products WHERE id=%s",(id,))
    p=cur.fetchone()
    conn.close()
    return f"""
    <div style='background:black;color:gold;font-family:Arial;padding:20px;'>
    <h2>✏️ تعديل المنتج</h2>
    <form method='POST' enctype='multipart/form-data'>
      الاسم:<br><input name='name' value='{p[0]}'><br><br>
      السعر:<br><input name='price' value='{p[1]}'><br><br>
      المخزون:<br><input name='stock' value='{p[2]}'><br><br>
      تغيير الصورة:<br><input type='file' name='image'><br><br>
      <button style='background:gold;color:black;padding:8px;'>تحديث</button>
    </form></div>
    """

# ----------------------------
# Admin - Delete Product
# ----------------------------
@app.route("/admin-delete-product/<int:id>")
def admin_delete_product(id):
    if not session.get("admin"):
        return redirect("/admin-login")
    conn=connect();cur=conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s",(id,))
    conn.commit();conn.close()
    return redirect("/admin")

# ----------------------------
# Customer Views
# ----------------------------
@app.route("/")
def index():
    conn=connect();cur=conn.cursor()
    cur.execute("SELECT id,name,price FROM products")
    products=cur.fetchall()
    conn.close()
    return render_template_string("""
<html dir="rtl">
<head><title>المتجر</title>
<style>
body { background:black;color:gold;font-family:Arial; }
.card {
  border:2px solid gold; border-radius:8px; width:200px; padding:10px;
  margin:10px; display:inline-block; vertical-align:top;
}
.btn { background:gold;color:black;padding:8px;font-weight:bold;text-decoration:none;}
</style>
</head>
<body>
<h1>🌟 متجر أولاد قايد 🌟</h1>
<a class="btn" href="/cart">🛒 سلة</a><hr>
{% for p in products %}
  <div class="card">
    <img src="/image/{{p[0]}}" width="150"><br><br>
    <strong>{{p[1]}}</strong><br>
    <span>{{p[2]}} ريال</span><br><br>
    <a class="btn" href="/add_to_cart/{{p[0]}}">➕ أضف للسلة</a>
  </div>
{% endfor %}
</body>
</html>
""",products=products)

# ----------------------------
# Add to Cart
# ----------------------------
@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):
    cart=session.get("cart",{});cart[str(id)]=cart.get(str(id),0)+1
    session["cart"]=cart;return redirect("/cart")

# ----------------------------
# Cart
# ----------------------------
@app.route("/cart")
def cart():
    cart=session.get("cart",{})
    items=[];total=0
    conn=connect();cur=conn.cursor()
    for pid,qty in cart.items():
        cur.execute("SELECT name,price FROM products WHERE id=%s",(pid,))
        p=cur.fetchone()
        cur.execute("SELECT image FROM products WHERE id=%s",(pid,))
        img=cur.fetchone()[0]
        items.append((pid,p[0],p[1],qty,img));total+=p[1]*qty
    conn.close()
    return render_template_string("""
<html dir="rtl">
<body style="background:black;color:gold;font-family:Arial;">
<h1>🛒 سلتك</h1>
<table border="1" width="100%" style="border-collapse:collapse;color:gold;">
<tr><th>صورة</th><th>الاسم</th><th>السعر</th><th>الكمية</th><th>الجميع</th></tr>
{% for i in items %}
<tr>
<td><img src="/image/{{i[0]}}" width="50"></td>
<td>{{i[1]}}</td><td>{{i[2]}}</td><td>{{i[3]}}</td><td>{{i[2]*i[3]}}</td>
</tr>
{% endfor %}
</table>
<h2>💰 الإجمالي: {{total}} ريال</h2>
<a class="btn" href="/checkout">📦 Checkout</a>
</body>
</html>
""",items=items,total=total)

# ----------------------------
# Checkout + Invoice
# ----------------------------
@app.route("/checkout",methods=["GET","POST"])
def checkout():
    cart=session.get("cart",{})
    if not cart: return redirect("/cart")
    if request.method=="POST":
        cname=request.form["customer_name"]
        cphone=request.form["customer_phone"]
        conn=connect();cur=conn.cursor()
        cur.execute("INSERT INTO orders (created_at,customer_name,customer_phone) VALUES (%s,%s,%s) RETURNING id",
                    (datetime.now(),cname,cphone))
        oid=cur.fetchone()[0];items=[];total=0
        for pid,qty in cart.items():
            cur.execute("SELECT name,price FROM products WHERE id=%s",(pid,))
            p=cur.fetchone();total+=p[1]*qty
            items.append((pid,p[0],p[1],qty))
            cur.execute("INSERT INTO order_items (order_id,product_id,quantity,price) VALUES (%s,%s,%s,%s)",
                        (oid,pid,qty,p[1]))
        conn.commit();conn.close();session["cart"]={}
        text=f"فاتورتي من سوبر ماركت أولاد قايد للتجارة العامة:%0A"
        for i in items: text+=f"{i[1]} x{i[3]} = {i[2]*i[3]} ريال%0A"
        text+=f"الإجمالي = {total} ريال%0Aرقم الزبون: {cphone}"
        wa_url=f"https://wa.me/967770295876?text={quote_plus(text)}"
        return render_template_string("""
<html dir="rtl">
<body style="background:black;color:gold;font-family:Arial;">
<h1>📄 فاتورتك</h1>
<p><strong style="color:gold;">سوبر ماركت أولاد قايد للتجارة العامة</strong></p>
<p><strong>اسم:</strong> {{cname}} - <strong>الهاتف:</strong> {{cphone}}</p>
<hr style="border:1px dashed gold;">
<table border="1" width="100%" style="border-collapse:collapse;color:gold;">
<tr><th>اسم</th><th>السعر</th><th>كمية</th><th>الإجمالي</th></tr>
{% for i in items %}
<tr><td>{{i[1]}}</td><td>{{i[2]}}</td><td>{{i[3]}}</td><td>{{i[2]*i[3]}}</td></tr>
{% endfor %}
</table>
<h2>💰 الإجمالي: {{total}} ريال</h2>
<a href="{{wa_url}}" style="background:gold;color:black;padding:10px;font-weight:bold;text-decoration:none;">📱 إرسال واتساب</a><br><br>
<a href="/" style="background:gold;color:black;padding:10px;font-weight:bold;text-decoration:none;">🏠 الرئيسية</a>
</body>
</html>
""",items=items,total=total,cname=cname,cphone=cphone,wa_url=wa_url)
    return """
<html dir="rtl">
<body style="background:black;color:gold;font-family:Arial;">
<h2>📦 Checkout</h2>
<form method="POST">
الاسم:<br><input name="customer_name" required><br><br>
الهاتف:<br><input name="customer_phone" required><br><br>
<button style="background:gold;color:black;padding:10px;font-weight:bold;">🧾 عرض الفاتورة</button>
</form>
</body>
</html>
"""

if __name__=="__main__":
    app.run()
    
