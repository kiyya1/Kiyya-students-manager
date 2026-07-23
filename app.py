import os
import io
import string
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import openpyxl

app = Flask(__name__)
app.secret_key = 'kiyya_secret_key_change_this'

# Database Configuration
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
    address = db.Column(db.String(200), nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    ft_approval_no = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Float, nullable=True)
    payment_type = db.Column(db.String(50), nullable=True)

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monthly_fee = db.Column(db.Float, default=3000.0)
    term_fee = db.Column(db.Float, default=8000.0)
    class_capacity = db.Column(db.Integer, default=30)  # Max students per section

# Initialize Database
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123')
        default_admin = User(username='admin', password_hash=hashed_pw)
        db.session.add(default_admin)
        db.session.commit()
    
    if not Setting.query.first():
        default_settings = Setting(monthly_fee=3000.0, term_fee=8000.0, class_capacity=30)
        db.session.add(default_settings)
        db.session.commit()

# --- Public Student Registration Page ---
@app.route('/')
def register_page():
    settings = Setting.query.first()
    return render_template('register.html', settings=settings)

@app.route('/add_student', methods=['POST'])
def add_student():
    full_name = request.form.get('full_name')
    grade = request.form.get('grade')
    phone = request.form.get('phone')
    address = request.form.get('address')
    payment_method = request.form.get('payment_method')
    ft_approval_no = request.form.get('ft_approval_no')
    payment_type = request.form.get('payment_type')
    
    settings = Setting.query.first()
    amount = settings.term_fee if payment_type == 'Term (3 Months)' else settings.monthly_fee

    # Automatic Section Assignment Logic (A, B, C...)
    existing_count = Student.query.filter_by(grade=grade).count()
    capacity = settings.class_capacity if settings.class_capacity > 0 else 30
    
    section_index = existing_count // capacity
    # Generates 'A', 'B', 'C', etc.
    assigned_section = string.ascii_uppercase[section_index % 26] 

    new_student = Student(
        full_name=full_name,
        grade=grade,
        section=assigned_section,
        phone=phone,
        address=address,
        payment_method=payment_method,
        ft_approval_no=ft_approval_no,
        amount=amount,
        payment_type=payment_type
    )
    db.session.add(new_student)
    db.session.commit()
    flash(f'ምዝገባዎ በስኬት ተጠናቋል! የተመደቡበት ሴክሽን፦ {assigned_section}', 'success')
    return redirect(url_for('register_page'))

# --- Admin Section ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('admin_dashboard'))
        else:
            flash('የተሳሳተ Username ወይም Password!', 'danger')
    return render_template('login.html')

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    students = Student.query.all()
    settings = Setting.query.first()
    return render_template('admin.html', students=students, settings=settings)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    settings = Setting.query.first()
    settings.monthly_fee = float(request.form.get('monthly_fee'))
    settings.term_fee = float(request.form.get('term_fee'))
    settings.class_capacity = int(request.form.get('class_capacity'))
    db.session.commit()
    
    flash('ቅንብሮች በስኬት ተቀይረዋል!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('ወጥተዋል!', 'info')
    return redirect(url_for('login'))

@app.route('/export_excel')
def export_excel():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    students = Student.query.all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students List"

    ws.append(["ID", "Full Name", "Grade", "Section", "Phone", "Address", "Payment Method", "FT Ref No", "Amount", "Payment Type"])

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