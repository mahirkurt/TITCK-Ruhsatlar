import sys
import logging
from pathlib import Path
import pandas as pd

# --- Loglama ve Klasör Kurulumu ---
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] - %(message)s",
                    stream=sys.stdout)
BASE_DIR = Path(__file__).resolve().parent
# Script, dosyaları projenin ana dizinindeki 'ham_veriler' klasöründe arayacak
RAW_DATA_DIR = BASE_DIR.parent / "ham_veriler"
PROCESSED_DATA_DIR = BASE_DIR / "islenmis_veriler"
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
    df.to_json(processed_file_path,
              orient='records',
              lines=True,
              force_ascii=False)
    logging.info(f"-> '{original_filename}' başarıyla '{output_filename}' olarak kaydedildi. ({len(df)} satır)")

def process_generic_file(filename, sheet_name, output_filename,
                         header_row, column_map, dtype=None,
                         skip_footer=0):
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
            "skipfooter": skip_footer
        }
        # Hatalı "engine" atamasını kaldırıyoruz. Pandas doğru motoru kendi seçecek.
        df = pd.read_excel(filepath, **read_args)
        
        # Sütun adı sağlamlaştırması: Boşlukları temizle ve büyük harfe çevir
        df.columns = [str(col).strip().upper() for col in df.columns]
        
        # column_map'teki anahtarları da büyük harfe çevirerek karşılaştırma yap
        upper_column_map = {k.upper(): v for k, v in column_map.items()}
        
        existing_cols = [col for col in upper_column_map if col in df.columns]
        if not existing_cols:
            logging.error(f"'{sheet_name}' sayfasında beklenen sütunlardan hiçbiri bulunamadı. Lütfen Excel'deki sütun adlarını kontrol edin.")
            return False

        df = df[existing_cols]
        df.rename(columns=upper_column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()

        save_as_jsonl(df, output_filename, filename)
        return True
    except ValueError as e:
        # Sayfa bulunamadı hatasını daha net yakala
        if "Worksheet named" in str(e):
             logging.error(f"KRİTİK HATA: '{filename}' içinde '{sheet_name}' adında bir sayfa bulunamadı! Lütfen Excel dosyasını açıp doğru sayfa adını yazın.")
        else:
            logging.error(f"'{sheet_name}' işlenirken DEĞER HATASI: {e}", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}", exc_info=True)
        return False

# ======================================================================
# İŞLEYİCİ FONKSİYONLAR (Yeniden Düzenlendi)
# ======================================================================

def process_ilac_fiyat_listesi():
    """İlaç fiyat listesi dosyasını işler."""
    column_map = {
        'İLAÇ ADI': 'ilac_adi', 'FİRMA ADI': 'firma_adi',
        'GERÇEK KAYNAK FİYAT': 'gercek_kaynak_fiyat'
    }
    return process_generic_file(
        "ilac_fiyat_listesi.xlsx", "REFERANS BAZLI İLAÇ LİSTESİ",
        "ilac_fiyatlari.jsonl", 1, column_map, dtype=str
    )

def process_ruhsatli_urunler():
    """Ruhsatlı ürünler listesini işler."""
    column_map = {
        'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde',
        'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma',
        'RUHSAT NUMARASI': 'ruhsat_no', 'RUHSAT TARİHİ': 'ruhsat_tarihi',
        'RUHSATI ASKIDA OLMAYAN ÜRÜN': 'ruhsat_durumu', 'ASKIYA ALINMA TARİHİ': 'askiya_alinma_tarihi'
    }
    # Bu dosya özel işlem gerektirdiği için şimdilik generic fonksiyona sokulmadı.
    # Eğer bu da 0 satır veriyorsa, header=5 değeri veya sütun adları hatalıdır.
    filepath = get_file_path("ruhsatli_ilaclar_listesi.xlsx")
    if not filepath: return True
    try:
        df = pd.read_excel(filepath, sheet_name="RUHSATLI ÜRÜNLER LİSTESİ",
                           header=5, dtype={'BARKOD': str, 'RUHSAT NUMARASI': str})
        df.columns = [str(col).strip().upper() for col in df.columns]
        upper_column_map = {k.upper(): v for k, v in column_map.items()}
        existing_cols = [col for col in upper_column_map if col in df.columns]
        if not existing_cols:
             logging.error("'RUHSATLI ÜRÜNLER LİSTESİ' sayfasında beklenen sütunlar bulunamadı.")
             return False
        df = df[existing_cols].rename(columns=upper_column_map)
        df.dropna(how='all', inplace=True)
        if 'ruhsat_durumu' in df.columns:
            ruhsat_map = {0: 'RUHSAT GEÇERLİ', 1: 'MADDE-23 GEREKÇELİ ASKIDA', 2: 'FARMAKOVİJİLANS GEREKÇELİ ASKIDA', 3: 'MADDE-22 GEREKÇELİ ASKIDA'}
            df['ruhsat_durumu'] = df['ruhsat_durumu'].map(ruhsat_map).fillna('Bilinmeyen Durum Kodu')
        save_as_jsonl(df, "ruhsatli_urunler.jsonl", "ruhsatli_ilaclar_listesi.xlsx")
        return True
    except Exception as e:
        logging.error(f"'RUHSATLI ÜRÜNLER LİSTESİ' işlenirken KRİTİK HATA: {e}", exc_info=True)
        return False

def process_etkin_maddeler():
    """Etkin madde listesi dosyasını işler."""
    column_map = {'ETKİN MADDE': 'etkin_madde_adi', 'KODU': 'basvuru_dosyasi_sayisi'}
    return process_generic_file("etkin_madde_listesi.xlsx", "Sheet1",
        "etkin_maddeler.jsonl", 5, column_map, skip_footer=1)

def process_skrs_aktif_urunler():
    """SKRS aktif ürünler listesi dosyasını işler."""
    column_map = {
        'İLAÇ ADI': 'urun_adi', 'BARKOD': 'barkod', 'ATC KODU': 'atc_kodu',
        'ATC ADI': 'atc_adi', 'FİRMA ADI': 'firma_adi', 'REÇETE TÜRÜ': 'recete_turu'
    }
    return process_generic_file("skrs_erecete_listesi.xlsx", "AKTİF ÜRÜNLER LİSTESİ",
        "skrs_aktif_urunler.jsonl", 2, column_map, dtype={'BARKOD': str})

def process_skrs_pasif_urunler():
    """SKRS pasif ürünler listesi dosyasını işler."""
    column_map = {
        'İLAÇ ADI': 'urun_adi', 'BARKOD': 'barkod', 'ATC KODU': 'atc_kodu',
        'ATC ADI': 'atc_adi', 'FİRMA ADI': 'firma_adi', 'REÇETE TÜRÜ': 'recete_turu'
    }
    return process_generic_file("skrs_erecete_listesi.xlsx", "PASİF ÜRÜNLER LİSTESİ",
        "skrs_pasif_urunler.jsonl", 2, column_map, dtype={'BARKOD': str})

def process_yurtdisi_etkin_maddeler():
    """Yurtdışı etkin madde listesi dosyasını işler."""
    column_map = {
        'ETKİN MADDE ADI': 'etkin_madde', 'HASTALIK/TANI': 'hastalik_tani', 'KISITLAMA': 'kisitlama'
    }
    # ❗️❗️ DİKKAT: Bu sayfa adını Excel dosyasını açıp kontrol ederek güncellemelisiniz. ❗️❗️
    sheet_name = "SAYFA_ADINI_KONTROL_EDİN" 
    return process_generic_file("yurtdisi_etkin_madde_listesi.xlsx", sheet_name,
        "yurtdisi_etkin_maddeler.jsonl", 1, column_map)

def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    functions = [
        process_ilac_fiyat_listesi,
        process_ruhsatli_urunler,
        process_etkin_maddeler,
        process_skrs_aktif_urunler,
        process_skrs_pasif_urunler,
        process_yurtdisi_etkin_maddeler
    ]
    results = []
    for func in functions:
        logging.info(f"--- {func.__name__} çalıştırılıyor ---")
        results.append(func())

    if all(results):
        logging.info("===== Tüm Dosyalar Başarıyla İşlendi =====")
    else:
        logging.error("!!! Bazı dosyalar işlenirken hatalar oluştu. Lütfen logları kontrol edin. !!!")
        sys.exit(1)

if __name__ == "__main__":
    main()
