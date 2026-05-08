# app/gemini_client/searching.py

import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import re
from google import genai
from google.genai import types
from config import Config

class AcademicSearchSystem:
    _sessions = {}  # Store clients, agents, and history by session_id
    _api_key_ids = {}  # Track API key IDs per session for logging
    _cancellation_flags = {}

    @classmethod
    def request_cancel(cls, session_id):
        cls._cancellation_flags[session_id] = True

    @classmethod
    def cancel_all(cls):
        for sid in list(cls._sessions.keys()):
            cls._cancellation_flags[sid] = True

    @classmethod
    def is_cancelled(cls, session_id):
        return cls._cancellation_flags.get(session_id, False)

    @classmethod
    def clear_cancel(cls, session_id):
        cls._cancellation_flags.pop(session_id, None)

    def __init__(self, session_id):
        self.session_id = session_id
        self.api_key = None
        self.api_key_id = None
        
        self.base_url = "https://digilib.uin-suka.ac.id/cgi/search/archive/simple"
        self.discuss_client = None
        self.search_client = None
        self.discuss_agent = None
        self.search_agent = None
        self.discuss_history = []  # Track conversation history
        self.search_history = []
        self._initialize_clients()

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
        return model_entry.model_id if model_entry else 'gemini-2.5-flash'  # Fallback safe default

    def _get_db_setting(self, key):
        from app.models.models import Setting
        try:
            setting = Setting.query.filter_by(key=key).first()
            return setting.value if setting else None
        except:
            return None

    def _initialize_clients(self):
        """Initialize or reuse Gemini clients and agents for this session."""
        if self.session_id in self._sessions:
            # Ambil kembali clients, agents, DAN history dari cache
            session_data = self._sessions[self.session_id]
            self.discuss_client = session_data['discuss_client']
            self.search_client = session_data['search_client']
            self.discuss_agent = session_data['discuss_agent']
            self.search_agent = session_data['search_agent']
            self.discuss_history = session_data['discuss_history']
            self.search_history = session_data['search_history']
            self.api_key_id = self._api_key_ids.get(self.session_id)
            print("\nReusing existing session [] === ", self.session_id, " with [] === ", len(self.discuss_history), " messages in history []")
            return

        try:
            # Dynamic API Key Loading - STRICT from APIKey table
            self.api_key = self._get_active_api_key()
            if not self.api_key:
                raise ValueError("Active API Key not found in database (APIKey table)")

            # Dynamic Model Loading - STRICT from AIModel table
            model_id = self._get_active_model_id()
            if not model_id:
                raise ValueError("Active AI Model not found in database (AIModel table)")
            
            # Dynamic Prompt Loading
            discuss_prompt_text = self._get_db_setting('discuss_prompt')
            if not discuss_prompt_text:
                 discuss_prompt_text = self._load_prompt('app/prompts/discuss_client.txt')

            search_prompt_text = self._get_db_setting('search_prompt')
            if not search_prompt_text:
                search_prompt_text = self._load_prompt('app/prompts/search_client.txt')

            self.discuss_client = genai.Client(api_key=self.api_key)
            self.discuss_agent = self.discuss_client.chats.create(
                model=model_id,
                config=types.GenerateContentConfig(system_instruction=discuss_prompt_text)
            )

            self.search_client = genai.Client(api_key=self.api_key)
            self.search_agent = self.search_client.chats.create(
                model=model_id,
                config=types.GenerateContentConfig(system_instruction=search_prompt_text)
            )

            self.discuss_history = []
            self.search_history = []

            # Simpan dengan struktur dictionary untuk kejelasan
            self._sessions[self.session_id] = {
                'discuss_client': self.discuss_client,
                'search_client': self.search_client,
                'discuss_agent': self.discuss_agent,
                'search_agent': self.search_agent,
                'discuss_history': self.discuss_history,
                'search_history': self.search_history,
                'discuss_prompt': discuss_prompt_text,
                'search_prompt': search_prompt_text
            }

            self._api_key_ids[self.session_id] = self.api_key_id
            print("\nClients and agents initialized successfully for session [] === ", self.session_id, " []")

        except Exception as e:
            print("\nError initializing clients [] === ", e, " []")
            raise Exception(f"Error initializing clients: {e}")

    def _recreate_clients(self):
        """Recreate clients if they've been closed."""
        try:
            # Remove old session from cache
            if self.session_id in self._sessions:
                del self._sessions[self.session_id]
            
            # Reinitialize
            self._initialize_clients()
            print("\nClients and agents recreated for session [] === ", self.session_id, " []")
            
        except Exception as e:
            print("\nError recreating clients [] === ", e, " []")
            raise 

    def _load_prompt(self, filename):
        """Load prompt from file."""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print("Warning [] === ", filename, " not found. Using default prompt []")
            return "You are a helpful academic research assistant."

    def update_prompts(self, discuss_prompt=None, search_prompt=None):
        """Force update the system instructions for agents while maintaining history."""
        from google.genai import types
        model_id = self._get_active_model_id()
        
        session_data = self._sessions.get(self.session_id, {})
        
        if discuss_prompt and discuss_prompt != session_data.get('discuss_prompt'):
            print(f"\n[Inspector] Discuss prompt changed. Recreating agent for session {self.session_id}...")
            # Safely get history
            hist = getattr(self.discuss_agent, 'history', None)
            if hist is None:
                hist = getattr(self.discuss_agent, '_history', [])
                
            self.discuss_agent = self.discuss_client.chats.create(
                model=model_id,
                config=types.GenerateContentConfig(system_instruction=discuss_prompt),
                history=hist
            )
            self._sessions[self.session_id]['discuss_agent'] = self.discuss_agent
            self._sessions[self.session_id]['discuss_prompt'] = discuss_prompt
            
        if search_prompt and search_prompt != session_data.get('search_prompt'):
            print(f"\n[Inspector] Search prompt changed. Recreating agent for session {self.session_id}...")
            hist = getattr(self.search_agent, 'history', None)
            if hist is None:
                hist = getattr(self.search_agent, '_history', [])

            self.search_agent = self.search_client.chats.create(
                model=model_id,
                config=types.GenerateContentConfig(system_instruction=search_prompt),
                history=hist
            )
            self._sessions[self.session_id]['search_agent'] = self.search_agent
            self._sessions[self.session_id]['search_prompt'] = search_prompt




    def _update_session_cache(self):
        """Update session cache with current state."""
        if self.session_id in self._sessions:
            self._sessions[self.session_id]['discuss_history'] = self.discuss_history
            self._sessions[self.session_id]['search_history'] = self.search_history

    def search_repository(self, query, max_results=5):
        """Search repository and return list of results."""
        encoded_query = urllib.parse.quote(query)
        search_url = f"{self.base_url}?screen=Search&dataset=archive&order=&q={encoded_query}&_action_search=Search"

        try:
            response = requests.get(search_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            results = []
            items = soup.find_all('tr', class_='ep_search_result')

            for item in items[:max_results]:
                title_elem = item.find('a', href=True)
                if title_elem:
                    link = urllib.parse.urljoin(self.base_url, title_elem['href'])
                    results.append({"link": link})

            if not results:
                print("No results found for keyword [] === ", query, " []")
                return []

            return results

        except requests.RequestException as e:
            print("Error searching repository [] === ", e, " []")
            return []

    def extract_metadata(self, html_content):
        """Extract metadata from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')

        citation_elem = soup.find('p', style=re.compile(r'margin-bottom:\s*1em'))
        citation = citation_elem.get_text(strip=True) if citation_elem else "No citation available"

        abstract_elem = soup.find('h2', string=re.compile(r'Abstract', re.IGNORECASE))
        abstract = "No abstract available"
        if abstract_elem:
            abstract_p = abstract_elem.find_next('p')
            if abstract_p:
                abstract = abstract_p.get_text(strip=True)

        uri_meta = soup.find('meta', attrs={'name': 'eprints.eprintid'})
        code = uri_meta['content'].strip() if uri_meta else "No code available"

        return {
            "citation": citation,
            "abstract": abstract,
            "code": code
        }

    def fetch_metadata(self, search_results):
        """Fetch metadata for each search result."""
        metadata_list = []

        for result in search_results:
            try:
                response = requests.get(result["link"], timeout=10)
                response.raise_for_status()
                metadata = self.extract_metadata(response.text)
                metadata_list.append(metadata)

            except requests.RequestException as e:
                print("Error fetching metadata [] === ", e, " []")
                continue

        return metadata_list

    def search_papers(self, query):
        """Complete search process: search repository and fetch metadata."""
        print("\nSearching for keyword [] === ", query, " []")
        search_results = self.search_repository(query)

        if not search_results:
            return []

        metadata_list = self.fetch_metadata(search_results)
        return metadata_list

    def extract_json_from_response(self, response_text):
        """Extract JSON content from Markdown response."""
        json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
        if json_match:
            return json_match.group(1)
        return response_text

    def process_search_response(self, response_text):
        """Process response from search agent."""
        try:
            clean_text = self.extract_json_from_response(response_text)
            response_data = json.loads(clean_text)

            keyword = ""
            for item in response_data:
                if item.get("role") == "keyword":
                    keyword = item.get("output", "")
                    break

            should_search = any(
                item.get("role") == "options" and item.get("search", False)
                for item in response_data
            )

            should_add_paper = any(
                item.get("role") == "options" and item.get("add_paper", False)
                for item in response_data
            )

            add_paper_codes = []
            if should_add_paper:
                for item in response_data:
                    if item.get("role") == "add_paper":
                        add_paper_codes = item.get("output", [])
                        break

            return should_search, keyword, add_paper_codes

        except json.JSONDecodeError as e:
            print("Error parsing JSON response [] === ", e, " []")
            print("Response content [] === ", response_text, " []")
            return False, "", []

    def process_search_request(self, user_input, chat_id=None, app_context=None):
        """
        Process search request using search agent.
        Now a generator that saves to DB and yields updates.
        Saves structured steps: {'msg': '...', 'status': '...'}
        """
        print(f"Analyzing request [ChatID: {chat_id}]")
        search_updates = []

        # Initial Update
        step = {"msg": "Analyzing request...", "status": "processing"}
        search_updates.append(step)
        yield {"update": step, "status": "processing"}

        # Add to search history
        self.search_history.append({"role": "user", "input": user_input})

        try:
            while True:
                if AcademicSearchSystem.is_cancelled(self.session_id):
                    yield {"error": "Search cancelled by user"}
                    return

                # Rate limit protection
                from app.gemini_client.throttler import GeminiThrottler
                GeminiThrottler.wait_if_needed()

                response = self.search_agent.send_message(user_input)

                self.search_history.append({"role": "agent", "output": response.text})
                
                # Log token usage for search agent
                try:
                    from app.gemini_client.usage_logger import log_token_usage_sync
                    usage_meta = response.usage_metadata
                    if usage_meta and self.api_key_id:
                        if app_context:
                            with app_context:
                                log_token_usage_sync(
                                    api_key_id=self.api_key_id,
                                    input_tokens=usage_meta.prompt_token_count or 0,
                                    output_tokens=usage_meta.candidates_token_count or 0,
                                    session_id=self.session_id,
                                    feature='search',
                                    input_content=user_input,
                                    output_content=response.text
                                )
                        else:
                            log_token_usage_sync(
                                api_key_id=self.api_key_id,
                                input_tokens=usage_meta.prompt_token_count or 0,
                                output_tokens=usage_meta.candidates_token_count or 0,
                                session_id=self.session_id,
                                feature='search',
                                input_content=user_input,
                                output_content=response.text
                            )
                except Exception as log_err:
                    print(f"[AcademicSearch] Could not log search usage: {log_err}")

                
                should_search, keyword, add_paper_codes = self.process_search_response(response.text)

                
                # Mark previous steps as completed before moving on is tricky because simple list;
                # for now we assume appended steps are the active ones.
                # Actually user wants "status setiap step", so let's mark the previous one as done?
                # Simpler: just append new steps. The latest one is usually "processing".
                
                if len(search_updates) > 0:
                     search_updates[-1]['status'] = 'completed'

                if should_search and keyword:
                    step = {"msg": f"Searching for keyword: {keyword}", "status": "processing"}
                    search_updates.append(step)
                    yield {"update": step, "status": "processing"}

                    search_results = self.search_papers(keyword)
                    
                    search_updates[-1]['status'] = 'completed'

                    if search_results:
                        step = {"msg": f"Search results found: {len(search_results)}", "status": "completed"}
                        search_updates.append(step)
                        yield {"update": step, "status": "processing"}
                    else:
                        step = {"msg": f"No results found for keyword: {keyword}", "status": "warning"}
                        search_updates.append(step)
                        yield {"update": step, "status": "processing"}

                    step = {"msg": "Analyzing search results and selecting relevant papers...", "status": "processing"}
                    search_updates.append(step)
                    yield {"update": step, "status": "processing"}

                    search_results_json = json.dumps(search_results, indent=4, ensure_ascii=False)
                    user_input = json.dumps([{
                        "role": "search_result",
                        "input": search_results_json
                    }])
                else:
                    step = {"msg": "Search completed.", "status": "completed"}
                    search_updates.append(step)
                    yield {"update": step, "status": "completed"}
                    
                    # Update cache
                    self._update_session_cache()
                    
                    # Return final result (via yield)
                    yield {
                        "complete": True, 
                        "paper_codes": add_paper_codes, 
                        "search_steps": search_updates
                    }
                    return

        except Exception as e:
            step = {"msg": f"Error during search: {str(e)}", "status": "error"}
            search_updates.append(step)
            yield {"error": str(e), "search_updates": search_updates}
            raise e

    def process_discuss_response(self, response_text):
        """Process response from discuss agent with improved error handling."""
        json_pattern = r'```json(.*?)```'
        matches = re.findall(json_pattern, response_text, re.DOTALL)

        if not matches:
            json_pattern = r'\{[\s\S]*?\}'
            matches = re.findall(json_pattern, response_text)

            if not matches:
                print("No JSON pattern found, returning raw response as user_output []")
                return response_text.strip(), None, None

        try:
            json_string = matches[0].strip()
            json_string = re.sub(r',\s*}', '}', json_string)
            json_string = re.sub(r',\s*]', ']', json_string)

            json_data = json.loads(json_string)

            if isinstance(json_data, list):
                data_list = json_data
            else:
                data_list = [json_data]

            user_output = ""
            system_output = ""

            for item in data_list:
                if isinstance(item, dict):
                    if item.get("role") == "user":
                        user_output = item.get("output", "")
                    elif item.get("role") == "system":
                        system_output = item.get("output", "")

            return user_output, system_output, None

        except json.JSONDecodeError as e:
            print("JSON decode error [] === ", e, " []")
            print("Trying to parse [] === ", json_string if 'json_string' in locals() else 'N/A', " []")
            print("Raw response [] === ", response_text, " []")
            return response_text.strip(), None, f"JSON decode error: {e}"
        
    def run_interactive_session(self, user_input):
        """Run interactive discussion session with conversation history."""
        max_retries = 2
        retry_count = 0
        error_msg = ""
        
        while retry_count < max_retries:
            try:
                # Format input dengan history context
                formatted_input = json.dumps([{
                    "role": "user",
                    "input": user_input
                }], indent=4, ensure_ascii=False)

                # Tambahkan ke history SEBELUM mengirim
                self.discuss_history.append({
                    "role": "user",
                    "content": user_input
                })

                # Rate limit protection
                from app.gemini_client.throttler import GeminiThrottler
                GeminiThrottler.wait_if_needed()

                # Kirim ke agent (agent sudah otomatis menyimpan history internal)
                response = self.discuss_agent.send_message(formatted_input)

                
                # Process response
                user_output, system_output, error = self.process_discuss_response(response.text)
                
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
                            feature='discuss',
                            input_content=user_input,
                            output_content=user_output if user_output else response.text
                        )
                except Exception as log_err:
                    print(f"[AcademicSearch] Could not log usage: {log_err}")

                
                # Tambahkan response ke history
                self.discuss_history.append({
                    "role": "assistant",
                    "content": user_output if user_output else response.text
                })

                # Update cache
                self._update_session_cache()

                print("\n[History] Total messages in session [] === ", len(self.discuss_history), " []")
                print("[History] user_output [] === ", user_output[:100] if user_output else 'None', "... []")

                if error:
                    print("Error in discuss response [] === ", error, " []")
                    return "", f"Error processing response: {error}", [], []

                search_steps = []
                add_paper_codes = []

                return system_output, user_output, add_paper_codes, search_steps

            except Exception as e:
                error_msg = str(e)
                print("An error occurred in run_interactive_session [] === ", error_msg, " []")
                
                if "closed" in error_msg.lower() and retry_count < max_retries - 1:
                    print("Attempting to recreate clients (attempt [] === ", retry_count + 1, "/", max_retries, ") []")
                    try:
                        self._recreate_clients()
                        retry_count += 1
                        continue
                    except Exception as recreate_error:
                        print("Failed to recreate clients [] === ", recreate_error, " []")
                        break
                else:
                    break
        
        return "", f"An error occurred: {error_msg}", [], []

    def load_history_from_db(self, chats):
        """Load conversation history from database and restore agent context."""
        print("\n[Load History] Loading [] === ", len(chats), " messages from database []")

        # Hanya load jika history masih kosong (agent baru dibuat)
        if len(self.discuss_history) > 0:
            print("[Load History] History already loaded, skipping []")
            return

        for chat in chats:
            if chat.user_id:  # User message
                user_msg = {
                    "role": "user",
                    "content": chat.message
                }
                self.discuss_history.append(user_msg)

                # Re-send ke agent untuk rebuild context
                formatted_input = json.dumps([{
                    "role": "user",
                    "input": chat.message
                }], indent=4, ensure_ascii=False)

                try:
                    # PENTING: Kirim dan tunggu response untuk maintain context
                    response = self.discuss_agent.send_message(formatted_input)
                    print("[Load History] Loaded user message [] === ", chat.message[:50], "... []")
                except Exception as e:
                    print("[Load History] Error loading message [] === ", e, " []")
                    pass

            else:  # AI response - hanya tambah ke history lokal, tidak perlu send
                ai_msg = {
                    "role": "assistant",
                    "content": chat.response
                }
                self.discuss_history.append(ai_msg)

                # Re-inject paper_context (list of paper codes pernah dibahas) ke
                # discuss_agent agar agent ingat paper yang disarankan sesi lalu.
                # Tanpa ini, follow-up seperti "jelaskan paper #2" kehilangan konteks
                # setelah cache RAM hilang (restart server).
                if chat.search_steps:
                    try:
                        raw = json.loads(chat.search_steps)
                        paper_codes = raw.get('paper_context') if isinstance(raw, dict) else None
                        if paper_codes:
                            system_input = json.dumps([{
                                "role": "system",
                                "input": json.dumps(paper_codes, indent=4, ensure_ascii=False)
                            }], indent=4, ensure_ascii=False)
                            try:
                                self.discuss_agent.send_message(system_input)
                                print("[Load History] Restored paper_context [] === ", len(paper_codes), " codes []")
                            except Exception as ctx_err:
                                print("[Load History] Error injecting paper_context [] === ", ctx_err, " []")
                    except (json.JSONDecodeError, AttributeError):
                        pass

        # Update cache after loading
        self._update_session_cache()
        print("[Load History] Successfully loaded [] === ", len(self.discuss_history), " messages []")

    @classmethod
    def clear_session(cls, session_id):
        """Clear session data for a specific session."""
        if session_id in cls._sessions:
            del cls._sessions[session_id]
            print("\nCleared session [] === ", session_id, " []")

    @classmethod
    def get_session_message_count(cls, session_id):
        """Get the number of messages in a session's history."""
        if session_id in cls._sessions:
            return len(cls._sessions[session_id]['discuss_history'])
        return 0
