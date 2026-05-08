# /app/models/models.py

from app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    chats = db.relationship('Chat', backref='user', lazy=True)
    saved_papers = db.relationship('SavedPaper', backref='user', lazy=True)
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True)

class ChatSession(db.Model):
    __tablename__ = 'chat_session'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feature = db.Column(db.String(50), nullable=False)  # 'general' or 'search'
    title = db.Column(db.String(100), nullable=False)   # Title for the session
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    chats = db.relationship('Chat', backref='session', lazy=True)

class Chat(db.Model):
    __tablename__ = 'chat'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Allow null for assistant messages
    feature = db.Column(db.String(50), nullable=False)  # 'general' or 'search'
    message = db.Column(db.Text, nullable=True)         # Allow null for assistant messages
    response = db.Column(db.Text, nullable=True)        # Allow null for user messages
    search_steps = db.Column(db.Text, nullable=True)    # JSON string for search steps
    search_status = db.Column(db.String(50), default='pending') # pending, processing, completed, error
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class SavedPaper(db.Model):
    __tablename__ = 'saved_paper'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    eprint_code = db.Column(db.String(50), nullable=False)
    title = db.Column(db.Text, nullable=False)

class Setting(db.Model):
    __tablename__ = 'setting'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

class APIKey(db.Model):
    __tablename__ = 'api_key'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(200), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AIModel(db.Model):
    __tablename__ = 'ai_model'
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=False)

class APIKeyUsage(db.Model):
    __tablename__ = 'api_key_usage'
    id = db.Column(db.Integer, primary_key=True)
    api_key_id = db.Column(db.Integer, db.ForeignKey('api_key.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=True)  # Can be null for non-session calls
    feature = db.Column(db.String(50), nullable=True)  # 'search', 'general', 'title'
    date = db.Column(db.Date, nullable=False)
    input_tokens = db.Column(db.Integer, default=0)
    output_tokens = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    input_content = db.Column(db.Text, nullable=True)
    output_content = db.Column(db.Text, nullable=True)
    request_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    
    api_key = db.relationship('APIKey', backref=db.backref('usage_logs', lazy=True))
    session = db.relationship('ChatSession', backref=db.backref('token_usage', lazy=True))


class SearchProgress(db.Model):
    __tablename__ = 'search_progress'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'), nullable=False, index=True)
    step_number = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='processing')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    chat = db.relationship('Chat', backref=db.backref('progress_steps', lazy='dynamic',
                           order_by='SearchProgress.step_number'))

    __table_args__ = (
        db.UniqueConstraint('chat_id', 'step_number', name='uq_chat_step'),
    )