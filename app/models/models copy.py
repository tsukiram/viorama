# app/models/models.py

from app import db
from datetime import datetime
import json

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    chats = db.relationship('Chat', backref='user', lazy=True)
    saved_papers = db.relationship('SavedPaper', backref='user', lazy=True)
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True)

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feature = db.Column(db.String(50), nullable=False)  # 'general' or 'search'
    title = db.Column(db.String(100), nullable=False)   # Title for the session
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    chats = db.relationship('Chat', backref='session', lazy=True)

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feature = db.Column(db.String(50), nullable=False)  # 'general' or 'search'
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    search_steps = db.Column(db.Text, nullable=True)    # JSON string for search steps
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class SavedPaper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    eprint_code = db.Column(db.String(50), nullable=False)
    title = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)