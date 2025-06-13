import requests
from bs4 import BeautifulSoup
import os
import re
import time
import sys # Programı hata durumunda durdurmak için

# --- Ayarlar (Değişiklik yok) ---
MAIN_URL = "https://www.titck.gov.tr/kubkt"
API_URL = "https://www.titck.gov.tr/getkubktviewdatatable"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
    "Connection": "keep-alive"
}
KUB_FOLDER = "KUB_Arsivi"
KT_FOLDER = "KT_Arsivi"

# --- Diğer Fonksiyonlar (Değişiklik yok) ---
def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|%]', "_", filename)

def extract_pdf_link(html_content):
    if not html_content or not isinstance(html_content, str): return None
    soup = BeautifulSoup(html_content, 'html.parser')
    link_tag = soup.find('a')
    return link_tag.get('href') if link_tag else None

def download_pdf(session, url, folder, filename):
    if not os.path.exists(folder): os.makedirs(folder)
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

# --- ANA SCRAPER FONKSİYONU (HATAYI ÇÖZECEK DEĞİŞİKLİKLER BURADA) ---
def run_scraper():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("1/3: CSRF token alınıyor...")
    main_page_response = session.get(MAIN_URL)
    
    # Sunucudan başarılı bir yanıt gelip gelmediğini kontrol et
    if main_page_response.status_code != 200:
        print(f"HATA: Ana sayfaya ulaşılamadı. Sunucu durum kodu: {main_page_response.status_code}")
        sys.exit(1) # Programı hata koduyla durdur

    soup = BeautifulSoup(main_page_response.content, 'html.parser')
    
    # ÖNCE TOKEN'I BULMAYA ÇALIŞ
    token_input = soup.find('input', {'name': '_token'})

    # SONRA BULUP BULAMADIĞINI KONTROL ET
    if not token_input:
        print("KRİTİK HATA: CSRF token'ı ana sayfa HTML'inde bulunamadı!")
        print("Sunucudan gelen sayfa bir engelleme veya CAPTCHA sayfası olabilir.")
        print("--- Sunucudan Alınan HTML'in Başı ---")
        # Hatanın sebebini anlamak için gelen HTML'in ilk 1000 karakterini yazdır.
        print(soup.prettify()[:1000])
        print("------------------------------------")
        sys.exit(1) # Programı hata koduyla durdur
    
    # Eğer buraya geldiyse, token bulunmuştur. Değerini alabiliriz.
    csrf_token = token_input['value']
    print("Token başarıyla alındı.")

    # Kodun geri kalanı aynı...
    payload = {'length': '-1', '_token': csrf_token}
    print("2/3: Tüm ilaç listesi çekiliyor...")
    api_response = session.post(API_URL, data=payload)
    api_response.raise_for_status()
    drug_list = api_response.json().get('data', [])
    total_drugs = len(drug_list)
    print(f"Toplam {total_drugs} ilaç verisi alındı.")

    print("\n3/3: PDF'ler işleniyor...")
    for i, drug in enumerate(drug_list):
        # ... (bu kısımda değişiklik yok)
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