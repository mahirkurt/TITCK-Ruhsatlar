#!/usr/bin/env python3
import sys
import logging
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# --- Loglama ve Klasör Kurulumu ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    stream=sys.stdout
)
BASE_URL = "https://www.titck.gov.tr"
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "ham_veriler"
OUTPUT_DIR.mkdir(exist_ok=True)

# İşlenecek sayfaların ve hedef dosya adlarının listesi
FILES_TO_DOWNLOAD = [
    {"output_filename": "ilac_fiyat_listesi.xlsx", "page_url": "https://titck.gov.tr/dinamikmodul/100"},
    {"output_filename": "ruhsatli_ilaclar_listesi.xlsx", "page_url": "https://www.titck.gov.tr/dinamikmodul/85"},
    {"output_filename": "etkin_madde_listesi.xlsx", "page_url": "https://www.titck.gov.tr/dinamikmodul/108"},
    {"output_filename": "yurtdisi_etkin_madde_listesi.xlsx", "page_url": "https://www.titck.gov.tr/dinamikmodul/126"},
    {"output_filename": "skrs_erecete_listesi.xlsx", "page_url": "https://www.titck.gov.tr/dinamikmodul/43"}
]

def download_from_page(config):
    """Verilen sayfadan .xlsx linkini bulur ve dosyayı indirir."""
    page_url = config["page_url"]
    output_filename = config["output_filename"]
    output_path = OUTPUT_DIR / output_filename
    
    logging.info(f"'{page_url}' sayfasından Excel linki aranıyor...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        page_response = requests.get(page_url, headers=headers, timeout=30)
        page_response.raise_for_status()

        soup = BeautifulSoup(page_response.content, 'lxml')
        link_tag = soup.find('a', href=lambda h: h and h.lower().endswith('.xlsx'))
        if not link_tag:
            logging.error(f"{page_url}: .xlsx linki bulunamadı.")
            return False

        file_url = urljoin(BASE_URL, link_tag['href'])
        logging.info(f"İndirme linki bulundu: {file_url}")

        file_response = requests.get(file_url, headers=headers, timeout=120)
        file_response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(file_response.content)

        logging.info(f"-> '{output_filename}' olarak kaydedildi.")
        return True

    except requests.RequestException as e:
        logging.error(f"Hata: {e}")
        return False

 def main():
    logging.info("===== Ham Veri İndirme Başlatıldı =====")
    results = [download_from_page(cfg) for cfg in FILES_TO_DOWNLOAD]
    if not all(results):
        logging.error("Bazı indirmeler başarısız oldu.")
        sys.exit(1)
    logging.info("Tüm dosyalar başarıyla indirildi.")

if __name__ == '__main__':
    main()
