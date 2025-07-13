# app/gemini_client/general_knowledge.py

from google import genai
from google.genai import types
from config import Config
import json

class GeneralKnowledgeSystem:
    _agents = {}  # Class-level dictionary to store agents by session_id

    def __init__(self, session_id):
        self.api_key = Config.GEMINI_API_KEY
        self.session_id = session_id
        self.client = None
        self.agent = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize or reuse the Gemini client and agent for the session."""
        if self.session_id in GeneralKnowledgeSystem._agents:
            self.agent = GeneralKnowledgeSystem._agents[self.session_id]
            print(f"\n✓ Reusing existing agent for general session {self.session_id}")
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
                prompt = self._load_prompt('app/prompts/base_information.txt')
                self.agent = self.client.chats.create(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(system_instruction=prompt)
                )
                GeneralKnowledgeSystem._agents[self.session_id] = self.agent
                print(f"\n✓ GeneralKnowledgeSystem client initialized for session {self.session_id}")
            except Exception as e:
                print(f"\n✗ Error initializing client for session {self.session_id}: {e}")
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
            response = self.agent.send_message(formatted_input)
            return response.text
        except Exception as e:
            print(f"Error in interactive session for session {self.session_id}: {e}")
            return None

    @classmethod
    def clear_session(cls, session_id):
        """Clear the agent for the given session_id."""
        if session_id in cls._agents:
            del cls._agents[session_id]
            print(f"\n✓ Cleared agent for general session {session_id}")