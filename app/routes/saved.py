# app/routes/saved.py
from flask import Blueprint, render_template, session, redirect, url_for
from app.models.models import User, SavedPaper

bp = Blueprint('saved', __name__, url_prefix='/saved')

@bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return redirect(url_for('auth.login'))
    
    saved_papers = SavedPaper.query.filter_by(user_id=user.id).all()
    return render_template('saved.html', user=user, saved_papers=saved_papers)