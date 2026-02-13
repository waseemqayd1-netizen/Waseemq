from flask import Flask, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
import os

app = Flask(__name__)
app.secret_key = "super_market_secret_key"

# DATABASE (Render compatible)
database_url = os.environ.get("DATABASE_URL")

if database_url:
    database_url = database_url.replace("postgres://", "postgresql://")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///shop.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =======================
# MODELS
# =======================

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    price = db.Column(db.Float)
    stock = db.Column(db.Integer)
    image = db.Column(db.String(300))
    category_id = db.Column(db.Integer)

with app.app_context():
    db.create_all()
    if not Admin.query.first():
        db.session.add(Admin(username="admin", password="1234"))
        db.session.commit()

# =======================
# STYLE
# =======================

STYLE = """
<style>
body{background:#000;color:gold;font-family:tahoma}
.card{background:#111;border:1px solid gold;border-radius:12px}
.table{color:gold}
input,select{background:#111;color:gold;border:1px solid gold}
.btn-gold{background:gold;color:black;font-weight:bold;border:none;padding:6px 12px;border-radius:6px}
.container{max-width:1100px;margin:auto}
.header{text-align:center;padding:20px;border-bottom:2px solid gold}
.footer{text-align:center;margin-top:50px;padding:20px;border-top:2px solid gold;font-size:14px}
img{max-width:100px;border-radius:8px}
</style>
"""

# =======================
# ADMIN LOGIN
# =======================

@app.route("/admin", methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        user=Admin.query.filter_by(
            username=request.form["username"],
            password=request.form["password"]
        ).first()
        if user:
            session["admin"]=True
            return redirect("/dashboard")

    return STYLE + """
    <div class='container'>
    <h2>دخول المدير</h2>
    <form method='post'>
    <input name='username' class='form-control mb-2' placeholder='اسم المستخدم'>
    <input name='password' type='password' class='form-control mb-2' placeholder='كلمة المرور'>
    <button class='btn-gold'>دخول</button>
    </form>
    </div>
    """

@app.route("/dashboard")
def dashboard():
    if not session.get("admin"): return redirect("/admin")
    return STYLE + """
    <div class='container'>
    <h2>لوحة التحكم</h2>
    <a href='/categories' class='btn-gold m-2'>الفئات</a>
    <a href='/products' class='btn-gold m-2'>المنتجات</a>
    </div>
    """

# =======================
# CATEGORY CRUD
# =======================

@app.route("/categories", methods=["GET","POST"])
def categories():
    if not session.get("admin"): return redirect("/admin")

    if request.method=="POST":
        db.session.add(Category(name=request.form["name"]))
        db.session.commit()
        return redirect("/categories")

    cats=Category.query.all()
    rows=""
    for c in cats:
        rows+=f"<tr><td>{c.name}</td><td><a href='/delete_cat/{c.id}' class='btn-gold'>حذف</a></td></tr>"

    return STYLE + f"""
    <div class='container'>
    <h3>الفئات</h3>
    <form method='post'>
    <input name='name' class='form-control mb-2'>
    <button class='btn-gold'>إضافة</button>
    </form>
    <table class='table'><tr><th>الفئة</th><th>تحكم</th></tr>{rows}</table>
    </div>
    """

@app.route("/delete_cat/<int:id>")
def delete_cat(id):
    Category.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect("/categories")

# =======================
# PRODUCT CRUD
# =======================

@app.route("/products", methods=["GET","POST"])
def products():
    if not session.get("admin"): return redirect("/admin")

    cats=Category.query.all()

    if request.method=="POST":
        db.session.add(Product(
            name=request.form["name"],
            price=float(request.form["price"]),
            stock=int(request.form["stock"]),
            image=request.form["image"],
            category_id=int(request.form["category_id"])
        ))
        db.session.commit()
        return redirect("/products")

    products=Product.query.all()
    rows=""
    for p in products:
        cat=Category.query.get(p.category_id)
        rows+=f"""
        <tr>
        <td>{p.name}</td>
        <td>{cat.name}</td>
        <td>{p.price}</td>
        <td>{p.stock}</td>
        <td><img src='{p.image}'></td>
        <td><a href='/delete_product/{p.id}' class='btn-gold'>حذف</a></td>
        </tr>
        """

    options="".join([f"<option value='{c.id}'>{c.name}</option>" for c in cats])

    return STYLE + f"""
    <div class='container'>
    <h3>المنتجات</h3>
    <form method='post'>
    <input name='name' class='form-control mb-2'>
    <input name='price' class='form-control mb-2'>
    <input name='stock' class='form-control mb-2'>
    <input name='image' class='form-control mb-2' placeholder='رابط الصورة'>
    <select name='category_id' class='form-control mb-2'>{options}</select>
    <button class='btn-gold'>إضافة</button>
    </form>
    <table class='table'>
    <tr><th>الاسم</th><th>الفئة</th><th>السعر</th><th>المخزون</th><th>الصورة</th><th>تحكم</th></tr>
    {rows}
    </table>
    </div>
    """

@app.route("/delete_product/<int:id>")
def delete_product(id):
    Product.query.filter_by(id=id).delete()
    db.session.commit()
    return redirect("/products")

# =======================
# CUSTOMER SHOP
# =======================

@app.route("/")
def shop():
    categories=Category.query.all()
    content=STYLE+"<div class='container'>"

    content+="""<div class='header'>
    <h3>سوبر ماركت اولاد قايد محمد</h3>
    <p>للتجارة العامة</p>
    <strong>اولاد قايد للتجارة العامة</strong>
    </div>"""

    for c in categories:
        products=Product.query.filter_by(category_id=c.id).all()
        content+=f"<h4>{c.name}</h4><div class='row'>"
        for p in products:
            content+=f"""
            <div class='card p-3 m-2'>
            <img src='{p.image}'>
            <h5>{p.name}</h5>
            <p>{p.price} ر.ي</p>
            <form action='/add/{p.id}' method='post'>
            <input type='number' name='qty' min='1' class='form-control mb-1'>
            <button class='btn-gold'>إضافة للسلة</button>
            </form>
            </div>
            """
        content+="</div>"

    content+="<a href='/cart' class='btn-gold'>سلة المشتريات</a>"

    content+="""<div class='footer'>
    📍 الازرق / موعد حماده : حبيل تود<br>
    لصاحبها « فايز / وإخوانه »<br><hr>
    إعداد وتصميم « م / وسيم العامري »<br>
    للتواصل 967770295876
    </div></div>"""

    return content

# =======================
# RUN
# =======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
