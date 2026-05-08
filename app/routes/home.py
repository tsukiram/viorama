# /app/routes/home.py

from flask import Blueprint, render_template, redirect, url_for, session
from app.models.models import User, SavedPaper
from sqlalchemy import desc

bp = Blueprint('home', __name__)

@bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('home.home'))

@bp.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if user is None:
        session.clear()
        return redirect(url_for('auth.login'))
    
    # === LOGIKA BARU: Ambil 3 paper terbaru yang disimpan pengguna ===
    recent_papers = SavedPaper.query.filter_by(user_id=user.id)\
        .order_by(desc(SavedPaper.id))\
        .limit(3)\
        .all()
    
    # Lewatkan recent_papers ke template
    return render_template('home.html', user=user, recent_papers=recent_papers)