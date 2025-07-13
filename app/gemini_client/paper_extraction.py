# app/gemini_client/paper_extraction.py

import requests
from bs4 import BeautifulSoup
import re

class PaperExtractionSystem:
    def __init__(self):
        self.base_url = "https://digilib.uin-suka.ac.id/id/eprint/"

    def extract_metadata(self, code):
        """Extract metadata for a paper given its eprint code."""
        url = f"{self.base_url}{code}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = soup.find('h1', class_='ep_tm_pagetitle').get_text(strip=True) if soup.find('h1', class_='ep_tm_pagetitle') else "No title available"
            
            citation_elem = soup.find('p', style=re.compile(r'margin-bottom:\s*1em'))
            citation = citation_elem.get_text(strip=True) if citation_elem else "No citation available"
            
            abstract_elem = soup.find('h2', string=re.compile(r'Abstract', re.IGNORECASE))
            abstract = "No abstract available"
            if abstract_elem:
                abstract_p = abstract_elem.find_next('p')
                if abstract_p:
                    abstract = abstract_p.get_text(strip=True)
            
            preview_link = ""
            full_text_link = ""
            dc_identifiers = soup.find_all('meta', attrs={'name': 'DC.identifier'})
            for identifier in dc_identifiers:
                content = identifier.get('content', '')
                if "BAB-I_IV-atau-V_DAFTAR-PUSTAKA.pdf" in content:
                    preview_link = content
                elif "BAB-II_sampai_SEBELUM-BAB-TERAKHIR.pdf" in content:
                    full_text_link = content
            
            return {
                "title": title,
                "citation": citation,
                "abstract": abstract,
                "preview_link": preview_link,
                "full_text_link": full_text_link,
                "url": url,
                "code": code
            }
        except requests.RequestException as e:
            return {"error": f"Error fetching paper: {e}"}