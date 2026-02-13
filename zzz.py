from flask import Flask, request, redirect, render_template_string, session
import psycopg2
import os
from datetime import datetime
from urllib.parse import quote_plus

app = Flask(__name__)
app.secret_key = "wasim-secret-key"

# ==============================
# Database Connection
# ==============================
def connect():
    return psycopg2.connect(os.environ.get("DATABASE_URL"), sslmode="require")

def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id SERIAL PRIMARY KEY,
        name TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT,
        price REAL,
        stock INTEGER,
        category_id INTEGER
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMP,
        customer_name TEXT,
        customer_phone TEXT,
        customer_location TEXT
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

# ==============================
# Admin Login
# ==============================
ADMIN_PASS = "080808"

@app.route("/admin-login", methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        if request.form["password"] == ADMIN_PASS:
            session["admin"] = True
            return redirect("/admin")
    return """
    <body style='background:black;color:gold;font-family:Arial;text-align:center;padding:40px'>
    <h2>دخول المدير</h2>
    <form method='POST'>
    <input type='password' name='password' placeholder='كلمة المرور'><br><br>
    <button>دخول</button>
    </form>
    </body>
    """

# ==============================
# Admin Panel
# ==============================
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/admin-login")

    conn=connect();cur=conn.cursor()
    cur.execute("SELECT * FROM categories")
    categories=cur.fetchall()

    cur.execute("""
    SELECT p.id,p.name,p.price,p.stock,c.name
    FROM products p
    LEFT JOIN categories c ON p.category_id=c.id
    """)
    products=cur.fetchall()
    conn.close()

    return render_template_string("""
    <html dir="rtl">
    <body style="background:black;color:gold;font-family:Arial;">
    <h1>لوحة المدير</h1>

    <h2>الفئات</h2>
    <a href="/admin-add-category">إضافة فئة</a>
    <ul>
    {% for c in categories %}
        <li>{{c[1]}} 
        <a href="/admin-delete-category/{{c[0]}}">حذف</a></li>
    {% endfor %}
    </ul>

    <h2>المنتجات</h2>
    <a href="/admin-add-product">إضافة منتج</a>

    {% for p in products %}
        {% if p[3] < 3 %}
        <div style="color:red;">⚠ {{p[1]}} المخزون منخفض ({{p[3]}})</div>
        {% endif %}
    {% endfor %}

    <table border="1" width="100%" style="border-collapse:collapse;">
    <tr><th>الاسم</th><th>السعر</th><th>المخزون</th><th>الفئة</th><th>حذف</th></tr>
    {% for p in products %}
    <tr>
    <td>{{p[1]}}</td>
    <td>{{p[2]}}</td>
    <td {% if p[3] < 3 %} style="color:red;" {% endif %}>{{p[3]}}</td>
    <td>{{p[4]}}</td>
    <td><a href="/admin-delete-product/{{p[0]}}">حذف</a></td>
    </tr>
    {% endfor %}
    </table>
    </body>
    </html>
    """,categories=categories,products=products)

# ==============================
# Add Category
# ==============================
@app.route("/admin-add-category", methods=["GET","POST"])
def admin_add_category():
    if not session.get("admin"):
        return redirect("/admin-login")
    if request.method=="POST":
        conn=connect();cur=conn.cursor()
        cur.execute("INSERT INTO categories (name) VALUES (%s)",(request.form["name"],))
        conn.commit();conn.close()
        return redirect("/admin")
    return """
    <body style='background:black;color:gold;'>
    <form method='POST'>
    اسم الفئة:<br>
    <input name='name'><br><br>
    <button>حفظ</button>
    </form>
    </body>
    """

@app.route("/admin-delete-category/<int:id>")
def admin_delete_category(id):
    conn=connect();cur=conn.cursor()
    cur.execute("DELETE FROM categories WHERE id=%s",(id,))
    conn.commit();conn.close()
    return redirect("/admin")

# ==============================
# Add Product
# ==============================
@app.route("/admin-add-product", methods=["GET","POST"])
def admin_add_product():
    conn=connect();cur=conn.cursor()
    cur.execute("SELECT * FROM categories")
    categories=cur.fetchall()

    if request.method=="POST":
        cur.execute("""
        INSERT INTO products (name,price,stock,category_id)
        VALUES (%s,%s,%s,%s)
        """,(request.form["name"],request.form["price"],
             request.form["stock"],request.form["category_id"]))
        conn.commit();conn.close()
        return redirect("/admin")

    return render_template_string("""
    <body style='background:black;color:gold;'>
    <form method='POST'>
    الاسم:<br><input name='name'><br>
    السعر:<br><input name='price'><br>
    المخزون:<br><input name='stock'><br>
    الفئة:<br>
    <select name="category_id">
    {% for c in categories %}
        <option value="{{c[0]}}">{{c[1]}}</option>
    {% endfor %}
    </select><br><br>
    <button>حفظ</button>
    </form>
    </body>
    """,categories=categories)

@app.route("/admin-delete-product/<int:id>")
def admin_delete_product(id):
    conn=connect();cur=conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s",(id,))
    conn.commit();conn.close()
    return redirect("/admin")

# ==============================
# Customer View
# ==============================
@app.route("/")
def index():
    conn=connect();cur=conn.cursor()
    cur.execute("SELECT * FROM categories")
    categories=cur.fetchall()
    conn.close()

    return render_template_string("""
    <html dir="rtl">
    <body style="background:black;color:gold;font-family:Arial;text-align:center;">
    <h1>سوبر ماركت اولاد قايد محمد</h1>
    <h3>للتجارة العامة</h3>

    {% for c in categories %}
    <div style="border:1px solid gold;margin:10px;padding:10px;">
    <a href="/category/{{c[0]}}" style="color:gold;font-size:20px;">{{c[1]}}</a>
    </div>
    {% endfor %}

    <br><a href="/cart">🛒 سلة المشتريات</a>

    <hr>
    📍 الموقع: الازرق / موعد حماده – حبيل تود<br>
    👤 للصحابها: فايز / وإخوانه<br>
    ⚙ اعداد وتصميم: م / وسيم العامري<br>
    📞 967770295876
    </body>
    </html>
    """,categories=categories)

# ==============================
# Category Products
# ==============================
@app.route("/category/<int:id>")
def category_view(id):
    conn=connect();cur=conn.cursor()
    cur.execute("SELECT name FROM categories WHERE id=%s",(id,))
    cname=cur.fetchone()[0]

    cur.execute("SELECT id,name,price,stock FROM products WHERE category_id=%s",(id,))
    products=cur.fetchall()
    conn.close()

    return render_template_string("""
    <body style="background:black;color:gold;">
    <h2>{{cname}}</h2>

    {% for p in products %}
    <div style="border:1px solid gold;margin:10px;padding:10px;">
    {{p[1]}} - {{p[2]}} ريال<br>

    {% if p[3] > 0 %}
        <a href="/add_to_cart/{{p[0]}}">➕ أضف</a>
    {% else %}
        <span style="color:red;">نفذ المخزون</span>
    {% endif %}
    </div>
    {% endfor %}

    <br><a href="/">رجوع</a>
    </body>
    """,cname=cname,products=products)

# ==============================
# Cart
# ==============================
@app.route("/add_to_cart/<int:id>")
def add_to_cart(id):
    conn=connect();cur=conn.cursor()
    cur.execute("SELECT stock FROM products WHERE id=%s",(id,))
    stock=cur.fetchone()[0]

    if stock <= 0:
        conn.close()
        return "المنتج نفذ"

    cart=session.get("cart",{})
    cart[str(id)]=cart.get(str(id),0)+1
    session["cart"]=cart
    conn.close()
    return redirect("/cart")

@app.route("/cart")
def cart():
    cart=session.get("cart",{})
    items=[];total=0
    conn=connect();cur=conn.cursor()

    for pid,qty in cart.items():
        cur.execute("SELECT name,price FROM products WHERE id=%s",(pid,))
        p=cur.fetchone()
        items.append((pid,p[0],p[1],qty))
        total+=p[1]*qty
    conn.close()

    return render_template_string("""
    <body style="background:black;color:gold;">
    <h2>سلة المشتريات</h2>

    <table border="1" width="100%">
    <tr><th>المنتج</th><th>السعر</th><th>الكمية</th><th>الإجمالي</th></tr>
    {% for i in items %}
    <tr>
    <td>{{i[1]}}</td>
    <td>{{i[2]}}</td>
    <td>{{i[3]}}</td>
    <td>{{i[2]*i[3]}}</td>
    </tr>
    {% endfor %}
    </table>

    <h3>الإجمالي: {{total}} ريال</h3>

    <a href="/checkout">عرض الفاتورة</a>
    </body>
    """,items=items,total=total)

# ==============================
# Checkout
# ==============================
@app.route("/checkout",methods=["GET","POST"])
def checkout():
    cart=session.get("cart",{})
    if not cart:
        return redirect("/")

    if request.method=="POST":
        cname=request.form["customer_name"]
        cphone=request.form["customer_phone"]
        clocation=request.form["customer_location"]

        conn=connect();cur=conn.cursor()
        cur.execute("""
        INSERT INTO orders (created_at,customer_name,customer_phone,customer_location)
        VALUES (%s,%s,%s,%s) RETURNING id
        """,(datetime.now(),cname,cphone,clocation))
        oid=cur.fetchone()[0]

        items=[];total=0

        for pid,qty in cart.items():
            cur.execute("SELECT name,price FROM products WHERE id=%s",(pid,))
            p=cur.fetchone()
            total+=p[1]*qty
            items.append((p[0],p[1],qty,p[1]*qty))

            cur.execute("""
            INSERT INTO order_items (order_id,product_id,quantity,price)
            VALUES (%s,%s,%s,%s)
            """,(oid,pid,qty,p[1]))

            cur.execute("UPDATE products SET stock=stock-%s WHERE id=%s",(qty,pid))

        conn.commit();conn.close()
        session["cart"]={}

        text="فاتورة سوبر ماركت اولاد قايد محمد%0A"
        for i in items:
            text+=f"{i[0]} x{i[2]} = {i[3]} ريال%0A"
        text+=f"الإجمالي {total} ريال"
        wa_url=f"https://wa.me/967770295876?text={quote_plus(text)}"

        return f"""
        <body style='background:black;color:gold;text-align:center;'>
        <h2>فاتورتك</h2>
        الاسم: {cname}<br>
        الهاتف: {cphone}<br>
        الموقع: {clocation}<br>
        <h3>الإجمالي: {total} ريال</h3>
        <a href='{wa_url}'>ارسال واتساب</a>
        </body>
        """

    return """
    <body style='background:black;color:gold;'>
    <form method='POST'>
    الاسم:<br><input name='customer_name'><br>
    الهاتف:<br><input name='customer_phone'><br>
    الموقع:<br><input name='customer_location'><br><br>
    <button>تأكيد</button>
    </form>
    </body>
    """

if __name__=="__main__":
    app.run()
    
