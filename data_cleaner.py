# -*- coding: utf-8 -*-
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

def process_yurtdisi_etkin_maddeler():
    """'yurtdisi_etkin_madde_listesi.xlsx' dosyasını özel kurallarla işler."""
    input_filename = "yurtdisi_etkin_madde_listesi.xlsx"
    sheet_name = "YD-Etkin madde listesi"
    output_filename = "yurtdisi_etkin_maddeler.jsonl"
    
    raw_file_path = RAW_DATA_DIR / input_filename
    if not raw_file_path.exists():
        logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {raw_file_path}")
        return True
    
    logging.info(f"'{input_filename}' -> '{sheet_name}' sayfası (özel kurallarla) işleniyor...")
    try:
        column_map = {
            'Etkin Madde Kodu': 'etkin_madde_kodu', 'Etkin Madde': 'etkin_madde', 'Farmasötik Form': 'farmasotik_form',
            'ATC Kodu': 'atc_kodu', 'ATC Adı': 'atc_adi', 'Reçete Türü': 'recete_turu',
            'TİTCK Yazılı Onayı Olmadan İthal Edilemeyecek İlaçlar': 'titck_onayi_gerekliligi',
            'ICD10 Kodu': 'icd10_kodu', 'ICD10 Adı': 'icd10_adi', 'Kullanım Şartları': 'kullanim_sartlari'
        }
        
        df = pd.read_excel(raw_file_path, sheet_name=sheet_name, header=1) # Başlıklar 2. satırda
        
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        # --- ÖZEL DÖNÜŞÜM KURALLARI ---

        # 1. TİTCK Onayı Kuralı
        df['titck_onayi_gerekliligi'] = np.where(df['titck_onayi_gerekliligi'] == 1, 'TİTCK Onayı Gerekir', 'TİTCK Onayı Gerekmez')

        # 2. ICD10 Adı Kuralı (Baş harfleri büyüt)
        df['icd10_adi'] = df['icd10_adi'].astype(str).apply(lambda x: '; '.join([name.strip().capitalize() for name in x.split(';')]))
        
        # 3. Kullanım Şartları Kuralı (Sayıları kaldır, cümle formatına getir)
        def format_kullanim_sarti(text):
            if not isinstance(text, str): return ""
            # Baştaki "1. ", "2. " gibi ifadeleri kaldır
            text = re.sub(r'^\d+\.\s*', '', text.strip())
            # Cümlenin sadece ilk harfini büyük yap
            return text.capitalize()

        df['kullanim_sartlari'] = df['kullanim_sartlari'].astype(str).apply(format_kullanim_sarti)

        # Diğer metin alanlarını temizle
        for col in ['etkin_madde', 'farmasotik_form', 'atc_adi', 'recete_turu', 'icd10_kodu']:
             if col in df.columns: df[col] = df[col].str.strip()
        
        processed_file_path = PROCESSED_DATA_DIR / output_filename
        df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"-> Başarıyla '{output_filename}' olarak kaydedildi. ({len(df)} satır)")
        return True
        
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}", exc_info=True) # Hata ayıklama için tam traceback
        return False

def process_ruhsatli_urunler():
    """Ruhsatlı ürünler listesini yeni kurallarla işler."""
    input_filename="ruhsatli_ilaclar_listesi.xlsx"
    sheet_name="RUHSATLI ÜRÜNLER LİSTESİ"
    output_filename="ruhsatli_urunler.jsonl"
    column_map = {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma', 'RUHSAT NUMARASI': 'ruhsat_no', 'RUHSAT TARİHİ': 'ruhsat_tarihi'}
    
    raw_file_path = RAW_DATA_DIR / input_filename
    if not raw_file_path.exists(): logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {raw_file_path}"); return True
    logging.info(f"'{input_filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        # İsteğiniz üzerine header=1 (2. satır) olarak güncellendi.
        df = pd.read_excel(raw_file_path, sheet_name=sheet_name, header=1, dtype={'BARKOD': str, 'RUHSAT NUMARASI': str})
        
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        if not existing_cols: logging.error(f"'{sheet_name}' sayfasında belirtilen sütunlardan hiçbiri bulunamadı."); return False
        
        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)
        
        for col in df.select_dtypes(include=['object']).columns: df[col] = df[col].str.strip()
        
        processed_file_path = PROCESSED_DATA_DIR / output_filename
        df.to_json(processed_file_path, orient='records', lines=True