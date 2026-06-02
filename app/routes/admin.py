# app/routes/admin.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models.models import Setting, User, APIKey, AIModel
from app import db
from app.admin_account import ADMIN_USERNAMES
import os

bp = Blueprint('admin', __name__, url_prefix='/admin')

def is_admin():
    """Check if current user is an admin."""
    if 'user_id' not in session:
        return False
    user = User.query.get(session['user_id'])
    if not user:
        return False
    return user.username in ADMIN_USERNAMES

@bp.route('')
@bp.route('/')
def dashboard():
    """Main administrative control panel."""
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home.index'))
    
    user = User.query.get(session['user_id'])
    
    from app.models.models import APIKey, AIModel, APIKeyUsage
    from sqlalchemy import desc
    from datetime import date
    
    # Platform quick stats
    active_key = APIKey.query.filter_by(is_active=True).first()
    active_model = AIModel.query.filter_by(is_active=True).first()
    
    # Today's usage
    today = date.today()
    today_usage = db.session.query(APIKeyUsage).filter_by(date=today).all()
    today_tokens = sum(u.total_tokens for u in today_usage)
    today_requests = len(today_usage)
    
    # Recent logs (Top 5)
    recent_logs = APIKeyUsage.query.order_by(desc(APIKeyUsage.created_at)).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                           user=user,
                           active_key=active_key,
                           active_model=active_model,
                           today_tokens=today_tokens,
                           today_requests=today_requests,
                           recent_logs=recent_logs)

@bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home.index'))
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # --- Handle System Prompts ---
        if action == 'save_prompts':
            prompt_keys = ['general_prompt', 'search_prompt', 'discuss_prompt', 'title_prompt']
            for key in prompt_keys:
                val = request.form.get(key)
                _save_setting(key, val)
            flash('System prompts updated successfully!', 'success')

        # --- Handle API Keys ---
        elif action == 'add_key':
            key = request.form.get('key_value')
            label = request.form.get('key_label')
            if key and label:
                new_key = APIKey(key=key, label=label, is_active=False)
                db.session.add(new_key)
                db.session.commit()
                flash('API Key added!', 'success')
        
        elif action == 'delete_key':
            key_id = request.form.get('key_id')
            key = APIKey.query.get(key_id)
            if key:
                # Manual cascade delete for usage logs to prevent IntegrityError
                from app.models.models import APIKeyUsage
                db.session.query(APIKeyUsage).filter_by(api_key_id=key.id).delete()
                
                db.session.delete(key)
                db.session.commit()
                flash('API Key deleted!', 'success')


        elif action == 'activate_key':
            key_id = request.form.get('key_id')
            # Deactivate all
            APIKey.query.update({APIKey.is_active: False})
            # Activate selected
            key = APIKey.query.get(key_id)
            if key:
                key.is_active = True
                _save_setting('gemini_api_key', key.key) # Sync for compatibility
                db.session.commit()
                flash(f'Activated API Key: {key.label}', 'success')

        # --- Handle AI Models ---
        elif action == 'add_model':
            model_id = request.form.get('model_id')
            label = request.form.get('model_label')
            if model_id and label:
                new_model = AIModel(model_id=model_id, label=label, is_active=False)
                db.session.add(new_model)
                db.session.commit()
                flash('Model added!', 'success')

        elif action == 'delete_model':
            model_id = request.form.get('db_model_id')
            model = AIModel.query.get(model_id)
            if model:
                db.session.delete(model)
                db.session.commit()
                flash('Model deleted!', 'success')

        elif action == 'activate_model':
            model_id = request.form.get('db_model_id')
            # Deactivate all
            AIModel.query.update({AIModel.is_active: False})
            # Activate selected
            model = AIModel.query.get(model_id)
            if model:
                model.is_active = True
                _save_setting('gemini_model', model.model_id) # Sync
                db.session.commit()
                flash(f'Activated Model: {model.label}', 'success')

        return redirect(url_for('admin.settings'))

    # Load Data
    api_keys = APIKey.query.order_by(APIKey.created_at.desc()).all()
    ai_models = AIModel.query.all()
    
    # Load settings (prompts)
    defaults = {
        'general_prompt': _load_file_safe('app/prompts/base_information.txt'),
        'search_prompt': _load_file_safe('app/prompts/search_client.txt'),
        'discuss_prompt': _load_file_safe('app/prompts/discuss_client.txt'),
        'title_prompt': _load_file_safe('app/prompts/summarize_title.txt')
    }
    settings_dict = {}
    for key in defaults.keys():
        setting = Setting.query.filter_by(key=key).first()
        settings_dict[key] = setting.value if setting else defaults[key]

    return render_template('admin/settings.html', 
                           settings=settings_dict, 
                           user=user,
                           api_keys=api_keys,
                           ai_models=ai_models)

def _save_setting(key, value):
    if value is not None:
        setting = Setting.query.filter_by(key=key).first()
        if not setting:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
        else:
            setting.value = value
    db.session.commit()

def _load_file_safe(path):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception:
        pass
    return ""


@bp.route('/usage')
def usage():
    """Display API key usage statistics."""
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home.index'))
    
    user = User.query.get(session['user_id'])
    
    from app.models.models import APIKeyUsage
    from sqlalchemy import desc
    
    # Get all usage logs, ordered by created_at descending (most recent first)
    usage_logs = db.session.query(APIKeyUsage)\
        .join(APIKey)\
        .order_by(desc(APIKeyUsage.created_at))\
        .limit(100)\
        .all()
    
    # Calculate totals per key
    key_totals = {}
    grand_total = 0
    for log in usage_logs:
        key_id = log.api_key_id
        if key_id not in key_totals:
            key_totals[key_id] = {
                'label': log.api_key.label,
                'total_tokens': 0,
                'total_requests': 0
            }
        key_totals[key_id]['total_tokens'] += log.total_tokens
        key_totals[key_id]['total_requests'] += log.request_count
        grand_total += log.total_tokens
    
    return render_template('admin/usage.html', 
                           user=user,
                           usage_logs=usage_logs,
                           key_totals=key_totals,
                           grand_total=grand_total)

@bp.route('/clear_usage', methods=['POST'])
def clear_usage():
    """Clear all API key usage logs."""
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home.index'))
    
    from app.models.models import APIKeyUsage
    try:
        # Delete all records from APIKeyUsage table
        db.session.query(APIKeyUsage).delete()
        db.session.commit()
        flash('All usage logs have been cleared successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing logs: {str(e)}', 'error')
        print(f"[Admin] Error clearing usage: {e}")
        
    return redirect(url_for('admin.usage'))

@bp.route('/inspector/general')
def inspector_general():
    if not is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('home.index'))
    user = User.query.get(session['user_id'])
    
    # Load default prompt
    from app.models.models import Setting
    prompt_setting = Setting.query.filter_by(key='general_prompt').first()
    default_prompt = prompt_setting.value if prompt_setting else _load_file_safe('app/prompts/base_information.txt')
    
    return render_template('admin/inspector_general.html', user=user, default_prompt=default_prompt)

@bp.route('/inspector/search')
def inspector_search():
    if not is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('home.index'))
    user = User.query.get(session['user_id'])
    
    # Load prompts
    from app.models.models import Setting
    prompts = {
        'search_prompt': Setting.query.filter_by(key='search_prompt').first().value if Setting.query.filter_by(key='search_prompt').first() else _load_file_safe('app/prompts/search_client.txt'),
        'discuss_prompt': Setting.query.filter_by(key='discuss_prompt').first().value if Setting.query.filter_by(key='discuss_prompt').first() else _load_file_safe('app/prompts/discuss_client.txt')
    }
    
    return render_template('admin/inspector_search.html', user=user, prompts=prompts)

@bp.route('/api/inspector/reset_session', methods=['POST'])
def api_reset_session():
    if not is_admin(): return jsonify({'error': 'Unauthorized'}), 401
    
    from app.gemini_client.searching import AcademicSearchSystem
    session_id = "debug_inspector_session"
    
    try:
        # Clear searching sessions
        if session_id in AcademicSearchSystem._sessions:
            del AcademicSearchSystem._sessions[session_id]
        if session_id in AcademicSearchSystem._api_key_ids:
            del AcademicSearchSystem._api_key_ids[session_id]
            
        return jsonify({'message': 'Debug session reset successfully.', 'logs': ['All agent memories cleared.']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


from flask import jsonify

import json, re
def _extract_gemini_error(e):
    """Parses cleaner error message from exception string."""
    err_str = str(e)
    try:
        match = re.search(r'\{.*\}', err_str, re.DOTALL)
        if match:
            try: data = json.loads(match.group(0).replace("'", '"'))
            except: data = {}
            if 'error' in data and isinstance(data['error'], dict):
                return data['error'].get('message', err_str)
            elif 'message' in data: return data['message']
    except: pass
    
    msg_match = re.search(r'"message":\s*"([^"]+)"', err_str)
    if msg_match: return msg_match.group(1)
    
    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
        return "Quota exceeded (429). Please wait a moment."
    return err_str


@bp.route('/api/inspector/general_call', methods=['POST'])
def api_general_call():
    if not is_admin(): return jsonify({'error': 'Unauthorized'}), 401
    from app.gemini_client.general_knowledge import GeneralKnowledgeSystem
    import json
    data = request.json
    user_input = data.get('input', '')
    custom_prompt = data.get('system_prompt', '')
    try:
        # Use AcademicSearchSystem for session management even for general call
        from app.gemini_client.searching import AcademicSearchSystem
        session_id = "debug_inspector_session"
        search_system = AcademicSearchSystem(session_id=session_id)
        
        # If prompt changed, we might need to recreate the agent
        # But for now, let's just use the current agent if it exists
        # Actually, let's create a temporary chat for General Inspector as it's separate from Academic
        # BUT the user wants memory, so let's stick to a persistent one.
        
        from google import genai
        from google.genai import types
        from app.models.models import AIModel, APIKey
        key_entry = APIKey.query.filter_by(is_active=True).first()
        model_entry = AIModel.query.filter_by(is_active=True).first()
        model_id = model_entry.model_id if model_entry else 'gemini-2.0-flash'
        
        client = genai.Client(api_key=key_entry.key)
        agent = client.chats.create(
            model=model_id,
            config=types.GenerateContentConfig(system_instruction=custom_prompt)
        )
        
        # Note: General Inspector doesn't share AcademicSearchSystem's history yet in this implementation
        # because SearchSystem is specific to the academic flow.
        # But we'll at least use the same model/key logic.

        formatted_input = json.dumps([{"role": "user", "input": user_input}], indent=4, ensure_ascii=False)
        from app.gemini_client.throttler import GeminiThrottler
        GeminiThrottler.wait_if_needed()
        response = agent.send_message(formatted_input)
        return jsonify({
            'output': response.text,
            'tokens': {
                'input': response.usage_metadata.prompt_token_count,
                'output': response.usage_metadata.candidates_token_count
            },
            'logs': [f"Sent payload: {formatted_input}", f"System Prompt used: {custom_prompt[:50]}..."],
            'technical_trace': {
                'full_payload_sent': formatted_input,
                'raw_response_received': response.text,
                'system_prompt': custom_prompt
            }
        })


    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/inspector/search_analyze', methods=['POST'])
def api_search_analyze():
    if not is_admin(): return jsonify({'error': 'Unauthorized'}), 401
    
    from app.gemini_client.searching import AcademicSearchSystem
    session_id = "debug_inspector_session"
    
    import json
    data = request.json
    user_input = data.get('input', '')
    custom_prompt = data.get('system_prompt', '')
    
    # Metadata for UI
    from app.models.models import APIKey, AIModel
    active_key = APIKey.query.filter_by(is_active=True).first()
    active_model = AIModel.query.filter_by(is_active=True).first()
    meta = {
        'api_label': active_key.label if active_key else 'Unknown',
        'model_label': active_model.label if active_model else 'Gemini Standard'
    }
    
    try:

        # Initialize search system
        search_system = AcademicSearchSystem(session_id=session_id)
        
        # Safe prompt update


        if custom_prompt:
             search_system.update_prompts(discuss_prompt=custom_prompt)

        # For Inspector: Call agent DIRECTLY to get raw output
        import json as json_lib
        formatted_input = json_lib.dumps([{
            "role": "user",
            "input": user_input
        }], indent=4, ensure_ascii=False)
        
        from app.gemini_client.throttler import GeminiThrottler
        GeminiThrottler.wait_if_needed()
        
        response = search_system.discuss_agent.send_message(formatted_input)
        raw_res = response.text  # THE RAW GEMINI OUTPUT
        
        # Still save to history for context persistence
        search_system.discuss_history.append({"role": "user", "content": user_input})
        search_system.discuss_history.append({"role": "assistant", "content": raw_res})
        search_system._update_session_cache()

        return jsonify({
            'output': raw_res,
            'metadata': meta,
            'tokens': {
                'input': response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                'output': response.usage_metadata.candidates_token_count if response.usage_metadata else 0
            },
            'logs': ["Decision analysis step completed (Raw Trace Active)."],
            'technical_trace': {
                'full_payload_sent': formatted_input,
                'raw_response_received': raw_res,
                'system_prompt': custom_prompt
            }
        })






    except Exception as e:
        import traceback
        traceback.print_exc()
        clean_msg = _extract_gemini_error(e)
        return jsonify({
            'error': clean_msg, 
            'logs': [f"CRITICAL: {str(e)}"],
            'metadata': meta
        }), 200 # Return 200 for UI visibility



@bp.route('/api/inspector/search_logic', methods=['POST'])
def api_search_logic():
    if not is_admin(): return jsonify({'error': 'Unauthorized'}), 401
    
    from app.gemini_client.searching import AcademicSearchSystem
    session_id = "debug_inspector_session"
    
    import json
    data = request.json
    system_output_intent = data.get('input', '')
    custom_prompt = data.get('system_prompt', '')
    
    from app.models.models import APIKey, AIModel
    active_key = APIKey.query.filter_by(is_active=True).first()
    active_model = AIModel.query.filter_by(is_active=True).first()
    meta = {
        'api_label': active_key.label if active_key else 'Unknown',
        'model_label': active_model.label if active_model else 'Gemini Standard'
    }
    
    try:
        search_system = AcademicSearchSystem(session_id=session_id)
        
        if custom_prompt:
             search_system.update_prompts(search_prompt=custom_prompt)

        # Call search agent
        from app.gemini_client.throttler import GeminiThrottler
        GeminiThrottler.wait_if_needed()
        
        response = search_system.search_agent.send_message(system_output_intent)
        
        # Save to history for persistence
        search_system.search_history.append({"role": "user", "parts": [system_output_intent]})
        search_system.search_history.append({"role": "model", "parts": [response.text]})
        
        return jsonify({
            'output': response.text,
            'tokens': {
                'input': response.usage_metadata.prompt_token_count,
                'output': response.usage_metadata.candidates_token_count
            },
            'logs': ["Search strategy thinking completed (Context active)."],
            'metadata': meta,
            'technical_trace': {
                'full_payload_sent': system_output_intent,
                'raw_response_received': response.text,
                'system_prompt': custom_prompt
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        clean_msg = _extract_gemini_error(e)
        return jsonify({
            'error': clean_msg, 
            'logs': [f"CRITICAL: {str(e)}"],
            'metadata': meta
        }), 200










@bp.route('/api/inspector/search_repository', methods=['POST'])
def api_search_repository():
    if not is_admin(): return jsonify({'error': 'Unauthorized'}), 401
    
    from app.models.models import APIKey, AIModel
    active_key = APIKey.query.filter_by(is_active=True).first()
    active_model = AIModel.query.filter_by(is_active=True).first()
    meta = {
        'api_label': active_key.label if active_key else 'Unknown',
        'model_label': active_model.label if active_model else 'Gemini Standard'
    }

    from app.gemini_client.searching import AcademicSearchSystem
    data = request.json
    keywords_raw = data.get('input', '').strip()

    try:
        session_id = "debug_inspector_session"
        search_system = AcademicSearchSystem(session_id=session_id)
        
        keyword = None
        
        # SMART INPUT HANDLING: Accept both plain text and JSON
        # First, try to parse as JSON with role structure
        try:
            import json
            # Check if it looks like JSON
            if keywords_raw.startswith('[') or keywords_raw.startswith('{'):
                clean_input = keywords_raw.replace('```json', '').replace('```', '').strip()
                parsed = json.loads(clean_input)
                if isinstance(parsed, list):
                    for item in parsed:
                        if item.get('role') == 'keyword':
                            keyword = item.get('output', '')
                            break
        except:
            pass
        
        # If no keyword found via JSON, treat input as plain text keyword directly
        if not keyword:
            keyword = keywords_raw

        if not keyword:
            return jsonify({'output': "No keyword provided.", 'logs': ["Please enter a keyword to search."], 'metadata': meta}), 200

        # Call the scraper directly via system
        results = search_system.search_papers(keyword)
        
        import json
        output_json = json.dumps(results, indent=4, ensure_ascii=False)
        
        return jsonify({
            'output': output_json,
            'metadata': meta,
            'logs': [f"Scraped repository for keyword: '{keyword}'", f"Found {len(results)} results."],
            'technical_trace': {
                'full_payload_sent': keyword,
                'raw_response_received': output_json
            }
        })





    except Exception as e:
        import traceback
        traceback.print_exc()
        clean_msg = _extract_gemini_error(e)
        return jsonify({
            'error': clean_msg, 
            'logs': [f"CRITICAL: {str(e)}"],
            'metadata': meta
        }), 200




@bp.route('/api/inspector/search_summarize', methods=['POST'])
def api_search_summarize():
    if not is_admin(): return jsonify({'error': 'Unauthorized'}), 401
    import json
    data = request.json
    paper_list_json = data.get('input', '[]')
    custom_prompt = data.get('system_prompt', '')
    
    # Metadata for UI
    from app.models.models import APIKey, AIModel
    active_key = APIKey.query.filter_by(is_active=True).first()
    active_model = AIModel.query.filter_by(is_active=True).first()
    meta = {
        'api_label': active_key.label if active_key else 'Unknown',
        'model_label': active_model.label if active_model else 'Gemini Standard'
    }

    from app.gemini_client.searching import AcademicSearchSystem
    session_id = "debug_inspector_session"

    try:
        search_system = AcademicSearchSystem(session_id=session_id)
        search_input_json = json.dumps([{"role": "system", "input": json.loads(paper_list_json)}], indent=4, ensure_ascii=False)
        
        response = search_system.discuss_agent.send_message(search_input_json)
        
        # History
        search_system.discuss_history.append({"role": "user", "parts": [search_input_json]})
        search_system.discuss_history.append({"role": "model", "parts": [response.text]})
        
        enhanced_output, _, _ = search_system.process_discuss_response(response.text)
        return jsonify({

            'output': enhanced_output if enhanced_output else response.text,
            'tokens': {
                'input': response.usage_metadata.prompt_token_count,
                'output': response.usage_metadata.candidates_token_count
            },
            'logs': ["Final summarization completed."],
            'technical_trace': {
                'full_payload_sent': search_input_json,
                'raw_response_received': response.text,
                'system_prompt': custom_prompt
            }
        })


    except Exception as e:
        import traceback
        traceback.print_exc()
        clean_msg = _extract_gemini_error(e)
        return jsonify({
            'error': clean_msg, 
            'logs': [f"CRITICAL: {str(e)}"],
            'metadata': meta
        }), 200

@bp.route('/users')
def users():
    if not is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home.index'))
    
    user = User.query.get(session['user_id'])
    all_users = User.query.all()
    
    users_data = []
    
    from app.models.models import ChatSession, APIKeyUsage
    from sqlalchemy import func
    
    # Pre-fetch usage data by session
    # We need to map user -> sessions -> api_key_usage
    # Because APIKeyUsage links to session_id, not user_id directly
    
    for u in all_users:
        total_tokens = 0
        
        # Get all session IDs for this user
        session_ids = [s.id for s in u.chat_sessions]
        
        if session_ids:
            # Sum tokens for these sessions
            result = db.session.query(func.sum(APIKeyUsage.total_tokens))\
                .filter(APIKeyUsage.session_id.in_(session_ids))\
                .scalar()
            if result:
                total_tokens = result
        
        users_data.append({
            'id': u.id,
            'username': u.username,
            'is_admin': u.username in ADMIN_USERNAMES,
            'total_tokens': total_tokens,
            'session_count': len(u.chat_sessions)
        })
    
    # Sort by tokens desc
    users_data.sort(key=lambda x: x['total_tokens'], reverse=True)
        
    return render_template('admin/user_management.html', user=user, users_data=users_data)

@bp.route('/delete_user', methods=['POST'])
def delete_user():
    if not is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('home.index'))
        
    user_id = request.form.get('user_id')
    user_to_delete = User.query.get(user_id)
    
    if not user_to_delete:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
        
    # Prevent self-deletion
    if user_to_delete.id == session.get('user_id'):
        flash('You cannot delete your own admin account.', 'error')
        return redirect(url_for('admin.users'))
        
    try:
        from app.models.models import ChatSession, Chat, SavedPaper, APIKeyUsage
        
        # 1. Delete Usage Logs associated with User's sessions
        session_ids = [s.id for s in user_to_delete.chat_sessions]
        if session_ids:
            db.session.query(APIKeyUsage).filter(APIKeyUsage.session_id.in_(session_ids)).delete(synchronize_session=False)
        
        # 2. Delete Chats (Cascade usually handles this, but manual is safer for SQLite)
        # Chats are linked to Sessions
        # Also direct link Chat -> User exists now? Check models.
        # Chat linked to session_id.
        
        # 3. Delete Saved Papers
        SavedPaper.query.filter_by(user_id=user_to_delete.id).delete()
        
        # 4. Delete Chat Sessions (will cascade delete chats if configured, but let's be sure)
        Chat.query.filter(Chat.session_id.in_(session_ids)).delete(synchronize_session=False)
        ChatSession.query.filter_by(user_id=user_to_delete.id).delete()
        
        # 5. Delete User
        db.session.delete(user_to_delete)
        db.session.commit()
        
        flash(f'User {user_to_delete.username} deleted successfully.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        print(f"Error deleting user: {e}")
        
    return redirect(url_for('admin.users'))




@bp.route('/user/<int:target_user_id>/history')
def user_history(target_user_id):
    if not is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('home.index'))

    user = User.query.get(session['user_id'])
    target_user = User.query.get_or_404(target_user_id)

    from app.models.models import ChatSession, Chat
    from sqlalchemy import desc

    sessions = ChatSession.query\
        .filter_by(user_id=target_user_id)\
        .order_by(desc(ChatSession.timestamp))\
        .all()

    import json as _json
    from app.models.models import SearchProgress

    sessions_data = []
    for s in sessions:
        chats = Chat.query\
            .filter_by(session_id=s.id)\
            .order_by(Chat.timestamp)\
            .all()

        chats_data = []
        for c in chats:
            steps = []
            if s.feature == 'search_v2' and c.message is None:
                raw_steps = SearchProgress.query\
                    .filter_by(chat_id=c.id)\
                    .order_by(SearchProgress.step_number)\
                    .all()
                for sp in raw_steps:
                    try:
                        steps.append(_json.loads(sp.message))
                    except Exception:
                        steps.append({'type': 'text', 'msg': sp.message})

            final_response = c.response or ''
            summary = []
            if s.feature == 'search_v2' and c.search_steps:
                try:
                    parsed = _json.loads(c.search_steps)
                    final_response = parsed.get('final_response') or final_response
                    summary = parsed.get('summary') or []
                except Exception:
                    pass

            chats_data.append({
                'message': c.message or '',
                'response': final_response,
                'steps': steps,
                'summary': summary,
                'search_status': c.search_status,
                'time': c.timestamp.strftime('%H:%M'),
            })

        sessions_data.append({'session': s, 'chats': chats_data})

    total_messages = sum(len(item['chats']) for item in sessions_data)

    return render_template('admin/user_history.html',
                           user=user,
                           target_user=target_user,
                           sessions_data=sessions_data,
                           total_messages=total_messages)


@bp.route('/logs')
def logs():
    if not is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('home.index'))
    user = User.query.get(session['user_id'])
    return render_template('admin/logs.html', user=user)

@bp.route('/api/logs')
def api_logs():
    """Returns the last N lines of the log file."""
    if not is_admin(): return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from flask import current_app
        log_path = os.path.join(current_app.root_path, '..', 'app.log')
        if not os.path.exists(log_path):
             return jsonify({'logs': []})
        
        # Read last 1000 lines efficiently-ish
        with open(log_path, 'r', encoding='utf-8') as f:
            # Simple approach: read all and slice. 
            # For massive logs, seek would be better, but this is fine for now.
            lines = f.readlines()
            return jsonify({'logs': lines[-2000:]}) # Return last 2000 lines
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
