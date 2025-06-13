import requests
from bs4 import BeautifulSoup
import os
import re
import time

# --- Ayarlar ---
MAIN_URL = "https://www.titck.gov.tr/kubkt"
API_URL = "https://www.titck.gov.tr/getkubktviewdatatable"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": MAIN_URL
}
KUB_FOLDER = "KUB_Arsivi"
KT_FOLDER = "KT_Arsivi"

def sanitize_filename(filename):
    """Dosya adlarındaki geçersiz karakterleri temizler."""
    return re.sub(r'[\\/*?:"<>|%]', "_", filename)

def extract_pdf_link(html_content):
    """HTML bloğundan PDF linkini ayıklar."""
    if not html_content or not isinstance(html_content, str): return None
    soup = BeautifulSoup(html_content, 'html.parser')
    link_tag = soup.find('a')
    return link_tag.get('href') if link_tag else None

def download_pdf(session, url, folder, filename):
    """Verilen URL'den PDF indirir."""
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    filepath = os.path.join(folder, filename)
    if os.path.exists(filepath):
        print(f"   -> Zaten mevcut: {filename}")
        return

    try:
        print(f"   -> İndiriliyor: {filename}")
        pdf_response = session.get(url, stream=True, timeout=30)
        pdf_response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in pdf_response.iter_content(chunk_size=8192):
                f.write(chunk)
    except requests.exceptions.RequestException as e:
        print(f"   !!! Hata: Dosya indirilemedi. URL: {url}, Hata: {e}")

def run_scraper():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("1/3: CSRF token alınıyor...")
    main_page_response = session.get(MAIN_URL)
    main_page_response.raise_for_status()
    soup = BeautifulSoup(main_page_response.content, 'html.parser')
    csrf_token = soup.find('input', {'name': '_token'})['value']
    print("Token alındı.")

    payload = {'length': '-1', '_token': csrf_token}
    print("2/3: Tüm ilaç listesi çekiliyor...")
    api_response = session.post(API_URL, data=payload)
    api_response.raise_for_status()
    drug_list = api_response.json().get('data', [])
    total_drugs = len(drug_list)
    print(f"Toplam {total_drugs} ilaç verisi alındı.")

    print("\n3/3: PDF'ler işleniyor...")
    for i, drug in enumerate(drug_list):
        drug_name = drug.get('name', f'isimsiz_ilac_{i}')
        print(f"\nİşleniyor ({i+1}/{total_drugs}): {drug_name}")

        kub_link = extract_pdf_link(drug.get('documentPathKub'))
        if kub_link:
            filename = sanitize_filename(drug_name) + "_KUB.pdf"
            download_pdf(session, kub_link, KUB_FOLDER, filename)
        
        kt_link = extract_pdf_link(drug.get('documentPathKt'))
        if kt_link:
            filename = sanitize_filename(drug_name) + "_KT.pdf"
            download_pdf(session, kt_link, KT_FOLDER, filename)
        
        time.sleep(0.1)

    print("\n--- Tüm İndirme İşlemleri Tamamlandı! ---")

if __name__ == "__main__":
    run_scraper()