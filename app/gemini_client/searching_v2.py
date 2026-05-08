# app/gemini_client/searching_v2.py
#
# Paper Search v2 — flow yang lebih simple dari v1:
# - Discuss agent: longgar (max ~2 konfirmasi), prompt static dari file
# - Search agent: sekali jalan, hanya generate batch keyword (utama + tambahan)
# - Iterasi keyword & search dilakukan oleh process_keyword_search (bukan agent loop)
# - Hasil tiap keyword di-yield apa adanya untuk streaming ke frontend
#
# Tidak share state apapun dengan v1 (AcademicSearchSystem).

import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import re
from google import genai
from google.genai import types


class AcademicSearchSystemV2:
    _sessions = {}            # cache per session_id
    _api_key_ids = {}         # api_key_id per session (untuk logging)
    _cancellation_flags = {}

    BASE_URL = "https://digilib.uin-suka.ac.id/cgi/search/archive/simple"

    # ---------------- Helpers ----------------
    @staticmethod
    def _norm_sid(session_id):
        """Normalize session_id to int for stable cache keys.

        Frontend POSTs session_id sebagai string (HTML data attribute),
        tetapi session baru dibuat dengan int (chat_session.id). Tanpa
        normalisasi ini, cache `_sessions` miss tiap follow-up → agent
        fresh setiap request → history hilang.
        """
        try:
            return int(session_id)
        except (TypeError, ValueError):
            return session_id

    # ---------------- Cancellation flags ----------------
    @classmethod
    def request_cancel(cls, session_id):
        cls._cancellation_flags[cls._norm_sid(session_id)] = True

    @classmethod
    def cancel_all(cls):
        for sid in list(cls._sessions.keys()):
            cls._cancellation_flags[sid] = True

    @classmethod
    def is_cancelled(cls, session_id):
        return cls._cancellation_flags.get(cls._norm_sid(session_id), False)

    @classmethod
    def clear_cancel(cls, session_id):
        cls._cancellation_flags.pop(cls._norm_sid(session_id), None)

    @classmethod
    def clear_session(cls, session_id):
        sid = cls._norm_sid(session_id)
        cls._sessions.pop(sid, None)
        cls._api_key_ids.pop(sid, None)
        cls._cancellation_flags.pop(sid, None)

    # ---------------- Init / clients ----------------
    def __init__(self, session_id):
        self.session_id = self._norm_sid(session_id)
        self.api_key = None
        self.api_key_id = None
        self.discuss_client = None
        self.search_client = None
        self.discuss_agent = None
        self.search_agent = None
        self.discuss_history = []
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
        return model_entry.model_id if model_entry else 'gemini-2.5-flash'

    def _load_prompt(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"[SearchV2] Prompt file not found: {filename}")
            return "You are a helpful academic research assistant."

    def _initialize_clients(self):
        if self.session_id in self._sessions:
            data = self._sessions[self.session_id]
            self.discuss_client = data['discuss_client']
            self.search_client = data['search_client']
            self.discuss_agent = data['discuss_agent']
            self.search_agent = data['search_agent']
            self.discuss_history = data['discuss_history']
            self.api_key_id = self._api_key_ids.get(self.session_id)
            print(f"[SearchV2] Reusing session {self.session_id} ({len(self.discuss_history)} msgs)")
            return

        self.api_key = self._get_active_api_key()
        if not self.api_key:
            raise ValueError("Active API Key not found in database (APIKey table)")

        model_id = self._get_active_model_id()
        if not model_id:
            raise ValueError("Active AI Model not found in database (AIModel table)")

        # Static prompts — TIDAK pakai Setting table (sengaja, isolasi dari v1).
        discuss_prompt = self._load_prompt('app/prompts/discuss_client_v2.txt')
        search_prompt = self._load_prompt('app/prompts/search_client_v2.txt')

        self.discuss_client = genai.Client(api_key=self.api_key)
        self.discuss_agent = self.discuss_client.chats.create(
            model=model_id,
            config=types.GenerateContentConfig(system_instruction=discuss_prompt),
        )

        self.search_client = genai.Client(api_key=self.api_key)
        self.search_agent = self.search_client.chats.create(
            model=model_id,
            config=types.GenerateContentConfig(system_instruction=search_prompt),
        )

        self.discuss_history = []

        self._sessions[self.session_id] = {
            'discuss_client': self.discuss_client,
            'search_client': self.search_client,
            'discuss_agent': self.discuss_agent,
            'search_agent': self.search_agent,
            'discuss_history': self.discuss_history,
        }
        self._api_key_ids[self.session_id] = self.api_key_id
        print(f"[SearchV2] Clients initialized for session {self.session_id}")

    def _recreate_clients(self):
        self._sessions.pop(self.session_id, None)
        self._initialize_clients()

    def _update_session_cache(self):
        if self.session_id in self._sessions:
            self._sessions[self.session_id]['discuss_history'] = self.discuss_history

    # ---------------- Repository search helpers ----------------
    def search_repository(self, query, max_results=None):
        """Fetch all matching paper links from Digilib for `query`.

        max_results=None means no cap (ambil semua hasil dari halaman pertama).
        """
        encoded = urllib.parse.quote(query)
        url = f"{self.BASE_URL}?screen=Search&dataset=archive&order=&q={encoded}&_action_search=Search"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')

            results = []
            items = soup.find_all('tr', class_='ep_search_result')
            iterable = items if max_results is None else items[:max_results]
            for item in iterable:
                a = item.find('a', href=True)
                if a:
                    link = urllib.parse.urljoin(self.BASE_URL, a['href'])
                    results.append({"link": link})
            return results
        except requests.RequestException as e:
            print(f"[SearchV2] Repository search error for '{query}': {e}")
            return []

    def extract_metadata(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        cite = soup.find('p', style=re.compile(r'margin-bottom:\s*1em'))
        citation = cite.get_text(strip=True) if cite else "No citation available"

        abstract = "No abstract available"
        ab_h2 = soup.find('h2', string=re.compile(r'Abstract', re.IGNORECASE))
        if ab_h2:
            ab_p = ab_h2.find_next('p')
            if ab_p:
                abstract = ab_p.get_text(strip=True)

        meta = soup.find('meta', attrs={'name': 'eprints.eprintid'})
        code = meta['content'].strip() if meta else ""

        return {"citation": citation, "abstract": abstract, "code": code}

    def fetch_metadata(self, search_results):
        out = []
        for r in search_results:
            try:
                resp = requests.get(r["link"], timeout=10)
                resp.raise_for_status()
                out.append(self.extract_metadata(resp.text))
            except requests.RequestException as e:
                print(f"[SearchV2] fetch_metadata error: {e}")
                continue
        return out

    def search_papers(self, query):
        results = self.search_repository(query)
        if not results:
            return []
        return self.fetch_metadata(results)

    # ---------------- Response parsing ----------------
    def _extract_json_block(self, text):
        m = re.search(r'```json\n([\s\S]*?)\n```', text)
        return m.group(1) if m else text

    def process_discuss_response(self, response_text):
        """Parse discuss agent output. Returns (user_output, system_output, error)."""
        json_pattern = r'```json(.*?)```'
        matches = re.findall(json_pattern, response_text, re.DOTALL)
        if not matches:
            json_pattern = r'\{[\s\S]*?\}'
            matches = re.findall(json_pattern, response_text)
            if not matches:
                return response_text.strip(), None, None

        try:
            js = matches[0].strip()
            js = re.sub(r',\s*}', '}', js)
            js = re.sub(r',\s*]', ']', js)
            data = json.loads(js)

            data_list = data if isinstance(data, list) else [data]
            user_output = ""
            system_output = ""
            for item in data_list:
                if not isinstance(item, dict):
                    continue
                if item.get("role") == "user":
                    user_output = item.get("output", "")
                elif item.get("role") == "system":
                    system_output = item.get("output", "")
            return user_output, system_output, None
        except json.JSONDecodeError as e:
            print(f"[SearchV2] discuss JSON parse error: {e}")
            return response_text.strip(), None, f"JSON decode error: {e}"

    def process_keyword_response(self, response_text):
        """Parse search agent output. Returns dict {utama: [...], tambahan: [...]}."""
        try:
            clean = self._extract_json_block(response_text)
            data = json.loads(clean)
            utama, tambahan = [], []
            for item in data:
                role = item.get("role")
                out = item.get("output", [])
                if not isinstance(out, list):
                    continue
                cleaned = [str(k).strip() for k in out if str(k).strip()]
                if role == "keywords_utama":
                    utama = cleaned
                elif role == "keywords_tambahan":
                    tambahan = cleaned

            # Cap counts (defensive — prompt sudah membatasi).
            utama = utama[:3]
            tambahan = tambahan[:3]

            # Dedup tambahan vs utama (case-insensitive).
            utama_lc = {k.lower() for k in utama}
            tambahan = [k for k in tambahan if k.lower() not in utama_lc]
            return {"utama": utama, "tambahan": tambahan}
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"[SearchV2] keyword JSON parse error: {e} | raw: {response_text[:200]}")
            return {"utama": [], "tambahan": []}

    # ---------------- Discuss agent (interactive) ----------------
    def run_interactive_session(self, user_input):
        """Send user message to discuss agent. Returns (system_output, user_output, error)."""
        max_retries = 2
        retry = 0
        last_err = ""

        while retry < max_retries:
            try:
                formatted = json.dumps([{"role": "user", "input": user_input}],
                                        indent=4, ensure_ascii=False)

                self.discuss_history.append({"role": "user", "content": user_input})

                from app.gemini_client.throttler import GeminiThrottler
                GeminiThrottler.wait_if_needed()

                response = self.discuss_agent.send_message(formatted)
                user_output, system_output, error = self.process_discuss_response(response.text)

                # Token usage logging
                try:
                    from app.gemini_client.usage_logger import log_token_usage_sync
                    usage = response.usage_metadata
                    if usage and self.api_key_id:
                        log_token_usage_sync(
                            api_key_id=self.api_key_id,
                            input_tokens=usage.prompt_token_count or 0,
                            output_tokens=usage.candidates_token_count or 0,
                            session_id=self.session_id,
                            feature='discuss_v2',
                            input_content=user_input,
                            output_content=user_output if user_output else response.text,
                        )
                except Exception as log_err:
                    print(f"[SearchV2] usage log error: {log_err}")

                self.discuss_history.append({
                    "role": "assistant",
                    "content": user_output if user_output else response.text,
                })
                self._update_session_cache()

                if error:
                    return "", f"Error processing response: {error}", error
                return system_output or "", user_output or "", None

            except Exception as e:
                last_err = str(e)
                print(f"[SearchV2] discuss send error: {last_err}")
                if "closed" in last_err.lower() and retry < max_retries - 1:
                    try:
                        self._recreate_clients()
                        retry += 1
                        continue
                    except Exception as rec_err:
                        print(f"[SearchV2] recreate error: {rec_err}")
                        break
                break

        return "", f"An error occurred: {last_err}", last_err

    # ---------------- Search flow (generator) ----------------
    def process_keyword_search(self, user_description, chat_id=None, app_context=None):
        """Generator: ask search agent for keywords, then iterate over each keyword.

        Yields events:
          - {"section": "utama"|"tambahan"}
          - {"keyword_result": {"keyword": str, "kw_type": str, "count": int, "results": [...]}}
          - {"complete": True, "all_empty": bool, "summary": [...]}
          - {"error": str}
        """
        try:
            # 1. Generate batch keyword (sekali jalan, no loop)
            from app.gemini_client.throttler import GeminiThrottler
            GeminiThrottler.wait_if_needed()

            agent_input = json.dumps([{"role": "user_description", "input": user_description}],
                                      indent=4, ensure_ascii=False)
            response = self.search_agent.send_message(agent_input)

            try:
                from app.gemini_client.usage_logger import log_token_usage_sync
                usage = response.usage_metadata
                if usage and self.api_key_id:
                    if app_context:
                        with app_context:
                            log_token_usage_sync(
                                api_key_id=self.api_key_id,
                                input_tokens=usage.prompt_token_count or 0,
                                output_tokens=usage.candidates_token_count or 0,
                                session_id=self.session_id,
                                feature='search_v2',
                                input_content=user_description,
                                output_content=response.text,
                            )
                    else:
                        log_token_usage_sync(
                            api_key_id=self.api_key_id,
                            input_tokens=usage.prompt_token_count or 0,
                            output_tokens=usage.candidates_token_count or 0,
                            session_id=self.session_id,
                            feature='search_v2',
                            input_content=user_description,
                            output_content=response.text,
                        )
            except Exception as log_err:
                print(f"[SearchV2] keyword usage log error: {log_err}")

            keywords = self.process_keyword_response(response.text)
            utama = keywords.get("utama", [])
            tambahan = keywords.get("tambahan", [])

            if not utama and not tambahan:
                yield {"error": "Search agent tidak menghasilkan kata kunci. Coba ulangi pencarian."}
                return

            # 2. Iterate utama → tambahan
            summary = []  # accumulate for final discuss agent context
            had_any_result = False

            sections = [("utama", utama), ("tambahan", tambahan)]
            for section_name, kw_list in sections:
                if not kw_list:
                    continue
                if AcademicSearchSystemV2.is_cancelled(self.session_id):
                    yield {"error": "Search cancelled by user"}
                    return

                yield {"section": section_name}

                for kw in kw_list:
                    if AcademicSearchSystemV2.is_cancelled(self.session_id):
                        yield {"error": "Search cancelled by user"}
                        return

                    results = self.search_papers(kw)
                    if results:
                        had_any_result = True

                    summary.append({
                        "keyword": kw,
                        "kw_type": section_name,
                        "count": len(results),
                        "results": results,
                    })
                    yield {"keyword_result": {
                        "keyword": kw,
                        "kw_type": section_name,
                        "count": len(results),
                        "results": results,
                    }}

            yield {
                "complete": True,
                "all_empty": (not had_any_result),
                "summary": summary,
            }

        except Exception as e:
            print(f"[SearchV2] keyword search error: {e}")
            import traceback
            traceback.print_exc()
            yield {"error": str(e)}

    # ---------------- Inject search summary to discuss agent ----------------
    def inject_paper_context(self, summary, app_context=None):
        """Send the FULL search summary (keywords tried + papers found) to discuss agent.

        Discuss agent jadi tahu:
        - Kata kunci apa saja yang sudah dicoba (utama vs tambahan)
        - Berapa hasil tiap keyword (termasuk yang 0)
        - Daftar lengkap paper unik yang ditemukan beserta keyword penemunya

        Tujuannya supaya pertanyaan lanjutan user dijawab dengan konteks penuh.
        Response discuss agent dibuang — frontend sudah render hasil.
        """
        if not summary:
            return

        # Build keyword history (semua keyword, termasuk 0 hasil)
        keyword_history = []
        for entry in summary:
            keyword_history.append({
                "keyword": entry.get("keyword", ""),
                "kw_type": entry.get("kw_type", ""),
                "count": entry.get("count", 0),
            })

        # Flatten unique papers (dedup by code)
        seen_codes = set()
        papers = []
        for entry in summary:
            kw = entry.get("keyword", "")
            kw_type = entry.get("kw_type", "")
            for p in entry.get("results", []):
                code = p.get("code")
                if not code or code in seen_codes:
                    continue
                seen_codes.add(code)
                papers.append({
                    "code": code,
                    "citation": p.get("citation", ""),
                    "abstract": p.get("abstract", ""),
                    "found_with_keyword": kw,
                    "found_in_section": kw_type,
                })

        # Build a single rich system payload — gampang di-parse oleh discuss agent.
        context_obj = {
            "event": "SEARCH_SUMMARY",
            "note": (
                "Sistem v2 sudah selesai melakukan pencarian. "
                "Berikut riwayat kata kunci yang dicoba dan daftar paper yang ditemukan. "
                "Pakai info ini sebagai konteks untuk menjawab pertanyaan lanjutan user "
                "(mis. user bertanya tentang paper tertentu, ringkasan, atau perbandingan). "
                "Frontend sudah menampilkan hasil ke user — jangan tampilkan ulang daftar paper."
            ),
            "keyword_history": keyword_history,
            "total_unique_papers": len(papers),
            "papers": papers,
        }

        try:
            payload = json.dumps([{"role": "system", "input": context_obj}],
                                  indent=2, ensure_ascii=False)
            from app.gemini_client.throttler import GeminiThrottler
            GeminiThrottler.wait_if_needed()
            response = self.discuss_agent.send_message(payload)

            try:
                from app.gemini_client.usage_logger import log_token_usage_sync
                usage = response.usage_metadata
                if usage and self.api_key_id:
                    if app_context:
                        with app_context:
                            log_token_usage_sync(
                                api_key_id=self.api_key_id,
                                input_tokens=usage.prompt_token_count or 0,
                                output_tokens=usage.candidates_token_count or 0,
                                session_id=self.session_id,
                                feature='discuss_v2_inject',
                                input_content=payload[:2000],
                                output_content=(response.text or '')[:1000],
                            )
                    else:
                        log_token_usage_sync(
                            api_key_id=self.api_key_id,
                            input_tokens=usage.prompt_token_count or 0,
                            output_tokens=usage.candidates_token_count or 0,
                            session_id=self.session_id,
                            feature='discuss_v2_inject',
                            input_content=payload[:2000],
                            output_content=(response.text or '')[:1000],
                        )
            except Exception as log_err:
                print(f"[SearchV2] inject usage log error: {log_err}")
        except Exception as e:
            print(f"[SearchV2] inject_paper_context error: {e}")

    def request_empty_suggestion(self, summary):
        """Ask discuss agent for fallback suggestion when ALL keywords return 0 results.

        `summary` adalah list dict spt yang dihasilkan process_keyword_search,
        dengan field keyword, kw_type, count, results.

        Returns the user_output string from discuss agent.
        """
        try:
            keyword_history = [
                {
                    "keyword": e.get("keyword", ""),
                    "kw_type": e.get("kw_type", ""),
                    "count": e.get("count", 0),
                }
                for e in (summary or [])
            ]
            context_obj = {
                "event": "ALL_KEYWORDS_EMPTY",
                "note": (
                    "Sistem v2 sudah selesai mencari tetapi SEMUA kata kunci yang dicoba "
                    "menghasilkan 0 paper di Digilib. Berikan saran ke user agar mencoba "
                    "istilah lain, perluas topik, atau ganti bahasa. Sebutkan juga kata "
                    "kunci apa saja yang sudah dicoba (utama vs tambahan)."
                ),
                "keyword_history": keyword_history,
                "total_unique_papers": 0,
            }
            payload = json.dumps([{"role": "system", "input": context_obj}],
                                  indent=2, ensure_ascii=False)
            from app.gemini_client.throttler import GeminiThrottler
            GeminiThrottler.wait_if_needed()
            response = self.discuss_agent.send_message(payload)
            user_output, _, _ = self.process_discuss_response(response.text)
            return user_output or response.text
        except Exception as e:
            print(f"[SearchV2] empty suggestion error: {e}")
            return ("Sayangnya semua kata kunci yang saya coba tidak menemukan paper. "
                    "Coba topik lain atau gunakan istilah yang lebih umum.")

    # ---------------- History restoration ----------------
    def load_history_from_db(self, chats):
        """Replay user messages to discuss agent so chat context is restored on reload."""
        if len(self.discuss_history) > 0:
            return
        for chat in chats:
            if chat.user_id and chat.message:
                self.discuss_history.append({"role": "user", "content": chat.message})
                try:
                    formatted = json.dumps([{"role": "user", "input": chat.message}],
                                            indent=4, ensure_ascii=False)
                    self.discuss_agent.send_message(formatted)
                except Exception as e:
                    print(f"[SearchV2] load_history send error: {e}")
            elif chat.response:
                self.discuss_history.append({"role": "assistant", "content": chat.response})
                # Restore paper context if present in search_steps
                if chat.search_steps:
                    try:
                        raw = json.loads(chat.search_steps)
                        summary = raw.get('summary') if isinstance(raw, dict) else None
                        if summary:
                            self.inject_paper_context(summary)
                    except (json.JSONDecodeError, AttributeError):
                        pass
        self._update_session_cache()
