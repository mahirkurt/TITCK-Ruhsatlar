import requests
from bs4 import BeautifulSoup
import os
import re
import time
import sys
# Selenium yerine undetected_chromedriver'ı içe aktarıyoruz
import undetected_chromedriver as uc

# --- Ayarlar ve Diğer Fonksiyonlar (Değişiklik yok) ---
MAIN_URL = "https://www.titck.gov.tr/kubkt"
API_URL = "https://www.titck.gov.tr/getkubktviewdatatable"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": MAIN_URL
}
KUB_FOLDER = "KUB_Arsivi"
KT_FOLDER = "KT_Arsivi"

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

# --- ANA SCRAPER FONKSİYONU (UNDETECTED_CHROMEDRIVER İLE GÜNCELLENDİ) ---
def run_scraper():
    print("1/4: 'Görünmez' sanal tarayıcı (undetected-chromedriver) başlatılıyor...")
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Normal Selenium yerine uc.Chrome() kullanıyoruz
    driver = uc.Chrome(options=options, use_subprocess=True)

    try:
        print("2/4: Ana sayfaya gidiliyor ve JavaScript'in yüklenmesi bekleniyor...")
        driver.get(MAIN_URL)
        time.sleep(7) # Bekleme süresini biraz artırmak işe yarayabilir

        page_html = driver.page_source
        soup = BeautifulSoup(page_html, 'html.parser')
        token_input = soup.find('input', {'name': '_token'})

        if not token_input:
            print("KRİTİK HATA: Görünmez tarayıcı ile bile CSRF token'ı bulunamadı!")
            print("Sitenin koruması çok yüksek veya geçici bir sorun var.")
            print("--- Alınan HTML'in Başı ---")
            print(soup.prettify()[:2000]) # Daha fazla HTML görelim
            print("--------------------------")
            sys.exit(1)
        
        csrf_token = token_input['value']
        print("Token başarıyla alındı!")

        session = requests.Session()
        session.headers.update(HEADERS)
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])

    finally:
        driver.quit()

    payload = {'length': '-1', '_token': csrf_token}
    print("3/4: Tüm ilaç listesi çekiliyor...")
    # ... (Kodun geri kalanı tamamen aynı)
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