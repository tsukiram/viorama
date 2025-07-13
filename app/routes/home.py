# app/routes/home.py

from flask import Blueprint, render_template, redirect, url_for, session
from app.models.models import User

bp = Blueprint('home', __name__)

@bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return redirect(url_for('auth.login'))
    return redirect(url_for('home.home'))

@bp.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return redirect(url_for('auth.login'))
    return render_template('home.html', user=user)