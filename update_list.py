import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# --- SABİTLER ve VERİ KAYNAKLARI (Değişiklik yok) ---
# ... Önceki yanıttaki PUBLIC_DATA_SOURCES ve PRIVATE_DATA_SOURCE tanımları burada olacak ...
BASE_URL = "https://www.titck.gov.tr"
LOGIN_URL = f"{BASE_URL}/login"
OUTPUT_DIR = "data"
PUBLIC_DATA_SOURCES = [
    {"name": "Ruhsatli_Urunler", "page_url": f"{BASE_URL}/dinamikmodul/85", "output_xlsx": os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_ruhsat.txt"), "skiprows": 4},
    {"name": "Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/100", "output_xlsx": os.path.join(OUTPUT_DIR, "ilac_fiyat_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "ilac_fiyat_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_fiyat.txt"), "skiprows": 3},
    {"name": "SKRS_E-Recete", "page_url": f"{BASE_URL}/dinamikmodul/43", "output_xlsx": os.path.join(OUTPUT_DIR, "skrs_erecete_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "skrs_erecete_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_skrs.txt"), "skiprows": 0},
    {"name": "Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/108", "output_xlsx": os.path.join(OUTPUT_DIR, "etkin_madde_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "etkin_madde_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_etkinmadde.txt"), "skiprows": 3},
    {"name": "Yurtdisi_Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/126", "output_xlsx": os.path.join(OUTPUT_DIR, "yurtdisi_etkin_madde_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "yurtdisi_etkin_madde_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_yurtdisi_etkinmadde.txt"), "skiprows": 3}
]
PRIVATE_DATA_SOURCE = {"name": "Detayli_Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/88", "output_xlsx": os.path.join(OUTPUT_DIR, "detayli_ilac_fiyat_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "detayli_ilac_fiyat_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_detayli_fiyat.txt"), "skiprows": 3}

# Headers artık Selenium'da yönetildiği için burada sadeleşebilir veya kalabilir
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}

# ... Diğer yardımcı fonksiyonlar (get_latest_file_info, download_file vb.) aynı kalıyor ...
def set_github_action_output(name, value):
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if github_output_file:
        with open(github_output_file, 'a') as f: f.write(f"{name}={value}\n")
    print(f"DEBUG: GHA Çıktısı Ayarlanıyor -> {name}={value}")
def get_latest_file_info(page_url, session=None):
    requester = session or requests
    try:
        response = requester.get(page_url, headers=HEADERS, timeout=30)
        response.raise_for_status(); soup = BeautifulSoup(response.content, 'html.parser')
        excel_link = soup.find('a', href=lambda href: href and href.endswith('.xlsx'))
        if not excel_link: print(f"HATA: .xlsx linki bulunamadı: {page_url}"); return None, None
        file_url = excel_link['href']
        file_name = os.path.basename(file_url)
        if not file_url.startswith('http'): file_url = f"{BASE_URL}{file_url}"
        print(f"Tespit edilen dosya: {file_name}")
        return file_url, file_name
    except requests.RequestException as e: print(f"HATA: Sayfa erişim hatası - {e}"); return None, None
def download_file(url, destination, session=None):
    requester = session or requests
    try:
        with requester.get(url, headers=HEADERS, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(destination, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        print(f"İndirme başarılı: {destination}"); return True
    except requests.RequestException as e: print(f"HATA: İndirme hatası - {e}"); return False
def convert_xlsx_to_csv(xlsx_path, csv_path, rows_to_skip):
    try:
        df = pd.read_excel(xlsx_path, skiprows=rows_to_skip)
        df.dropna(how='all', inplace=True); df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"CSV oluşturuldu: {csv_path}"); return True
    except Exception as e: print(f"HATA: CSV dönüştürme hatası - {e}"); return False
def process_data_source(source, session=None):
    print(f"\n--- {source['name']} Veri Kaynağı İşleniyor ---")
    latest_url, latest_name = get_latest_file_info(source['page_url'], session=session)
    if not latest_url: 
        print(f"UYARI: {source['name']} için dosya bilgisi alınamadı, bu kaynak atlanıyor.")
        return False
    last_known_name = ""
    if os.path.exists(source['last_known_file_record']):
        with open(source['last_known_file_record'], 'r') as f: last_known_name = f.read().strip()
    if latest_name != last_known_name:
        print(f"Yeni bir {source['name']} dosyası tespit edildi.")
        if not download_file(latest_url, source['output_xlsx'], session=session): return False
        if not convert_xlsx_to_csv(source['output_xlsx'], source['output_csv'], source['skiprows']): return False
        with open(source['last_known_file_record'], 'w') as f: f.write(latest_name)
        print(f"{source['name']} başarıyla güncellendi."); return True
    else: print(f"{source['name']} listesi güncel."); return False

# ❗️❗️ TAMAMEN YENİLENEN FONKSİYON ❗️❗️
def process_private_source_with_selenium(source):
    print(f"\n--- {source['name']} (Selenium ile) Veri Kaynağı İşleniyor ---")
    username = os.getenv("TITCK_USERNAME")
    password = os.getenv("TITCK_PASSWORD")
    if not (username and password):
        print("UYARI: TITCK_USERNAME ve TITCK_PASSWORD secret'ları bulunamadı. Bu adım atlanıyor.")
        return False

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    
    driver = None
    try:
        # Selenium WebDriver'ı başlat
        print("DEBUG: Selenium WebDriver başlatılıyor...")
        service = Service() # Otomatik olarak chromedriver'ı bulur
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Giriş yap
        print(f"DEBUG: Selenium ile login sayfasına gidiliyor: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        time.sleep(3) # Sayfanın tam yüklenmesini bekle
        
        print("DEBUG: Kullanıcı adı ve şifre alanları dolduruluyor...")
        # Not: Sitedeki input ID'leri değişirse bu satırların güncellenmesi gerekir.
        driver.find_element(By.ID, "username").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        
        print("DEBUG: Giriş butonuna tıklanıyor...")
        driver.find_element(By.ID, "login-btn").click()
        time.sleep(5) # Giriş sonrası yönlendirmenin tamamlanmasını bekle
        
        # Girişin başarılı olup olmadığını kontrol et
        print(f"DEBUG: Giriş sonrası mevcut URL: {driver.current_url}")
        if "login" in driver.current_url.lower():
            print("HATA: Giriş başarısız. Sayfa hala login ekranında.")
            driver.quit()
            return False
        print("Giriş başarılı.")

        # Giriş yapılmış cookie'leri al ve requests session'ına aktar
        selenium_cookies = driver.get_cookies()
        requests_session = requests.Session()
        for cookie in selenium_cookies:
            requests_session.cookies.set(cookie['name'], cookie['value'])
        
        print("DEBUG: Cookie'ler requests'e aktarıldı. Korumalı kaynak işleniyor...")
        return process_data_source(source, session=requests_session)

    except Exception as e:
        print(f"HATA: Selenium ile özel kaynak işlenirken bir hata oluştu: {e}")
        if driver:
            driver.save_screenshot('selenium_error.png') # Hata anının ekran görüntüsünü alır
        return False
    finally:
        # Tarayıcıyı her zaman kapat
        if driver:
            driver.quit()
            print("DEBUG: Selenium WebDriver kapatıldı.")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    any_update_done = False
    updated_sources = []

    # Halka açık kaynakları işle
    for source in PUBLIC_DATA_SOURCES:
        time.sleep(3) # Halka açık istekler arasında kısa bir bekleme hala iyi bir fikir
        if process_data_source(source):
            any_update_done = True
            updated_sources.append(source['name'])

    # Şifre korumalı kaynağı Selenium ile işle
    time.sleep(3)
    if process_private_source_with_selenium(PRIVATE_DATA_SOURCE):
        any_update_done = True
        updated_sources.append(PRIVATE_DATA_SOURCE['name'])

    summary = f"Otomatik Veri Güncellemesi: {', '.join(updated_sources)}" if any_update_done else 'Veriler güncel, herhangi bir değişiklik yapılmadı.'
    set_github_action_output('updated', str(any_update_done).lower())
    set_github_action_output('summary', summary)

if __name__ == "__main__":
    main()