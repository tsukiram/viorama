# /app/routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.models import User, db
from werkzeug.security import generate_password_hash, check_password_hash

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('home.home'))
        else:
            # Gunakan flash untuk pesan error
            flash('Username atau password salah.', 'danger')
            return redirect(url_for('auth.login'))
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validasi yang lebih bersih
        error = None
        if not username or not password or not confirm_password:
            error = 'Semua field wajib diisi.'
        elif len(password) < 8:
            error = 'Password minimal 8 karakter.'
        elif password != confirm_password:
            error = 'Password tidak cocok.'
        elif User.query.filter_by(username=username).first():
            error = f"Username '{username}' sudah digunakan."

        if error:
            flash(error, 'danger')
            return render_template('register.html')
        
        # Jika tidak ada error, lanjutkan
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        # === INI BAGIAN PERUBAHAN UTAMA ===
        # 1. HAPUS baris ini untuk mencegah login otomatis
        # session['user_id'] = new_user.id 
        
        # 2. TAMBAHKAN pesan flash sukses
        flash('Akun berhasil dibuat! Silakan masuk.', 'success')
        
        # 3. Redirect ke halaman login
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Anda telah berhasil keluar.', 'success')
    return redirect(url_for('auth.login'))