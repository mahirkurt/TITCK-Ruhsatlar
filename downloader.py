# downloader.py (Opsiyonel CAPTCHA Çözücülü Nihai Hali)

import os
import sys
import requests
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from twocaptcha import TwoCaptcha

# --- KULLANICI AYARLARI ---
LOGIN_URL = "https://ebs.titck.gov.tr/Login/Login" # Doğru giriş URL'si
DOWNLOAD_PAGE_URL = "https://www.titck.gov.tr/dinamikmodul/100" # Örnek

# Gizli bilgileri ortam değişkenlerinden al
USERNAME = os.getenv("TITCK_USERNAME")
PASSWORD = os.getenv("TITCK_PASSWORD")
TWOCAPTCHA_API_KEY = os.getenv("TWOCAPTCHA_API_KEY")

# --- Klasör Tanımlamaları ---
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "ham_veriler"
CAPTCHA_IMAGE_PATH = BASE_DIR / "captcha_image.png"
OUTPUT_DIR.mkdir(exist_ok=True)


def solve_image_captcha(page, api_key):
    """Sayfadaki resimli CAPTCHA'yı 2Captcha ile çözer."""
    print("Resimli CAPTCHA tespit edildi. Çözüm deneniyor...")
    try:
        captcha_element = page.locator("#imgCaptcha")
        captcha_element.wait_for(timeout=10000)
        captcha_element.screenshot(path=CAPTCHA_IMAGE_PATH)
        
        print("Resim 2Captcha servisine gönderiliyor...")
        config = {'apiKey': api_key, 'defaultTimeout': 120, 'pollingInterval': 5}
        solver = TwoCaptcha(**config)
        result = solver.normal(str(CAPTCHA_IMAGE_PATH))
        
        captcha_text = result['code']
        print(f"CAPTCHA çözüldü! Çözüm: {captcha_text}")
        return captcha_text
    except Exception as e:
        print(f"CAPTCHA çözülürken bir hata oluştu: {e}")
        return None


def main():
    if not all([USERNAME, PASSWORD]):
        print("HATA: TITCK_USERNAME ve TITCK_PASSWORD secret'ları tanımlanmamış.")
        sys.exit(1)

    with sync_playwright() as p:
        print("Tarayıcı başlatılıyor...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            print(f"Giriş sayfasına gidiliyor: {LOGIN_URL}")
            page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3) # Sayfanın tam oturması için kısa bir bekleme

            # --- OPSİYONEL CAPTCHA KONTROLÜ ---
            # Sayfada CAPTCHA elementi var mı ve görünür mü diye kontrol et
            captcha_input_locator = page.locator("#GuvenlikKodu")
            if captcha_input_locator.is_visible():
                print("Giriş sayfasında CAPTCHA alanı bulundu.")
                if not TWOCAPTCHA_API_KEY:
                    raise Exception("CAPTCHA bulundu fakat TWOCAPTCHA_API_KEY secret'ı tanımlanmamış.")
                
                captcha_solution = solve_image_captcha(page, TWOCAPTCHA_API_KEY)
                if not captcha_solution:
                    raise Exception("CAPTCHA çözme işlemi başarısız oldu.")
                
                print("Güvenlik kodu giriliyor...")
                captcha_input_locator.fill(captcha_solution)
            else:
                print("CAPTCHA alanı bulunamadı. Normal giriş deneniyor.")

            # --- NORMAL GİRİŞ ADIMLARI ---
            print("Kullanıcı adı ve şifre giriliyor...")
            page.fill("#kullaniciAdi", USERNAME)
            page.fill("#sifre", PASSWORD)
            
            print("Giriş butonuna tıklanıyor...")
            page.click("button[type='submit']")
            
            print("Giriş yapılıyor, sayfanın yüklenmesi bekleniyor...")
            page.wait_for_load_state("networkidle", timeout=30000)

            # Girişin başarılı olup olmadığını kontrol et
            if "Login" in page.title() or "Giriş" in page.title():
                 raise Exception("Giriş başarısız oldu, hala giriş sayfasındayız. Bilgiler veya CAPTCHA çözümü yanlış olabilir.")
            print("Giriş başarılı!")

            # ... İndirme adımları buraya eklenecek ...
            # Önceki kodumuzdaki gibi devam edilebilir.
            
            print("Tüm işlemler başarıyla tamamlandı.")
            browser.close()

        except Exception as e:
            print(f"Ana otomasyon bloğunda bir hata oluştu: {e}")
            page.screenshot(path="debug_screenshot.png")
            print("Hata anının ekran görüntüsü 'debug_screenshot.png' olarak kaydedildi.")
            browser.close()
            sys.exit(1)


if __name__ == "__main__":
    main()