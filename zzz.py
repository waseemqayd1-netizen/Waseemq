from flask import Flask, request, render_template_string, redirect, url_for, flash
import sqlite3, os, uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"

STORE_NAME = "سوبر ماركت أولاد قايد محمد"
WHATSAPP_NUMBER = "967770295876"
ADMIN_PASSWORD = "080808"

DB_FILE = "supermarket.db"
UPLOAD_FOLDER = "static/images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= قاعدة البيانات =================
def connect():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories(
        name TEXT PRIMARY KEY
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        name TEXT PRIMARY KEY,
        price REAL,
        stock INTEGER,
        image TEXT,
        category TEXT
    )
    """)

    cur.execute("INSERT OR IGNORE INTO categories VALUES ('عام')")

    conn.commit()
    conn.close()

init_db()

# ================= دوال =================
def get_categories():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT name FROM categories")
    data = [r[0] for r in cur.fetchall()]
    conn.close()
    return data

def get_products():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products")
    data = cur.fetchall()
    conn.close()
    return data

def add_category(name):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO categories VALUES (?)",(name,))
    conn.commit()
    conn.close()

def add_product(name, price, stock, image, category):
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO products VALUES(?,?,?,?,?)",(name,price,stock,image,category))
    conn.commit()
    conn.close()

# ================= واجهة الزبون =================
@app.route("/")
def home():
    products = get_products()
    categories = get_categories()

    html = """
<!DOCTYPE html>
<html lang="ar">
<head>
<meta charset="UTF-8">
<title>المتجر</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{direction:rtl;background:#000;color:#D4AF37;padding:20px;font-family:Tahoma}
.logo{
font-size:32px;
font-weight:bold;
text-align:center;
background:linear-gradient(90deg,#FFD700,#D4AF37,#FFD700);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
margin-bottom:20px;
}
.card{
background:#111;
border:1px solid #D4AF37;
margin:10px;
padding:10px;
text-align:center;
transition:0.3s;
}
.card:hover{
box-shadow:0 0 15px #D4AF37;
transform:scale(1.03);
}
.btn-gold{
background:#D4AF37;
color:black;
font-weight:bold;
}
.table{color:#D4AF37}
input,select{
background:#111;
color:#D4AF37;
border:1px solid #D4AF37;
}
</style>
</head>
<body class="container">

<div class="logo">🏪 {{store}}</div>

<div class="row mb-3">
<div class="col"><input id="custName" class="form-control" placeholder="اسم الزبون"></div>
<div class="col"><input id="custPhone" class="form-control" placeholder="رقم الهاتف"></div>
<div class="col"><input id="custCity" class="form-control" placeholder="المدينة"></div>
</div>

<input id="search" class="form-control mb-3" placeholder="🔍 بحث عن منتج..." onkeyup="searchProduct()">

<div class="mb-3">
{% for c in categories %}
<button class="btn btn-gold btn-sm" onclick="filterCategory('{{c}}')">{{c}}</button>
{% endfor %}
<button class="btn btn-secondary btn-sm" onclick="filterCategory('all')">الكل</button>
</div>

<div class="row" id="products">
{% for p in products %}
<div class="col-md-3 product" data-name="{{p[0]}}" data-category="{{p[4]}}">
<div class="card">
{% if p[3] %}
<img src="{{p[3]}}" height="120">
{% endif %}
<h5>{{p[0]}}</h5>
<p>{{p[1]}} ريال</p>
<input type="number" min="1" max="{{p[2]}}" value="1" id="q{{loop.index}}" class="form-control mb-2">
<button onclick="add('{{p[0]}}',{{p[1]}},{{loop.index}})" class="btn btn-gold btn-sm">إضافة</button>
</div>
</div>
{% endfor %}
</div>

<h3 class="mt-4">🛒 السلة</h3>
<table class="table table-bordered" id="cart">
<tr><th>المنتج</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>
</table>

<button onclick="makeBill()" class="btn btn-gold">عرض الفاتورة</button>
<button onclick="sendWhats()" class="btn btn-success">إرسال واتساب</button>

<div id="bill" class="mt-4"></div>

<script>
let cart={};

function add(name,price,index){
let qty=parseInt(document.getElementById("q"+index).value);
if(!cart[name]) cart[name]={price:price,qty:0};
cart[name].qty+=qty;
renderCart();
}

function renderCart(){
let table=document.getElementById("cart");
table.innerHTML="<tr><th>المنتج</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>";
for(let n in cart){
let t=cart[n].price*cart[n].qty;
let row=table.insertRow();
row.insertCell(0).innerText=n;
row.insertCell(1).innerText=cart[n].qty;
row.insertCell(2).innerText=cart[n].price;
row.insertCell(3).innerText=t;
}
}

function makeBill(){
let total=0;
let name=document.getElementById("custName").value;
let phone=document.getElementById("custPhone").value;
let city=document.getElementById("custCity").value;

let bill="<h4>فاتورة شراء</h4>";
bill+="<p>الاسم: "+name+"<br>الهاتف: "+phone+"<br>المدينة: "+city+"</p>";
bill+="<table class='table table-bordered'>";
bill+="<tr><th>المنتج</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>";

for(let n in cart){
let t=cart[n].price*cart[n].qty;
total+=t;
bill+="<tr><td>"+n+"</td><td>"+cart[n].qty+"</td><td>"+cart[n].price+"</td><td>"+t+"</td></tr>";
}

bill+="<tr><th colspan='3'>المجموع</th><th>"+total+"</th></tr></table>";
document.getElementById("bill").innerHTML=bill;
}

function sendWhats(){
let total=0;
let name=document.getElementById("custName").value;
let phone=document.getElementById("custPhone").value;
let city=document.getElementById("custCity").value;

let msg="فاتورة شراء%0Aالاسم: "+name+"%0Aالهاتف: "+phone+"%0Aالمدينة: "+city+"%0A-----------%0A";

for(let n in cart){
let t=cart[n].price*cart[n].qty;
total+=t;
msg+=n+" - "+cart[n].qty+" = "+t+"%0A";
}

msg+="-----------%0Aالمجموع: "+total;
window.open("https://wa.me/{{phone}}?text="+msg,"_blank");
}

function searchProduct(){
let input=document.getElementById("search").value.toLowerCase();
let items=document.querySelectorAll(".product");
items.forEach(p=>{
p.style.display=p.dataset.name.toLowerCase().includes(input)?"block":"none";
});
}

function filterCategory(cat){
let items=document.querySelectorAll(".product");
items.forEach(p=>{
if(cat=="all"){p.style.display="block";}
else{p.style.display=p.dataset.category==cat?"block":"none";}
});
}
</script>

</body>
</html>
"""
    return render_template_string(html,products=products,categories=categories,store=STORE_NAME,phone=WHATSAPP_NUMBER)

# ================= صفحة المدير =================
@app.route("/admin",methods=["GET","POST"])
def admin():
    if request.method=="POST":
        if request.form.get("password")!=ADMIN_PASSWORD:
            flash("كلمة المرور خطأ")
            return redirect("/admin")

        action=request.form.get("action")

        if action=="add_category":
            add_category(request.form.get("category"))

        if action=="add_product":
            name=request.form.get("name")
            price=float(request.form.get("price"))
            stock=int(request.form.get("stock"))
            category=request.form.get("category")

            image=""
            file=request.files.get("image")
            if file and file.filename:
                filename=str(uuid.uuid4())+"_"+file.filename
                image=os.path.join(UPLOAD_FOLDER,filename)
                file.save(image)

            add_product(name,price,stock,image,category)

        return redirect("/admin")

    categories=get_categories()
    products=get_products()

    return render_template_string("""
<h2>صفحة المدير</h2>
<form method="POST">
<input type="password" name="password" placeholder="كلمة المرور" required><br><br>

<h4>إضافة فئة</h4>
<input name="category" placeholder="اسم الفئة">
<input type="hidden" name="action" value="add_category">
<button>إضافة فئة</button>
</form>

<hr>

<form method="POST" enctype="multipart/form-data">
<input type="password" name="password" placeholder="كلمة المرور" required><br><br>
<h4>إضافة منتج</h4>
<input name="name" placeholder="اسم المنتج" required><br>
<input name="price" type="number" step="0.01" placeholder="السعر" required><br>
<input name="stock" type="number" placeholder="الكمية" required><br>
<select name="category">
{% for c in categories %}
<option value="{{c}}">{{c}}</option>
{% endfor %}
</select><br><br>
<input type="file" name="image"><br><br>
<input type="hidden" name="action" value="add_product">
<button>إضافة المنتج</button>
</form>
""",categories=categories,products=products)

# ================= تشغيل =================
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
    
