# -*- coding: utf-8 -*-
"""
Bu betik, TİTCK'dan indirilen çeşitli ham Excel dosyalarını okur,
temizler, standardize eder, kodları metne çevirir
ve yapay zeka modellerinin kullanabileceği temiz .jsonl formatında kaydeder.

Nihai Sürüm - Tüm dosyalar ve özel kurallar dahildir.
"""
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


def get_file_path(filename):
    """Dosya yolunu oluşturur ve varlığını kontrol eder."""
    path = RAW_DATA_DIR / filename
    if not path.exists():
        logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {path}")
        return None
    return path

def save_as_jsonl(df, output_filename, original_filename=""):
    """DataFrame'i JSONL formatında kaydeder."""
    processed_file_path = PROCESSED_DATA_DIR / output_filename
    df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
    logging.info(f"-> '{original_filename}' başarıyla '{output_filename}' olarak kaydedildi. ({len(df)} satır)")

# ==============================================================================
# İŞLEYİCİ FONKSİYONLAR
# ==============================================================================

def process_ilac_fiyat_listesi():
    """'ilac_fiyat_listesi.xlsx' dosyasını, teşhis edilen doğru yapıya göre işler."""
    filename = "ilac_fiyat_listesi.xlsx"
    filepath = get_file_path(filename)
    if not filepath: return True
        
    sheet_name = "REFERANS BAZLI İLAÇ LİSTESİ"
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        column_map = {'ILAC ADI': 'urun_adi', 'FIRMA ADI': 'firma_adi', 'GERCEK KAYNAK FIYAT (GKF) (€)': 'gkf_eur'}
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=1, dtype=str)
        
        df = df[list(column_map.keys())]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        save_as_jsonl(df, "ilac_fiyatlari.jsonl", filename)
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False

def process_ruhsatli_urunler():
    """Ruhsatlı ürünler listesini işler ve ruhsat durum kodlarını metne çevirir."""
    filename = "ruhsatli_ilaclar_listesi.xlsx"
    filepath = get_file_path(filename)
    if not filepath: return True
    
    sheet_name = "RUHSATLI ÜRÜNLER LİSTESİ"
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        column_map = {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma', 'RUHSATI ASKIDA OLMAYAN ÜRÜN': 'ruhsat_durumu'}
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=1, dtype={'BARKOD': str})
        
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        if 'ruhsat_durumu' in df.columns:
            ruhsat_map = {0: 'Ruhsat Geçerli', 1: 'Madde-23 Gerekçeli Askıda', 2: 'Farmakovijilans Gerekçeli Askıda', 3: 'Madde-22 Gerekçeli Askıda'}
            df['ruhsat_durumu'] = pd.to_numeric(df['ruhsat_durumu'], errors='coerce').map(ruhsat_map).fillna('Bilinmeyen Durum Kodu')

        save_as_jsonl(df, "ruhsatli_urunler.jsonl", filename)
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False

def process_etkin_maddeler():
    """Etkin madde listesini işler."""
    filename = "etkin_madde_listesi.xlsx"
    filepath = get_file_path(filename)
    if not filepath: return True

    sheet_name = "Sheet1"
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        column_map = {'Etkin Madde Adı': 'etkin_madde_adi', 'Sayı': 'basvuru_dosyasi_sayisi'}
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=5, skipfooter=1)
        
        df = df[list(column_map.keys())]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        save_as_jsonl(df, "etkin_maddeler.jsonl", filename)
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False

def process_yurtdisi_etkin_maddeler():
    """Yurtdışı etkin madde listesini özel kurallarla işler."""
    filename = "yurtdisi_etkin_madde_listesi.xlsx"
    filepath = get_file_path(filename)
    if not filepath: return True
        
    sheet_name = "YD-Etkin madde listesi"
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası (özel kurallarla) işleniyor...")
    try:
        column_map = {'Etkin Madde': 'etkin_madde', 'Farmasötik Form': 'farmasotik_form', 'TİTCK YAZILI ONAYI OLMADAN İTHAL EDİLEMEYECEK İLAÇLAR LİSTESİNDE YER ALAN ETKİN MADDELER': 'titck_onayi_gerekliligi', 'KULLANIM ŞARTLARI': 'kullanim_sartlari'}
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=1)
        
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        if 'titck_onayi_gerekliligi' in df.columns:
            df['titck_onayi_gerekliligi'] = np.where(df['titck_onayi_gerekliligi'] == 1, 'TİTCK Onayı Gerekir', 'TİTCK Onayı Gerekmez')
        if 'kullanim_sartlari' in df.columns:
            def format_kullanim_sarti(text):
                if not isinstance(text, str): return ""
                text = re.sub(r'^\d+[\.\)]\s*', '', text.strip())
                return text.capitalize() if text else ""
            df['kullanim_sartlari'] = df['kullanim_sartlari'].astype(str).apply(format_kullanim_sarti)
        
        save_as_jsonl(df, "yurtdisi_etkin_maddeler.jsonl", filename)
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}", exc_info=True)
        return False

def process_skrs_erecete():
    """skrs_erecete_listesi.xlsx dosyasındaki AKTİF ve PASİF sayfalarını işler."""
    filename = "skrs_erecete_listesi.xlsx"
    filepath = get_file_path(filename)
    if not filepath: return True
    
    try:
        # AKTİF SAYFASI
        sheet_name_aktif = "AKTİF ÜRÜNLER LİSTESİ"
        if sheet_name_aktif in pd.ExcelFile(filepath).sheet_names:
            logging.info(f"'{filename}' -> '{sheet_name_aktif}' sayfası işleniyor...")
            column_map_aktif = {'İlaç Adı': 'urun_adi', 'Barkod': 'barkod', 'ATC Kodu': 'atc_kodu', 'Firma Adı': 'firma_adi'}
            df_aktif = pd.read_excel(filepath, sheet_name=sheet_name_aktif, header=2, dtype={'Barkod': str})
            df_aktif = df_aktif[list(column_map_aktif.keys())]
            df_aktif.rename(columns=column_map_aktif, inplace=True)
            df_aktif.dropna(how='all', inplace=True)
            save_as_jsonl(df_aktif, "skrs_aktif_urunler.jsonl", filename)
        
        # PASİF SAYFASI
        sheet_name_pasif = "PASİF ÜRÜNLER LİSTESİ"
        if sheet_name_pasif in pd.ExcelFile(filepath).sheet_names:
            logging.info(f"'{filename}' -> '{sheet_name_pasif}' sayfası işleniyor...")
            column_map_pasif = {'İlaç Adı': 'urun_adi', 'Barkod': 'barkod', 'ATC Kodu': 'atc_kodu', 'Firma Adı': 'firma_adi'}
            df_pasif = pd.read_excel(filepath, sheet_name=sheet_name_pasif, header=2, dtype={'Barkod': str})
            df_pasif = df_pasif[list(column_map_pasif.keys())]
            df_pasif.rename(columns=column_map_pasif, inplace=True)
            df_pasif.dropna(how='all', inplace=True)
            save_as_jsonl(df_pasif, "skrs_pasif_urunler.jsonl", filename)
    except Exception as e:
        logging.error(f"'{filename}' işlenirken KRİTİK HATA: {e}")
        return False
    return True

def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    
    results = [
        process_ilac_fiyat_listesi(),
        process_ruhsatli_urunler(),
        process_etkin_maddeler(),
        process_yurtdisi_etkin_maddeler(),
        process_skrs_erecete(),
    ]
    
    if all(results):
        logging.info("===== Tüm Dosyalar Başarıyla İşlendi =====")
    else:
        logging.error("!!! Bazı dosyalar işlenirken hatalar oluştu. Lütfen logları kontrol edin. !!!")
        sys.exit(1)

if __name__ == "__main__":
    main()
