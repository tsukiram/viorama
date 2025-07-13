# app/routes/paper.py

from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
from app.models.models import User, SavedPaper, db
from app.gemini_client.paper_extraction import PaperExtractionSystem

bp = Blueprint('paper', __name__, url_prefix='/paper')

@bp.route('/<string:code>')
def detail(code):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return redirect(url_for('auth.login'))
    
    paper_system = PaperExtractionSystem()
    metadata = paper_system.extract_metadata(code)
    is_saved = SavedPaper.query.filter_by(user_id=user.id, eprint_code=code).first() is not None
    return render_template('paper_detail.html', user=user, paper=metadata, is_saved=is_saved)

@bp.route('/save/<string:code>', methods=['POST'])
def save_paper(code):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return jsonify({'error': 'User not found'}), 401
    
    if SavedPaper.query.filter_by(user_id=user.id, eprint_code=code).first():
        return jsonify({'error': 'Paper already bookmarked'}), 400
    
    paper_system = PaperExtractionSystem()
    metadata = paper_system.extract_metadata(code)
    if 'error' in metadata:
        return jsonify({'error': metadata['error']}), 500
    
    paper = SavedPaper(
        user_id=user.id,
        eprint_code=code,
        title=metadata.get('title', 'No title available')
    )
    db.session.add(paper)
    db.session.commit()
    return jsonify({'message': 'Paper bookmarked successfully'})

@bp.route('/remove/<string:code>', methods=['POST'])
def remove_paper(code):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return jsonify({'error': 'User not found'}), 401
    
    paper = SavedPaper.query.filter_by(user_id=user.id, eprint_code=code).first()
    if not paper:
        return jsonify({'error': 'Paper not found in saved list'}), 404
    
    db.session.delete(paper)
    db.session.commit()
    return jsonify({'message': 'Paper removed successfully'})