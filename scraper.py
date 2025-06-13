import requests
from bs4 import BeautifulSoup
import os
import re
import time
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# --- Ayarlar ---
MAIN_URL = "https://www.titck.gov.tr/kubkt"
API_URL = "https://www.titck.gov.tr/getkubktviewdatatable"
HEADERS = { # Bu artık sadece API isteği için kullanılacak
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": MAIN_URL
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

# --- ANA SCRAPER FONKSİYONU (SELENIUM İLE GÜNCELLENDİ) ---
def run_scraper():
    print("1/4: Selenium ile sanal tarayıcı başlatılıyor...")
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Tarayıcının arayüzünü gösterme (sunucu için gerekli)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        print("2/4: Ana sayfaya gidiliyor ve JavaScript'in yüklenmesi bekleniyor...")
        driver.get(MAIN_URL)
        # Sayfanın tam yüklenmesi için birkaç saniye bekle
        time.sleep(5)

        # Yüklenmiş sayfanın HTML'ini al
        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')

        # Şimdi token'ı bu tam yüklenmiş HTML'de ara
        token_input = soup.find('input', {'name': '_token'})

        if not token_input:
            print("KRİTİK HATA: Selenium ile bile CSRF token'ı bulunamadı!")
            print("Sayfa yapısı değişmiş veya yüklenememiş olabilir.")
            print("--- Selenium'dan Alınan HTML'in Başı ---")
            print(soup.prettify()[:1500])
            print("------------------------------------")
            sys.exit(1)
        
        csrf_token = token_input['value']
        print("Token başarıyla alındı.")

        # Selenium tarayıcısından çerezleri alıp requests session'ına aktar
        # Bu sayede aynı oturumdan devam edebiliriz
        session = requests.Session()
        session.headers.update(HEADERS)
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])

    finally:
        # Tarayıcıyı kapatmayı unutma
        driver.quit()

    # Adım 3 ve 4: Token ve çerezlerle API isteğini requests ile yap (daha hızlı)
    payload = {'length': '-1', '_token': csrf_token}
    print("3/4: Tüm ilaç listesi çekiliyor...")
    api_response = session.post(API_URL, data=payload)
    api_response.raise_for_status()
    drug_list = api_response.json().get('data', [])
    total_drugs = len(drug_list)
    print(f"Toplam {total_drugs} ilaç verisi alındı.")

    print("\n4/4: PDF'ler işleniyor...")
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