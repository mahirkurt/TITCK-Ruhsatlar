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
OUTPUT_DIR = BASE_DIR / "ham_veriler"
DOWNLOAD_DIR = os.path.abspath(OUTPUT_DIR)

# --- İndirilecek Veri Kaynakları (Sadece Halka Açık Olanlar) ---
DATA_SOURCES = [
    {"name": "Ruhsatli_Urunler", "page_url": f"{BASE_URL}/dinamikmodul/85", "skiprows": 4, "output_filename": "ruhsatli_ilaclar_listesi.xlsx"},
    {"name": "Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/100", "skiprows": 3, "output_filename": "ilac_fiyat_listesi.xlsx"},
    {"name": "SKRS_E-Recete", "page_url": f"{BASE_URL}/dinamikmodul/43", "skiprows": 0, "output_filename": "skrs_erecete_listesi.xlsx"},
    {"name": "Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/108", "skiprows": 3, "output_filename": "etkin_madde_listesi.xlsx"},
    {"name": "Yurtdisi_Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/126", "skiprows": 3, "output_filename": "yurtdisi_etkin_madde_listesi.xlsx"}
]

def setup_driver():
    """Selenium WebDriver'ı ayarlar ve başlatır."""
    logging.info("Selenium WebDriver başlatılıyor...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("prefs", {"download.default_directory": DOWNLOAD_DIR})
    
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
            
            if os.path.exists(output_xlsx): os.remove(output_xlsx)

            excel_link_element.click()
            
            logging.info("Dosya indirmesinin tamamlanması için 60 saniye bekleniyor...")
            time.sleep(60)
            
            downloaded_file_path = os.path.join(DOWNLOAD_DIR, file_name_from_url)
            if not os.path.exists(downloaded_file_path):
                 logging.error(f"Beklenen dosya '{downloaded_file_path}' indirme klasöründe bulunamadı.")
                 return False
            
            shutil.move(downloaded_file_path, output_xlsx)
            logging.info(f"İndirilen dosya '{output_xlsx}' olarak kaydedildi.")

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
        driver.save_screenshot(os.path.join(DOWNLOAD_DIR, f"{source['name']}_error.png"))
        return False

def main():
    """Ana program akışı: Tek bir Selenium oturumu ile tüm işlemleri yönetir."""
    logging.info("===== Ham Veri İndirme Başlatıldı (Sadece Halka Açık) =====")
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    updated_sources = []
    driver = None
    
    try:
        driver = setup_driver()
        
        for source in DATA_SOURCES:
            if process_source_with_selenium(driver, source):
                updated_sources.append(source['name'])
            
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
    
if __name__ == "__main__":
    main()

