#!/usr/bin/env python3
import json
import sys
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# --- Ayarlar ve Loglama ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s")
BASE_URL = "https://www.titck.gov.tr"
FILES_TO_CHECK = [
    {"key": "ilac_fiyat_listesi", "page_url": "https://titck.gov.tr/dinamikmodul/100"},
    {"key": "ruhsatli_ilaclar_listesi", "page_url": "https://www.titck.gov.tr/dinamikmodul/85"},
    {"key": "etkin_madde_listesi", "page_url": "https://www.titck.gov.tr/dinamikmodul/108"},
    {"key": "yurtdisi_etkin_madde_listesi", "page_url": "https://www.titck.gov.tr/dinamikmodul/126"},
    {"key": "skrs_erecete_listesi", "page_url": "https://www.titck.gov.tr/dinamikmodul/43"},
]
STATE_FILE = "last_known_links.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)


def load_state():
    """Varolan state dosyasını oku; yoksa None döndür."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_state(state):
    """State dosyasını yazar."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fetch_xlsx_link(page_url):
    """Sayfadaki .xlsx linkini döner; hata durumunda None."""
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(page_url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "lxml")
        tag = soup.find("a", href=lambda h: h and h.lower().endswith(".xlsx"))
        if tag:
            return urljoin(BASE_URL, tag["href"])
        logging.warning(f"{page_url} sayfasında .xlsx linki bulunamadı.")
        return None
    except requests.RequestException as e:
        logging.warning(f"{page_url} sayfası işlenemedi: {e}")
        return None


def main():
    state = load_state()
    new_state = {}
    changed_keys = []
    first_run = state is None

    for cfg in FILES_TO_CHECK:
        key = cfg["key"]
        url = cfg["page_url"]
        link = fetch_xlsx_link(url)
        new_state[key] = link
        if not first_run and link and link != state.get(key):
            changed_keys.append(key)

    save_state(new_state)
    is_updated = bool(changed_keys)

    # GitHub Actions outputs
    print(f"::set-output name=is_updated::{str(is_updated).lower()}")
    print(f"::set-output name=changed_files::{','.join(changed_keys)}")

    sys.exit(0)


if __name__ == "__main__":
    main()
