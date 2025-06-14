# -*- coding: utf-8 -*-
import pandas as pd; from pathlib import Path; import logging; import numpy as np; import re
logging.basicConfig(level=logging.INFO, format="%(message)s")
RAW_DATA_DIR = Path("ham_veriler")
PROCESSED_DATA_DIR = Path("islenmis_veriler")
PROCESSED_DATA_DIR.mkdir(exist_ok=True)

logging.info("-> 'yurtdisi_etkin_madde_listesi.xlsx' işleniyor...")
filepath = RAW_DATA_DIR / "yurtdisi_etkin_madde_listesi.xlsx"
if filepath.exists():
    try:
        column_map = {'Etkin Madde': 'etkin_madde', 'Farmasötik Form': 'farmasotik_form', 'TİTCK YAZILI ONAYI OLMADAN İTHAL EDİLEMEYECEK İLAÇLAR LİSTESİNDE YER ALAN ETKİN MADDELER': 'titck_onayi_gerekliligi', 'KULLANIM ŞARTLARI': 'kullanim_sartlari'}
        df = pd.read_excel(filepath, sheet_name="YD-Etkin madde listesi", header=1)
        df = df[list(column_map.keys())]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)
        if 'titck_onayi_gerekliligi' in df.columns: df['titck_onayi_gerekliligi'] = np.where(df['titck_onayi_gerekliligi'] == 1, 'TİTCK Onayı Gerekir', 'TİTCK Onayı Gerekmez')
        if 'kullanim_sartlari' in df.columns:
            def format_kullanim_sarti(text):
                if not isinstance(text, str): return ""
                text = re.sub(r'^\d+[\.\)]\s*', '', text.strip()); return text.capitalize() if text else ""
            df['kullanim_sartlari'] = df['kullanim_sartlari'].astype(str).apply(format_kullanim_sarti)
        df.to_json(PROCESSED_DATA_DIR / "yurtdisi_etkin_maddeler.jsonl", orient='records', lines=True, force_ascii=False)
        logging.info("   -> Başarılı.")
    except Exception as e:
        logging.error(f"   -> HATA: {e}")
else:
    logging.warning("   -> Dosya bulunamadı, atlanıyor.")