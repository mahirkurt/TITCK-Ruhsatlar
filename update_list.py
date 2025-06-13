import os
import re
import time # Bekleme yapmak için time modülünü ekliyoruz
import requests
import pandas as pd
from bs4 import BeautifulSoup

# --- SABİTLER ve VERİ KAYNAKLARI (Değişiklik yok) ---
BASE_URL = "https://www.titck.gov.tr"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
OUTPUT_DIR = "data"
LOGIN_URL = f"{BASE_URL}/login"
PUBLIC_DATA_SOURCES = [
    {"name": "Ruhsatli_Urunler", "page_url": f"{BASE_URL}/dinamikmodul/85", "output_xlsx": os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_ruhsat.txt"), "skiprows": 4},
    {"name": "Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/100", "output_xlsx": os.path.join(OUTPUT_DIR, "ilac_fiyat_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "ilac_fiyat_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_fiyat.txt"), "skiprows": 3},
    {"name": "SKRS_E-Recete", "page_url": f"{BASE_URL}/dinamikmodul/43", "output_xlsx": os.path.join(OUTPUT_DIR, "skrs_erecete_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "skrs_erecete_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_skrs.txt"), "skiprows": 0},
    {"name": "Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/108", "output_xlsx": os.path.join(OUTPUT_DIR, "etkin_madde_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "etkin_madde_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_etkinmadde.txt"), "skiprows": 3},
    {"name": "Yurtdisi_Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/126", "output_xlsx": os.path.join(OUTPUT_DIR, "yurtdisi_etkin_madde_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "yurtdisi_etkin_madde_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_yurtdisi_etkinmadde.txt"), "skiprows": 3}
]
PRIVATE_DATA_SOURCE = {"name": "Detayli_Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/88", "output_xlsx": os.path.join(OUTPUT_DIR, "detayli_ilac_fiyat_listesi.xlsx"), "output_csv": os.path.join(OUTPUT_DIR, "detayli_ilac_fiyat_listesi.csv"), "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_detayli_fiyat.txt"), "skiprows": 3}

# Diğer tüm fonksiyonlar (process_data_source, process_private_source vb.) öncekiyle tamamen aynı kalıyor.
# Sadece main() fonksiyonunu güncelliyoruz.
def set_github_action_output(name, value):
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if github_output_file:
        with open(github_output_file, 'a') as f: f.write(f"{name}={value}\n")
    print(f"DEBUG: GHA Çıktısı Ayarlanıyor -> {name}={value}")
def get_latest_file_info(page_url, session=None):
    print(f"DEBUG: 'get_latest_file_info' başlatıldı. URL: {page_url}")
    requester = session or requests
    try:
        response = requester.get(page_url, headers=HEADERS, timeout=30)
        print(f"DEBUG: Sayfa durumu kodu: {response.status_code}")
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
    print(f"Dosya indiriliyor: {url}")
    requester = session or requests
    try:
        with requester.get(url, headers=HEADERS, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(destination, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        print(f"İndirme başarılı: {destination}"); return True
    except requests.RequestException as e: print(f"HATA: İndirme hatası - {e}"); return False
def convert_xlsx_to_csv(xlsx_path, csv_path, rows_to_skip):
    print(f"CSV'ye dönüştürülüyor: {xlsx_path}")
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
    print(f"DEBUG: Mevcut bilinen dosya: '{last_known_name}', Sitedeki dosya: '{latest_name}'")
    if latest_name != last_known_name:
        print(f"Yeni bir {source['name']} dosyası tespit edildi.")
        if not download_file(latest_url, source['output_xlsx'], session=session): return False
        if not convert_xlsx_to_csv(source['output_xlsx'], source['output_csv'], source['skiprows']): return False
        with open(source['last_known_file_record'], 'w') as f: f.write(latest_name)
        print(f"{source['name']} başarıyla güncellendi."); return True
    else: print(f"{source['name']} listesi güncel."); return False
def process_private_source(source):
    print(f"\n--- {source['name']} (Giriş Gerekli) Veri Kaynağı İşleniyor ---")
    username = os.getenv("TITCK_USERNAME")
    password = os.getenv("TITCK_PASSWORD")
    if not (username and password):
        print("UYARI: TITCK_USERNAME ve TITCK_PASSWORD secret'ları bulunamadı. Bu adım atlanıyor.")
        return False
    print("DEBUG: Secret'lar başarıyla okundu.")
    with requests.Session() as s:
        try:
            print(f"DEBUG: Adım 1 - Login sayfasına GET isteği atılıyor: {LOGIN_URL}")
            login_page_res = s.get(LOGIN_URL, headers=HEADERS, timeout=30); login_page_res.raise_for_status()
            soup = BeautifulSoup(login_page_res.content, 'html.parser')
            print("DEBUG: Adım 2 - Anti-CSRF token'ları aranıyor.")
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})
            eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})
            print(f"DEBUG: __VIEWSTATE bulundu mu? {'Evet' if viewstate else 'Hayır'}")
            print(f"DEBUG: __EVENTVALIDATION bulundu mu? {'Evet' if eventvalidation else 'Hayır'}")
            payload = {
                'username': username, 'password': password,
                '__VIEWSTATE': viewstate['value'] if viewstate else '',
                '__EVENTVALIDATION': eventvalidation['value'] if eventvalidation else '',
                'ctl00$ctl00$body$ContentPlaceHolder1$Login1$LoginButton': 'Giriş'
            }
            print("DEBUG: Adım 3 - Giriş için POST isteği atılıyor.")
            login_post_res = s.post(LOGIN_URL, data=payload, headers=HEADERS, timeout=30); login_post_res.raise_for_status()
            login_success_text = "Logout" in login_post_res.text or "Çıkış" in login_post_res.text
            print(f"DEBUG: Adım 4 - Giriş başarılı mı? -> {login_success_text}")
            if not login_success_text:
                 print("HATA: Giriş başarısız oldu. Kullanıcı adı/şifre hatalı veya site yapısı değişmiş.")
                 return False
            print("Giriş başarılı.")
            print("DEBUG: Adım 5 - Korumalı kaynak için 'process_data_source' çağrılıyor.")
            return process_data_source(source, session=s)
        except Exception as e:
            print(f"HATA: Özel kaynak işlenirken kritik bir hata oluştu: {e}")
            return False

# ----- GÜNCELLENEN ANA FONKSİYON -----
def main():
    print("--- Ana Script Başlatıldı ---")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    any_update_done = False
    updated_sources = []
    
    print("\n>>> Halka Açık Kaynaklar Döngüsü Başlatılıyor...")
    for source in PUBLIC_DATA_SOURCES:
        # ❗️❗️ YENİ EKLENEN SATIR ❗️❗️
        # Her bir kaynak arasında 5 saniye bekle
        print(f"DEBUG: Rate limiting'i önlemek için 5 saniye bekleniyor...")
        time.sleep(5)
        
        if process_data_source(source):
            any_update_done = True
            updated_sources.append(source['name'])
    print("<<< Halka Açık Kaynaklar Döngüsü Tamamlandı.")
    
    # ❗️❗️ YENİ EKLENEN SATIR ❗️❗️
    # Özel kaynağa geçmeden önce de bir bekleme ekleyelim
    print(f"DEBUG: Özel kaynağa geçmeden önce 5 saniye bekleniyor...")
    time.sleep(5)
    
    print("\n>>> Şifre Korumalı Kaynak İşlemi Başlatılıyor...")
    if process_private_source(PRIVATE_DATA_SOURCE):
        any_update_done = True
        updated_sources.append(PRIVATE_DATA_SOURCE['name'])
    print("<<< Şifre Korumalı Kaynak İşlemi Tamamlandı.")
    
    print("\n--- Sonuçlar Bildiriliyor ---")
    summary = f"Otomatik Veri Güncellemesi: {', '.join(updated_sources)}" if any_update_done else 'Veriler güncel, herhangi bir değişiklik yapılmadı.'
    set_github_action_output('updated', str(any_update_done).lower())
    set_github_action_output('summary', summary)
    print("--- Ana Script Tamamlandı ---")


if __name__ == "__main__":
    main()