# app/gemini_client/usage_logger.py

from datetime import date, datetime
from flask import current_app

def log_token_usage_sync(api_key_id, input_tokens=0, output_tokens=0, session_id=None, feature=None, input_content=None, output_content=None):

    """
    Log token usage for the given API key.
    Now supports per-session tracking.
    """
    if not api_key_id:
        return
    
    try:
        from app import db
        from app.models.models import APIKeyUsage
        
        today = date.today()
        
        # Create new record for each call (no upsert, individual tracking)
        usage = APIKeyUsage(
            api_key_id=api_key_id,
            session_id=session_id,
            feature=feature,
            date=today,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_content=input_content,
            output_content=output_content,
            request_count=1,
            created_at=datetime.utcnow()

        )
        db.session.add(usage)
        db.session.commit()
        
        session_info = f", session={session_id}" if session_id else ""
        feature_info = f", feature={feature}" if feature else ""
        print(f"[UsageLogger] Logged {input_tokens + output_tokens} tokens for key {api_key_id}{session_info}{feature_info}")
    except Exception as e:
        print(f"[UsageLogger] Error logging usage: {e}")
