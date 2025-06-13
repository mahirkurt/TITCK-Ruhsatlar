import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

# --- SABİTLER ---
BASE_URL = "https://www.titck.gov.tr"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
OUTPUT_DIR = "data"
LOGIN_URL = f"{BASE_URL}/login"

# --- YÖNETİLECEK VERİ KAYNAKLARI ---
# Halka açık kaynaklar
PUBLIC_DATA_SOURCES = [
    {
        "name": "Ruhsatli_Urunler",
        "page_url": f"{BASE_URL}/dinamikmodul/85",
        "output_xlsx": os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.xlsx"),
        "output_csv": os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.csv"),
        "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_ruhsat.txt"),
        "skiprows": 4
    },
    # ... Diğer 4 halka açık kaynak tanımı burada ...
    {
        "name": "Fiyat_Listesi",
        "page_url": f"{BASE_URL}/dinamikmodul/100",
        "output_xlsx": os.path.join(OUTPUT_DIR, "ilac_fiyat_listesi.xlsx"),
        "output_csv": os.path.join(OUTPUT_DIR, "ilac_fiyat_listesi.csv"),
        "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_fiyat.txt"),
        "skiprows": 3
    },
    {
        "name": "SKRS_E-Recete",
        "page_url": f"{BASE_URL}/dinamikmodul/43",
        "output_xlsx": os.path.join(OUTPUT_DIR, "skrs_erecete_listesi.xlsx"),
        "output_csv": os.path.join(OUTPUT_DIR, "skrs_erecete_listesi.csv"),
        "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_skrs.txt"),
        "skiprows": 0
    },
    {
        "name": "Etkin_Madde",
        "page_url": f"{BASE_URL}/dinamikmodul/108",
        "output_xlsx": os.path.join(OUTPUT_DIR, "etkin_madde_listesi.xlsx"),
        "output_csv": os.path.join(OUTPUT_DIR, "etkin_madde_listesi.csv"),
        "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_etkinmadde.txt"),
        "skiprows": 3
    },
    {
        "name": "Yurtdisi_Etkin_Madde",
        "page_url": f"{BASE_URL}/dinamikmodul/126",
        "output_xlsx": os.path.join(OUTPUT_DIR, "yurtdisi_etkin_madde_listesi.xlsx"),
        "output_csv": os.path.join(OUTPUT_DIR, "yurtdisi_etkin_madde_listesi.csv"),
        "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_yurtdisi_etkinmadde.txt"),
        "skiprows": 3
    }
]

# Şifre korumalı kaynak
PRIVATE_DATA_SOURCE = {
    "name": "Detayli_Fiyat_Listesi",
    "page_url": f"{BASE_URL}/dinamikmodul/88",
    "output_xlsx": os.path.join(OUTPUT_DIR, "detayli_ilac_fiyat_listesi.xlsx"),
    "output_csv": os.path.join(OUTPUT_DIR, "detayli_ilac_fiyat_listesi.csv"),
    "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_detayli_fiyat.txt"),
    "skiprows": 3 # Değer kontrol edilmeli.
}

# ----- Yardımcı Fonksiyonlar (Değişiklik yok)-----
# ... set_github_action_output, get_latest_file_info, download_file, convert_xlsx_to_csv, process_data_source fonksiyonları öncekiyle aynı ...
# (Okunabilirliği artırmak için tekrar eklenmedi, önceki yanıttaki halleriyle aynı kalacaklar)
def set_github_action_output(name, value):
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if github_output_file:
        with open(github_output_file, 'a') as f: f.write(f"{name}={value}\n")
def get_latest_file_info(page_url, session=None): # session objesi eklendi
    print(f"Sayfa kontrol ediliyor: {page_url}")
    requester = session or requests
    try:
        response = requester.get(page_url, headers=HEADERS, timeout=30)
        response.raise_for_status(); soup = BeautifulSoup(response.content, 'html.parser')
        excel_link = soup.find('a', href=lambda href: href and href.endswith('.xlsx'))
        if not excel_link: return None, None
        file_url = excel_link['href']
        file_name = os.path.basename(file_url)
        if not file_url.startswith('http'): file_url = f"{BASE_URL}{file_url}"
        print(f"Tespit edilen en güncel dosya: {file_name}")
        return file_url, file_name
    except requests.RequestException as e: print(f"HATA: {e}"); return None, None
def download_file(url, destination, session=None): # session objesi eklendi
    print(f"Dosya indiriliyor: {url}")
    requester = session or requests
    try:
        with requester.get(url, headers=HEADERS, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(destination, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        print(f"Dosya başarıyla indirildi: {destination}"); return True
    except requests.RequestException as e: print(f"HATA: {e}"); return False
def convert_xlsx_to_csv(xlsx_path, csv_path, rows_to_skip):
    try:
        df = pd.read_excel(xlsx_path, skiprows=rows_to_skip)
        df.dropna(how='all', inplace=True); df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"CSV başarıyla oluşturuldu: {csv_path}"); return True
    except Exception as e: print(f"HATA: {e}"); return False
def process_data_source(source):
    print(f"\n--- {source['name']} Veri Kaynağı İşleniyor ---")
    latest_url, latest_name = get_latest_file_info(source['page_url'])
    if not latest_url: return False
    last_known_name = ""
    if os.path.exists(source['last_known_file_record']):
        with open(source['last_known_file_record'], 'r') as f: last_known_name = f.read().strip()
    if latest_name != last_known_name:
        print(f"Yeni bir {source['name']} dosyası tespit edildi...")
        if not download_file(latest_url, source['output_xlsx']): return False
        if not convert_xlsx_to_csv(source['output_xlsx'], source['output_csv'], source['skiprows']): return False
        with open(source['last_known_file_record'], 'w') as f: f.write(latest_name)
        print(f"{source['name']} başarıyla güncellendi."); return True
    else: print(f"{source['name']} listesi güncel."); return False

# ----- YENİ FONKSİYON: ŞİFRELİ KAYNAK İÇİN -----
def process_private_source(source):
    """
    Login gerektiren bir veri kaynağını işler.
    """
    print(f"\n--- {source['name']} (Giriş Gerekli) Veri Kaynağı İşleniyor ---")
    
    # Adım 1: Ortam değişkenlerinden Secret'ları oku
    username = os.getenv("TITCK_USERNAME")
    password = os.getenv("TITCK_PASSWORD")

    if not (username and password):
        print("HATA: TITCK_USERNAME ve TITCK_PASSWORD secret'ları bulunamadı. Bu adım atlanıyor.")
        return False
    
    # Adım 2: Oturum (Session) başlat
    with requests.Session() as s:
        try:
            # Adım 3: Login sayfasından anti-CSRF token'larını al (gerekliyse)
            print(f"Login sayfasına erişiliyor: {LOGIN_URL}")
            login_page_res = s.get(LOGIN_URL, headers=HEADERS)
            login_page_res.raise_for_status()
            soup = BeautifulSoup(login_page_res.content, 'html.parser')
            
            # ASP.NET sitelerinde yaygın olan token'lar
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})
            eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})

            # Adım 4: Giriş için payload'u hazırla
            payload = {
                'username': username,
                'password': password,
                '__VIEWSTATE': viewstate['value'] if viewstate else '',
                '__EVENTVALIDATION': eventvalidation['value'] if eventvalidation else '',
                'ctl00$ctl00$body$ContentPlaceHolder1$Login1$LoginButton': 'Giriş' # Butonun adı değişebilir
            }

            # Adım 5: Giriş yap (POST isteği)
            print("Giriş yapılıyor...")
            login_post_res = s.post(LOGIN_URL, data=payload, headers=HEADERS)
            login_post_res.raise_for_status()

            # Girişin başarılı olup olmadığını kontrol et (örneğin, "Hoş geldiniz" metni var mı?)
            if "Logout" not in login_post_res.text:
                 print("HATA: Giriş başarısız oldu. Kullanıcı adı/şifre hatalı veya site yapısı değişmiş.")
                 return False
            
            print("Giriş başarılı.")

            # Adım 6: Artık giriş yapılmış session ile korumalı sayfayı işle
            # Not: Korumalı sayfa için get_latest_file_info ve download_file fonksiyonlarına session'ı iletiyoruz.
            latest_url, latest_name = get_latest_file_info(source['page_url'], session=s)
            if not latest_url:
                return False

            last_known_name = ""
            if os.path.exists(source['last_known_file_record']):
                with open(source['last_known_file_record'], 'r') as f: last_known_name = f.read().strip()

            if latest_name != last_known_name:
                print(f"Yeni bir {source['name']} dosyası tespit edildi...")
                if not download_file(latest_url, source['output_xlsx'], session=s): return False
                if not convert_xlsx_to_csv(source['output_xlsx'], source['output_csv'], source['skiprows']): return False
                with open(source['last_known_file_record'], 'w') as f: f.write(latest_name)
                print(f"{source['name']} başarıyla güncellendi.")
                return True
            else:
                print(f"{source['name']} listesi güncel.")
                return False

        except Exception as e:
            print(f"HATA: Özel kaynak işlenirken bir hata oluştu: {e}")
            return False

# ----- GÜNCELLENMİŞ ANA FONKSİYON -----
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    any_update_done = False
    updated_sources = []

    # 1. Halka açık kaynakları işle
    for source in PUBLIC_DATA_SOURCES:
        if process_data_source(source):
            any_update_done = True
            updated_sources.append(source['name'])
    
    # 2. Şifre korumalı kaynağı işle
    if process_private_source(PRIVATE_DATA_SOURCE):
        any_update_done = True
        updated_sources.append(PRIVATE_DATA_SOURCE['name'])

    # 3. Sonuçları GHA'ya bildir
    set_github_action_output('updated', str(any_update_done).lower())
    if any_update_done:
        summary = f"Otomatik Veri Güncellemesi: {', '.join(updated_sources)}"
        set_github_action_output('summary', summary)
    else:
        set_github_action_output('summary', 'Veriler güncel, herhangi bir değişiklik yapılmadı.')

if __name__ == "__main__":
    main()