# app/routes/search.py

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, current_app
from app.models.models import User, ChatSession, Chat, SearchProgress, db
from app.gemini_client.searching import AcademicSearchSystem
from app.gemini_client.title_generator import TitleGenerator
import json
import re
import mistune
import traceback
from markupsafe import Markup
from datetime import datetime
import time
import threading

bp = Blueprint('search', __name__, url_prefix='/search')

SEARCH_STALE_SECONDS = 300


def _add_progress_step(chat_id, msg, status='processing'):
    """Insert a SearchProgress row. Automatically marks previous step as completed."""
    try:
        last = SearchProgress.query.filter_by(chat_id=chat_id)\
            .order_by(SearchProgress.step_number.desc()).first()
        if last and last.status == 'processing':
            last.status = 'completed'
        next_num = (last.step_number + 1) if last else 1
        db.session.add(SearchProgress(
            chat_id=chat_id, step_number=next_num,
            message=msg, status=status,
        ))
        db.session.commit()
        return next_num
    except Exception as e:
        db.session.rollback()
        print(f"[SearchRoute] Failed to persist step: {e}")
        return None

@bp.context_processor
def inject_cache_buster():
    return {'cache_buster': int(time.time())}

def format_response(response_text):
    """Transform Markdown and link patterns into clean HTML."""
    try:
        response_text = re.sub(
            r'<<link<<(\d+)<<(.+?)>>(\d+)>>link>>',
            r'<a href="/paper/\1" class="text-blue-600 hover:underline" target="_blank">\2</a>',
            response_text
        )
        markdown = mistune.create_markdown(escape=False)
        html = markdown(response_text)
        return Markup(f'<div class="markdown-content">{html}</div>')
    except Exception as e:
        print("Error in format_response [] === ", e, " []")
        traceback.print_exc()
        return Markup(f"<div class='markdown-content'>Error formatting response: {str(e)}</div>")

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
        else:
            return redirect(url_for('search.index'))
    
    return render_template('search.html', user=user, chat_sessions=chat_sessions, current_session=current_session, chats=chats)

@bp.route('/chat', methods=['POST'])
def chat():
    print("\n[SEARCH-CHAT] NEW REQUEST RECEIVED []")
    
    if 'user_id' not in session:
        print("[SEARCH-CHAT] ERROR [] === User not authenticated []")
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    user_input = data.get('message')
    session_id = data.get('session_id')

    print("[SEARCH-CHAT] User ID [] === ", session['user_id'], " []")
    print("[SEARCH-CHAT] Message [] === '", user_input[:100] if user_input else '', "{'...' if len(user_input) > 100 else ''} []")
    print("[SEARCH-CHAT] Session ID from request [] === ", session_id, " []")

    if not user_input:
        print("[SEARCH-CHAT] ERROR [] === No message provided []")
        return jsonify({'error': 'No message provided'}), 400

    try:
        new_session_created = False
        chat_session = None
        
        if not session_id or session_id == 'null' or session_id == 'undefined':
            print("\n[SEARCH-CHAT] CREATING NEW SESSION []")
            new_session_created = True
            
            try:
                generated_title = TitleGenerator.generate_title(user_input)
                print("[SEARCH-CHAT] Title generated [] === '", generated_title, "' []")
            except Exception as title_error:
                print("[SEARCH-CHAT] Title generation failed [] === ", title_error, " []")
                generated_title = "New Search Session"
            
            chat_session = ChatSession(
                user_id=session['user_id'],
                feature='search',
                title=generated_title
            )
            
            db.session.add(chat_session)
            db.session.flush()
            
            session_id = chat_session.id
            print("[SEARCH-CHAT] New session ID [] === ", session_id, " []")
            
        else:
            print("\n[SEARCH-CHAT] USING EXISTING SESSION []")
            print("[SEARCH-CHAT] Looking up session_id [] === ", session_id, " []")
            chat_session = ChatSession.query.filter_by(
                id=session_id, 
                user_id=session['user_id']
            ).first()
            
            if not chat_session:
                print("[SEARCH-CHAT] ERROR [] === Session not found []")
                db.session.rollback()
                return jsonify({'error': 'Invalid session ID'}), 404
            
            print("[SEARCH-CHAT] Found session [] === '", chat_session.title, "' []")

        # Save user message
        user_chat = Chat(
            session_id=session_id,
            user_id=session['user_id'],
            feature='search',
            message=user_input,
            response=None,
            search_steps=None
        )
        db.session.add(user_chat)
        db.session.commit()
        print("[SEARCH-CHAT] Saved user message []")

        # Initialize search system
        print("\n[SEARCH-CHAT] Initializing AcademicSearchSystem []")
        search_system = AcademicSearchSystem(session_id)
        
        # Load history untuk existing session
        if not new_session_created:
            previous_chats = Chat.query.filter_by(
                session_id=session_id
            ).order_by(Chat.timestamp.asc()).all()[:-1]
            
            if previous_chats:
                print("[SEARCH-CHAT] Loading [] === ", len(previous_chats), " previous messages []")
                search_system.load_history_from_db(previous_chats)
        
        # Process assistant response
        system_output, user_output, add_paper_codes, search_steps = search_system.run_interactive_session(user_input)
        
        initial_response = user_output if user_output and user_output.strip() else "I apologize, but I couldn't generate a proper response. Please try again."
        print("[SEARCH-CHAT] Initial response generated []")
        
        formatted_initial_response = format_response(initial_response)
        initial_search_steps_json = json.dumps(search_steps, ensure_ascii=False) if search_steps else json.dumps([])
        
        assistant_chat = Chat(
            session_id=session_id,
            user_id=None,
            feature='search',
            message=None,
            response=str(formatted_initial_response),
            search_steps=initial_search_steps_json
        )
        db.session.add(assistant_chat)
        db.session.commit()
        print("[SEARCH-CHAT] Saved assistant response []")
        
        response_data = {
            'message': user_input,
            'initial_response': str(formatted_initial_response),
            'needs_search': bool(system_output),
            'system_output': system_output or '',
            'paper_codes': add_paper_codes if add_paper_codes else [],
            'search_steps': search_steps if search_steps else [],
            'timestamp': assistant_chat.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'chat_id': assistant_chat.id
        }
        
        if new_session_created:
            response_data['new_session_id'] = session_id
            print(f"\n[SEARCH-CHAT] RETURNING NEW SESSION ID [] === {session_id} (Type: {type(session_id)}) []")
            print(f"[SEARCH-CHAT] FULL RESPONSE DATA KEYS: {list(response_data.keys())}")
        
        print("[SEARCH-CHAT] REQUEST COMPLETED []")
        
        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        print("\n[SEARCH-CHAT] CRITICAL ERROR [] === ", e, " []")
        print("[SEARCH-CHAT] Traceback [] === \n", traceback.format_exc(), " []")
        return jsonify({'error': 'An internal server error occurred.'}), 500

@bp.route('/check_search_status/<int:chat_id>', methods=['GET'])
def check_search_status(chat_id):
    """Return new progress steps since ?after=N. DB is source of truth."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404

        chat_session = ChatSession.query.get(chat.session_id)
        if not chat_session or chat_session.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403

        after = request.args.get('after', 0, type=int)
        db_status = chat.search_status or 'pending'

        # Stale detection: processing but latest step is too old.
        if db_status == 'processing':
            latest_step = SearchProgress.query.filter_by(chat_id=chat_id)\
                .order_by(SearchProgress.step_number.desc()).first()
            if latest_step and (datetime.utcnow() - latest_step.created_at).total_seconds() > SEARCH_STALE_SECONDS:
                chat.search_status = 'error'
                db.session.commit()
                db_status = 'error'

        # Fetch only new steps since cursor.
        new_steps = SearchProgress.query.filter(
            SearchProgress.chat_id == chat_id,
            SearchProgress.step_number > after,
        ).order_by(SearchProgress.step_number.asc()).all()

        steps_data = [{'step_number': s.step_number, 'msg': s.message, 'status': s.status} for s in new_steps]
        latest_num = new_steps[-1].step_number if new_steps else after

        # Build backward-compat fields for restoreAndPollSearchProgress.
        all_steps_for_compat = None
        if after == 0 and new_steps:
            all_steps_for_compat = steps_data

        result = {
            'status': 'complete' if db_status == 'completed' else db_status,
            'new_steps': steps_data,
            'latest_step_number': latest_num,
            'is_processing': db_status == 'processing',
            'is_completed': db_status == 'completed',
            'is_error': db_status == 'error',
        }

        if all_steps_for_compat is not None:
            result['search_steps'] = all_steps_for_compat

        if db_status == 'completed' and chat.response:
            paper_codes = []
            search_updates = steps_data
            if chat.search_steps:
                try:
                    parsed = json.loads(chat.search_steps)
                    if isinstance(parsed, dict):
                        paper_codes = parsed.get('paper_context', [])
                        search_updates = parsed.get('steps', steps_data)
                    elif isinstance(parsed, list):
                        search_updates = parsed
                except Exception:
                    pass
            result['result'] = {
                'success': True,
                'search_updates': search_updates,
                'enhanced_response': chat.response,
                'paper_codes': paper_codes,
                'complete': True,
            }

        if db_status == 'error':
            result['error'] = 'Search failed or timed out.'

        if db_status == 'cancelled':
            result['is_cancelled'] = True
            if chat.response:
                result['result'] = {
                    'success': False,
                    'cancelled': True,
                    'enhanced_response': chat.response,
                    'search_updates': steps_data,
                    'paper_codes': [],
                    'complete': True,
                }

        return jsonify(result)
    except Exception as e:
        print("Error checking search status [] === ", e, " []")
        return jsonify({'error': str(e)}), 500

@bp.route('/search_process/<int:chat_id>', methods=['GET', 'POST'])
def search_process(chat_id):
    """Kick off background search. Client polls /check_search_status for progress."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404

        chat_session = ChatSession.query.get(chat.session_id)
        if not chat_session or chat_session.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403

        system_output = request.args.get('system_output', '')
        if not system_output:
            return jsonify({'error': 'No system output provided'}), 400

        if chat.search_status == 'processing':
            return jsonify({'started': False, 'reason': 'already_processing'})

        # Fresh start — clear any leftover cancel flag.
        chat.search_status = 'processing'
        db.session.commit()
        AcademicSearchSystem.clear_cancel(chat.session_id)

        app = current_app._get_current_object()
        session_id = chat.session_id

        def run_search():
            with app.app_context():
                try:
                    search_system = AcademicSearchSystem(session_id)
                    gen = search_system.process_search_request(
                        user_input=system_output,
                        chat_id=chat_id,
                        app_context=app.app_context(),
                    )

                    paper_codes = []
                    final_search_updates = []

                    for step in gen:
                        if AcademicSearchSystem.is_cancelled(session_id):
                            _add_progress_step(chat_id, "Search cancelled by user.", "warning")

                            # Collect search history for context.
                            all_steps = SearchProgress.query.filter_by(chat_id=chat_id)\
                                .order_by(SearchProgress.step_number.asc()).all()
                            steps_summary = "\n".join(
                                [f"- {s.message}" for s in all_steps if s.status != 'warning']
                            )

                            try:
                                cancel_context = json.dumps([{
                                    "role": "system",
                                    "input": (
                                        "PENCARIAN DIBATALKAN oleh user.\n\n"
                                        f"Riwayat langkah pencarian yang sudah dilakukan sebelum dibatalkan:\n{steps_summary}\n\n"
                                        "Tugasmu:\n"
                                        "1. Informasikan bahwa pencarian telah DIBATALKAN/DIHENTIKAN.\n"
                                        "2. Tampilkan riwayat langkah pencarian yang sudah dilakukan di atas.\n"
                                        "3. Tanyakan apakah user ingin mencoba lagi atau mencari topik lain."
                                    )
                                }], ensure_ascii=False)
                                cancel_response = search_system.discuss_agent.send_message(cancel_context)
                                enhanced_output, _, _ = search_system.process_discuss_response(cancel_response.text)
                                if enhanced_output and enhanced_output.strip():
                                    cancelled_msg = format_response(enhanced_output)
                                else:
                                    cancelled_msg = format_response(
                                        f"**Pencarian dibatalkan.**\n\nRiwayat pencarian sebelum dibatalkan:\n{steps_summary}\n\nSilakan coba lagi atau tanyakan hal lain."
                                    )
                            except Exception:
                                cancelled_msg = format_response(
                                    f"**Pencarian dibatalkan.**\n\nRiwayat pencarian sebelum dibatalkan:\n{steps_summary}\n\nSilakan coba lagi atau tanyakan hal lain."
                                )

                            chat_obj = Chat.query.get(chat_id)
                            if chat_obj:
                                chat_obj.response = str(cancelled_msg)
                                chat_obj.search_status = 'cancelled'
                                chat_obj.search_steps = json.dumps({
                                    'steps': [{'msg': s.message, 'status': s.status} for s in all_steps],
                                    'paper_context': [],
                                }, ensure_ascii=False)
                                db.session.commit()

                            AcademicSearchSystem.clear_cancel(session_id)
                            return

                        if "update" in step:
                            update = step["update"]
                            _add_progress_step(chat_id, update["msg"], update.get("status", "processing"))
                        elif "complete" in step:
                            paper_codes = step.get("paper_codes", [])
                            final_search_updates = step.get("search_steps", [])
                            print("Search generator completed. Paper codes:", len(paper_codes))
                        elif "error" in step:
                            raise Exception(step["error"])

                    _add_progress_step(chat_id, "Generating final response...", "processing")

                    enhanced_response = None
                    if paper_codes:
                        search_input_json = json.dumps(
                            [{"role": "system", "input": json.dumps(paper_codes, indent=4, ensure_ascii=False)}],
                            indent=4, ensure_ascii=False,
                        )

                        from app.gemini_client.throttler import GeminiThrottler
                        GeminiThrottler.wait_if_needed()

                        system_response = search_system.discuss_agent.send_message(search_input_json)
                        enhanced_output, _, _ = search_system.process_discuss_response(system_response.text)

                        try:
                            from app.gemini_client.usage_logger import log_token_usage_sync
                            usage_meta = system_response.usage_metadata
                            if usage_meta and search_system.api_key_id:
                                log_token_usage_sync(
                                    api_key_id=search_system.api_key_id,
                                    input_tokens=usage_meta.prompt_token_count or 0,
                                    output_tokens=usage_meta.candidates_token_count or 0,
                                    session_id=session_id,
                                    feature='discuss',
                                    input_content=search_input_json,
                                    output_content=enhanced_output if enhanced_output else system_response.text,
                                )
                        except Exception as log_err:
                            print(f"[SearchRoute] Could not log final usage: {log_err}")

                        if enhanced_output and enhanced_output.strip():
                            enhanced_response = format_response(enhanced_output)
                        else:
                            enhanced_response = format_response("No relevant information found from the search results.")
                    else:
                        enhanced_response = format_response("I couldn't find any specific papers matching your request after the search, but feel free to ask something else!")

                    # Write final state to DB. Also write chat.search_steps for modal backward compat.
                    chat_obj = Chat.query.get(chat_id)
                    if chat_obj:
                        chat_obj.response = str(enhanced_response)
                        chat_obj.search_status = 'completed'
                        all_steps = SearchProgress.query.filter_by(chat_id=chat_id)\
                            .order_by(SearchProgress.step_number.asc()).all()
                        chat_obj.search_steps = json.dumps({
                            'steps': [{'msg': s.message, 'status': s.status} for s in all_steps],
                            'paper_context': paper_codes,
                        }, ensure_ascii=False)
                        db.session.commit()

                except Exception as search_error:
                    print("Search background error:", search_error)
                    traceback.print_exc()
                    _add_progress_step(chat_id, f"Error: {search_error}", "error")
                    try:
                        chat_obj = Chat.query.get(chat_id)
                        if chat_obj:
                            chat_obj.search_status = 'error'
                            db.session.commit()
                    except Exception as db_err:
                        db.session.rollback()
                        print(f"Failed to update chat status in DB: {db_err}")

        thread = threading.Thread(target=run_search, daemon=True)
        thread.start()

        return jsonify({'started': True})

    except Exception as e:
        print("Error in search_process init:", e)
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@bp.route('/cancel_search/<int:chat_id>', methods=['POST'])
def cancel_search(chat_id):
    """Cancel an active search for this chat."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404

        chat_session = ChatSession.query.get(chat.session_id)
        if not chat_session or chat_session.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403

        if chat.search_status != 'processing':
            return jsonify({'cancelled': False, 'reason': 'not_processing'})

        # Only set the flag. Thread will detect it, generate response, and set status='cancelled'.
        AcademicSearchSystem.request_cancel(chat.session_id)

        return jsonify({'cancelled': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/stop_all_searches', methods=['POST'])
def stop_all_searches():
    """Admin: stop ALL running searches across all users."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from app.models.models import User
    user = User.query.get(session['user_id'])
    if not user or user.username != 'admin':
        return jsonify({'error': 'Admin only'}), 403

    try:
        processing = Chat.query.filter_by(search_status='processing').all()
        count = len(processing)

        # Set flags — threads will detect and handle gracefully.
        AcademicSearchSystem.cancel_all()

        # For chats where thread may already be dead (no active thread to detect flag),
        # force-set status so they don't stay stuck at 'processing' forever.
        for c in processing:
            _add_progress_step(c.id, "Search stopped by admin.", "warning")

        db.session.commit()

        return jsonify({'stopped': True, 'count': count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


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
        print("[SEARCH-RENAME] ERROR [] === ", e, " []")
        return jsonify({'error': 'An internal server error occurred while renaming.', 'success': False}), 500

@bp.route('/delete_session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized', 'success': False}), 401
    
    chat_session = ChatSession.query.filter_by(id=session_id, user_id=session['user_id']).first()
    if not chat_session:
        return jsonify({'error': 'Session not found or not owned by user', 'success': False}), 404
    
    try:
        chat_ids = [c.id for c in Chat.query.filter_by(session_id=session_id).all()]
        if chat_ids:
            SearchProgress.query.filter(SearchProgress.chat_id.in_(chat_ids)).delete(synchronize_session=False)
        Chat.query.filter_by(session_id=session_id).delete()
        db.session.delete(chat_session)
        AcademicSearchSystem.clear_session(session_id)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Session deleted successfully'})
    except Exception as e:
        db.session.rollback()
        print("[SEARCH-DELETE] ERROR [] === ", e, " []")
        return jsonify({'error': 'An internal server error occurred while deleting.', 'success': False}), 500
