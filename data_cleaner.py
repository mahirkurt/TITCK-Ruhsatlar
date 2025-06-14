# -*- coding: utf-8 -*-
"""
Bu betik, TİTCK'dan indirilen çeşitli ham Excel dosyalarını okur,
temel temizlik yapar ve yapay zeka modellerinin kullanabileceği
temiz .jsonl formatında kaydeder.

Nihai Sürüm - Tüm dosyalar eklenmiştir.
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


def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    
    # İşlenecek dosyaların tam konfigürasyon listesi
    files_to_process = [
        {
            "input_filename": "ruhsatli_ilaclar_listesi.xlsx",
            "sheet_name": "RUHSATLI ÜRÜNLER LİSTESİ",
            "output_filename": "ruhsatli_urunler.jsonl",
            "header_row": 1,
            "column_map": {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma'}
        },
        {
            "input_filename": "etkin_madde_listesi.xlsx",
            "sheet_name": "Sheet1",
            "output_filename": "etkin_maddeler.jsonl",
            "header_row": 5,
            "column_map": {'Etkin Madde Adı': 'etkin_madde_adi', 'Sayı': 'basvuru_dosyasi_sayisi'}
        },
        {
            "input_filename": "yurtdisi_etkin_madde_listesi.xlsx",
            "sheet_name": "YD-Etkin madde listesi",
            "output_filename": "yurtdisi_etkin_maddeler.jsonl",
            "header_row": 1,
            "column_map": {'Etkin Madde': 'etkin_madde', 'Farmasötik Form': 'farmasotik_form', 'ATC Kodu': 'atc_kodu'}
        },
        # --- YENİ EKLENEN DOSYALAR ---
        {
            "input_filename": "skrs_erecete_listesi.xlsx",
            "sheet_name": "AKTİF ÜRÜNLER LİSTESİ",
            "output_filename": "skrs_aktif_urunler.jsonl",
            "header_row": 2,
            "column_map": {'İlaç Adı': 'urun_adi', 'Barkod': 'barkod', 'ATC Kodu': 'atc_kodu', 'Firma Adı': 'firma_adi'}
        },
        {
            "input_filename": "skrs_erecete_listesi.xlsx",
            "sheet_name": "PASİF ÜRÜNLER LİSTESİ",
            "output_filename": "skrs_pasif_urunler.jsonl",
            "header_row": 2,
            "column_map": {'İlaç Adı': 'urun_adi', 'Barkod': 'barkod', 'ATC Kodu': 'atc_kodu', 'Firma Adı': 'firma_adi'}
        }
        # -----------------------------
    ]
    
    all_success = True

    for config in files_to_process:
        filepath = RAW_DATA_DIR / config["input_filename"]
        if not filepath.exists():
            logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {filepath}")
            continue

        logging.info(f"'{config['input_filename']}' -> '{config['sheet_name']}' sayfası işleniyor...")
        try:
            df = pd.read_excel(filepath, sheet_name=config.get("sheet_name", 0), header=config["header_row"])
            
            existing_cols = [col for col in config["column_map"].keys() if col in df.columns]
            if not existing_cols:
                logging.error(f"'{config['sheet_name']}' sayfasında belirtilen sütunlardan hiçbiri bulunamadı.")
                all_success = False
                continue

            df = df[existing_cols]
            df.rename(columns=config["column_map"], inplace=True)
            df.dropna(how='all', inplace=True)
            
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].str.strip()

            processed_file_path = PROCESSED_DATA_DIR / config["output_filename"]
            df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
            logging.info(f"-> Başarıyla '{config['output_filename']}' olarak kaydedildi. ({len(df)} satır)")

        except Exception as e:
            logging.error(f"'{config['sheet_name']}' işlenirken KRİTİK HATA: {e}")
            all_success = False
            continue

    if all_success:
        logging.info("===== Tüm Dosyalar Başarıyla İşlendi =====")
    else:
        logging.error("!!! Bazı dosyalar işlenirken hatalar oluştu. Lütfen logları kontrol edin. !!!")
        sys.exit(1)


if __name__ == "__main__":
    main()