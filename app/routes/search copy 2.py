# app\routes\search.py
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from app.models.models import User, ChatSession, Chat, db
from app.gemini_client.searching import AcademicSearchSystem
import json
import re

bp = Blueprint('search', __name__, url_prefix='/search')

def format_response(response_text):
    """Transform <<link<<{code}<<{title}>>{code}>>link>> into HTML <a> tags."""
    return re.sub(
        r'<<link<<(\d+)<<(.+?)>>(\d+)>>link>>',
        r'<a href="/paper/\1" class="text-blue-600 hover:underline">\2</a>',
        response_text
    )

@bp.route('/')
@bp.route('/<int:session_id>')
def index(session_id=None):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return redirect(url_for('auth.login'))
    
    chat_sessions = ChatSession.query.filter_by(user_id=user.id, feature='search').order_by(ChatSession.timestamp.desc()).all()
    current_session = None
    chats = []
    if session_id:
        current_session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
        if current_session:
            chats = Chat.query.filter_by(session_id=session_id).order_by(Chat.timestamp.asc()).all()
    
    return render_template('search.html', user=user, chat_sessions=chat_sessions, current_session=current_session, chats=chats)

@bp.route('/new_session', methods=['POST'])
def new_session():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return jsonify({'error': 'User not found'}), 401
    
    title = request.json.get('title', 'New Search Session')
    new_session = ChatSession(
        user_id=user.id,
        feature='search',
        title=title
    )
    db.session.add(new_session)
    db.session.commit()
    
    return jsonify({'session_id': new_session.id})

@bp.route('/chat/<int:session_id>', methods=['POST'])
def chat(session_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return jsonify({'error': 'User not found'}), 401
    
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        chat_session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
        if not chat_session:
            return jsonify({'error': 'Invalid session ID'}), 404
        
        search_system = AcademicSearchSystem(session_id)
        user_output, add_paper_codes, search_steps = search_system.run_interactive_session(user_input)
        
        if user_output is None:
            return jsonify({'error': 'No valid response received'}), 500
        
        # Format response to convert link patterns to HTML
        formatted_response = format_response(user_output)
        search_steps_json = json.dumps(search_steps, ensure_ascii=False)
        chat = Chat(
            session_id=session_id,
            user_id=user.id,
            feature='search',
            message=user_input,
            response=formatted_response,
            search_steps=search_steps_json
        )
        db.session.add(chat)
        db.session.commit()
        
        return jsonify({
            'message': user_input,
            'response': formatted_response,
            'paper_codes': add_paper_codes,
            'search_steps': search_steps,
            'timestamp': chat.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/delete_session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return jsonify({'error': 'User not found'}), 401
    
    chat_session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
    if not chat_session:
        return jsonify({'error': 'Invalid session ID'}), 404
    
    AcademicSearchSystem.clear_session(session_id)
    Chat.query.filter_by(session_id=session_id).delete()
    db.session.delete(chat_session)
    db.session.commit()
    
    return jsonify({'message': 'Session deleted successfully'})