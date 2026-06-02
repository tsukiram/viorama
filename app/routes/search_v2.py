# app/routes/search_v2.py
#
# Paper Search v2 — flow simple, static prompt, streaming per keyword.
# Tidak share state apapun dengan v1 search.

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, current_app, Response, stream_with_context
from app.models.models import User, ChatSession, Chat, SearchProgress, db
from app.gemini_client.searching_v2 import AcademicSearchSystemV2
from app.gemini_client.title_generator import TitleGenerator
from concurrent.futures import ThreadPoolExecutor
import json
import time
import threading
import traceback
from datetime import datetime

# Executor untuk title generation paralel (dipakai oleh chat_stream)
_title_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='v2-title')


def _generate_title_safe(user_input):
    try:
        return TitleGenerator.generate_title(user_input)
    except Exception as e:
        print(f"[SearchV2-stream] title gen error: {e}")
        return None

bp = Blueprint('search_v2', __name__, url_prefix='/search-v2')

FEATURE = 'search_v2'
SEARCH_STALE_SECONDS = 180  # v2 lebih cepat, batas stale lebih pendek


# ---------- Filter labels (untuk tampilan ke user) ----------
_PAPER_TYPE_LABELS = {
    'article':           'Article',
    'book_section':      'Book Section',
    'monograph':         'Monograph',
    'conference_item':   'Conference or Workshop Item',
    'book':              'Book',
    'thesis':            'Thesis',
    'patent':            'Patent',
    'image':             'Image',
    'video':             'Video',
    'audio':             'Audio',
    'experiment':        'Experiment',
    'teaching_resource': 'Teaching Resource',
    'other':             'Other',
}


def _format_filter_description(filters):
    """Bangun string deskripsi filter aktif (Bahasa Indonesia, ringkas).

    Hasil contoh: "tahun 2020-2024, tipe Thesis"
    Kalau tidak ada filter, return string kosong.
    """
    if not filters:
        return ''
    parts = []

    df = filters.get('date_from') or ''
    dt = filters.get('date_to') or ''
    yf = df[:4] if df else ''
    yt = dt[:4] if dt else ''
    if yf and yt:
        parts.append(f"tahun {yf}–{yt}")
    elif yf:
        parts.append(f"sejak tahun {yf}")
    elif yt:
        parts.append(f"sampai tahun {yt}")

    pt = filters.get('paper_type') or filters.get('thesis_type')
    if pt:
        label = _PAPER_TYPE_LABELS.get(pt, pt.title())
        parts.append(f"tipe {label}")

    return ', '.join(parts)


# ---------- Helpers ----------
def _add_progress_step(chat_id, payload, status='processing'):
    """Insert SearchProgress row. payload bisa dict (akan di-JSON) atau string.

    Auto-mark step sebelumnya sebagai 'completed' kalau masih 'processing'.
    """
    try:
        last = SearchProgress.query.filter_by(chat_id=chat_id) \
            .order_by(SearchProgress.step_number.desc()).first()
        if last and last.status == 'processing':
            last.status = 'completed'
        next_num = (last.step_number + 1) if last else 1
        msg = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        db.session.add(SearchProgress(
            chat_id=chat_id, step_number=next_num,
            message=msg, status=status,
        ))
        db.session.commit()
        return next_num
    except Exception as e:
        db.session.rollback()
        print(f"[SearchV2Route] progress insert error: {e}")
        return None


@bp.context_processor
def inject_cache_buster():
    return {'cache_buster': int(time.time())}


# ---------- Background search worker (shared) ----------
def _run_keyword_search_background(app, session_id, chat_id, system_output, filters=None):
    """Kick off keyword search in a daemon thread.

    Used both by /chat (new session inline kickoff) and /search_process (explicit kickoff).
    Caller must have already set chat.search_status='processing' and committed.

    `filters` is optional dict with keys: date_from, date_to, paper_type.
    """
    def run_search():
        with app.app_context():
            try:
                system = AcademicSearchSystemV2(session_id)
                gen = system.process_keyword_search(
                    user_description=system_output,
                    chat_id=chat_id,
                    app_context=app.app_context(),
                    filters=filters,
                )

                summary = []
                all_empty = True

                for event in gen:
                    if AcademicSearchSystemV2.is_cancelled(session_id):
                        _add_progress_step(chat_id, {"type": "cancelled"}, status='warning')
                        chat_obj = Chat.query.get(chat_id)
                        if chat_obj:
                            chat_obj.search_status = 'cancelled'
                            chat_obj.search_steps = json.dumps(
                                {'summary': summary, 'cancelled': True},
                                ensure_ascii=False,
                            )
                            db.session.commit()
                        AcademicSearchSystemV2.clear_cancel(session_id)
                        return

                    if "section" in event:
                        _add_progress_step(
                            chat_id,
                            {"type": "section", "section": event["section"]},
                            status='processing',
                        )
                    elif "keyword_start" in event:
                        ks = event["keyword_start"]
                        _add_progress_step(
                            chat_id,
                            {"type": "keyword_start", **ks},
                            status='processing',
                        )
                    elif "keyword_result" in event:
                        kr = event["keyword_result"]
                        _add_progress_step(
                            chat_id,
                            {"type": "keyword_result", **kr},
                            status='completed',
                        )
                        summary.append(kr)
                    elif "complete" in event:
                        all_empty = event.get("all_empty", False)
                        summary = event.get("summary", summary)
                    elif "error" in event:
                        raise Exception(event["error"])

                chat_obj = Chat.query.get(chat_id)
                if not chat_obj:
                    return

                final_summary_text = None
                if all_empty:
                    suggestion = system.request_empty_suggestion(summary)
                    final_summary_text = suggestion or "Tidak ada karya tulis ditemukan untuk semua kata kunci."
                    chat_obj.response = final_summary_text
                else:
                    try:
                        final_summary_text = system.inject_paper_context(summary, app_context=app.app_context())
                    except Exception as inj_err:
                        print(f"[SearchV2] inject error: {inj_err}")

                chat_obj.search_status = 'completed'
                chat_obj.search_steps = json.dumps(
                    {
                        'summary': summary,
                        'all_empty': all_empty,
                        'final_response': final_summary_text or '',
                    },
                    ensure_ascii=False,
                )
                db.session.commit()

            except Exception as search_err:
                print(f"[SearchV2] background error: {search_err}")
                traceback.print_exc()
                _add_progress_step(chat_id, {"type": "error", "msg": str(search_err)}, status='error')
                try:
                    chat_obj = Chat.query.get(chat_id)
                    if chat_obj:
                        chat_obj.search_status = 'error'
                        db.session.commit()
                except Exception:
                    db.session.rollback()

    thread = threading.Thread(target=run_search, daemon=True)
    thread.start()


# ---------- Routes ----------
@bp.route('/')
@bp.route('/<int:session_id>')
def index(session_id=None):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.get(session['user_id'])
    if user is None:
        session.pop('user_id', None)
        return redirect(url_for('auth.login'))

    chat_sessions = ChatSession.query.filter_by(user_id=user.id, feature=FEATURE) \
        .order_by(ChatSession.timestamp.desc()).all()

    current_session = None
    chats = []
    if session_id:
        current_session = ChatSession.query.filter_by(id=session_id, user_id=user.id).first()
        if current_session and current_session.feature == FEATURE:
            chats = Chat.query.filter_by(session_id=session_id) \
                .order_by(Chat.timestamp.asc()).all()
        else:
            return redirect(url_for('search_v2.index'))

    return render_template(
        'search_v2.html',
        user=user,
        chat_sessions=chat_sessions,
        current_session=current_session,
        chats=chats,
    )


@bp.route('/chat', methods=['POST'])
def chat():
    """Receive user message → run discuss agent v2 → return next-step instruction."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    user_input = data.get('message')
    session_id = data.get('session_id')

    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    try:
        new_session_created = False
        chat_session = None

        if not session_id or session_id in ('null', 'undefined'):
            new_session_created = True
            try:
                title = TitleGenerator.generate_title(user_input)
            except Exception as title_err:
                print(f"[SearchV2] title gen error: {title_err}")
                title = "New Search v2"

            chat_session = ChatSession(
                user_id=session['user_id'],
                feature=FEATURE,
                title=title,
            )
            db.session.add(chat_session)
            db.session.flush()
            session_id = chat_session.id
        else:
            chat_session = ChatSession.query.filter_by(
                id=session_id, user_id=session['user_id']).first()
            if not chat_session or chat_session.feature != FEATURE:
                db.session.rollback()
                return jsonify({'error': 'Invalid session ID'}), 404

        # Save user message
        user_chat = Chat(
            session_id=session_id,
            user_id=session['user_id'],
            feature=FEATURE,
            message=user_input,
            response=None,
            search_steps=None,
        )
        db.session.add(user_chat)
        db.session.commit()

        # Discuss agent v2
        search_system = AcademicSearchSystemV2(session_id)

        if not new_session_created:
            previous = Chat.query.filter_by(session_id=session_id) \
                .order_by(Chat.timestamp.asc()).all()[:-1]
            if previous:
                search_system.load_history_from_db(previous)

        system_output, user_output, _err = search_system.run_interactive_session(user_input)

        initial_response = user_output if user_output and user_output.strip() \
            else "Maaf, terjadi kendala saat memproses pesan. Coba lagi."

        # In v2, kita TIDAK pakai mistune format_response — discuss agent v2 keluar plain markdown
        # dan frontend (marked.js) yang render. Tapi untuk konsistensi storage, simpan apa adanya.
        assistant_chat = Chat(
            session_id=session_id,
            user_id=None,
            feature=FEATURE,
            message=None,
            response=initial_response,
            search_steps=None,
        )
        db.session.add(assistant_chat)
        db.session.commit()

        # Kick off background search inline when discuss agent emits system_output.
        # This keeps the search running across the new-session redirect that the
        # frontend performs immediately after this response.
        search_started = False
        if system_output and system_output.strip():
            assistant_chat.search_status = 'processing'
            db.session.commit()
            AcademicSearchSystemV2.clear_cancel(session_id)
            _run_keyword_search_background(
                current_app._get_current_object(),
                session_id,
                assistant_chat.id,
                system_output,
            )
            search_started = True

        response_data = {
            'message': user_input,
            'initial_response': initial_response,
            'needs_search': bool(system_output),
            'search_started': search_started,
            'system_output': system_output or '',
            'timestamp': assistant_chat.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'chat_id': assistant_chat.id,
        }
        if new_session_created:
            response_data['new_session_id'] = session_id

        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        print(f"[SearchV2] chat error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'An internal server error occurred.'}), 500


@bp.route('/chat_stream', methods=['POST'])
def chat_stream():
    """Streaming version dari /chat.

    Stream initial_response (jawaban discuss agent untuk user) per-chunk via SSE,
    lalu kick off keyword search di background. Frontend setelah stream selesai
    akan polling /check_status seperti biasa untuk hasil pencarian.

    Events:
      { type: meta, session_id, new_session, session_title }
      { type: chunk, text }
      { type: error, message }
      { type: done, chat_id, needs_search, search_started }
    """
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    user_input = data.get('message')
    session_id = data.get('session_id')
    user_id = session['user_id']

    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    # Sanitize filters dari client. Kosong/None = tidak filter.
    raw_filters = data.get('filters') or {}
    filters = {
        'date_from':  (raw_filters.get('date_from') or '').strip() or None,
        'date_to':    (raw_filters.get('date_to') or '').strip() or None,
        # paper_type baru menggantikan thesis_type — terima keduanya untuk backward-compat
        'paper_type': (raw_filters.get('paper_type')
                       or raw_filters.get('thesis_type')
                       or '').strip() or None,
    }
    has_any_filter = any(filters.values())

    new_session_created = False
    chat_session = None
    title_future = None

    try:
        if not session_id or session_id in ('null', 'undefined'):
            new_session_created = True

            # Spawn title generation di thread background — jalan paralel dgn discuss agent
            title_future = _title_executor.submit(_generate_title_safe, user_input)

            # Pakai placeholder title dulu — akan di-update lewat event title_update
            chat_session = ChatSession(user_id=user_id, feature=FEATURE, title="New Search...")
            db.session.add(chat_session)
            db.session.commit()
            session_id = chat_session.id
        else:
            chat_session = ChatSession.query.filter_by(id=session_id, user_id=user_id).first()
            if not chat_session or chat_session.feature != FEATURE:
                return jsonify({'error': 'Invalid session'}), 404

        # Save user message (committed sebelum stream supaya history konsisten)
        user_chat = Chat(
            session_id=session_id,
            user_id=user_id,
            feature=FEATURE,
            message=user_input,
            response=None,
            search_steps=None,
        )
        db.session.add(user_chat)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[SearchV2-stream] setup error: {e}")
        traceback.print_exc()
        return jsonify({'error': 'Setup failed'}), 500

    app = current_app._get_current_object()
    session_title = chat_session.title

    def event_stream():
        meta = {
            'type': 'meta',
            'session_id': session_id,
            'new_session': new_session_created,
            'session_title': session_title,
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

        # Run discuss agent (blocking — Gemini call)
        try:
            search_system = AcademicSearchSystemV2(session_id)
            if not new_session_created:
                with app.app_context():
                    previous = Chat.query.filter_by(session_id=session_id) \
                        .order_by(Chat.timestamp.asc()).all()[:-1]
                    if previous:
                        search_system.load_history_from_db(previous)

            system_output, user_output, _err = search_system.run_interactive_session(user_input)
            initial_response = (
                user_output if user_output and user_output.strip()
                else "Maaf, terjadi kendala saat memproses pesan. Coba lagi."
            )

            # Append info filter aktif (hardcoded di sini, bukan dari LLM)
            # supaya user lihat filter apa yang sedang dipakai pencariannya.
            if has_any_filter and system_output:
                filter_desc = _format_filter_description(filters)
                if filter_desc:
                    initial_response = initial_response.rstrip() + f"\n\n_Filter aktif: {filter_desc}._"
        except Exception as e:
            print(f"[SearchV2-stream] discuss error: {e}")
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': 'Gagal memproses pesan'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'chat_id': None, 'needs_search': False, 'search_started': False}, ensure_ascii=False)}\n\n"
            return

        # Save assistant chat
        chat_id = None
        try:
            with app.app_context():
                assistant_chat = Chat(
                    session_id=session_id,
                    user_id=None,
                    feature=FEATURE,
                    message=None,
                    response=initial_response,
                    search_steps=None,
                )
                db.session.add(assistant_chat)
                db.session.commit()
                chat_id = assistant_chat.id
        except Exception as e:
            print(f"[SearchV2-stream] save assistant error: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass

        # Title update — tunggu title future selesai (sudah jalan paralel dengan discuss agent
        # jadi biasanya sudah ready). Kalau belum, kasih waktu max 5 detik.
        if title_future is not None:
            try:
                final_title = title_future.result(timeout=5)
                if final_title:
                    with app.app_context():
                        cs = ChatSession.query.get(session_id)
                        if cs:
                            cs.title = final_title
                            db.session.commit()
                    yield f"data: {json.dumps({'type': 'title_update', 'session_id': session_id, 'title': final_title}, ensure_ascii=False)}\n\n"
            except Exception as title_err:
                print(f"[SearchV2-stream] title future error: {title_err}")

        # Stream initial_response per-chunk (server-side artificial chunking
        # — discuss agent v2 sudah selesai, tinggal dipotong jadi chunk
        # supaya client bisa render typewriter).
        text = initial_response
        CHUNK = 24
        for i in range(0, len(text), CHUNK):
            piece = text[i:i + CHUNK]
            yield f"data: {json.dumps({'type': 'chunk', 'text': piece}, ensure_ascii=False)}\n\n"

        # Kick off background keyword search jika ada system_output
        search_started = False
        if system_output and system_output.strip() and chat_id:
            try:
                with app.app_context():
                    a_chat = Chat.query.get(chat_id)
                    if a_chat:
                        a_chat.search_status = 'processing'
                        db.session.commit()
                AcademicSearchSystemV2.clear_cancel(session_id)
                _run_keyword_search_background(
                    app, session_id, chat_id, system_output,
                    filters=filters if has_any_filter else None,
                )
                search_started = True
            except Exception as e:
                print(f"[SearchV2-stream] search kickoff error: {e}")

        done = {
            'type': 'done',
            'chat_id': chat_id,
            'needs_search': bool(system_output),
            'search_started': search_started,
        }
        yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@bp.route('/search_process/<int:chat_id>', methods=['POST'])
def search_process(chat_id):
    """Kick off background keyword search. Frontend polls /check_status."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        chat = Chat.query.get(chat_id)
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404

        chat_session = ChatSession.query.get(chat.session_id)
        if not chat_session or chat_session.user_id != session['user_id']:
            return jsonify({'error': 'Unauthorized'}), 403
        if chat_session.feature != FEATURE:
            return jsonify({'error': 'Wrong feature'}), 400

        system_output = request.args.get('system_output', '') or (request.json or {}).get('system_output', '')
        if not system_output:
            return jsonify({'error': 'No system output provided'}), 400

        if chat.search_status == 'processing':
            return jsonify({'started': False, 'reason': 'already_processing'})

        chat.search_status = 'processing'
        db.session.commit()
        AcademicSearchSystemV2.clear_cancel(chat.session_id)

        _run_keyword_search_background(
            current_app._get_current_object(),
            chat.session_id,
            chat_id,
            system_output,
        )

        return jsonify({'started': True})

    except Exception as e:
        db.session.rollback()
        print(f"[SearchV2] search_process init error: {e}")
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@bp.route('/check_status/<int:chat_id>', methods=['GET'])
def check_status(chat_id):
    """Polling endpoint for frontend.

    Returns new SearchProgress steps (each message is a JSON-serialized event)
    plus final search_steps blob when completed/cancelled/error.
    """
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

        # Stale detection
        if db_status == 'processing':
            latest = SearchProgress.query.filter_by(chat_id=chat_id) \
                .order_by(SearchProgress.step_number.desc()).first()
            if latest and (datetime.utcnow() - latest.created_at).total_seconds() > SEARCH_STALE_SECONDS:
                chat.search_status = 'error'
                db.session.commit()
                db_status = 'error'

        new_steps = SearchProgress.query.filter(
            SearchProgress.chat_id == chat_id,
            SearchProgress.step_number > after,
        ).order_by(SearchProgress.step_number.asc()).all()

        events = []
        for s in new_steps:
            try:
                parsed = json.loads(s.message)
            except (json.JSONDecodeError, TypeError):
                parsed = {"type": "raw", "msg": s.message}
            parsed['_step'] = s.step_number
            parsed['_status'] = s.status
            events.append(parsed)

        latest_num = new_steps[-1].step_number if new_steps else after

        result = {
            'status': 'complete' if db_status == 'completed' else db_status,
            'new_events': events,
            'latest_step_number': latest_num,
            'is_processing': db_status == 'processing',
            'is_completed': db_status == 'completed',
            'is_error': db_status == 'error',
            'is_cancelled': db_status == 'cancelled',
        }

        if db_status in ('completed', 'cancelled'):
            summary = []
            all_empty = False
            cancelled = False
            final_response_steps = ''
            if chat.search_steps:
                try:
                    parsed = json.loads(chat.search_steps)
                    if isinstance(parsed, dict):
                        summary = parsed.get('summary', [])
                        all_empty = parsed.get('all_empty', False)
                        cancelled = parsed.get('cancelled', False)
                        final_response_steps = parsed.get('final_response', '') or ''
                except json.JSONDecodeError:
                    pass
            # Kalau all_empty, suggestion di-save ke chat.response. Kalau tidak,
            # ringkasan dari inject_paper_context disimpan di search_steps.final_response.
            final_response = final_response_steps or (chat.response or '')
            result['result'] = {
                'success': db_status == 'completed',
                'summary': summary,
                'all_empty': all_empty,
                'cancelled': cancelled,
                'final_response': final_response,
                'complete': True,
            }

        if db_status == 'error':
            result['error'] = 'Pencarian gagal atau timeout.'

        return jsonify(result)
    except Exception as e:
        print(f"[SearchV2] check_status error: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/cancel_search/<int:chat_id>', methods=['POST'])
def cancel_search(chat_id):
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

        AcademicSearchSystemV2.request_cancel(chat.session_id)
        return jsonify({'cancelled': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/rename_session/<int:session_id>', methods=['POST'])
def rename_session(session_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized', 'success': False}), 401

    data = request.json or {}
    new_title = (data.get('title') or '').strip()
    if not new_title:
        return jsonify({'error': 'Title cannot be empty', 'success': False}), 400

    cs = ChatSession.query.filter_by(id=session_id, user_id=session['user_id']).first()
    if not cs or cs.feature != FEATURE:
        return jsonify({'error': 'Session not found', 'success': False}), 404

    try:
        cs.title = new_title
        db.session.commit()
        return jsonify({'success': True, 'new_title': new_title})
    except Exception as e:
        db.session.rollback()
        print(f"[SearchV2] rename error: {e}")
        return jsonify({'error': 'Internal error', 'success': False}), 500


@bp.route('/delete_session/<int:session_id>', methods=['POST'])
def delete_session(session_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized', 'success': False}), 401

    cs = ChatSession.query.filter_by(id=session_id, user_id=session['user_id']).first()
    if not cs or cs.feature != FEATURE:
        return jsonify({'error': 'Session not found', 'success': False}), 404

    try:
        chat_ids = [c.id for c in Chat.query.filter_by(session_id=session_id).all()]
        if chat_ids:
            SearchProgress.query.filter(SearchProgress.chat_id.in_(chat_ids)) \
                .delete(synchronize_session=False)
        Chat.query.filter_by(session_id=session_id).delete()
        db.session.delete(cs)
        AcademicSearchSystemV2.clear_session(session_id)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        print(f"[SearchV2] delete error: {e}")
        return jsonify({'error': 'Internal error', 'success': False}), 500
