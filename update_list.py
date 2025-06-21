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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    stream=sys.stdout
)

# --- Sabitler ve Ana Yapılandırma ---
BASE_URL = "https://www.titck.gov.tr"
BASE_DIR = Path(__file__).resolve().parent
# İndirilen ham dosyaların kaydedileceği klasör ('data_cleaner.py' ile uyumlu)
OUTPUT_DIR = BASE_DIR / "ham_veriler"
DOWNLOAD_DIR = os.path.abspath(OUTPUT_DIR)

# --- İndirilecek Veri Kaynakları (Sadece Halka Açık Olanlar) ---
DATA_SOURCES = [
    {"name": "Ruhsatli_Urunler", "page_url": f"{BASE_URL}/dinamikmodul/85", "output_filename": "ruhsatli_ilaclar_listesi.xlsx"},
    {"name": "Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/100", "output_filename": "ilac_fiyat_listesi.xlsx"},
    {"name": "SKRS_E-Recete", "page_url": f"{BASE_URL}/dinamikmodul/43", "output_filename": "skrs_erecete_listesi.xlsx"},
    {"name": "Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/108", "output_filename": "etkin_madde_listesi.xlsx"},
    {"name": "Yurtdisi_Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/126", "output_filename": "yurtdisi_etkin_madde_listesi.xlsx"}
]

def setup_driver():
    """GitHub Actions ortamı ile uyumlu, kararlı bir Selenium WebDriver ayarlar ve başlatır."""
    logging.info("Selenium WebDriver başlatılıyor...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("prefs", {"download.default_directory": DOWNLOAD_DIR})

    # GitHub Actions tarafından sağlanan chromedriver yolunu kullanır
    driver_path = os.getenv("CHROME_DRIVER_PATH")
    if driver_path:
        logging.info(f"GitHub Actions tarafından sağlanan Chromedriver kullanılacak: {driver_path}")
        service = Service(executable_path=driver_path)
    else:
        logging.warning("Lokal ortamda çalışılıyor, otomatik Chromedriver kullanılacak.")
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

def process_source_with_selenium(driver, source):
    """Verilen driver'ı kullanarak tek bir kaynağı işler ve indirir."""
    try:
        logging.info(f"--- '{source['name']}' Veri Kaynağı İşleniyor ---")
        output_xlsx = os.path.join(DOWNLOAD_DIR, source['output_filename'])
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
            
            if os.path.exists(output_xlsx): os.remove(output_xlsx)

            excel_link_element.click()
            
            logging.info("Dosya indirmesinin tamamlanması için 60 saniye bekleniyor...")
            time.sleep(60)
            
            downloaded_file_path = os.path.join(DOWNLOAD_DIR, file_name_from_url)
            if not os.path.exists(downloaded_file_path):
                 logging.error(f"Beklenen dosya '{downloaded_file_path}' indirme klasöründe bulunamadı.")
                 return False, False # İndirme başarısız, güncelleme yok
            
            shutil.move(downloaded_file_path, output_xlsx)
            logging.info(f"İndirilen dosya '{output_xlsx}' olarak kaydedildi.")

            with open(last_known_file_record, 'w') as f:
                f.write(file_name_from_url)
            logging.info(f"'{source['name']}' başarıyla güncellendi.")
            return True, True # Başarılı, güncelleme var
        else:
            logging.info(f"'{source['name']}' listesi güncel. İşlem yapılmadı.")
            return True, False # Başarılı, güncelleme yok
            
    except Exception as e:
        logging.error(f"'{source['name']}' işlenirken bir hata oluştu: {e}")
        driver.save_screenshot(os.path.join(DOWNLOAD_DIR, f"{source['name']}_error.png"))
        return False, False # Başarısız, güncelleme yok

def main():
    """Ana program akışı: Tek bir Selenium oturumu ile tüm işlemleri yönetir."""
    logging.info("===== Ham Veri İndirme Başlatıldı =====")
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    updated_sources_names = []
    all_successful = True
    driver = None
    
    try:
        driver = setup_driver()
        
        for source in DATA_SOURCES:
            success, was_updated = process_source_with_selenium(driver, source)
            
            if was_updated:
                updated_sources_names.append(source['name'])
            
            if not success:
                all_successful = False
            
            if source != DATA_SOURCES[-1]:
                 logging.info("Sonraki kaynağa geçmeden önce 3 saniye bekleniyor...")
                 time.sleep(3)
    
    finally:
        if driver:
            driver.quit()
            logging.info("Selenium WebDriver kapatıldı.")

    summary = f"İndirilenler: {', '.join(updated_sources_names)}" if updated_sources_names else 'Yeni dosya bulunamadı.'
    set_github_action_output('updated', str(bool(updated_sources_names)).lower())
    set_github_action_output('summary', summary)
    
    if not all_successful:
        logging.error("İndirme sırasında bir veya daha fazla kaynakta hata oluştu.")
        sys.exit(1)
        
    logging.info("===== Ham Veri İndirme Tamamlandı =====")
    
if __name__ == "__main__":
    main()
