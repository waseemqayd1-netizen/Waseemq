from flask import Flask, request, jsonify, render_template_string, redirect, session, send_file
import sqlite3, os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import fonts
from reportlab.lib.units import inch
from reportlab.platypus import TableStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

app = Flask(__name__)
app.secret_key = "admin_secret"
DB="store.db"

def connect():
    conn=sqlite3.connect(DB)
    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    conn=connect()
    cur=conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        stock INTEGER
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total REAL,
        date TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_name TEXT,
        quantity INTEGER,
        price REAL
    )""")

    conn.commit()
    conn.close()

init_db()

# =======================
# الصفحة الرئيسية (Responsive 100%)
# =======================
@app.route("/")
def index():
    conn=connect()
    products=conn.execute("SELECT * FROM products").fetchall()
    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>سوبر ماركت اولاد قايد محمد</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

<style>
body{
 background:#0f0f0f;
 color:white;
 font-family:Cairo;
}
.navbar{
 background:black;
 box-shadow:0 0 15px gold;
}
.brand{
 color:gold;
 font-weight:bold;
 font-size:18px;
}
.card{
 background:#1c1c1c;
 border:1px solid gold;
 border-radius:15px;
}
.btn-gold{
 background:gold;
 font-weight:bold;
}
.sidebar{
 position:fixed;
 top:0;
 right:-100%;
 width:100%;
 max-width:350px;
 height:100%;
 background:#111;
 padding:20px;
 transition:0.4s;
 overflow:auto;
}
.sidebar.active{ right:0; }
@media(min-width:768px){
 .sidebar{ width:350px; }
}
</style>
</head>
<body>

<nav class="navbar p-3">
<div class="container-fluid">
<span class="brand">
سوبر ماركت اولاد قايد محمد<br>
<small>للتجارة العامة</small>
</span>
<button class="btn btn-gold" onclick="toggleCart()">🛒</button>
</div>
</nav>

<div class="container mt-4">
<div class="row">
{% for p in products %}
<div class="col-6 col-md-4 mb-3">
<div class="card p-3 text-center">
<h6>{{p.name}}</h6>
<h5>{{p.price}} ريال</h5>
<button class="btn btn-gold w-100"
onclick="addToCart('{{p.name}}',{{p.price}})">
إضافة
</button>
</div>
</div>
{% endfor %}
</div>
</div>

<div class="sidebar" id="cart">
<h4 class="text-warning">سلة المشتريات</h4>
<div id="items"></div>
<hr>
<h5 id="total"></h5>
<button class="btn btn-gold w-100" onclick="checkout()">إتمام الطلب</button>
</div>

<script>
let cart=[];

function addToCart(name,price){
 let item=cart.find(p=>p.name==name);
 if(item){item.quantity++;}
 else{cart.push({name,price,quantity:1});}
 renderCart();
}

function toggleCart(){
 document.getElementById("cart").classList.toggle("active");
}

function renderCart(){
 let html="";
 let total=0;
 cart.forEach(p=>{
  total+=p.price*p.quantity;
  html+=p.name+" × "+p.quantity+"<br>";
 });
 document.getElementById("items").innerHTML=html;
 document.getElementById("total").innerHTML="الإجمالي: "+total+" ريال";
}

function checkout(){
 fetch("/checkout",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({cart:cart})
 }).then(r=>r.json()).then(d=>{
  if(d.success){
   window.location="/invoice/"+d.order_id;
  }
 });
}
</script>

<footer class="text-center mt-4 text-warning">
إعداد وتصميم: « م / وسيم العامري »
</footer>

</body>
</html>
""",products=products)

# =======================
# إنهاء الطلب + حفظ
# =======================
@app.route("/checkout",methods=["POST"])
def checkout():
    data=request.json
    cart=data["cart"]

    conn=connect()
    cur=conn.cursor()

    total=0
    cur.execute("INSERT INTO orders(total,date) VALUES(?,?)",
                (0,datetime.now().strftime("%Y-%m-%d %H:%M")))
    order_id=cur.lastrowid

    for item in cart:
        total+=item["price"]*item["quantity"]
        cur.execute("""INSERT INTO order_items(order_id,product_name,quantity,price)
                       VALUES(?,?,?,?)""",
                    (order_id,item["name"],item["quantity"],item["price"]))

    cur.execute("UPDATE orders SET total=? WHERE id=?",(total,order_id))
    conn.commit()
    conn.close()

    return {"success":True,"order_id":order_id}

# =======================
# إنشاء فاتورة PDF احترافية
# =======================
@app.route("/invoice/<int:order_id>")
def invoice(order_id):
    conn=connect()
    order=conn.execute("SELECT * FROM orders WHERE id=?",(order_id,)).fetchone()
    items=conn.execute("SELECT * FROM order_items WHERE order_id=?",(order_id,)).fetchall()
    conn.close()

    file_path=f"invoice_{order_id}.pdf"
    doc=SimpleDocTemplate(file_path)
    elements=[]

    elements.append(Paragraph("سوبر ماركت اولاد قايد محمد"))
    elements.append(Spacer(1,0.3*inch))
    elements.append(Paragraph("للتجارة العامة"))
    elements.append(Spacer(1,0.3*inch))
    elements.append(Paragraph(f"رقم الفاتورة: {order_id}"))
    elements.append(Spacer(1,0.3*inch))

    data=[["المنتج","الكمية","السعر"]]
    for i in items:
        data.append([i["product_name"],i["quantity"],i["price"]])

    table=Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.gold),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ]))

    elements.append(table)
    elements.append(Spacer(1,0.5*inch))
    elements.append(Paragraph(f"الإجمالي: {order['total']} ريال"))
    elements.append(Spacer(1,0.5*inch))
    elements.append(Paragraph("إعداد وتصميم: م / وسيم العامري"))

    doc.build(elements)

    return send_file(file_path,as_attachment=True)

# =======================
# لوحة مدير فخمة
# =======================
@app.route("/admin")
def admin():
    conn=connect()
    products=conn.execute("SELECT * FROM products").fetchall()
    orders=conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    total=conn.execute("SELECT IFNULL(SUM(total),0) FROM orders").fetchone()[0]
    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#0f0f0f;color:white;}
.card{background:#1c1c1c;border:1px solid gold;}
</style>
</head>
<body class="p-4">

<h3 class="text-warning">لوحة تحكم المدير</h3>

<div class="row mb-4">
<div class="col-md-6">
<div class="card p-3">
<h5>عدد الطلبات</h5>
<h3>{{orders}}</h3>
</div>
</div>
<div class="col-md-6">
<div class="card p-3">
<h5>إجمالي المبيعات</h5>
<h3>{{total}} ريال</h3>
</div>
</div>
</div>

<h5 class="text-warning">المنتجات</h5>
<table class="table table-dark">
<tr><th>الاسم</th><th>السعر</th><th>المخزون</th></tr>
{% for p in products %}
<tr>
<td>{{p.name}}</td>
<td>{{p.price}}</td>
<td>{{p.stock}}</td>
</tr>
{% endfor %}
</table>

</body>
</html>
""",products=products,orders=orders,total=total)

if __name__=="__main__":
    app.run(debug=True)
    

