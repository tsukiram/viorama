# C:\Users\rama\Desktop\viorama_app\viorama\app\gemini_client\searching.py
import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import re
from google import genai
from google.genai import types
from config import Config

class AcademicSearchSystem:
    _agents = {}  # Store agents by session_id

    def __init__(self, session_id):
        self.api_key = Config.GEMINI_API_KEY
        self.base_url = "https://digilib.uin-suka.ac.id/cgi/search/archive/simple"
        self.session_id = session_id
        self.discuss_client = None
        self.search_client = None
        self.discuss_agent = None
        self.search_agent = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize Gemini clients and agents if not already initialized for this session."""
        if self.session_id in self._agents:
            self.discuss_agent, self.search_agent = self._agents[self.session_id]
            print(f"\n✓ Reusing existing agents for session {self.session_id}")
            return

        try:
            self.discuss_client = genai.Client(api_key=self.api_key)
            discuss_prompt = self._load_prompt('app/prompts/discuss_client.txt')
            self.discuss_agent = self.discuss_client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(system_instruction=discuss_prompt)
            )

            self.search_client = genai.Client(api_key=self.api_key)
            search_prompt = self._load_prompt('app/prompts/search_client.txt')
            self.search_agent = self.search_client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(system_instruction=search_prompt)
            )

            self._agents[self.session_id] = (self.discuss_agent, self.search_agent)
            print(f"\n✓ Clients initialized successfully for session {self.session_id}")

        except Exception as e:
            print(f"\n✗ Error initializing clients: {e}")
            raise Exception(f"Error initializing clients: {e}")

    def _load_prompt(self, filename):
        """Load prompt from file."""
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Warning: {filename} not found. Using default prompt.")
            return "You are a helpful academic research assistant."

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
                print(f"No results found for keyword: {query}")
                return []

            return results

        except requests.RequestException as e:
            print(f"Error searching repository: {e}")
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
                print(f"Error fetching metadata: {e}")
                continue

        return metadata_list

    def search_papers(self, query):
        """Complete search process: search repository and fetch metadata."""
        print(f"\nSearching for keyword: {query}")
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
            print(f"Error parsing JSON response: {e}")
            print(f"Response content: {response_text}")
            return False, "", []

    def process_search_request(self, user_input):
        """Process search request using search agent."""
        print("Analyzing request...")
        search_steps = []

        while True:
            response = self.search_agent.send_message(user_input)
            should_search, keyword, add_paper_codes = self.process_search_response(response.text)

            if should_search and keyword:
                search_steps.append(f"Searching for keyword: {keyword}")
                search_results = self.search_papers(keyword)
                search_results_json = json.dumps(search_results, indent=4, ensure_ascii=False)
                print("\nSearch results found:", len(search_results))
                search_steps.append(f"Search results found: {len(search_results)}")
                print("Analyzing search results and selecting relevant papers...")
                search_steps.append("Analyzing search results and selecting relevant papers...")

                user_input = json.dumps([{
                    "role": "search_result",
                    "input": search_results_json
                }])
            else:
                code_list = json.dumps(add_paper_codes, indent=4, ensure_ascii=False)
                search_steps.append(f"Selected paper codes: {code_list}")
                return add_paper_codes, search_steps

    def process_discuss_response(self, response_text):
        """Process response from discuss agent with improved error handling."""
        # print(f"Processing discuss response: {response_text}")
        json_pattern = r'```json(.*?)```'
        matches = re.findall(json_pattern, response_text, re.DOTALL)

        if not matches:
            json_pattern = r'\{[\s\S]*?\}'
            matches = re.findall(json_pattern, response_text)

            if not matches:
                print("No JSON pattern found, returning raw response as user_output")
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

            # print(f"Parsed user_output: {user_output}")
            # print(f"Parsed system_output: {system_output}")
            return user_output, system_output, None

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Trying to parse: {json_string if 'json_string' in locals() else 'N/A'}")
            print(f"Raw response: {response_text}")
            return response_text.strip(), None, f"JSON decode error: {e}"

    def run_interactive_session(self, user_input):
        """Run interactive discussion session with single message processing."""
        try:
            formatted_input = json.dumps([{
                "role": "user",
                "input": user_input
            }], indent=4, ensure_ascii=False)
            # print(f"Formatted input: {formatted_input}")

            response = self.discuss_agent.send_message(formatted_input)
            # print(f"Raw discuss response: {response.text}")
            user_output, system_output, error = self.process_discuss_response(response.text)
            user_output_before_search = user_output
            print(f"\nuser_output_before_search: {user_output_before_search}")
            # print(f"\nsystem_output: {system_output}")

            if error:
                print(f"Error in discuss response: {error}")
                return f"Error processing response: {error}", [], []

            search_steps = []
            add_paper_codes = []

            # if system_output:
            #     print("\nProcessing search request...")
            #     add_paper_codes, search_steps = self.process_search_request(system_output)
            #     print("\nSearch completed.")

            #     if add_paper_codes:
            #         search_input = json.dumps([{
            #             "role": "system",
            #             "input": json.dumps(add_paper_codes, indent=4, ensure_ascii=False)
            #         }], indent=4, ensure_ascii=False)
            #         # print(f"Search input for discuss agent: {search_input}")

            #         system_response = self.discuss_agent.send_message(search_input)
            #         user_output, _, _ = self.process_discuss_response(system_response.text)
            #         # print(f"\nFinal user_output: {user_output}")

            return system_output, user_output, add_paper_codes, search_steps

        except Exception as e:
            print(f"An error occurred in run_interactive_session: {e}")
            return f"An error occurred: {e}", [], []

    @classmethod
    def clear_session(cls, session_id):
        """Clear agents for a specific session."""
        if session_id in cls._agents:
            del cls._agents[session_id]
            print(f"\n✓ Cleared agents for session {self.session_id}")