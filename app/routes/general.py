# /app/routes/general.py

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response, stream_with_context, current_app
from app.models.models import User, ChatSession, Chat, db
from app.gemini_client.general_knowledge import GeneralKnowledgeSystem
from app.gemini_client.title_generator import TitleGenerator
from datetime import datetime
import pytz
import locale
import markdown
import traceback
import time
import json

bp = Blueprint('general', __name__, url_prefix='/general')

@bp.context_processor
def inject_cache_buster():
    return {'cache_buster': int(time.time())}


def markdown_to_html(text):
    """Filter Jinja untuk mengonversi Markdown ke HTML."""
    return markdown.markdown(text, extensions=['fenced_code', 'tables'])

@bp.app_template_filter('markdown')
def markdown_filter(text):
    return markdown_to_html(text)

try:
    locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Indonesian_Indonesia.1252')
    except locale.Error:
        pass

def get_local_timezone():
    return pytz.timezone('Asia/Jakarta')

@bp.route('/')
@bp.route('/<int:session_id>')
def index(session_id=None):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    
    local_tz = get_local_timezone()
    today_local = datetime.now(local_tz)
    formatted_date = today_local.strftime('%A, %d %B %Y') 

    chat_sessions = ChatSession.query.filter_by(user_id=user.id, feature='general').order_by(ChatSession.timestamp.desc()).all()
    
    current_session_data = None
    chats = []
    if session_id:
        current_session_data = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
        if current_session_data:
            chats = Chat.query.filter_by(session_id=session_id).order_by(Chat.timestamp.asc()).all()
        else:
            return redirect(url_for('general.index'))
            
    return render_template('general.html', 
                           user=user, 
                           chat_sessions=chat_sessions, 
                           current_session=current_session_data, 
                           chats=chats,
                           today_date=formatted_date)

@bp.route('/chat', methods=['POST'])
def chat():
    print(f"\n{'='*60}")
    print(f"[ROUTE-CHAT] NEW REQUEST RECEIVED")
    print(f"{'='*60}")
    
    if 'user_id' not in session:
        print(f"[ROUTE-CHAT] ERROR: User not authenticated")
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    user_input = data.get('message')
    session_id = data.get('session_id')

    print(f"[ROUTE-CHAT] User ID: {session['user_id']}")
    print(f"[ROUTE-CHAT] Message: '{user_input[:100]}{'...' if len(user_input) > 100 else ''}'")
    print(f"[ROUTE-CHAT] Session ID from request: {session_id}")
    print(f"[ROUTE-CHAT] Session ID type: {type(session_id)}")

    if not user_input:
        print(f"[ROUTE-CHAT] ERROR: No message provided")
        return jsonify({'error': 'No message provided'}), 400

    try:
        new_session_created = False
        chat_session = None
        
        # Check if session_id is None or empty string or 'null'
        if not session_id or session_id == 'null' or session_id == 'undefined':
            print(f"\n[ROUTE-CHAT] *** CREATING NEW SESSION ***")
            new_session_created = True
            
            # Generate title
            print(f"[ROUTE-CHAT] Calling TitleGenerator.generate_title()...")
            try:
                generated_title = TitleGenerator.generate_title(user_input)
                print(f"[ROUTE-CHAT] Title generated: '{generated_title}'")
            except Exception as title_error:
                print(f"[ROUTE-CHAT] Title generation failed: {title_error}")
                print(f"[ROUTE-CHAT] Traceback: {traceback.format_exc()}")
                generated_title = "New Chat"
            
            # Create new session
            print(f"[ROUTE-CHAT] Creating ChatSession object...")
            chat_session = ChatSession(
                user_id=session['user_id'],
                feature='general',
                title=generated_title
            )
            
            print(f"[ROUTE-CHAT] Adding to database...")
            db.session.add(chat_session)
            
            print(f"[ROUTE-CHAT] Flushing to get ID...")
            db.session.flush()  # Get the ID without committing yet
            
            session_id = chat_session.id
            print(f"[ROUTE-CHAT] New session ID: {session_id}")
            print(f"[ROUTE-CHAT] Session title: '{generated_title}'")
            
        else:
            print(f"\n[ROUTE-CHAT] *** USING EXISTING SESSION ***")
            print(f"[ROUTE-CHAT] Looking up session_id: {session_id}")
            chat_session = ChatSession.query.filter_by(
                id=session_id, 
                user_id=session['user_id']
            ).first()
            
            if not chat_session:
                print(f"[ROUTE-CHAT] ERROR: Session not found or permission denied")
                db.session.rollback()
                return jsonify({'error': 'Invalid session ID or permission denied'}), 404
            
            print(f"[ROUTE-CHAT] Found session: '{chat_session.title}'")

        # Process with GeneralKnowledgeSystem
        print(f"\n[ROUTE-CHAT] Processing with GeneralKnowledgeSystem...")
        try:
            general_system = GeneralKnowledgeSystem(session_id)
            response_text = general_system.run_interactive_session(user_input)
            
            if response_text is None:
                response_text = "Maaf, saya tidak dapat memproses permintaan Anda saat ini."
                print(f"[ROUTE-CHAT] AI returned None, using default response")
            else:
                print(f"[ROUTE-CHAT] AI response received (length: {len(response_text)} chars)")
        except Exception as ai_error:
            print(f"[ROUTE-CHAT] AI processing error: {ai_error}")
            print(f"[ROUTE-CHAT] Traceback: {traceback.format_exc()}")
            response_text = "Maaf, terjadi kesalahan saat memproses permintaan Anda."
        
        # Save to database
        print(f"\n[ROUTE-CHAT] Saving chat to database...")
        chat_entry = Chat(
            session_id=session_id,
            user_id=session['user_id'],
            feature='general',
            message=user_input,
            response=response_text
        )
        db.session.add(chat_entry)
        
        print(f"[ROUTE-CHAT] Committing to database...")
        db.session.commit()
        print(f"[ROUTE-CHAT] Database commit successful")
        
        # Prepare response
        response_data = {'response': response_text}
        
        if new_session_created:
            response_data['new_session_id'] = session_id
            print(f"\n[ROUTE-CHAT] *** RETURNING NEW SESSION ID: {session_id} ***")
        else:
            print(f"\n[ROUTE-CHAT] *** RETURNING RESPONSE FOR EXISTING SESSION ***")
        
        print(f"[ROUTE-CHAT] Response keys: {list(response_data.keys())}")
        print(f"{'='*60}")
        print(f"[ROUTE-CHAT] REQUEST COMPLETED SUCCESSFULLY")
        print(f"{'='*60}\n")
        
        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        print(f"\n[ROUTE-CHAT] CRITICAL ERROR")
        print(f"[ROUTE-CHAT] Exception: {e}")
        print(f"[ROUTE-CHAT] Traceback:\n{traceback.format_exc()}")
        print(f"{'='*60}\n")
        return jsonify({'error': 'An internal server error occurred.'}), 500

@bp.route('/chat_stream', methods=['POST'])
def chat_stream():
    """Streaming chat endpoint (Server-Sent Events).

    Mengirim event JSON per baris:
      { "type": "meta", "session_id": int, "new_session": bool }
      { "type": "chunk", "text": "..." }
      { "type": "done" }
      { "type": "error", "message": "..." }
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    user_input = data.get('message')
    session_id = data.get('session_id')
    user_id = session['user_id']

    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    new_session_created = False
    chat_session = None

    try:
        if not session_id or session_id in ('null', 'undefined'):
            new_session_created = True
            try:
                generated_title = TitleGenerator.generate_title(user_input)
            except Exception as title_error:
                print(f"[STREAM-CHAT] Title generation failed: {title_error}")
                generated_title = "New Chat"

            chat_session = ChatSession(
                user_id=user_id,
                feature='general',
                title=generated_title
            )
            db.session.add(chat_session)
            db.session.commit()
            session_id = chat_session.id
        else:
            chat_session = ChatSession.query.filter_by(id=session_id, user_id=user_id).first()
            if not chat_session:
                return jsonify({'error': 'Invalid session ID or permission denied'}), 404
    except Exception as e:
        db.session.rollback()
        print(f"[STREAM-CHAT] Setup error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': 'Failed to prepare session'}), 500

    app = current_app._get_current_object()

    def event_stream():
        meta = {
            'type': 'meta',
            'session_id': session_id,
            'new_session': new_session_created,
            'session_title': chat_session.title if chat_session else None,
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

        full_response = ""
        had_error = False
        try:
            general_system = GeneralKnowledgeSystem(session_id)
            for kind, payload in general_system.run_streaming_session(user_input):
                if kind == 'chunk':
                    full_response += payload
                    yield f"data: {json.dumps({'type': 'chunk', 'text': payload}, ensure_ascii=False)}\n\n"
                elif kind == 'error':
                    had_error = True
                    yield f"data: {json.dumps({'type': 'error', 'message': payload}, ensure_ascii=False)}\n\n"
                elif kind == 'done':
                    full_response = payload or full_response
        except Exception as e:
            had_error = True
            print(f"[STREAM-CHAT] Stream error: {e}")
            print(traceback.format_exc())
            yield f"data: {json.dumps({'type': 'error', 'message': 'Streaming failed'}, ensure_ascii=False)}\n\n"

        # Persist chat after stream ends (success only)
        if not had_error and full_response:
            try:
                with app.app_context():
                    chat_entry = Chat(
                        session_id=session_id,
                        user_id=user_id,
                        feature='general',
                        message=user_input,
                        response=full_response,
                    )
                    db.session.add(chat_entry)
                    db.session.commit()
            except Exception as save_err:
                print(f"[STREAM-CHAT] Save error: {save_err}")
                print(traceback.format_exc())

        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@bp.route('/rename_session/<int:session_id>', methods=['POST'])
def rename_session(session_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized', 'success': False}), 401
    
    data = request.json
    new_title = data.get('title', '').strip()
    
    if not new_title:
        return jsonify({'error': 'Title cannot be empty', 'success': False}), 400
    
    chat_session = ChatSession.query.filter_by(id=session_id, user_id=session['user_id']).first()
    if not chat_session:
        return jsonify({'error': 'Session not found or not owned by user', 'success': False}), 404
    
    try:
        chat_session.title = new_title
        db.session.commit()
        return jsonify({'success': True, 'message': 'Session renamed successfully', 'new_title': new_title})
    except Exception as e:
        db.session.rollback()
        print(f"[ROUTE-RENAME] ERROR: {e}")
        return jsonify({'error': 'An internal server error occurred while renaming.', 'success': False}), 500

@bp.route('/delete_session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized', 'success': False}), 401
    
    chat_session = ChatSession.query.filter_by(id=session_id, user_id=session['user_id']).first()
    if not chat_session:
        return jsonify({'error': 'Session not found or not owned by user', 'success': False}), 404
    
    try:
        Chat.query.filter_by(session_id=session_id).delete()
        db.session.delete(chat_session)
        GeneralKnowledgeSystem.clear_session(session_id)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Session deleted successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"[ROUTE-DELETE] ERROR: {e}")
        return jsonify({'error': 'An internal server error occurred while deleting.', 'success': False}), 500