import os
import requests
import pandas as pd
from bs4 import BeautifulSoup

# --- SABİTLER ---
# TİTCK'nın dinamik modül sayfası
BASE_URL = "https://www.titck.gov.tr"
DATA_PAGE_URL = f"{BASE_URL}/dinamikmodul/85"

# İndirilen ve işlenen dosyaların adları
OUTPUT_DIR = "data"
LAST_KNOWN_FILE_RECORD = os.path.join(OUTPUT_DIR, "last_known_file.txt")
OUTPUT_XLSX_PATH = os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.xlsx")
OUTPUT_CSV_PATH = os.path.join(OUTPUT_DIR, "ruhsatli_ilaclar_listesi.csv")

def get_latest_file_info():
    """
    TİTCK sayfasını ziyaret eder ve en güncel Excel dosyası linkini ve adını bulur.
    """
    print(f"Sayfa kontrol ediliyor: {DATA_PAGE_URL}")
    try:
        response = requests.get(DATA_PAGE_URL, timeout=30)
        response.raise_for_status()  # HTTP hatalarında exception fırlat
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Sayfadaki '.xlsx' uzantılı linki arıyoruz.
        # Genellikle bu linkler belirli bir yapıya sahiptir. Bu yapı değişirse buranın güncellenmesi gerekir.
        excel_link = soup.find('a', href=lambda href: href and href.endswith('.xlsx'))
        
        if not excel_link:
            print("HATA: Sayfada .xlsx uzantılı bir dosya linki bulunamadı.")
            return None, None

        file_url = excel_link['href']
        file_name = os.path.basename(file_url)

        # Link göreceli olabilir (örn: /documents/...), bu durumda tam URL oluşturulur.
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
        with requests.get(url, stream=True, timeout=60) as r:
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
        # TİTCK dosyası genellikle ilk satırda bir başlık içerir, bu yüzden header=0 varsayımı genellikle yanlıştır.
        # Dosyanın yapısını inceleyip doğru 'skiprows' veya 'header' değerini bulmak gerekebilir.
        # Genellikle ilk birkaç satır boş veya birleşik hücre olabilir. 
        # Örnek olarak ilk 4 satırı atladığımızı varsayalım. Bu değer dosya değiştikçe ayarlanmalıdır.
        df = pd.read_excel(xlsx_path, skiprows=4)
        
        # Veri temizliği adımı eklenebilir. Örneğin tamamen boş satırları kaldırmak:
        df.dropna(how='all', inplace=True)
        
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"CSV dosyası başarıyla oluşturuldu: {csv_path}")
        return True
    except Exception as e:
        print(f"HATA: Excel dosyası CSV'ye dönüştürülürken bir sorun oluştu: {e}")
        return False

def main():
    """Ana otomasyon fonksiyonu."""
    
    # data klasörünün var olduğundan emin ol
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. En güncel dosya bilgisini webden al
    latest_url, latest_name = get_latest_file_info()
    if not latest_url:
        # Script'i sonlandır, çünkü devam etmek için link gerekli
        exit(1)

    # 2. Daha önce kaydedilen dosya adını kontrol et
    last_known_name = ""
    if os.path.exists(LAST_KNOWN_FILE_RECORD):
        with open(LAST_KNOWN_FILE_RECORD, 'r') as f:
            last_known_name = f.read().strip()

    # 3. Dosya adları farklıysa güncelleme yap
    if latest_name != last_known_name:
        print("Yeni bir dosya tespit edildi. Güncelleme işlemi başlatılıyor...")
        
        # Yeni dosyayı indir
        if not download_file(latest_url, OUTPUT_XLSX_PATH):
             exit(1) # İndirme başarısız olursa çık
        
        # Excel'i CSV'ye dönüştür
        if not convert_xlsx_to_csv(OUTPUT_XLSX_PATH, OUTPUT_CSV_PATH):
            exit(1) # Dönüştürme başarısız olursa çık

        # Başarılı olursa, en son dosya adını kaydet
        with open(LAST_KNOWN_FILE_RECORD, 'w') as f:
            f.write(latest_name)
            
        print("Güncelleme başarıyla tamamlandı.")
        # GitHub Actions'ın değişikliği algılaması için bir çıktı verelim
        # Bu, sonraki adımlarda kullanılabilir.
        print(f"::set-output name=updated::true")

    else:
        print("Mevcut liste güncel. Herhangi bir işlem yapılmadı.")
        print(f"::set-output name=updated::false")


if __name__ == "__main__":
    main()