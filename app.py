import os
import io
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import openpyxl

app = Flask(__name__)
app.secret_key = 'kiyya_secret_key_change_this'

# Database Configuration (Render PostgreSQL or local SQLite)
db_url = os.environ.get('DATABASE_URL', 'sqlite:///students.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(20), nullable=False)
    section = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)             # አድራሻ
    payment_method = db.Column(db.String(50), nullable=True)        # CBE, Telebirr, etc.
    ft_approval_no = db.Column(db.String(100), nullable=True)       # FT approval / Reference No
    amount = db.Column(db.Float, nullable=True)                     # የገንዘብ መጠን
    payment_type = db.Column(db.String(50), nullable=True)          # Monthly / Term

# Initialize Database and Create Default Admin
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123')
        default_admin = User(username='admin', password_hash=hashed_pw)
        db.session.add(default_admin)
        db.session.commit()

# Routes
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    students = Student.query.all()
    return render_template('index.html', students=students)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('በስኬት ገብተዋል!', 'success')
            return redirect(url_for('index'))
        else:
            flash('የተሳሳተ Username ወይም Password!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('ወጥተዋል!', 'info')
    return redirect(url_for('login'))

@app.route('/add_student', methods=['POST'])
def add_student():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    full_name = request.form.get('full_name')
    grade = request.form.get('grade')
    section = request.form.get('section')
    phone = request.form.get('phone')
    address = request.form.get('address')
    payment_method = request.form.get('payment_method')
    ft_approval_no = request.form.get('ft_approval_no')
    amount = request.form.get('amount')
    payment_type = request.form.get('payment_type')

    new_student = Student(
        full_name=full_name,
        grade=grade,
        section=section,
        phone=phone,
        address=address,
        payment_method=payment_method,
        ft_approval_no=ft_approval_no,
        amount=float(amount) if amount else 0.0,
        payment_type=payment_type
    )
    db.session.add(new_student)
    db.session.commit()
    flash('ተማሪው በስኬት ተመዝግቧል!', 'success')
    return redirect(url_for('index'))

@app.route('/export_excel')
def export_excel():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    students = Student.query.all()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students List"

    # Header Row
    ws.append(["ID", "Full Name", "Grade", "Section", "Phone", "Address", "Payment Method", "FT / Ref No", "Amount (ETB)", "Payment Type"])

    # Data Rows
    for s in students:
        ws.append([s.id, s.full_name, s.grade, s.section, s.phone, s.address, s.payment_method, s.ft_approval_no, s.amount, s.payment_type])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="students_list.xlsx"
    )

if __name__ == '__main__':
    app.run(debug=True)