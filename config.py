# config.py

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///viorama.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GEMINI_API_KEY = 'AIzaSyAStcdhr6BWTe-knJU9BwBwTuEF204xDGw'  # Replace with your actual Gemini API key