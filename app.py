import os
import io
import string
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

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
    amount_paid = db.Column(db.Float, default=0.0)
    payment_type = db.Column(db.String(50), nullable=True)

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    monthly_fee = db.Column(db.Float, default=3000.0)
    term_fee = db.Column(db.Float, default=8000.0)
    class_capacity = db.Column(db.Integer, default=30)
    default_address = db.Column(db.String(200), default="አቃቂ ቃሊቲ ወረዳ 09")

# Initialize Database
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        hashed_pw = generate_password_hash('admin123')
        default_admin = User(username='admin', password_hash=hashed_pw)
        db.session.add(default_admin)
        db.session.commit()
    
    settings = Setting.query.first()
    if not settings:
        default_settings = Setting(
            monthly_fee=3000.0, 
            term_fee=8000.0, 
            class_capacity=30,
            default_address="አቃቂ ቃሊቲ ወረዳ 09"
        )
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
    amount_paid = float(request.form.get('amount_paid', 0))
    
    settings = Setting.query.first()

    # Automatic Section Assignment Logic (A, B, C...)
    existing_count = Student.query.filter_by(grade=grade).count()
    capacity = settings.class_capacity if (settings and settings.class_capacity > 0) else 30
    
    section_index = existing_count // capacity
    assigned_section = string.ascii_uppercase[section_index % 26] 

    new_student = Student(
        full_name=full_name,
        grade=grade,
        section=assigned_section,
        phone=phone,
        address=address,
        payment_method=payment_method,
        ft_approval_no=ft_approval_no,
        amount_paid=amount_paid,
        payment_type=payment_type
    )
    db.session.add(new_student)
    db.session.commit()
    flash(f'ምዝገባዎ በስኬት ተጠናቋል! የተመደቡበት ሴክሽን፦ {assigned_section}', 'success')
    return redirect(url_for('register_page'))

# --- Admin Auth Section ---
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

# --- Add New Admin / Register ---
@app.route('/create_admin', methods=['POST'])
def create_admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    new_username = request.form.get('new_username')
    new_password = request.form.get('new_password')
    
    existing_user = User.query.filter_by(username=new_username).first()
    if existing_user:
        flash('ይህ Username አስቀድሞ ተይዟል! እባክህ ሌላ ይምረጡ።', 'danger')
    else:
        hashed_pw = generate_password_hash(new_password)
        new_user = User(username=new_username, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash(f'አዲስ Admin ({new_username}) በስኬት ተፈጥሯል!', 'success')
        
    return redirect(url_for('admin_dashboard'))

# --- Edit / Change Password ---
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    current_user = User.query.get(session['user_id'])
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    
    if check_password_hash(current_user.password_hash, old_password):
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('የይለፍ ቃልህ (Password) በስኬት ተቀይሯል!', 'success')
    else:
        flash('የድሮው የይለፍ ቃል የተሳሳተ ነው!', 'danger')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    students = Student.query.all()
    settings = Setting.query.first()
    
    # Financial Analytics Calculation
    total_expected = 0.0
    total_paid = 0.0
    
    student_data = []
    for s in students:
        expected = settings.term_fee if s.payment_type == 'Term (3 Months)' else settings.monthly_fee
        paid = s.amount_paid or 0.0
        remaining = expected - paid
        
        total_expected += expected
        total_paid += paid
        
        student_data.append({
            'student': s,
            'expected': expected,
            'paid': paid,
            'remaining': remaining
        })

    total_unpaid = total_expected - total_paid

    return render_template('admin.html', 
                           student_data=student_data, 
                           settings=settings,
                           total_expected=total_expected,
                           total_paid=total_paid,
                           total_unpaid=total_unpaid,
                           total_students=len(students))

@app.route('/update_settings', methods=['POST'])
def update_settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    settings = Setting.query.first()
    if not settings:
        settings = Setting()
        db.session.add(settings)

    settings.monthly_fee = float(request.form.get('monthly_fee'))
    settings.term_fee = float(request.form.get('term_fee'))
    settings.class_capacity = int(request.form.get('class_capacity'))
    settings.default_address = request.form.get('default_address')
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
    settings = Setting.query.first()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Financial Summary"

    # Styling Definitions
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=11, bold=True)

    headers = [
        "ID", "Full Name", "Grade", "Section", "Phone", "Address", 
        "Payment Method", "FT Ref No", "Payment Type", 
        "Total Fee Required (ETB)", "Amount Paid (ETB)", "Remaining Balance (ETB)"
    ]
    ws.append(headers)

    # Apply Header Styles
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Populate Data
    start_row = 2
    for s in students:
        expected = settings.term_fee if s.payment_type == 'Term (3 Months)' else settings.monthly_fee
        paid = s.amount_paid or 0.0
        remaining = expected - paid

        row_data = [
            s.id, s.full_name, s.grade, s.section, s.phone, s.address,
            s.payment_method, s.ft_approval_no, s.payment_type,
            expected, paid, remaining
        ]
        ws.append(row_data)

    end_row = start_row + len(students) - 1

    # Add Totals Row if there are students
    if len(students) > 0:
        total_row = [
            "", "TOTAL", "", "", "", "", "", "", "",
            f"=SUM(J2:J{end_row})", f"=SUM(K2:K{end_row})", f"=SUM(L2:L{end_row})"
        ]
        ws.append(total_row)
        
        # Style Total Row
        last_r = ws.max_row
        for c in range(1, len(headers) + 1):
            cell = ws.cell(row=last_r, column=c)
            cell.font = bold_font
            cell.fill = PatternFill(start_color="F2F2F2", fill_type="solid")

    # Format Column Widths automatically
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Student_Financial_Report.xlsx"
    )

if __name__ == '__main__':
    app.run(debug=True)