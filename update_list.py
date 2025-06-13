import os
import requests
import pandas as pd
from bs4 import BeautifulSoup

# --- SABİTLER ---
# TİTCK'nın dinamik modül sayfası
BASE_URL = "https://www.titck.gov.tr"
DATA_PAGE_URL = f"{BASE_URL}/dinamikmodul/85"

# Sunucuya normal bir tarayıcı gibi görünmek için User-Agent başlığı
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# İndirilen ve işlenen dosyaların adları
OUTPUT_DIR = "data"
LAST_KNOWN_FILE_RECORD = os.path.join(OUTPUT_DIR, "last_known_file.txt")
OUTPUT_XLSX_PATH = os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.xlsx")
OUTPUT_CSV_PATH = os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.csv")


def set_github_action_output(name, value):
    """
    GitHub Actions workflow'unda bir sonraki adımın kullanabilmesi için çıktı değişkeni ayarlar.
    Bu yöntem, eski '::set-output' komutundan daha yeni ve güvenlidir.
    """
    # GITHUB_OUTPUT ortam değişkeni, GitHub Actions tarafından sağlanır.
    # Bu değişkenin işaret ettiği dosyaya yazılan her satır bir çıktı olur.
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if github_output_file:
        with open(github_output_file, 'a') as f:
            # a: append modu, dosyanın sonuna ekler
            f.write(f"{name}={value}\n")
        print(f"GitHub Actions çıktısı ayarlandı: {name}={value}")
    else:
        print(f"Lokalde çalışılıyor, GitHub Actions çıktısı ayarlanmadı: {name}={value}")


def get_latest_file_info():
    """
    TİTCK sayfasını ziyaret eder ve en güncel Excel dosyası linkini ve adını bulur.
    """
    print(f"Sayfa kontrol ediliyor: {DATA_PAGE_URL}")
    try:
        response = requests.get(DATA_PAGE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()  # HTTP hatalarında exception fırlat
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        excel_link = soup.find('a', href=lambda href: href and href.endswith('.xlsx'))
        
        if not excel_link:
            print("HATA: Sayfada .xlsx uzantılı bir dosya linki bulunamadı.")
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
    """Verilen URL'den dosyayı indirir."""
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


def convert_xlsx_to_csv(xlsx_path, csv_path):
    """Excel dosyasını okur ve CSV formatına dönüştürür."""
    try:
        print(f"{xlsx_path} dosyası CSV'ye dönüştürülüyor...")
        # TİTCK dosyasının yapısına göre ilk 4 satırı atlıyoruz.
        # Bu yapı gelecekte değişirse bu sayının güncellenmesi gerekebilir.
        df = pd.read_excel(xlsx_path, skiprows=4)
        
        # Tamamen boş olan satırları veri setinden kaldır
        df.dropna(how='all', inplace=True)
        
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"CSV dosyası başarıyla oluşturuldu: {csv_path}")
        return True
    except Exception as e:
        print(f"HATA: Excel dosyası CSV'ye dönüştürülürken bir sorun oluştu: {e}")
        return False


def main():
    """Ana otomasyon fonksiyonu."""
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    latest_url, latest_name = get_latest_file_info()
    if not latest_url:
        set_github_action_output('updated', 'false')
        exit(1)

    last_known_name = ""
    if os.path.exists(LAST_KNOWN_FILE_RECORD):
        with open(LAST_KNOWN_FILE_RECORD, 'r') as f:
            last_known_name = f.read().strip()

    if latest_name != last_known_name:
        print("Yeni bir dosya tespit edildi. Güncelleme işlemi başlatılıyor...")
        
        if not download_file(latest_url, OUTPUT_XLSX_PATH):
             set_github_action_output('updated', 'false')
             exit(1)
        
        if not convert_xlsx_to_csv(OUTPUT_XLSX_PATH, OUTPUT_CSV_PATH):
            set_github_action_output('updated', 'false')
            exit(1)

        with open(LAST_KNOWN_FILE_RECORD, 'w') as f:
            f.write(latest_name)
            
        print("Güncelleme başarıyla tamamlandı.")
        set_github_action_output('updated', 'true')
    else:
        print("Mevcut liste güncel. Herhangi bir işlem yapılmadı.")
        set_github_action_output('updated', 'false')


if __name__ == "__main__":
    main()