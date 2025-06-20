#!/usr/bin/env python3
import sys
import os
import time
import shutil
import logging
from pathlib import Path
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Loglama ve Klasör Kurulumu ---
# Standart ve temiz bir loglama yapısı kuruyoruz.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    stream=sys.stdout
)

# --- Sabitler ve Ana Yapılandırma ---
BASE_URL = "https://www.titck.gov.tr"
LOGIN_URL = f"{BASE_URL}/login"
BASE_DIR = Path(__file__).resolve().parent
# İndirilen ham dosyaların kaydedileceği klasör ('data_cleaner.py' ile uyumlu)
OUTPUT_DIR = BASE_DIR / "ham_veriler"
# Selenium'un dosyaları indireceği klasörün tam yolunu alıyoruz.
DOWNLOAD_DIR = os.path.abspath(OUTPUT_DIR)

# --- İndirilecek Veri Kaynakları ---
# Tüm kaynakları tek bir listede, modüler bir yapıda tanımlıyoruz.
# 'is_private': Giriş yapma gerekliliğini belirtir.
# 'name': Dosya adlandırma ve loglama için kullanılır.
# 'output_filename': İndirildikten sonra dosyaya verilecek standart isim.
DATA_SOURCES = [
    {"name": "Ruhsatli_Urunler", "page_url": f"{BASE_URL}/dinamikmodul/85", "is_private": False, "skiprows": 4, "output_filename": "ruhsatli_ilaclar_listesi.xlsx"},
    {"name": "Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/100", "is_private": False, "skiprows": 3, "output_filename": "ilac_fiyat_listesi.xlsx"},
    {"name": "SKRS_E-Recete", "page_url": f"{BASE_URL}/dinamikmodul/43", "is_private": False, "skiprows": 0, "output_filename": "skrs_erecete_listesi.xlsx"},
    {"name": "Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/108", "is_private": False, "skiprows": 3, "output_filename": "etkin_madde_listesi.xlsx"},
    {"name": "Yurtdisi_Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/126", "is_private": False, "skiprows": 3, "output_filename": "yurtdisi_etkin_madde_listesi.xlsx"},
    {"name": "Detayli_Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/88", "is_private": True, "skiprows": 3, "output_filename": "detayli_ilac_fiyat_listesi.xlsx"}
]

def setup_driver():
    """
    GitHub Actions ortamı ile uyumlu, kararlı bir Selenium WebDriver ayarlar ve başlatır.
    """
    logging.info("Selenium WebDriver başlatılıyor...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Tarayıcıyı arayüz olmadan (arka planda) çalıştırır
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # Dosyaların doğrudan projedeki 'ham_veriler' klasörüne indirilmesini sağlar
    chrome_options.add_experimental_option("prefs", {"download.default_directory": DOWNLOAD_DIR})

    # GitHub Actions tarafından sağlanan chromedriver yolunu kullanır
    driver_path = os.getenv("CHROME_DRIVER_PATH")
    if driver_path:
        logging.info(f"GitHub Actions tarafından sağlanan Chromedriver kullanılacak: {driver_path}")
        service = Service(executable_path=driver_path)
    else:
        logging.info("Lokal ortamda otomatik Chromedriver kullanılacak.")
        service = Service()
        
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def set_github_action_output(name, value):
    """GitHub Actions için çıktı değişkeni ayarlar."""
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if github_output_file:
        with open(github_output_file, 'a') as f:
            f.write(f"{name}={value}\n")
    logging.info(f"GHA Çıktısı Ayarlandı -> {name}={value}")

def login(driver):
    """Verilen driver ile TİTCK sitesine giriş yapar."""
    username = os.getenv("TITCK_USERNAME")
    password = os.getenv("TITCK_PASSWORD")
    if not (username and password):
        logging.warning("TITCK_USERNAME ve TITCK_PASSWORD secret'ları bulunamadı. Giriş yapılamıyor.")
        return False
    
    try:
        logging.info(f"Selenium ile login sayfasına gidiliyor: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        # Akıllı Bekleme: Elementler görünür olana kadar 15 saniye bekler. Bu, zamanlama hatalarını önler.
        wait = WebDriverWait(driver, 15)
        
        logging.info("Kullanıcı adı alanı bekleniyor ve dolduruluyor (ID ile)...")
        user_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
        user_field.send_keys(username)

        logging.info("Şifre alanı bekleniyor ve dolduruluyor (ID ile)...")
        pass_field = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        pass_field.send_keys(password)
        
        logging.info("Giriş butonu bekleniyor ve tıklanıyor...")
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_button.click()
        
        logging.info("Giriş sonrası yönlendirme için bekleniyor...")
        WebDriverWait(driver, 15).until_not(EC.url_contains("login"))
        
        logging.info("Giriş başarılı.")
        return True

    except Exception as e:
        logging.error(f"Giriş işlemi sırasında bir hata oluştu: {e}")
        driver.save_screenshot('login_error.png') # Hata anının ekran görüntüsünü kaydet
        return False

def process_source_with_selenium(driver, source):
    """Verilen driver'ı kullanarak tek bir kaynağı işler."""
    try:
        logging.info(f"--- '{source['name']}' Veri Kaynağı İşleniyor ---")
        output_xlsx = os.path.join(DOWNLOAD_DIR, source['output_filename'])
        output_csv = os.path.join(DOWNLOAD_DIR, source['output_filename'].replace('.xlsx', '.csv'))
        last_known_file_record = os.path.join(DOWNLOAD_DIR, f"last_known_file_{source['name']}.txt")
        
        logging.info(f"Sayfaya gidiliyor: {source['page_url']}")
        driver.get(source['page_url'])
        
        wait = WebDriverWait(driver, 20)
        excel_link_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(@href, '.xlsx')]")))
        
        file_name_from_url = os.path.basename(excel_link_element.get_attribute('href'))
        logging.info(f"Tespit edilen dosya: {file_name_from_url}")

        last_known_name = ""
        if os.path.exists(last_known_file_record):
            with open(last_known_file_record, 'r') as f:
                last_known_name = f.read().strip()

        if file_name_from_url != last_known_name:
            logging.info(f"Yeni bir '{source['name']}' dosyası tespit edildi. İndirme başlıyor...")
            
            # Eski dosyaları temizle (varsa)
            if os.path.exists(output_xlsx): os.remove(output_xlsx)

            excel_link_element.click()
            
            logging.info("Dosya indirmesinin tamamlanması için 60 saniye bekleniyor...")
            time.sleep(60)
            
            # İndirilen dosyayı bulup doğru isme taşıma
            # Tarayıcının indirdiği orijinal isimli dosyayı bulup standart ismimize taşıyoruz.
            downloaded_file_path = os.path.join(DOWNLOAD_DIR, file_name_from_url)
            if not os.path.exists(downloaded_file_path):
                 logging.error(f"Beklenen dosya '{downloaded_file_path}' indirme klasöründe bulunamadı.")
                 return False
            
            shutil.move(downloaded_file_path, output_xlsx)
            logging.info(f"İndirilen dosya '{output_xlsx}' olarak kaydedildi.")

            # CSV'ye dönüştür
            df = pd.read_excel(output_xlsx, skiprows=source['skiprows'])
            df.dropna(how='all', inplace=True)
            df.to_csv(output_csv, index=False, encoding='utf-8-sig')
            logging.info(f"CSV oluşturuldu: {output_csv}")

            with open(last_known_file_record, 'w') as f:
                f.write(file_name_from_url)
            logging.info(f"'{source['name']}' başarıyla güncellendi.")
            return True
        else:
            logging.info(f"'{source['name']}' listesi güncel. İşlem yapılmadı.")
            return False
            
    except Exception as e:
        logging.error(f"'{source['name']}' işlenirken bir hata oluştu: {e}")
        driver.save_screenshot(f"{source['name']}_error.png")
        return False

def main():
    """Ana program akışı: Tek bir Selenium oturumu ile tüm işlemleri yönetir."""
    logging.info("===== Ham Veri İndirme Başlatıldı (Nihai Selenium Metodu) =====")
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    updated_sources = []
    driver = None
    is_logged_in = False
    
    try:
        driver = setup_driver()
        
        for source in DATA_SOURCES:
            if source['is_private'] and not is_logged_in:
                is_logged_in = login(driver)
                if not is_logged_in:
                    logging.error("Giriş başarısız olduğu için özel kaynaklar işlenemeyecek.")
                    break # Döngüden tamamen çık
            
            if source['is_private'] and not is_logged_in:
                logging.warning(f"Giriş yapılmadığı için '{source['name']}' atlanıyor.")
                continue

            if process_source_with_selenium(driver, source):
                updated_sources.append(source['name'])
            
            # Her işlem arasında nezaketen bekleme
            if source != DATA_SOURCES[-1]:
                 logging.info("Sonraki kaynağa geçmeden önce 3 saniye bekleniyor...")
                 time.sleep(3)
    
    finally:
        if driver:
            driver.quit()
            logging.info("Selenium WebDriver kapatıldı.")

    summary = f"Otomatik Veri Güncellemesi: {', '.join(updated_sources)}" if updated_sources else 'Tüm veriler güncel, herhangi bir değişiklik yapılmadı.'
    set_github_action_output('updated', str(bool(updated_sources)).lower())
    set_github_action_output('summary', summary)
    logging.info("===== Ham Veri İndirme Tamamlandı =====")
    if not all(res is not None for res in updated_sources):
        sys.exit(1)

if __name__ == "__main__":
    main()

