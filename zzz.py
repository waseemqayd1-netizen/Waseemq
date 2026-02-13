from flask import Flask, request, render_template_string, redirect, session, jsonify
import sqlite3, os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback123")

DB_FILE = "store.db"
UPLOAD_FOLDER = "static/uploads"
STORE_PHONE = "967771602370"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= DATABASE =================

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
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total REAL,
            date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price REAL
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= STORE =================

@app.route("/")
def store():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    products = cur.fetchall()
    conn.close()

    return render_template_string("""
<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="UTF-8">
<title>متجر وسيم</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{direction:rtl;background:#f8f9fa;padding:20px}
.card:hover{transform:scale(1.05);transition:.3s}
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

{% set final = p[2] - (p[2]*p[4]/100) %}
{% if p[4] > 0 %}
<p><del>{{p[2]}}</del> <span class="text-danger">{{final}}</span> ريال</p>
{% else %}
<p class="text-danger">{{p[2]}} ريال</p>
{% endif %}

<p>المخزون: {{p[3]}}</p>

<input type="number" min="1" max="{{p[3]}}" value="1" id="q{{p[0]}}" class="form-control mb-2">

<button onclick="addToCart({{p[0]}}, '{{p[1]}}', {{final}})" 
class="btn btn-success" {% if p[3] <= 0 %}disabled{% endif %}>
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
<button onclick="checkout()" class="btn btn-primary">تأكيد الطلب</button>

<script>
let cart=[];

function addToCart(id,name,price){
let qty=document.getElementById("q"+id).value;
cart.push({id:id,name:name,price:price,quantity:parseInt(qty)});
render();
}

function render(){
let total=0;
document.getElementById("cart").innerHTML="";
cart.forEach(i=>{
document.getElementById("cart").innerHTML+=
`<li>${i.name} × ${i.quantity} = ${i.price*i.quantity}</li>`;
total+=i.price*i.quantity;
});
document.getElementById("total").innerHTML="الإجمالي: "+total+" ريال";
}

function checkout(){
fetch("/checkout",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({cart:cart})
})
.then(r=>r.json())
.then(data=>{
if(data.success){
let msg="طلب جديد:%0A";
cart.forEach(i=>{
msg+=i.name+" × "+i.quantity+"%0A";
});
msg+="%0Aالإجمالي: "+data.total+" ريال";
window.open("https://wa.me/""" + STORE_PHONE + """?text="+encodeURIComponent(msg));
cart=[];
render();
}else{
alert(data.error);
}
});
}
</script>

</body>
</html>
""", products=products)

# ================= CHECKOUT =================

@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.json
    cart = data["cart"]

    conn = connect()
    cur = conn.cursor()

    total = 0
    cur.execute("INSERT INTO orders (total,date) VALUES (?,?)",
                (0, datetime.now().strftime("%Y-%m-%d %H:%M")))
    order_id = cur.lastrowid

    for item in cart:
        cur.execute("SELECT price,stock,discount FROM products WHERE id=?",
                    (item["id"],))
        product = cur.fetchone()

        if not product:
            continue

        price, stock, discount = product

        if stock < item["quantity"]:
            conn.close()
            return jsonify({"error":"المخزون غير كافي"})

        final = price - (price*discount/100)
        item_total = final * item["quantity"]
        total += item_total

        cur.execute("UPDATE products SET stock = stock - ? WHERE id=?",
                    (item["quantity"], item["id"]))

        cur.execute("""
        INSERT INTO order_items (order_id,product_id,quantity,price)
        VALUES (?,?,?,?)
        """,(order_id,item["id"],item["quantity"],final))

    cur.execute("UPDATE orders SET total=? WHERE id=?",(total,order_id))

    conn.commit()
    conn.close()

    return jsonify({"success":True,"total":total})

# ================= LOGIN =================

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form["password"]==os.environ.get("ADMIN_PASSWORD"):
            session["admin"]=True
            return redirect("/admin")
    return """
    <h3>تسجيل دخول المدير</h3>
    <form method="post">
    <input type="password" name="password" placeholder="كلمة المرور">
    <button>دخول</button>
    </form>
    """

# ================= ADMIN =================

@app.route("/admin", methods=["GET","POST"])
def admin():
    if not session.get("admin"):
        return redirect("/login")

    conn=connect()
    cur=conn.cursor()

    if request.method=="POST":
        name=request.form["name"]
        price=request.form["price"]
        stock=request.form["stock"]
        discount=request.form["discount"]

        file=request.files["image"]
        filename=secure_filename(file.filename)
        path=os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        cur.execute("""
        INSERT INTO products (name,price,stock,discount,image)
        VALUES (?,?,?,?,?)
        """,(name,price,stock,discount,path))
        conn.commit()

    cur.execute("SELECT * FROM products")
    products=cur.fetchall()
    conn.close()

    return render_template_string("""
<h2>لوحة المدير</h2>
<a href="/">المتجر</a> | <a href="/stats">الإحصائيات</a>
<hr>
<form method="post" enctype="multipart/form-data">
اسم: <input name="name"><br>
سعر: <input name="price"><br>
مخزون: <input name="stock"><br>
خصم%: <input name="discount"><br>
صورة: <input type="file" name="image"><br>
<button>إضافة</button>
</form>
<hr>
{% for p in products %}
<div>
{{p[1]}} | مخزون: {{p[3]}}
<a href="/delete/{{p[0]}}">حذف</a>
</div>
{% endfor %}
""", products=products)

@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return redirect("/login")
    conn=connect()
    cur=conn.cursor()
    cur.execute("DELETE FROM products WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return redirect("/admin")

# ================= STATS =================

@app.route("/stats")
def stats():
    conn=connect()
    cur=conn.cursor()
    cur.execute("SELECT date,total FROM orders")
    data=cur.fetchall()
    conn.close()

    dates=[d[0] for d in data]
    totals=[d[1] for d in data]

    return render_template_string("""
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<h2>إحصائيات المبيعات</h2>
<canvas id="chart"></canvas>
<script>
new Chart(document.getElementById('chart'),{
type:'line',
data:{
labels: {{dates|safe}},
datasets:[{label:'المبيعات',data: {{totals|safe}},borderWidth:2}]
}
});
</script>
""", dates=dates, totals=totals)

# ================= RUN =================

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
    
