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

# --- SABİTLER ve VERİ KAYNAKLARI ---
BASE_URL = "https://www.titck.gov.tr"
LOGIN_URL = f"{BASE_URL}/login"
OUTPUT_DIR = "data"
DOWNLOAD_DIR = os.path.abspath(OUTPUT_DIR)
PUBLIC_DATA_SOURCES = [
    {"name": "Ruhsatli_Urunler", "page_url": f"{BASE_URL}/dinamikmodul/85", "is_private": False, "skiprows": 4},
    {"name": "Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/100", "is_private": False, "skiprows": 3},
    {"name": "SKRS_E-Recete", "page_url": f"{BASE_URL}/dinamikmodul/43", "is_private": False, "skiprows": 0},
    {"name": "Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/108", "is_private": False, "skiprows": 3},
    {"name": "Yurtdisi_Etkin_Madde", "page_url": f"{BASE_URL}/dinamikmodul/126", "is_private": False, "skiprows": 3}
]
PRIVATE_DATA_SOURCE = {"name": "Detayli_Fiyat_Listesi", "page_url": f"{BASE_URL}/dinamikmodul/88", "is_private": True, "skiprows": 3}
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}

def setup_driver():
    print("DEBUG: Selenium WebDriver başlatılıyor...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("prefs", {"download.default_directory": DOWNLOAD_DIR})
    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def set_github_action_output(name, value):
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if github_output_file:
        with open(github_output_file, 'a') as f: f.write(f"{name}={value}\n")
    print(f"DEBUG: GHA Çıktısı Ayarlanıyor -> {name}={value}")

def process_source_with_selenium(driver, source):
    try:
        print(f"\n--- {source['name']} Veri Kaynağı İşleniyor ---")
        output_xlsx = os.path.join(DOWNLOAD_DIR, f"{source['name']}.xlsx")
        output_csv = os.path.join(DOWNLOAD_DIR, f"{source['name']}.csv")
        last_known_file_record = os.path.join(DOWNLOAD_DIR, f"last_known_file_{source['name']}.txt")
        
        print(f"DEBUG: Sayfaya gidiliyor: {source['page_url']}")
        driver.get(source['page_url'])
        
        wait = WebDriverWait(driver, 20) # Bekleme süresini biraz artırdım
        excel_link_element = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(@href, '.xlsx')]")))
        
        file_name = os.path.basename(excel_link_element.get_attribute('href'))
        print(f"Tespit edilen dosya: {file_name}")

        last_known_name = ""
        if os.path.exists(last_known_file_record):
            with open(last_known_file_record, 'r') as f: last_known_name = f.read().strip()

        if file_name != last_known_name:
            print(f"Yeni bir {source['name']} dosyası tespit edildi.")
            
            # Eski dosyaları temizle (varsa)
            if os.path.exists(output_xlsx): os.remove(output_xlsx)
            if os.path.exists(output_csv): os.remove(output_csv)

            print("DEBUG: Dosyayı indirmek için linke tıklanıyor...")
            excel_link_element.click()
            
            print("DEBUG: Dosya indirmesi için 30 saniye bekleniyor...")
            time.sleep(30)
            
            downloaded_files = [f for f in os.listdir(DOWNLOAD_DIR) if f.lower().endswith('.xlsx') and not f.startswith('~')]
            potential_file = os.path.join(DOWNLOAD_DIR, file_name)

            if os.path.exists(potential_file):
                shutil.move(potential_file, output_xlsx)
                print(f"İndirilen dosya taşındı ve yeniden adlandırıldı: {output_xlsx}")
            else:
                 print(f"HATA: Beklenen dosya '{potential_file}' indirme klasöründe bulunamadı.")
                 return False

            df = pd.read_excel(output_xlsx, skiprows=source['skiprows'])
            df.dropna(how='all', inplace=True); df.to_csv(output_csv, index=False, encoding='utf-8-sig')
            print(f"CSV oluşturuldu: {output_csv}")

            with open(last_known_file_record, 'w') as f: f.write(file_name)
            print(f"{source['name']} başarıyla güncellendi.")
            return True
        else:
            print(f"{source['name']} listesi güncel.")
            return False
            
    except Exception as e:
        print(f"HATA: {source['name']} işlenirken bir hata oluştu: {e}")
        driver.save_screenshot(f"{source['name']}_error.png")
        return False

def login_and_process_private(driver, source):
    print(f"\n--- {source['name']} (Nihai Selenium Metodu) Veri Kaynağı İşleniyor ---")
    username = os.getenv("TITCK_USERNAME")
    password = os.getenv("TITCK_PASSWORD")
    if not (username and password):
        print("UYARI: TITCK_USERNAME ve TITCK_PASSWORD secret'ları bulunamadı. Bu adım atlanıyor.")
        return False
    
    try:
        print(f"DEBUG: Selenium ile login sayfasına gidiliyor: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 15)
        
        print("DEBUG: Kullanıcı adı alanı bekleniyor ve dolduruluyor (ID ile)...")
        # ❗️❗️ DÜZELTME BURADA: By.NAME yerine By.ID ❗️❗️
        user_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
        user_field.send_keys(username)

        print("DEBUG: Şifre alanı bekleniyor ve dolduruluyor (ID ile)...")
        # ❗️❗️ DÜZELTME BURADA: By.NAME yerine By.ID ❗️❗️
        pass_field = wait.until(EC.visibility_of_element_located((By.ID, "password")))
        pass_field.send_keys(password)
        
        print("DEBUG: Giriş butonu bekleniyor ve tıklanıyor...")
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_button.click()
        
        print("DEBUG: Giriş sonrası yönlendirme için bekleniyor...")
        WebDriverWait(driver, 15).until(EC.url_changes(LOGIN_URL))
        
        if "login" in driver.current_url.lower():
            print("HATA: Giriş başarısız. Sayfa hala login ekranında."); return False
            
        print("Giriş başarılı.")
        return process_source_with_selenium(driver, source)

    except Exception as e:
        print(f"HATA: Giriş ve özel kaynak işlemi sırasında bir hata oluştu: {e}")
        driver.save_screenshot('login_fatal_error.png')
        return False

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    any_update_done = False
    updated_sources = []
    
    driver = setup_driver()
    is_logged_in = False
    
    try:
        for source in DATA_SOURCES:
            if source['is_private']:
                if not is_logged_in:
                    is_logged_in = login(driver) # Bu fonksiyonu ayrı tutmak daha temiz
                
                if is_logged_in:
                    if process_source_with_selenium(driver, source):
                        any_update_done = True
                        updated_sources.append(source['name'])
                else:
                    print("UYARI: Giriş yapılamadığı için özel kaynak atlanıyor.")
            else: # Public source
                if process_source_with_selenium(driver, source):
                    any_update_done = True
                    updated_sources.append(source['name'])
            
            time.sleep(3) # Her işlem arasında nezaketen bekle
    finally:
        if driver:
            driver.quit()
            print("DEBUG: Ana işlem sonunda WebDriver kapatıldı.")

    summary = f"Otomatik Veri Güncellemesi: {', '.join(updated_sources)}" if any_update_done else 'Tüm veriler güncel, herhangi bir değişiklik yapılmadı.'
    set_github_action_output('updated', str(any_update_done).lower())
    set_github_action_output('summary', summary)

if __name__ == "__main__":
    # Bu yeniden yapılandırma ile main fonksiyonunu basitleştirebiliriz.
    # Şimdilik bu şekilde bırakıyorum, çünkü hata ayıklaması daha kolay.
    # Önceki main() fonksiyonundaki mantığı koruyalım, daha sağlamdı.
    
    driver = setup_driver()
    try:
        # Önce halka açık olanları tek seferde halledelim.
        # Bu sunucunun hassasiyeti nedeniyle artık hepsini Selenium ile yapmak en mantıklısı.
        for source in [s for s in DATA_SOURCES if not s['is_private']]:
            if process_source_with_selenium(driver, source):
                any_update_done = True
                updated_sources.append(source['name'])
            time.sleep(3)

        # Sonra giriş yapıp özel olanı halledelim.
        private_source = next((s for s in DATA_SOURCES if s['is_private']), None)
        if private_source:
             if login_and_process_private(driver, private_source):
                 any_update_done = True
                 updated_sources.append(private_source['name'])

    finally:
        if driver:
            driver.quit()
            print("DEBUG: Ana işlem sonunda WebDriver kapatıldı.")
        
        summary = f"Otomatik Veri Güncellemesi: {', '.join(updated_sources)}" if any_update_done else 'Tüm veriler güncel, herhangi bir değişiklik yapılmadı.'
        set_github_action_output('updated', str(any_update_done).lower())
        set_github_action_output('summary', summary)