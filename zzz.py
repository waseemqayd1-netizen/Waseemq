from flask import Flask, request, redirect, render_template_string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from sqlalchemy import func

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shop.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# =====================
# MODELS
# =====================

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    price = db.Column(db.Float)
    cost_price = db.Column(db.Float)
    stock = db.Column(db.Integer)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total = db.Column(db.Float)
    profit = db.Column(db.Float)
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer)
    product_name = db.Column(db.String(200))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    total = db.Column(db.Float)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(300))
    amount = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(200))
    quantity = db.Column(db.Integer)
    type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =====================
# إنشاء الجداول (بديل before_first_request)
# =====================

with app.app_context():
    db.create_all()

# =====================
# BASE TEMPLATE
# =====================

BASE_HTML = """
<!DOCTYPE html>
<html dir="rtl">
<head>
<meta charset="UTF-8">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#0d0d0d;color:gold}
.card{background:#1a1a1a;border:1px solid gold}
.table{color:gold}
.navbar{background:black}
</style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark">
<div class="container">
<a class="navbar-brand text-warning" href="/">نظام المحل</a>
<div>
<a class="btn btn-warning me-2" href="/products">المنتجات</a>
<a class="btn btn-warning me-2" href="/new_invoice">فاتورة</a>
<a class="btn btn-warning" href="/expenses">المصروفات</a>
</div>
</div>
</nav>

<div class="container mt-4">
{{content|safe}}
</div>

</body>
</html>
"""

# =====================
# DASHBOARD
# =====================

@app.route("/")
def dashboard():
    total_profit = db.session.query(func.sum(Invoice.profit)).scalar() or 0
    total_expenses = db.session.query(func.sum(Expense.amount)).scalar() or 0
    net_profit = total_profit - total_expenses

    today = date.today()
    today_sales = db.session.query(func.sum(Invoice.total))\
        .filter(func.date(Invoice.created_at)==today).scalar() or 0

    content = f"""
<div class='row text-center'>
<div class='col-md-3'><div class='card p-3'><h5>مبيعات اليوم</h5><h3>{today_sales}</h3></div></div>
<div class='col-md-3'><div class='card p-3'><h5>إجمالي الأرباح</h5><h3>{total_profit}</h3></div></div>
<div class='col-md-3'><div class='card p-3'><h5>المصروفات</h5><h3>{total_expenses}</h3></div></div>
<div class='col-md-3'><div class='card p-3'><h5>صافي الربح</h5><h3>{net_profit}</h3></div></div>
</div>
"""
    return render_template_string(BASE_HTML, content=content)

# =====================
# PRODUCTS
# =====================

@app.route("/products", methods=["GET","POST"])
def products():
    if request.method == "POST":
        db.session.add(Product(
            name=request.form["name"],
            price=float(request.form["price"]),
            cost_price=float(request.form["cost_price"]),
            stock=int(request.form["stock"])
        ))
        db.session.commit()
        return redirect("/products")

    products = Product.query.all()
    rows = ""
    for p in products:
        rows += f"<tr><td>{p.name}</td><td>{p.price}</td><td>{p.cost_price}</td><td>{p.stock}</td></tr>"

    content = f"""
<h2>إدارة المنتجات</h2>
<form method="post" class="row g-2 mb-4">
<div class="col"><input class="form-control" name="name" placeholder="اسم المنتج"></div>
<div class="col"><input class="form-control" name="price" placeholder="سعر البيع"></div>
<div class="col"><input class="form-control" name="cost_price" placeholder="سعر التكلفة"></div>
<div class="col"><input class="form-control" name="stock" placeholder="المخزون"></div>
<div class="col"><button class="btn btn-warning">حفظ</button></div>
</form>

<table class="table table-dark table-striped">
<tr><th>الاسم</th><th>البيع</th><th>التكلفة</th><th>المخزون</th></tr>
{rows}
</table>
"""
    return render_template_string(BASE_HTML, content=content)

# =====================
# NEW INVOICE
# =====================

@app.route("/new_invoice", methods=["GET","POST"])
def new_invoice():
    products = Product.query.all()

    if request.method == "POST":
        total = 0
        profit = 0

        invoice = Invoice(payment_method=request.form["payment"])
        db.session.add(invoice)
        db.session.commit()

        invoice_rows = ""

        for p in products:
            qty = request.form.get(f"qty_{p.id}")
            if qty and int(qty) > 0:
                qty = int(qty)

                if p.stock < qty:
                    return "المخزون غير كافي"

                line_total = qty * p.price
                line_profit = qty * (p.price - p.cost_price)

                total += line_total
                profit += line_profit
                p.stock -= qty

                db.session.add(InvoiceItem(
                    invoice_id=invoice.id,
                    product_name=p.name,
                    quantity=qty,
                    price=p.price,
                    total=line_total
                ))

                invoice_rows += f"""
<tr>
<td>{p.name}</td>
<td>{qty}</td>
<td>{p.price}</td>
<td>{line_total}</td>
</tr>
"""

        discount = float(request.form.get("discount") or 0)
        vat = float(request.form.get("vat") or 0)

        total = total - discount
        total = total + (total * vat / 100)

        invoice.total = total
        invoice.profit = profit
        db.session.commit()

        content = f"""
<h2>فاتورة رقم {invoice.id}</h2>
<table class="table table-dark">
<tr><th>المنتج</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr>
{invoice_rows}
</table>

<h5>خصم: {discount}</h5>
<h5>ضريبة: {vat}%</h5>
<h3>الإجمالي النهائي: {total}</h3>
<h5>طريقة الدفع: {invoice.payment_method}</h5>

<a href="/" class="btn btn-warning">رجوع للرئيسية</a>
"""
        return render_template_string(BASE_HTML, content=content)

    inputs = ""
    for p in products:
        inputs += f"""
<div class='col-md-4'>
<label>{p.name} (المتوفر {p.stock})</label>
<input type='number' name='qty_{p.id}' class='form-control' min='0'>
</div>
"""

    content = f"""
<h2>فاتورة جديدة</h2>
<form method="post">
<div class="row">{inputs}</div>

<hr>
<div class="row">
<div class="col"><input name="discount" class="form-control" placeholder="خصم"></div>
<div class="col"><input name="vat" class="form-control" placeholder="ضريبة %"></div>
<div class="col">
<select name="payment" class="form-control">
<option>نقد</option>
<option>تحويل</option>
<option>آجل</option>
</select>
</div>
</div>

<br>
<button class="btn btn-warning">حفظ الفاتورة</button>
</form>
"""
    return render_template_string(BASE_HTML, content=content)

# =====================
# EXPENSES
# =====================

@app.route("/expenses", methods=["GET","POST"])
def expenses():
    if request.method == "POST":
        db.session.add(Expense(
            description=request.form["description"],
            amount=float(request.form["amount"])
        ))
        db.session.commit()
        return redirect("/expenses")

    expenses = Expense.query.all()
    rows = ""
    for e in expenses:
        rows += f"<tr><td>{e.description}</td><td>{e.amount}</td></tr>"

    content = f"""
<h2>المصروفات</h2>
<form method="post" class="row g-2 mb-4">
<div class="col"><input name="description" class="form-control" placeholder="الوصف"></div>
<div class="col"><input name="amount" class="form-control" placeholder="المبلغ"></div>
<div class="col"><button class="btn btn-warning">حفظ</button></div>
</form>

<table class="table table-dark">
<tr><th>الوصف</th><th>المبلغ</th></tr>
{rows}
</table>
"""
    return render_template_string(BASE_HTML, content=content)

if __name__ == "__main__":
    app.run(debug=True)
    
