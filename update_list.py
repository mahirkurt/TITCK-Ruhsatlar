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
# Halka açık kaynaklar (5 adet)
PUBLIC_DATA_SOURCES = [
    {
        "name": "Ruhsatli_Urunler",
        "page_url": f"{BASE_URL}/dinamikmodul/85",
        "output_xlsx": os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.xlsx"),
        "output_csv": os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.csv"),
        "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_ruhsat.txt"),
        "skiprows": 4
    },
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
    "skiprows": 3
}

def set_github_action_output(name, value):
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if github_output_file:
        with open(github_output_file, 'a') as f: f.write(f"{name}={value}\n")
    print(f"GHA Çıktısı: {name}={value}")

def get_latest_file_info(page_url, session=None):
    print(f"Sayfa kontrol ediliyor: {page_url}")
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
    except requests.RequestException as e: print(f"HATA: {e}"); return None, None

def download_file(url, destination, session=None):
    print(f"Dosya indiriliyor: {url}")
    requester = session or requests
    try:
        with requester.get(url, headers=HEADERS, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(destination, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        print(f"İndirme başarılı: {destination}"); return True
    except requests.RequestException as e: print(f"HATA: {e}"); return False

def convert_xlsx_to_csv(xlsx_path, csv_path, rows_to_skip):
    print(f"CSV'ye dönüştürülüyor: {xlsx_path}")
    try:
        df = pd.read_excel(xlsx_path, skiprows=rows_to_skip)
        df.dropna(how='all', inplace=True); df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"CSV oluşturuldu: {csv_path}"); return True
    except Exception as e: print(f"HATA: {e}"); return False

def process_data_source(source, session=None):
    print(f"\n--- {source['name']} Veri Kaynağı İşleniyor ---")
    latest_url, latest_name = get_latest_file_info(source['page_url'], session=session)
    if not latest_url: return False
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

def process_private_source(source):
    print(f"\n--- {source['name']} (Giriş Gerekli) Veri Kaynağı İşleniyor ---")
    username = os.getenv("TITCK_USERNAME")
    password = os.getenv("TITCK_PASSWORD")
    if not (username and password):
        print("UYARI: TITCK_USERNAME ve TITCK_PASSWORD secret'ları bulunamadı. Bu adım atlanıyor.")
        return False
    with requests.Session() as s:
        try:
            print(f"Login sayfasına erişiliyor: {LOGIN_URL}")
            login_page_res = s.get(LOGIN_URL, headers=HEADERS); login_page_res.raise_for_status()
            soup = BeautifulSoup(login_page_res.content, 'html.parser')
            payload = {
                'username': username,
                'password': password,
                '__VIEWSTATE': soup.find('input', {'name': '__VIEWSTATE'})['value'] if soup.find('input', {'name': '__VIEWSTATE'}) else '',
                '__EVENTVALIDATION': soup.find('input', {'name': '__EVENTVALIDATION'})['value'] if soup.find('input', {'name': '__EVENTVALIDATION'}) else '',
                'ctl00$ctl00$body$ContentPlaceHolder1$Login1$LoginButton': 'Giriş'
            }
            print("Giriş yapılıyor...")
            login_post_res = s.post(LOGIN_URL, data=payload, headers=HEADERS); login_post_res.raise_for_status()
            if "Logout" not in login_post_res.text and "Çıkış" not in login_post_res.text:
                 print("HATA: Giriş başarısız oldu. Kullanıcı adı/şifre hatalı veya site yapısı değişmiş.")
                 return False
            print("Giriş başarılı.")
            return process_data_source(source, session=s)
        except Exception as e:
            print(f"HATA: Özel kaynak işlenirken bir hata oluştu: {e}")
            return False

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
    summary = f"Otomatik Veri Güncellemesi: {', '.join(updated_sources)}" if any_update_done else 'Veriler güncel, herhangi bir değişiklik yapılmadı.'
    set_github_action_output('summary', summary)

if __name__ == "__main__":
    main()