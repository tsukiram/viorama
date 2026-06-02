# app/gemini_client/general_knowledge.py

from google import genai
from google.genai import types
from config import Config
import json

class GeneralKnowledgeSystem:
    _agents = {}  # Class-level dictionary to store agents by session_id
    _api_key_ids = {}  # Track API key ID per session for logging

    def __init__(self, session_id):
        self.session_id = session_id
        self.api_key = None
        self.api_key_id = None
        self.client = None
        self.agent = None
        self._initialize_client()

    def _get_active_api_key(self):
        from app.models.models import APIKey
        key_entry = APIKey.query.filter_by(is_active=True).first()
        if key_entry:
            self.api_key_id = key_entry.id
            return key_entry.key
        return None

    def _get_active_model_id(self):
        from app.models.models import AIModel
        model_entry = AIModel.query.filter_by(is_active=True).first()
        return model_entry.model_id if model_entry else 'gemini-2.5-flash'

    def _get_db_setting(self, key):
        from app.models.models import Setting
        try:
            setting = Setting.query.filter_by(key=key).first()
            return setting.value if setting else None
        except:
            return None

    def _initialize_client(self):
        """Initialize or reuse the Gemini client and agent for the session."""
        if self.session_id in GeneralKnowledgeSystem._agents:
            self.agent = GeneralKnowledgeSystem._agents[self.session_id]
            self.api_key_id = GeneralKnowledgeSystem._api_key_ids.get(self.session_id)
            print(f"\nReusing existing agent for general session {self.session_id}")
        else:
            try:
                # Dynamic API Key - STRICT from APIKey table
                self.api_key = self._get_active_api_key()
                if not self.api_key:
                    raise ValueError("Active API Key not found in database (APIKey table)")

                # Dynamic Model - STRICT from AIModel table
                model_id = self._get_active_model_id()
                
                prompt_text = self._get_db_setting('general_prompt')
                if not prompt_text:
                     prompt_text = self._load_prompt('app/prompts/base_information.txt')

                self.client = genai.Client(api_key=self.api_key)
                self.agent = self.client.chats.create(
                    model=model_id,
                    config=types.GenerateContentConfig(system_instruction=prompt_text)
                )
                GeneralKnowledgeSystem._agents[self.session_id] = self.agent
                GeneralKnowledgeSystem._api_key_ids[self.session_id] = self.api_key_id
                print(f"\nGeneralKnowledgeSystem client initialized for session {self.session_id}")
            except Exception as e:
                print(f"\nError initializing client for session {self.session_id}: {e}")
                raise Exception(f"Error initializing client: {e}")

    def _load_prompt(self, filename):
        """Load prompt from file."""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Warning: {filename} not found. Using default prompt.")
            return "You are a helpful assistant for general knowledge inquiries."

    def run_interactive_session(self, user_input):
        """Run an interactive session with the Gemini API."""
        try:
            formatted_input = json.dumps([{
                "role": "user",
                "input": user_input
            }], indent=4, ensure_ascii=False)

            # Rate limit protection
            from app.gemini_client.throttler import GeminiThrottler
            GeminiThrottler.wait_if_needed()

            response = self.agent.send_message(formatted_input)


            # Log token usage
            try:
                from app.gemini_client.usage_logger import log_token_usage_sync
                usage_meta = response.usage_metadata
                if usage_meta and self.api_key_id:
                    log_token_usage_sync(
                        api_key_id=self.api_key_id,
                        input_tokens=usage_meta.prompt_token_count or 0,
                        output_tokens=usage_meta.candidates_token_count or 0,
                        session_id=self.session_id,
                        feature='general',
                        input_content=user_input,
                        output_content=response.text
                    )

            except Exception as log_err:
                print(f"[GeneralKnowledge] Could not log usage: {log_err}")

            return response.text
        except Exception as e:
            print(f"Error in interactive session for session {self.session_id}: {e}")
            return None

    def run_streaming_session(self, user_input):
        """Stream tokens dari Gemini. Yields tuples ('chunk', text) atau ('done', full_text)."""
        formatted_input = json.dumps([{
            "role": "user",
            "input": user_input
        }], indent=4, ensure_ascii=False)

        from app.gemini_client.throttler import GeminiThrottler
        GeminiThrottler.wait_if_needed()

        full_text = ""
        last_chunk = None
        try:
            stream = self.agent.send_message_stream(formatted_input)
            for chunk in stream:
                last_chunk = chunk
                piece = getattr(chunk, 'text', None) or ''
                if piece:
                    full_text += piece
                    yield ('chunk', piece)
        except Exception as e:
            if "client has been closed" in str(e).lower():
                # Client expired — clear cache and reinitialize for next request
                GeneralKnowledgeSystem.clear_session(self.session_id)
                try:
                    self._initialize_client()
                    stream2 = self.agent.send_message_stream(formatted_input)
                    for chunk in stream2:
                        last_chunk = chunk
                        piece = getattr(chunk, 'text', None) or ''
                        if piece:
                            full_text += piece
                            yield ('chunk', piece)
                except Exception as e2:
                    print(f"[GeneralKnowledge] Streaming error after reinit for session {self.session_id}: {e2}")
                    yield ('error', str(e2))
                    return
            else:
                print(f"[GeneralKnowledge] Streaming error for session {self.session_id}: {e}")
                yield ('error', str(e))
                return

        # Log token usage from final chunk metadata if available
        try:
            from app.gemini_client.usage_logger import log_token_usage_sync
            usage_meta = getattr(last_chunk, 'usage_metadata', None) if last_chunk else None
            if usage_meta and self.api_key_id:
                log_token_usage_sync(
                    api_key_id=self.api_key_id,
                    input_tokens=usage_meta.prompt_token_count or 0,
                    output_tokens=usage_meta.candidates_token_count or 0,
                    session_id=self.session_id,
                    feature='general',
                    input_content=user_input,
                    output_content=full_text
                )
        except Exception as log_err:
            print(f"[GeneralKnowledge] Could not log usage: {log_err}")

        yield ('done', full_text)

    @classmethod
    def clear_session(cls, session_id):
        """Clear the agent for the given session_id."""
        if session_id in cls._agents:
            del cls._agents[session_id]
            print(f"\nCleared agent for general session {session_id}")