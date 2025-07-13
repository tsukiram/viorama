# app/routes/general.py

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from app.models.models import User, ChatSession, Chat, db
from app.gemini_client.general_knowledge import GeneralKnowledgeSystem
import json

bp = Blueprint('general', __name__, url_prefix='/general')

@bp.route('/')
@bp.route('/<int:session_id>')
def index(session_id=None):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return redirect(url_for('auth.login'))
    
    chat_sessions = ChatSession.query.filter_by(user_id=user.id, feature='general').order_by(ChatSession.timestamp.desc()).all()
    current_session = None
    chats = []
    if session_id:
        current_session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
        if current_session:
            chats = Chat.query.filter_by(session_id=session_id).order_by(Chat.timestamp.asc()).all()
    
    return render_template('general.html', user=user, chat_sessions=chat_sessions, current_session=current_session, chats=chats)

@bp.route('/new_session', methods=['POST'])
def new_session():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return jsonify({'error': 'User not found'}), 401
    
    title = request.json.get('title', 'New General Session')
    new_session = ChatSession(
        user_id=user.id,
        feature='general',
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
        
        general_system = GeneralKnowledgeSystem(session_id)
        response = general_system.run_interactive_session(user_input)
        
        if response is None:
            return jsonify({'error': 'No response received'}), 500
        
        chat = Chat(
            session_id=session_id,
            user_id=user.id,
            feature='general',
            message=user_input,
            response=response
        )
        db.session.add(chat)
        db.session.commit()
        
        return jsonify({
            'message': user_input,
            'response': response,
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
    
    GeneralKnowledgeSystem.clear_session(session_id)
    Chat.query.filter_by(session_id=session_id).delete()
    db.session.delete(chat_session)
    db.session.commit()
    
    return jsonify({'message': 'Session deleted successfully'})