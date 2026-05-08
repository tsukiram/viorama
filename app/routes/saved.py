# /app/routes/saved.py

from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from app.models.models import User, SavedPaper
from app import db  # <-- TAMBAHKAN IMPORT INI
from sqlalchemy import desc

bp = Blueprint('saved', __name__, url_prefix='/saved')

@bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if user is None:
        session.clear()
        return redirect(url_for('auth.login'))
    
    # Ambil semua paper, diurutkan dari yang terbaru disimpan
    saved_papers = SavedPaper.query.filter_by(user_id=user.id).order_by(desc(SavedPaper.id)).all()
    
    return render_template('saved.html', user=user, saved_papers=saved_papers)

# === ENDPOINT BARU UNTUK MENGHAPUS PAPER ===
@bp.route('/remove/<string:eprint_code>', methods=['POST'])
def remove_paper(eprint_code):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    paper_to_delete = SavedPaper.query.filter_by(user_id=session['user_id'], eprint_code=eprint_code).first()

    if not paper_to_delete:
        return jsonify({'success': False, 'error': 'Paper not found in your saved list'}), 404
        
    try:
        db.session.delete(paper_to_delete)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Paper removed successfully.'})
    except Exception as e:
        db.session.rollback()
        print(f"Error removing saved paper: {e}")
        return jsonify({'success': False, 'error': 'An internal error occurred.'}), 500