# C:\Users\rama\Desktop\viorama_app\viorama\app\routes\search.py
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response, current_app
from app.models.models import User, ChatSession, Chat, db
from app.gemini_client.searching import AcademicSearchSystem
import json
import re
import mistune
import traceback
from markupsafe import Markup
import time

bp = Blueprint('search', __name__, url_prefix='/search')

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
        print(f"Error in format_response: {e}")
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
    print(f"Created new session: {new_session.id}")
    
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
        
        # Save user message
        user_chat = Chat(
            session_id=session_id,
            user_id=user.id,
            feature='search',
            message=user_input,
            response=None,
            search_steps=None
        )
        db.session.add(user_chat)
        db.session.commit()
        print(f"Saved user message: {user_input}")

        # Initialize search system
        search_system = AcademicSearchSystem(session_id)
        
        # Process assistant response
        system_output, user_output, add_paper_codes, search_steps = search_system.run_interactive_session(user_input)
        
        # Store initial response
        initial_response = user_output if user_output and user_output.strip() else "I apologize, but I couldn't generate a proper response. Please try again."
        print(f"Initial response: {initial_response}")
        
        # Format and save initial response
        formatted_initial_response = format_response(initial_response)
        initial_search_steps_json = json.dumps(search_steps, ensure_ascii=False) if search_steps else json.dumps([])
        
        # Save initial assistant response to database
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
        print("Saved initial response to database")
        
        # Return initial response immediately
        initial_response_data = {
            'message': user_input,
            'initial_response': str(formatted_initial_response),
            'needs_search': bool(system_output),
            'system_output': system_output or '',
            'paper_codes': add_paper_codes if add_paper_codes else [],
            'search_steps': search_steps if search_steps else [],
            'timestamp': assistant_chat.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'chat_id': assistant_chat.id
        }
        
        return jsonify(initial_response_data)
        
    except Exception as e:
        print(f"Error in chat route: {str(e)}")
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@bp.route('/search_process/<int:chat_id>', methods=['GET', 'POST'])
def search_process(chat_id):
    """Process search and stream real-time updates using SSE"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Get the chat and verify ownership
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        chat_session = ChatSession.query.get(chat.session_id)
        if not chat_session or chat_session.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get the system output from the query parameter
        system_output = request.args.get('system_output', '')
        if not system_output:
            return jsonify({'error': 'No system output provided'}), 400
        
        # Get the search system and process search
        search_system = AcademicSearchSystem(chat.session_id)
        
        # Store the Flask app instance for use in generator
        app = current_app._get_current_object()
        
        def generate():
            search_updates = []
            add_paper_codes = []
            
            try:
                search_updates.append("Processing search request...")
                yield f"data: {json.dumps({'update': 'Processing search request...'}, ensure_ascii=False)}\n\n"
                time.sleep(0.5)
                
                current_input = system_output
                
                while True:
                    # search_updates.append("Analyzing search request...")
                    # yield f"data: {json.dumps({'update': 'Analyzing search request...'}, ensure_ascii=False)}\n\n"
                    time.sleep(0.5)
                    
                    response = search_system.search_agent.send_message(current_input)
                    should_search, keyword, additional_codes = search_system.process_search_response(response.text)
                    print(f"Search agent response: {response.text}, should_search: {should_search}, keyword: {keyword}, additional_codes: {additional_codes}")

                    if should_search and keyword:
                        search_updates.append(f"Searching for keyword: {keyword}")
                        yield f"data: {json.dumps({'update': f'Searching for keyword: {keyword}'}, ensure_ascii=False)}\n\n"
                        time.sleep(0.5)
                        
                        search_results = search_system.search_papers(keyword)
                        print(f"Search results: {search_results}")
                        
                        if search_results:
                            search_updates.append(f"Search results found: {len(search_results)}")
                            yield f"data: {json.dumps({'update': f'Search results found: {len(search_results)}'}, ensure_ascii=False)}\n\n"
                        else:
                            search_updates.append(f"No results found for keyword: {keyword}")
                            yield f"data: {json.dumps({'update': f'No results found for keyword: {keyword}'}, ensure_ascii=False)}\n\n"
                            search_updates.append("Search results found: 0")
                            yield f"data: {json.dumps({'update': 'Search results found: 0'}, ensure_ascii=False)}\n\n"
                        
                        search_updates.append("Analyzing search results and selecting relevant papers...")
                        yield f"data: {json.dumps({'update': 'Analyzing search results and selecting relevant papers...'}, ensure_ascii=False)}\n\n"
                        time.sleep(0.5)
                        
                        search_results_json = json.dumps(search_results, indent=4, ensure_ascii=False)
                        current_input = json.dumps([{"role": "search_result", "input": search_results_json}], ensure_ascii=False)
                    else:
                        add_paper_codes.extend(additional_codes)
                        break
                
                search_updates.append("Search completed.")
                yield f"data: {json.dumps({'update': 'Search completed.'}, ensure_ascii=False)}\n\n"
                
                # Get enhanced response if we have paper codes
                enhanced_response = None
                if add_paper_codes:
                    search_input = json.dumps([{"role": "system", "input": json.dumps(add_paper_codes, indent=4, ensure_ascii=False)}], indent=4, ensure_ascii=False)
                    print(f"Sending to discuss_agent: {search_input}")
                    
                    try:
                        system_response = search_system.discuss_agent.send_message(search_input)
                        print(f"Discuss agent response: {system_response.text}")
                        enhanced_output, _, _ = search_system.process_discuss_response(system_response.text)
                        print(f"Processed discuss response: {enhanced_output}")
                        
                        if enhanced_output and enhanced_output.strip():
                            enhanced_response = format_response(enhanced_output)
                            # Update the database with enhanced response using proper app context
                            with app.app_context():
                                chat_obj = Chat.query.get(chat_id)
                                if chat_obj:
                                    chat_obj.response = str(enhanced_response)
                                    chat_obj.search_steps = json.dumps(search_updates, ensure_ascii=False)
                                    db.session.commit()
                                    print("Updated database with enhanced response")
                        else:
                            print("Enhanced output is empty or invalid")
                            enhanced_response = format_response("No relevant information found from the search results.")
                            with app.app_context():
                                chat_obj = Chat.query.get(chat_id)
                                if chat_obj:
                                    chat_obj.response = str(enhanced_response)
                                    chat_obj.search_steps = json.dumps(search_updates, ensure_ascii=False)
                                    db.session.commit()
                    except Exception as discuss_error:
                        print(f"Error in discuss_agent: {str(discuss_error)}")
                        traceback.print_exc()
                        search_updates.append(f"Error processing enhanced response: {str(discuss_error)}")
                        enhanced_response = format_response("An error occurred while processing the search results.")
                        with app.app_context():
                            chat_obj = Chat.query.get(chat_id)
                            if chat_obj:
                                chat_obj.response = str(enhanced_response)
                                chat_obj.search_steps = json.dumps(search_updates, ensure_ascii=False)
                                db.session.commit()
                
                # Send final response
                final_data = {
                    'success': True,
                    'search_updates': search_updates,
                    'enhanced_response': str(enhanced_response) if enhanced_response else None,
                    'paper_codes': add_paper_codes,
                    'timestamp': chat.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'complete': True
                }
                print(f"Final SSE data: {final_data}")
                yield f"data: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                
            except Exception as search_error:
                print(f"Search error: {str(search_error)}")
                traceback.print_exc()
                search_updates.append(f"Search error: {str(search_error)}")
                error_data = {
                    'success': False,
                    'search_updates': search_updates,
                    'error': str(search_error),
                    'complete': True
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        print(f"Error in search_process: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@bp.route('/get_enhanced_response/<int:chat_id>', methods=['GET'])
def get_enhanced_response(chat_id):
    """Get enhanced response if available (for polling-based updates)"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        chat_session = ChatSession.query.get(chat.session_id)
        if not chat_session or chat_session.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify({
            'chat_id': chat_id,
            'response': chat.response,
            'search_steps': json.loads(chat.search_steps) if chat.search_steps else [],
            'timestamp': chat.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'is_updated': True
        })
        
    except Exception as e:
        print(f"Error getting enhanced response: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

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
    print(f"Deleted session: {session_id}")
    
    return jsonify({'message': 'Session deleted successfully'})