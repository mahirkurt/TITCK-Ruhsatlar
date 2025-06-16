#!/usr/bin/env python3
import sys
import logging
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# --- Loglama ve Klasör Kurulumu ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s"
)
BASE_URL = "https://www.titck.gov.tr"
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "ham_veriler"
OUTPUT_DIR.mkdir(exist_ok=True)

# İndirilecek dosyalar ve sayfa URL'leri
FILES_TO_DOWNLOAD = [
    {"output_filename": "ilac_fiyat_listesi.xlsx", "page_url": "https://titck.gov.tr/dinamikmodul/100"},
    {"output_filename": "ruhsatli_ilaclar_listesi.xlsx", "page_url": "https://www.titck.gov.tr/dinamikmodul/85"},
    {"output_filename": "etkin_madde_listesi.xlsx", "page_url": "https://www.titck.gov.tr/dinamikmodul/108"},
    {"output_filename": "yurtdisi_etkin_madde_listesi.xlsx", "page_url": "https://www.titck.gov.tr/dinamikmodul/126"},
    {"output_filename": "skrs_erecete_listesi.xlsx", "page_url": "https://www.titck.gov.tr/dinamikmodul/43"}
]


def fetch_with_retry(url, retries=3, backoff=5):
    """URL'den içerik çeker; başarısızsa belirli sayıda yeniden dener."""
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            logging.warning(f"{url}: Deneme {attempt}/{retries} başarısız: {e}")
            if attempt < retries:
                time.sleep(backoff)
            else:
                logging.error(f"{url}: Tüm denemeler başarısız, atlanıyor.")
                return None


def download_from_page(config):
    """Sayfadan .xlsx linki bulur ve dosyayı indirir."""
    page_url = config["page_url"]
    output_filename = config["output_filename"]
    output_path = OUTPUT_DIR / output_filename

    logging.info(f"{page_url} sayfasından Excel linki aranıyor...")
    page_resp = fetch_with_retry(page_url)
    if not page_resp:
        return False

    soup = BeautifulSoup(page_resp.content, "lxml")
    tag = soup.find("a", href=lambda h: h and h.lower().endswith(".xlsx"))
    if not tag:
        logging.error(f"{page_url}: .xlsx linki bulunamadı.")
        return False

    file_url = urljoin(BASE_URL, tag['href'])
    logging.info(f"İndirme linki bulundu: {file_url}")

    file_resp = fetch_with_retry(file_url)
    if not file_resp:
        return False

    with open(output_path, 'wb') as f:
        f.write(file_resp.content)
    logging.info(f"-> '{output_filename}' olarak kaydedildi.")
    return True


def main():
    logging.info("===== Ham Veri İndirme Başlatıldı =====")
    results = [download_from_page(cfg) for cfg in FILES_TO_DOWNLOAD]

    if all(results):
        logging.info("Tüm dosyalar başarıyla indirildi.")
        sys.exit(0)
    else:
        logging.warning("Bazı dosyalar indirilemedi, yine de işlem tamamlandı.")
        sys.exit(0)


if __name__ == '__main__':
    main()
