# app/gemini_client/title_generator.py

import re
from google import genai
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TitleGenerator:
    """Generate concise titles from chat messages using Gemini API."""

    @classmethod
    def generate_title(cls, message):
        """Generate a short 2-3 word title from the first message."""
        logger.info("[TitleGenerator] Starting title generation for message: '%s%s'",
                    message[:100], '...' if len(message) > 100 else '')
        
        try:
            from flask import has_app_context
            if not has_app_context():
                return cls._fallback_title(message)

            from app.models.models import APIKey, AIModel, Setting

            key_entry = APIKey.query.filter_by(is_active=True).first()
            api_key = key_entry.key if key_entry else None
            
            if not api_key:
                logger.error("[TitleGenerator] No Active API Key found in APIKey table. Using fallback title.")
                return cls._fallback_title(message)

            model_entry = AIModel.query.filter_by(is_active=True).first()
            model_id = model_entry.model_id if model_entry else 'gemini-2.5-flash'  # Fallback
            
            custom_prompt_setting = Setting.query.filter_by(key='title_prompt').first()
            custom_prompt = custom_prompt_setting.value if custom_prompt_setting else None

            # Initialize client
            client = genai.Client(api_key=api_key)
            logger.info("[TitleGenerator] Gemini client initialized")

            # Create prompt
            if custom_prompt:
                prompt = f"{custom_prompt}\n\nMessage: {message}\n\nTitle:"
            else:
                prompt = f"""You are an expert title generator. Create a very short 2-3 word title from this message.

Rules:
- Output ONLY 2-3 words
- NO prefixes, quotes, or explanations
- Use the SAME language as the message
- Extract ONLY the core topic

Message: {message}

Title:"""
            
            
            logger.info("[TitleGenerator] Sending prompt to Gemini")
            
            # Rate limit protection
            from app.gemini_client.throttler import GeminiThrottler
            GeminiThrottler.wait_if_needed()

            # Generate content
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )

            
            logger.info("[TitleGenerator] Response received")
            
            # Log token usage
            try:
                from app.gemini_client.usage_logger import log_token_usage_sync
                usage_meta = response.usage_metadata
                if usage_meta and key_entry:
                    log_token_usage_sync(
                        api_key_id=key_entry.id,
                        input_tokens=usage_meta.prompt_token_count or 0,
                        output_tokens=usage_meta.candidates_token_count or 0,
                        session_id=None,  # Title generation happens before session exists
                        feature='title',
                        input_content=prompt,
                        output_content=response.text
                    )

            except Exception as log_err:
                logger.warning(f"[TitleGenerator] Could not log usage: {log_err}")
            
            # Extract title
            raw_title = response.text
            logger.info("[TitleGenerator] Raw title: '%s'", raw_title)

            if not raw_title:
                logger.warning("[TitleGenerator] Empty response, using fallback")
                return cls._fallback_title(message)

            # Clean title.,45
            title = raw_title.strip().strip('"\'*:')
            title = re.sub(r'^(Title:|Judul:)\s*', '', title, flags=re.IGNORECASE)
            
            word_count = len(title.split())
            logger.info("[TitleGenerator] Cleaned title: '%s' (%d words)", title, word_count)

            # Validate word count
            if word_count > 4:
                title = ' '.join(title.split()[:4])
                logger.info("[TitleGenerator] Truncated to: '%s'", title)
            elif word_count < 1 or not title:
                logger.warning("[TitleGenerator] Invalid title, using fallback")
                return cls._fallback_title(message)

            logger.info("[TitleGenerator] Final title: '%s'", title)
            return title

        except Exception as e:
            logger.error("[TitleGenerator] Error: %s", e, exc_info=True)
            return cls._fallback_title(message)

    @staticmethod
    def _fallback_title(message):
        """Create a simple fallback title from the message."""
        clean_message = re.sub(r'[^\w\s]', '', message)
        words = [w for w in clean_message.split() if len(w) > 2][:3]
        
        if not words:
            words = clean_message.split()[:3]
        
        if not words:
            logger.info("[TitleGenerator] Fallback: 'Chat Baru'")
            return "Chat Baru"
        
        title = ' '.join(words).capitalize()
        logger.info("[TitleGenerator] Fallback: '%s'", title)
        return title