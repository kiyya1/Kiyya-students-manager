from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# SQLite Database Setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'school.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monthly_fee = db.Column(db.Float, default=3000.0)
    term_fee = db.Column(db.Float, default=8000.0)
    bus_fee = db.Column(db.Float, default=1500.0)
    default_address = db.Column(db.String(200), default="አቃቂ ቃሊቲ ወረዳ 09")

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    bus_service = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200))
    payment_type = db.Column(db.String(50), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    ft_approval_no = db.Column(db.String(100), nullable=False)
    registered_at = db.Column(db.DateTime, server_default=db.func.now())

# Initialize DB & Admin
with app.app_context():
    db.create_all()
    if not Settings.query.first():
        db.session.add(Settings())
        db.session.commit()
    if not AdminUser.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123')
        db.session.add(AdminUser(username='admin', password_hash=hashed_pw))
        db.session.commit()

@app.route('/')
def index():
    settings = Settings.query.first()
    return render_template('register.html', settings=settings)

@app.route('/add_student', methods=['POST'])
def add_student():
    try:
        full_name = request.form.get('full_name')
        grade = request.form.get('grade')
        phone = request.form.get('phone')
        bus_service = request.form.get('bus_service')
        address = request.form.get('address')
        payment_type = request.form.get('payment_type')
        payment_method = request.form.get('payment_method')
        amount_paid = float(request.form.get('amount_paid', 0))
        ft_approval_no = request.form.get('ft_approval_no')

        student = Student(
            full_name=full_name, grade=grade, phone=phone,
            bus_service=bus_service, address=address,
            payment_type=payment_type, payment_method=payment_method,
            amount_paid=amount_paid, ft_approval_no=ft_approval_no
        )
        db.session.add(student)
        db.session.commit()
        flash("ምዝገባው በተሳካ ሁኔታ ተጠናቋል!", "success")
        return redirect(url_for('print_receipt', student_id=student.id))
    except Exception as e:
        db.session.rollback()
        flash("ስህተት ተፈጥሯል፣ እባክዎ ደግመው ይሞክሩ።", "danger")
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = AdminUser.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_logged_in'] = True
            session['admin_username'] = admin.username
            return redirect(url_for('admin_dashboard'))
        else:
            flash("የተሳሳተ የተጠቃሚ ስም ወይም ፓስወርድ!", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    students = Student.query.order_by(Student.id.desc()).all()
    settings = Settings.query.first()
    return render_template('admin.html', students=students, settings=settings)

@app.route('/admin/change_password', methods=['POST'])
def change_password():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    admin = AdminUser.query.filter_by(username=session.get('admin_username')).first()

    if not admin or not check_password_hash(admin.password_hash, current_password):
        flash("የአሁኑ ፓስወርድ አልተዛመደም!", "danger")
        return redirect(url_for('admin_dashboard'))

    if new_password != confirm_password:
        flash("አዲሱ ፓስወርድ እና ማረጋገጫው አይመሳሰሉም!", "warning")
        return redirect(url_for('admin_dashboard'))

    admin.password_hash = generate_password_hash(new_password)
    db.session.commit()
    flash("ፓስወርድዎ በተሳካ ሁኔታ ተቀይሯል!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/receipt/<int:student_id>')
def print_receipt(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template('receipt.html', student=student)

if __name__ == '__main__':
    app.run(debug=True)