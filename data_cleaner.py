# -*- coding: utf-8 -*-
"""
Bu betik, TİTCK'dan indirilen çeşitli ham Excel dosyalarını okur,
temizler, standardize eder ve yapay zeka modellerinin kullanabileceği
temiz .jsonl formatında kaydeder.

Nihai Sürüm - Sadece mevcut dosyaları işler.
"""
import pandas as pd
from pathlib import Path
import sys
import logging

# --- Loglama ve Klasör Kurulumu ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s", stream=sys.stdout)
BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BASE_DIR / "ham_veriler"
PROCESSED_DATA_DIR = BASE_DIR / "islenmis_veriler"
RAW_DATA_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

def process_ruhsatli_urunler():
    """Ruhsatlı ürünler listesini işler."""
    filename = "ruhsatli_ilaclar_listesi.xlsx"
    filepath = RAW_DATA_DIR / filename
    
    if not filepath.exists():
        logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {filepath}")
        return True # Dosya yoksa başarılı say, devam et
    
    sheet_name = "RUHSATLI ÜRÜNLER LİSTESİ"
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        # Sadece var olan ve ihtiyaç duyulan temel sütunlar
        column_map = {
            'BARKOD': 'barkod', 
            'ÜRÜN ADI': 'urun_adi', 
            'ETKİN MADDE': 'etkin_madde', 
            'ATC KODU': 'atc_kodu', 
            'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma'
        }
        
        # Başlıkların 2. satırda olduğunu biliyoruz (header=1)
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=1, dtype={'BARKOD': str})
        
        # Dosyada var olan ve bizim istediğimiz sütunları al
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        if not existing_cols:
            logging.error(f"'{sheet_name}' sayfasında belirtilen sütunlardan hiçbiri bulunamadı.")
            return False
            
        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        # Temizlenmiş dosyayı kaydet
        processed_file_path = PROCESSED_DATA_DIR / "ruhsatli_urunler.jsonl"
        df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"-> '{filename}' başarıyla 'ruhsatli_urunler.jsonl' olarak kaydedildi. ({len(df)} satır)")
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False

def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    
    # Sadece ve sadece ruhsatli_urunler fonksiyonunu çağırıyoruz.
    success = process_ruhsatli_urunler()
    
    if success:
        logging.info("===== İşlem Başarıyla Tamamlandı =====")
    else:
        logging.error("!!! İşlem sırasında bir hata oluştu. Lütfen logları kontrol edin. !!!")
        sys.exit(1)


if __name__ == "__main__":
    main()