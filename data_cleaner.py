# Dosya Adı: data_cleaner.py

import pandas as pd
from pathlib import Path
import sys
import logging
import re
import numpy as np

# --- Loglama ve Klasör Kurulumu ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s", stream=sys.stdout)
BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BASE_DIR / "ham_veriler"
PROCESSED_DATA_DIR = BASE_DIR / "islenmis_veriler"
RAW_DATA_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)


def process_file(config):
    """Genel bir dosya işleme fonksiyonu."""
    input_filename = config["input_filename"]
    sheet_name = config["sheet_name"]
    output_filename = config["output_filename"]
    header_row = config["header_row"]
    column_map = config["column_map"]
    
    filepath = RAW_DATA_DIR / input_filename
    if not filepath.exists():
        logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {filepath}")
        return True
    
    logging.info(f"'{input_filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=header_row, dtype=str)
        
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        if not existing_cols:
            logging.error(f"'{sheet_name}' sayfasında belirtilen sütunlardan hiçbiri bulunamadı. Lütfen Excel dosyasını ve column_map'i kontrol edin.")
            return False

        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)
        
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()

        processed_file_path = PROCESSED_DATA_DIR / output_filename
        df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"-> Başarıyla '{output_filename}' olarak kaydedildi. ({len(df)} satır)")
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False

def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    
    files_to_process = [
        {
            "input_filename": "ilac_fiyat_listesi.xlsx",
            "sheet_name": "REFERANS BAZLI İLAÇ LİSTESİ",
            "output_filename": "ilac_fiyatlari.jsonl",
            "header_row": 1,
            "column_map": {
                'ILAC ADI': 'urun_adi',
                'FIRMA ADI': 'firma_adi',
                'GERCEK KAYNAK FIYAT (GKF) (€)': 'gkf_eur'
            }
        },
        {
            "input_filename": "ruhsatli_ilaclar_listesi.xlsx",
            "sheet_name": "RUHSATLI ÜRÜNLER LİSTESİ",
            "output_filename": "ruhsatli_urunler.jsonl",
            "header_row": 1,
            "column_map": {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma'}
        }
        # İhtiyaç duyduğunuz diğer dosyaları bu listeye ekleyebilirsiniz.
    ]
    
    results = [process_file(config) for config in files_to_process]
    
    if all(results):
        logging.info("===== Tüm Dosyalar Başarıyla İşlendi =====")
    else:
        logging.error("!!! Bazı dosyalar işlenirken hatalar oluştu. Lütfen logları kontrol edin. !!!")
        sys.exit(1)

if __name__ == "__main__":
    main()