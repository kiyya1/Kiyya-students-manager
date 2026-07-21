import sqlite3
import csv
import os
from io import StringIO
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, Response, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ለ Session ደህንነት የሚያስፈልግ ሚስጥራዊ ቁልፍ
app.secret_key = os.environ.get('SECRET_KEY', 'wabi_school_admin_secret_key_2026')

def init_db():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    # 1. የተማሪዎች ሰንጠረዥ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            age INTEGER NOT NULL,
            grade TEXT NOT NULL,
            parent_phone TEXT NOT NULL
        )
    ''')
    
    # 2. የአስተዳዳሪዎች ሰንጠረዥ (Admins Table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # ነባሪ አድሚን (Default Admin) ከሌለ መፍጠር - Password: admin123
    cursor.execute('SELECT * FROM admins WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        hashed_password = generate_password_hash('admin123')
        cursor.execute('INSERT INTO admins (username, password) VALUES (?, ?)', ('admin', hashed_password))
        
    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('እባክዎ መጀመሪያ ወደ ሲስተሙ ይግቡ!', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('students.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admins WHERE username = ?', (username,))
        admin = cursor.fetchone()
        conn.close()
        
        # የይለፍ ቃሉን በ Hash ማረጋገጥ
        if admin and check_password_hash(admin[2], password):
            session['logged_in'] = True
            session['username'] = username
            flash('እንኳን ደህና መጡ! በተሳካ ሁኔታ ገብተዋል።', 'success')
            return redirect(url_for('display_students'))
        else:
            flash('የተሳሳተ የተጠቃሚ ስም ወይም የይለፍ ቃል!', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('በተሳካ ሁኔታ ወጥተዋል።', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        age = request.form['age']
        grade = request.form['grade']
        parent_phone = request.form['parent_phone']
        
        conn = sqlite3.connect('students.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO students (fullname, age, grade, parent_phone)
            VALUES (?, ?, ?, ?)
        ''', (fullname, age, grade, parent_phone))
        conn.commit()
        conn.close()

        success_message = f"ተማሪ {fullname} በዳታቤዝ ውስጥ በተሳካ ሁኔታ ተመዝግቧል!"
        return render_template('index.html', success=True, message=success_message)

@app.route('/students')
@login_required
def display_students():
    search_query = request.args.get('search', '')
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM students')
    total_students = cursor.fetchone()[0]

    if search_query:
        cursor.execute('SELECT * FROM students WHERE fullname LIKE ?', ('%' + search_query + '%',))
    else:
        cursor.execute('SELECT * FROM students')
        
    all_students = cursor.fetchall()
    conn.close()
    
    return render_template('students.html', students=all_students, search_query=search_query, total_students=total_students)

@app.route('/export_csv')
@login_required
def export_csv():
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students')
    students = cursor.fetchall()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'ሙሉ ስም', 'እድሜ', 'ክፍል', 'የወላጅ ስልክ'])
    for student in students:
        cw.writerow(student)
        
    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers["Content-Disposition"] = "attachment; filename=registered_students.csv"
    return output

@app.route('/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        fullname = request.form['fullname']
        age = request.form['age']
        grade = request.form['grade']
        parent_phone = request.form['parent_phone']
        
        cursor.execute('''
            UPDATE students
            SET fullname = ?, age = ?, grade = ?, parent_phone = ?
            WHERE id = ?
        ''', (fullname, age, grade, parent_phone, student_id))
        
        conn.commit()
        conn.close()
        return redirect(url_for('display_students'))
    
    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    conn.close()
    
    return render_template('edit.html', student=student)

@app.route('/delete/<int:student_id>', methods=['POST'])
@login_required
def delete_student(student_id):
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('display_students'))

if __name__ == '__main__':
    app.run(debug=True)