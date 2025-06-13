import os
import requests
import pandas as pd
from bs4 import BeautifulSoup

# --- SABİTLER ---
BASE_URL = "https://www.titck.gov.tr"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
OUTPUT_DIR = "data"

# --- YÖNETİLECEK VERİ KAYNAKLARI ---
# Sisteme yeni bir liste eklemek için bu listeye yeni bir sözlük eklemeniz yeterlidir.
DATA_SOURCES = [
    {
        "name": "Ruhsatli_Urunler",
        "page_url": f"{BASE_URL}/dinamikmodul/85",
        "output_xlsx": os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.xlsx"),
        "output_csv": os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.csv"),
        "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_ruhsat.txt"),
        "skiprows": 4 # Bu liste için Excel'de atlanacak satır sayısı
    },
    {
        "name": "Fiyat_Listesi",
        "page_url": f"{BASE_URL}/dinamikmodul/100",
        "output_xlsx": os.path.join(OUTPUT_DIR, "ilac_fiyat_listesi.xlsx"),
        "output_csv": os.path.join(OUTPUT_DIR, "ilac_fiyat_listesi.csv"),
        "last_known_file_record": os.path.join(OUTPUT_DIR, "last_known_file_fiyat.txt"),
        "skiprows": 3 # Bu liste için Excel'de atlanacak satır sayısı (değişebilir, kontrol edilmeli)
    }
]


def set_github_action_output(name, value):
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if github_output_file:
        with open(github_output_file, 'a') as f:
            f.write(f"{name}={value}\n")
        print(f"GitHub Actions çıktısı ayarlandı: {name}={value}")
    else:
        print(f"Lokalde çalışılıyor, GHA çıktısı ayarlanmadı: {name}={value}")

def get_latest_file_info(page_url):
    print(f"Sayfa kontrol ediliyor: {page_url}")
    try:
        response = requests.get(page_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        excel_link = soup.find('a', href=lambda href: href and href.endswith('.xlsx'))
        
        if not excel_link:
            print(f"HATA: Sayfada .xlsx uzantılı bir dosya linki bulunamadı: {page_url}")
            return None, None

        file_url = excel_link['href']
        file_name = os.path.basename(file_url)
        if not file_url.startswith('http'):
            file_url = f"{BASE_URL}{file_url}"
        
        print(f"Tespit edilen en güncel dosya: {file_name}")
        return file_url, file_name
    except requests.RequestException as e:
        print(f"HATA: Web sayfasına erişilirken bir sorun oluştu: {e}")
        return None, None

def download_file(url, destination):
    print(f"Dosya indiriliyor: {url}")
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(destination, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Dosya başarıyla indirildi: {destination}")
        return True
    except requests.RequestException as e:
        print(f"HATA: Dosya indirilirken bir sorun oluştu: {e}")
        return False

def convert_xlsx_to_csv(xlsx_path, csv_path, rows_to_skip):
    print(f"{xlsx_path} dosyası CSV'ye dönüştürülüyor...")
    try:
        df = pd.read_excel(xlsx_path, skiprows=rows_to_skip)
        df.dropna(how='all', inplace=True)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"CSV dosyası başarıyla oluşturuldu: {csv_path}")
        return True
    except Exception as e:
        print(f"HATA: Excel dosyası CSV'ye dönüştürülürken bir sorun oluştu: {e}")
        return False

def process_data_source(source):
    """
    Tek bir veri kaynağını işleyen genel fonksiyon.
    Güncelleme varsa True, yoksa False döner.
    """
    print(f"\n--- {source['name']} Veri Kaynağı İşleniyor ---")
    
    latest_url, latest_name = get_latest_file_info(source['page_url'])
    if not latest_url:
        return False

    last_known_name = ""
    if os.path.exists(source['last_known_file_record']):
        with open(source['last_known_file_record'], 'r') as f:
            last_known_name = f.read().strip()

    if latest_name != last_known_name:
        print(f"Yeni bir {source['name']} dosyası tespit edildi. Güncelleme işlemi başlatılıyor...")
        if not download_file(latest_url, source['output_xlsx']):
            return False
        if not convert_xlsx_to_csv(source['output_xlsx'], source['output_csv'], source['skiprows']):
            return False
        with open(source['last_known_file_record'], 'w') as f:
            f.write(latest_name)
        print(f"{source['name']} başarıyla güncellendi.")
        return True
    else:
        print(f"{source['name']} listesi güncel. İşlem yapılmadı.")
        return False

def main():
    """Ana otomasyon fonksiyonu."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    any_update_done = False
    updated_sources = []

    for source in DATA_SOURCES:
        was_updated = process_data_source(source)
        if was_updated:
            any_update_done = True
            updated_sources.append(source['name'])

    set_github_action_output('updated', str(any_update_done).lower())
    
    if any_update_done:
        summary = f"Otomatik Veri Güncellemesi: {', '.join(updated_sources)}"
        set_github_action_output('summary', summary)
    else:
        set_github_action_output('summary', 'Veriler güncel, herhangi bir değişiklik yapılmadı.')

if __name__ == "__main__":
    main()