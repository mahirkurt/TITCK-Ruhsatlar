import os
import time
import shutil
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- SABİTLER ---
BASE_URL = "https://www.titck.gov.tr"
LOGIN_URL = f"{BASE_URL}/login"
OUTPUT_DIR = "data"
# Klasörün tam yolunu alıyoruz, Selenium için bu gerekli.
DOWNLOAD_DIR = os.path.abspath(OUTPUT_DIR)

# --- VERİ KAYNAKLARI LİSTESİ ---
# is_private: Giriş yapma gerekliliğini belirtir.
# name: Dosya adlandırma ve loglama için kullanılır.
DATA_SOURCES = [
    {"name": "Ruhsatli_Urunler", "page_url": f"{BASE_URL}/dinamikmodul/85", "is_private": False, "skiprows": 4},
    {"name": "Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/100", "is_private": False, "skiprows": 3},
    {"name": "SKRS_E-Recete", "page_url": f"{BASE_URL}/dinamikmodul/43", "is_private": False, "skiprows": 0},
    {"name": "Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/108", "is_private": False, "skiprows": 3},
    {"name": "Yurtdisi_Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/126", "is_private": False, "skiprows": 3},
    {"name": "Detayli_Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/88", "is_private": True, "skiprows": 3}
]

def setup_driver():
    """Selenium WebDriver'ı ayarlar ve başlatır."""
    print("DEBUG: Selenium WebDriver başlatılıyor...")
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Tarayıcıyı arayüz olmadan çalıştırır
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Dosyaların doğrudan projedeki 'data' klasörüne indirilmesini sağlar
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
    print(f"DEBUG: GHA Çıktısı Ayarlanıyor -> {name}={value}")

def login(driver):
    """Verilen driver ile TİTCK sitesine giriş yapar."""
    username = os.getenv("TITCK_USERNAME")
    password = os.getenv("TITCK_PASSWORD")
    if not (username and password):
        print("UYARI: TITCK_USERNAME ve TITCK_PASSWORD secret'ları bulunamadı. Giriş yapılamıyor.")
        return False
    
    try:
        print(f"DEBUG: Selenium ile login sayfasına gidiliyor: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        # Akıllı Bekleme: Elementler görünür olana kadar 10 saniye bekler.
        wait = WebDriverWait(driver, 10)
        
        print("DEBUG: Kullanıcı adı alanı bekleniyor ve dolduruluyor (ID ile)...")
        # HTML'den bulduğumuz doğru ID'leri kullanıyoruz.
        user_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
        user_field.send_keys(username)

        print("DEBUG: Şifre alanı bekleniyor ve dolduruluyor (ID ile)...")
        pass_field = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        pass_field.send_keys(password)
        
        print("DEBUG: Giriş butonu bekleniyor ve tıklanıyor...")
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_button.click()
        
        print("DEBUG: Giriş sonrası yönlendirme için bekleniyor...")
        # Girişin başarılı olduğunu, URL'nin artık 'login' içermediğini kontrol ederek anlıyoruz.
        WebDriverWait(driver, 15).until_not(EC.url_contains("login"))
        
        print(f"DEBUG: Giriş sonrası mevcut URL: {driver.current_url}")
        print("Giriş başarılı.")
        return True

    except Exception as e:
        print(f"HATA: Giriş işlemi sırasında bir hata oluştu: {e}")
        driver.save_screenshot('login_error.png')
        return False

def process_source_with_selenium(driver, source):
    """Verilen driver'ı kullanarak tek bir kaynağı işler."""
    try:
        print(f"\n--- {source['name']} Veri Kaynağı İşleniyor ---")
        # Dosya yollarını her kaynak için özel olarak belirliyoruz.
        output_xlsx = os.path.join(DOWNLOAD_DIR, f"{source['name']}.xlsx")
        output_csv = os.path.join(DOWNLOAD_DIR, f"{source['name']}.csv")
        last_known_file_record = os.path.join(DOWNLOAD_DIR, f"last_known_file_{source['name']}.txt")
        
        print(f"DEBUG: Sayfaya gidiliyor: {source['page_url']}")
        driver.get(source['page_url'])
        
        wait = WebDriverWait(driver, 20)
        excel_link_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(@href, '.xlsx')]")))
        
        file_name_from_url = os.path.basename(excel_link_element.get_attribute('href'))
        print(f"Tespit edilen dosya: {file_name_from_url}")

        last_known_name = ""
        if os.path.exists(last_known_file_record):
            with open(last_known_file_record, 'r') as f:
                last_known_name = f.read().strip()

        if file_name_from_url != last_known_name:
            print(f"Yeni bir {source['name']} dosyası tespit edildi.")
            
            # Eski dosyaları temizle (varsa)
            if os.path.exists(output_xlsx): os.remove(output_xlsx)
            if os.path.exists(output_csv): os.remove(output_csv)

            print("DEBUG: Dosyayı indirmek için linke tıklanıyor...")
            excel_link_element.click()
            
            # Dosya indirmesinin tamamlanması için bekleme
            print("DEBUG: Dosya indirmesi için 45 saniye bekleniyor...")
            time.sleep(45)
            
            # İndirilen dosyayı bulup doğru isme taşıma mantığı
            # İndirilen dosyanın adının ne olacağını bilemeyebiliriz, bu yüzden klasördeki en yeni .xlsx'i buluruz.
            files_in_download_dir = [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.xlsx')]
            if not files_in_download_dir:
                 print("HATA: Dosya indirilemedi veya indirme klasöründe .xlsx bulunamadı.")
                 return False

            latest_file = max(files_in_download_dir, key=os.path.getctime)
            print(f"DEBUG: İndirilen dosya tespit edildi: {latest_file}")
            shutil.move(latest_file, output_xlsx)
            print(f"İndirilen dosya taşındı ve yeniden adlandırıldı: {output_xlsx}")

            # CSV'ye dönüştür
            df = pd.read_excel(output_xlsx, skiprows=source['skiprows'])
            df.dropna(how='all', inplace=True)
            df.to_csv(output_csv, index=False, encoding='utf-8-sig')
            print(f"CSV oluşturuldu: {output_csv}")

            with open(last_known_file_record, 'w') as f:
                f.write(file_name_from_url)
            print(f"{source['name']} başarıyla güncellendi.")
            return True
        else:
            print(f"{source['name']} listesi güncel.")
            return False
            
    except Exception as e:
        print(f"HATA: {source['name']} işlenirken bir hata oluştu: {e}")
        driver.save_screenshot(f"{source['name']}_error.png")
        return False

def main():
    """Ana program akışı"""
    print("--- Otomasyon Script'i Başlatıldı ---")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    updated_sources = []
    driver = setup_driver()
    is_logged_in = False
    
    try:
        # Tüm veri kaynakları için döngü
        for source in DATA_SOURCES:
            # Eğer kaynak özelse ve henüz giriş yapılmadıysa, giriş yap
            if source['is_private'] and not is_logged_in:
                is_logged_in = login(driver)
                # Giriş başarısızsa özel kaynakları atla
                if not is_logged_in:
                    print("UYARI: Giriş başarısız olduğu için kalan özel kaynaklar işlenemeyecek.")
                    break # Döngüden tamamen çık
            
            # Kaynağı işle (giriş yapılmışsa session cookie'leri ile, değilse normal)
            if process_source_with_selenium(driver, source):
                updated_sources.append(source['name'])
            
            print("DEBUG: Sonraki kaynağa geçmeden önce 3 saniye bekleniyor...")
            time.sleep(3)
    
    finally:
        # Her durumda WebDriver'ı güvenli bir şekilde kapat
        if driver:
            driver.quit()
            print("DEBUG: Ana işlem sonunda WebDriver kapatıldı.")

    # Sonucu GitHub Actions'a bildir
    summary = f"Otomatik Veri Güncellemesi: {', '.join(updated_sources)}" if updated_sources else 'Tüm veriler güncel, herhangi bir değişiklik yapılmadı.'
    set_github_action_output('updated', str(bool(updated_sources)).lower())
    set_github_action_output('summary', summary)
    print("--- Otomasyon Script'i Tamamlandı ---")

if __name__ == "__main__":
    main()