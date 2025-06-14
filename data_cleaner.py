# Dosya Adı: data_cleaner.py

# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path
import sys
import logging

# --- Loglama Yapılandırması ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] - %(message)s", stream=sys.stdout)
# --- Klasör Tanımlamaları ---
BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BASE_DIR / "ham_veriler"
PROCESSED_DATA_DIR = BASE_DIR / "islenmis_veriler"
RAW_DATA_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

def process_generic_file(input_filename, sheet_name, output_filename, header_row, column_map, text_columns=None, skip_footer=0):
    raw_file_path = RAW_DATA_DIR / input_filename
    if not raw_file_path.exists():
        logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {raw_file_path}")
        return True
    logging.info(f"'{input_filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        df = pd.read_excel(raw_file_path, sheet_name=sheet_name, header=header_row, skipfooter=skip_footer, dtype=text_columns)
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        if not existing_cols:
            logging.error(f"'{sheet_name}' sayfasında belirtilen sütunlardan hiçbiri bulunamadı."); return False
        df = df[existing_cols]; df.rename(columns=column_map, inplace=True); df.dropna(how='all', inplace=True)
        for col in df.select_dtypes(include=['object']).columns: df[col] = df[col].str.strip()
        processed_file_path = PROCESSED_DATA_DIR / output_filename
        df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"-> Başarıyla '{output_filename}' olarak kaydedildi. ({len(df)} satır)"); return True
    except Exception as e: logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}", exc_info=False); return False

def process_ilac_fiyat_listesi():
    column_map = {'ILAC ADI': 'urun_adi', 'FIRMA ADI': 'firma_adi', 'GERCEK KAYNAK FIYAT (GKF) (€)': 'gkf_eur'}
    return process_generic_file("ilac_fiyat_listesi.xlsx", "YURTDIŞI FİYAT LİSTESİ", "ilac_fiyatlari.jsonl", 0, column_map)

def process_ruhsatli_urunler():
    column_map = {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma', 'RUHSAT NUMARASI': 'ruhsat_no', 'RUHSAT TARİHİ': 'ruhsat_tarihi', 'RUHSATI ASKIDA OLMAYAN ÜRÜN': 'ruhsat_durumu', 'ASKIYA ALINMA TARİHİ': 'askiya_alinma_tarihi'}
    raw_file_path = RAW_DATA_DIR / "ruhsatli_ilaclar_listesi.xlsx"
    if not raw_file_path.exists(): logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {raw_file_path}"); return True
    logging.info("'ruhsatli_ilaclar_listesi.xlsx' -> 'RUHSATLI ÜRÜNLER LİSTESİ' sayfası işleniyor...")
    try:
        df = pd.read_excel(raw_file_path, sheet_name="RUHSATLI ÜRÜNLER LİSTESİ", header=5, dtype={'BARKOD': str, 'RUHSAT NUMARASI': str})
        existing_cols = [col for col in column_map.keys() if col in df.columns]; df = df[existing_cols]; df.rename(columns=column_map, inplace=True); df.dropna(how='all', inplace=True)
        ruhsat_map = {0: 'Ruhsat Geçerli', 1: 'Madde-23 Gerekçeli Askıda', 2: 'Farmakovijilans