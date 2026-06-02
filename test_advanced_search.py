"""
Eksperimen pencarian advanced di Digilib UIN Suka.
Test URL dengan filter date range + keyword, lihat struktur hasilnya.

Usage:
    python3 test_advanced_search.py

Edit variabel KEYWORD, DATE_FROM, DATE_TO di bawah untuk eksperimen.
"""

import requests
from bs4 import BeautifulSoup
import urllib.parse
import sys


# ======================= EDIT DI SINI =======================
KEYWORD   = "basis data"          # boleh kosong "" untuk filter date saja
DATE_FROM = "2020-01-01"          # format: YYYY-MM-DD, atau None untuk skip
DATE_TO   = "2024-12-31"
MAX_SHOW  = 10                    # tampilkan top-N hasil
# ============================================================


BASE_ADV = "https://digilib.uin-suka.ac.id/cgi/search/archive/advanced"


def build_advanced_url(keyword=None, date_from=None, date_to=None):
    """Konstruk URL advanced search sesuai pola Digilib (eprints).

    Param `date` formatnya: YYYY-MM-DD-YYYY-MM-DD
    Kalau cuma date_from / date_to saja, separator-nya tetap dipakai.
    """
    params = [
        ('screen', 'Search'),
        ('dataset', 'archive'),
        ('_action_search', 'Search'),
        ('documents_merge', 'ALL'),
        ('documents', ''),
        ('title_merge', 'ALL'),
        ('title', ''),
        ('creators_name_merge', 'ALL'),
        ('creators_name', ''),
        ('note_merge', 'ALL'),
        ('note', ''),
        ('userid', ''),
        ('abstract_merge', 'ALL'),
        ('abstract', ''),
    ]

    # Date range
    if date_from or date_to:
        df = date_from or ''
        dt = date_to or ''
        params.append(('date', f'{df}-{dt}'))
    else:
        params.append(('date', ''))

    params.extend([
        ('keywords_merge', 'ALL'),
        ('keywords', keyword or ''),
        ('subjects_merge', 'ANY'),
        ('department_merge', 'ALL'),
        ('department', ''),
        ('editors_name_merge', 'ALL'),
        ('editors_name', ''),
        ('refereed', 'EITHER'),
        ('publication_merge', 'ALL'),
        ('publication', ''),
        ('satisfyall', 'ALL'),
        ('order', '-date/creators_name/title'),
    ])

    return BASE_ADV + '?' + urllib.parse.urlencode(params)


def main():
    url = build_advanced_url(KEYWORD, DATE_FROM, DATE_TO)
    print("=" * 80)
    print(f"Keyword   : '{KEYWORD}'")
    print(f"Date range: {DATE_FROM}  →  {DATE_TO}")
    print("-" * 80)
    print(f"URL:\n{url}")
    print("=" * 80)

    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"\n[ERROR] Request gagal: {e}")
        sys.exit(1)

    print(f"\nHTTP Status: {r.status_code}")
    print(f"Response size: {len(r.text):,} bytes\n")

    soup = BeautifulSoup(r.text, 'html.parser')

    # Coba beberapa selector hasil pencarian
    items = soup.find_all('tr', class_='ep_search_result')
    if not items:
        # Fallback: coba citation list (kadang eprints render beda di advanced)
        items = soup.select('p.ep_search_result_div, div.ep_search_result, li.ep_search_result')

    # Cari indikator jumlah total hasil di halaman
    total_text = ""
    matches_section = soup.find(string=lambda s: s and 'matches' in s.lower())
    if matches_section:
        total_text = matches_section.strip()[:200]

    print(f"Hasil ditemukan di halaman ini: {len(items)}")
    if total_text:
        print(f"Indikator total: {total_text}")
    print()

    if not items:
        print("[!] Tidak ada hasil dengan selector standar.")
        print("    Coba print 500 karakter HTML pertama untuk debug:\n")
        print(r.text[:500])
        return

    print(f"Top-{min(MAX_SHOW, len(items))} hasil:\n")
    for i, item in enumerate(items[:MAX_SHOW], 1):
        text = item.get_text(' ', strip=True)
        # Pendekkan
        text_short = text[:160] + ('...' if len(text) > 160 else '')

        a = item.find('a', href=True)
        link = urllib.parse.urljoin(BASE_ADV, a['href']) if a else '(no link)'

        print(f"{i:>2}. {text_short}")
        print(f"     → {link}")
        print()


if __name__ == '__main__':
    main()
