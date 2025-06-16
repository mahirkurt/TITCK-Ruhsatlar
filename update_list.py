import logging

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

def process_generic_file(filename, sheet_name, output_filename, header_row, column_map, dtype=None, skip_footer=0):
    """Ortak Excel işleme ve JSONL kaydetme adımlarını gerçekleştirir."""
    filepath = get_file_path(filename)
    if not filepath:
        return True

    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        read_args = {
            "sheet_name": sheet_name,
            "header": header_row,
            "dtype": dtype,
        }
        if skip_footer:
            read_args["skipfooter"] = skip_footer

        df = pd.read_excel(filepath, **read_args)

        existing_cols = [col for col in column_map.keys() if col in df.columns]
        if not existing_cols:
            logging.error(f"'{sheet_name}' sayfasında beklenen sütunlardan hiçbiri bulunamadı.")
            return False

        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()

        save_as_jsonl(df, output_filename, filename)
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False

# ==============================================================================
# İŞLEYİCİ FONKSİYONLAR
# ==============================================================================

def process_ilac_fiyat_listesi():
    """'ilac_fiyat_listesi.xlsx' dosyasını, içindeki gerçek sütunlara göre işler."""
    filename = "ilac_fiyat_listesi.xlsx"
    filepath = get_file_path(filename)
    if not filepath: return True
        
    sheet_name = "REFERANS BAZLI İLAÇ LİSTESİ"
    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        # --- DOĞRU SÜTUN ADLARI (Bu dosyanın gerçek içeriği) ---
        column_map = {
            'İLAÇ ADI': 'ILAC ADI',
            'FİRMA ADI': 'FIRMA ADI', 
            'GERÇEK KAYNAK FİYAT': 'GERCEK KAYNAK FIYAT', 
        }
        # -----------------------------------------------------------
        
        df = pd.read_excel(filepath, sheet_name=sheet_name, header=1, dtype=str) # header=1 (Excel'deki 2. satır)
        
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        if not existing_cols:
            logging.error(f"'{sheet_name}' sayfasında beklenen sütunlardan hiçbiri bulunamadı.")
            return False

        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        save_as_jsonl(df, "ilac_fiyatlari.jsonl", filename)
        return True
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}")
        return False

def process_ruhsatli_urunler():
    """Ruhsatlı ürünler listesini işler ve ruhsat durum kodlarını metne çevirir."""
    column_map = {'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde', 'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma', 'RUHSAT NUMARASI': 'ruhsat_no', 'RUHSAT TARİHİ': 'ruhsat_tarihi', 'RUHSATI ASKIDA OLMAYAN ÜRÜN': 'ruhsat_durumu', 'ASKIYA ALINMA TARİHİ': 'askiya_alinma_tarihi'}
    raw_file_path = RAW_DATA_DIR / "ruhsatli_ilaclar_listesi.xlsx"
    if not raw_file_path.exists():
        logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {raw_file_path}")
        return True
    logging.info("'ruhsatli_ilaclar_listesi.xlsx' -> 'RUHSATLI ÜRÜNLER LİSTESİ' sayfası işleniyor...")
    try:
        df = pd.read_excel(raw_file_path, sheet_name="RUHSATLI ÜRÜNLER LİSTESİ", header=5, dtype={'BARKOD': str, 'RUHSAT NUMARASI': str})
        existing_cols = [col for col in column_map.keys() if col in df.columns]
        df = df[existing_cols]
        df.rename(columns=column_map, inplace=True)
        df.dropna(how='all', inplace=True)
        ruhsat_map = {0: 'Ruhsat Geçerli', 1: 'Madde-23 Gerekçeli Askıda', 2: 'Farmakovijilans Gerekçeli Askıda', 3: 'Madde-22 Gerekçeli Askıda'}
        if 'ruhsat_durumu' in df.columns:
            df['ruhsat_durumu'] = df['ruhsat_durumu'].map(ruhsat_map).fillna('Bilinmeyen Durum Kodu')
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()
        processed_file_path = PROCESSED_DATA_DIR / "ruhsatli_urunler.jsonl"
        df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"-> Başarıyla 'ruhsatli_urunler.jsonl' olarak kaydedildi. ({len(df)} satır)")
        return True
    except Exception as e:
        logging.error(f"'RUHSATLI ÜRÜNLER LİSTESİ' işlenirken KRİTİK HATA: {e}", exc_info=False)
        return False

def process_etkin_maddeler():
    """Etkin madde listesini işler."""
    column_map = {'ETKİN MADDE': 'etkin_madde_adi', 'KODU': 'basvuru_dosyasi_sayisi'}
    return process_generic_file("etkin_madde_listesi.xlsx", "Sheet1", "etkin_maddeler.jsonl", 5, column_map, skip_footer=1)

def process_skrs_aktif_urunler():
    """SKRS Aktif ürünler listesini işler ve durum kodlarını metne çevirir."""
    column_map = {'İlaç Adı': 'urun_adi', 'Barkod': 'barkod', 'ATC Kodu': 'atc_kodu', 'ATC Adı': 'atc_adi', 'Firma Adı': 'firma_adi', 'Reçete Türü': 'recete_turu', 'Temel İlaç Listesi Durumu': 'temel_ilac_listesi_durumu', 'Çocuk Temel İlaç Listesi Durumu': 'cocuk_temel_ilac_listesi_durumu', 'Yenidoğan Temel İlaç Listesi Durumu': 'yenidogan_temel_ilac_listesi_durumu', 'Aktif Ürünler Listesine Alındığı Tarih': 'listeye_alinma_tarihi'}
    raw_file_path = RAW_DATA_DIR / "skrs_erecete_listesi.xlsx"
    if not raw_file_path.exists(): logging.warning(f"Kaynak dosya bulunamadı, atlanıyor: {raw_file_path}"); return True
    logging.info("'skrs_erecete_listesi.xlsx' -> 'AKTİF ÜRÜNLER LİSTESİ' sayfası işleniyor...")
    try:
        df = pd.read_excel(raw_file_path, sheet_name="AKTİF ÜRÜNLER LİSTESİ", header=2, dtype={'Barkod': str})
        existing_cols = [col for col in column_map.keys() if col in df.columns]; df = df[existing_cols]; df.rename(columns=column_map, inplace=True); df.dropna(how='all', inplace=True)
        durum_map = {0: 'Listede Değil', 1: 'Temel Listede', 2: 'Tamamlayıcı Listede'}
        durum_sutunlari = ['temel_ilac_listesi_durumu', 'cocuk_temel_ilac_listesi_durumu', 'yenidogan_temel_ilac_listesi_durumu']
        for col in durum_sutunlari:
            if col in df.columns: df[col] = df[col].map(durum_map).fillna('Bilinmeyen Kod (' + df[col].astype(str) + ')')
        for col in df.select_dtypes(include=['object']).columns: df[col] = df[col].str.strip()
        processed_file_path = PROCESSED_DATA_DIR / "skrs_aktif_urunler.jsonl"; df.to_json(processed_file_path, orient='records', lines=True, force_ascii=False)
        logging.info(f"-> Başarıyla 'skrs_aktif_urunler.jsonl' olarak kaydedildi. ({len(df)} satır)"); return True
    except Exception as e: logging.error(f"'AKTİF ÜRÜNLER LİSTESİ' işlenirken KRİTİK HATA: {e}", exc_info=False); return False

def process_skrs_pasif_urunler():
    """SKRS Pasif ürünler listesini işler."""
    column_map = {'İlaç Adı': 'urun_adi', 'Barkod': 'barkod', 'ATC Kodu': 'atc_kodu', 'ATC Adı': 'atc_adi', 'Firma Adı': 'firma_adi', 'Reçete Türü': 'recete_turu', 'Pasif Ürünler Listesine Alındığı Tarih': 'listeye_alinma_tarihi'}
    return process_generic_file("skrs_erecete_listesi.xlsx", "PASİF ÜRÜNLER LİSTESİ", "skrs_pasif_urunler.jsonl", 2, column_map, {'Barkod': str})

def process_yurtdisi_etkin_maddeler():
    """Yurtdışı etkin madde listesini işler."""
    column_map = {'ETKİN MADDE ADI': 'etkin_madde', 'HASTALIK/TANI': 'hastalik_tani', 'KISITLAMA': 'kisitlama'}
    return process_generic_file("yurtdisi_etkin_madde_listesi.xlsx", "YD-Etkin madde listesi", "yurtdisi_etkin_maddeler.jsonl", 1, column_map)

def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    
    results = [
        process_ilac_fiyat_listesi(),
        process_ruhsatli_urunler(),
        # İhtiyaç duyduğunuz diğer dosyalar için fonksiyonlar buraya eklenebilir.
    ]
    
    if all(results):
        logging.info("===== Tüm Dosyalar Başarıyla İşlendi =====")
    else:
        logging.error("!!! Bazı dosyalar işlenirken hatalar oluştu. Lütfen logları kontrol edin. !!!")
        sys.exit(1)


if __name__ == "__main__":
    main()
