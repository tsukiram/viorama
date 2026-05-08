# /app/routes/paper.py

from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from app.models.models import User, SavedPaper
from app import db
from app.gemini_client.paper_extraction import PaperExtractionSystem
import time

bp = Blueprint('paper', __name__, url_prefix='/paper')

@bp.context_processor
def inject_cache_buster():
    return {'cache_buster': int(time.time())}

@bp.route('/<string:code>')
def detail(code):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if user is None:
        session.clear()
        return redirect(url_for('auth.login'))
    
    paper_system = PaperExtractionSystem()
    metadata = paper_system.extract_metadata(code)
    
    is_saved = SavedPaper.query.filter_by(user_id=user.id, eprint_code=code).first() is not None
    
    return render_template('paper_detail.html', user=user, paper=metadata, is_saved=is_saved)

@bp.route('/save/<string:code>', methods=['POST'])
def save_paper(code):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    # Cek apakah sudah tersimpan
    existing_paper = SavedPaper.query.filter_by(user_id=session['user_id'], eprint_code=code).first()
    if existing_paper:
        return jsonify({'success': False, 'error': 'Paper already saved'}), 400
    
    # Ambil metadata paper
    paper_system = PaperExtractionSystem()
    metadata = paper_system.extract_metadata(code)
    
    if 'error' in metadata:
        return jsonify({'success': False, 'error': metadata['error']}), 500
    
    try:
        # Simpan paper (HANYA user_id, eprint_code, dan title)
        paper = SavedPaper(
            user_id=session['user_id'],
            eprint_code=code,
            title=metadata.get('title', 'No title available')
        )
        db.session.add(paper)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Paper saved successfully!'})
    except Exception as e:
        db.session.rollback()
        print(f"Error saving paper: {e}")
        return jsonify({'success': False, 'error': 'Failed to save paper'}), 500


@bp.route('/remove/<string:code>', methods=['POST'])
def remove_paper(code):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    paper = SavedPaper.query.filter_by(user_id=session['user_id'], eprint_code=code).first()
    if not paper:
        return jsonify({'success': False, 'error': 'Paper not in saved list'}), 404
    
    try:
        db.session.delete(paper)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Paper removed successfully.'})
    except Exception as e:
        db.session.rollback()
        print(f"Error removing paper: {e}")
        return jsonify({'success': False, 'error': 'Failed to remove paper'}), 500