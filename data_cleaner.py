import sys
import logging
from pathlib import Path
import pandas as pd

# --- Loglama ve Klasör Kurulumu ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    stream=sys.stdout
)
BASE_DIR = Path(__file__).resolve().parent
# Ham verilerin okunacağı ve işlenmiş verilerin yazılacağı klasörleri belirliyoruz
RAW_DATA_DIR = BASE_DIR / "ham_veriler"
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
    df.to_json(
        processed_file_path,
        orient='records',
        lines=True,
        force_ascii=False
    )
    logging.info(f"-> '{original_filename}' başarıyla '{output_filename}' olarak kaydedildi. ({len(df)} satır)")


def process_generic_file(config):
    """
    Ortak Excel işleme ve JSONL kaydetme adımlarını gerçekleştiren ana fonksiyon.
    Konfigürasyon sözlüğü alır.
    """
    filename = config['filename']
    sheet_name = config['sheet_name']
    output_filename = config['output_filename']
    header_row = config['header_row']
    column_map = config['column_map']
    dtype = config.get('dtype') # dtype zorunlu değil
    
    filepath = get_file_path(filename)
    if not filepath:
        return True # Dosya yoksa başarılı say, devam et

    logging.info(f"'{filename}' -> '{sheet_name}' sayfası işleniyor...")
    try:
        # engine='openpyxl' parametresini açıkça belirtmek en sağlıklısıdır.
        df = pd.read_excel(
            filepath,
            sheet_name=sheet_name,
            header=header_row,
            dtype=dtype,
            engine='openpyxl'
        )
        
        # Sütun adı sağlamlaştırması: Boşlukları temizle ve büyük harfe çevir
        df.columns = [str(col).strip().upper() for col in df.columns]
        
        # column_map'teki anahtarları da büyük harfe çevirerek karşılaştırma yap
        upper_column_map = {k.upper(): v for k, v in column_map.items()}
        
        # DataFrame'de bulunan ve bizim istediğimiz sütunları filtrele
        existing_cols = [col for col in upper_column_map if col in df.columns]
        
        if not existing_cols:
            logging.error(f"'{sheet_name}' sayfasında beklenen sütunlardan hiçbiri bulunamadı. Lütfen Excel'deki sütun adlarını ve 'column_map'i kontrol edin.")
            return False

        df = df[existing_cols]
        df.rename(columns=upper_column_map, inplace=True)
        df.dropna(how='all', inplace=True)

        # Metin olan tüm sütunlardaki gereksiz boşlukları temizle
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()

        save_as_jsonl(df, output_filename, filename)
        return True
    
    except ValueError as e:
        # Sayfa bulunamadı hatasını daha net yakala ve kullanıcıyı yönlendir
        if "Worksheet named" in str(e):
             logging.error(f"KRİTİK HATA: '{filename}' içinde '{sheet_name}' adında bir sayfa bulunamadı! Lütfen Excel dosyasını açıp doğru sayfa adını yazın.")
        else:
            logging.error(f"'{sheet_name}' işlenirken DEĞER HATASI: {e}", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"'{sheet_name}' işlenirken KRİTİK HATA: {e}", exc_info=True)
        return False

# ======================================================================
# DOSYA İŞLEME KONFİGÜRASYONLARI
# ======================================================================

FILES_TO_PROCESS = [
    {
        "filename": "ilac_fiyat_listesi.xlsx",
        "sheet_name": "REFERANS BAZLI İLAÇ LİSTESİ",
        "output_filename": "ilac_fiyatlari.jsonl",
        "header_row": 1,
        "column_map": {
            'İLAÇ ADI': 'ilac_adi',
            'FİRMA ADI': 'firma_adi',
            'GERÇEK KAYNAK FİYAT': 'gercek_kaynak_fiyat'
        },
        "dtype": str
    },
    {
        "filename": "ruhsatli_ilaclar_listesi.xlsx",
        "sheet_name": "RUHSATLI ÜRÜNLER LİSTESİ",
        "output_filename": "ruhsatli_urunler.jsonl",
        "header_row": 5, # Bu dosyada başlıklar 6. satırda (index 5)
        "column_map": {
            'BARKOD': 'barkod', 'ÜRÜN ADI': 'urun_adi', 'ETKİN MADDE': 'etkin_madde',
            'ATC KODU': 'atc_kodu', 'RUHSAT SAHİBİ FİRMA': 'ruhsat_sahibi_firma',
            'RUHSAT NUMARASI': 'ruhsat_no', 'RUHSAT TARİHİ': 'ruhsat_tarihi',
        },
        "dtype": {'BARKOD': str, 'RUHSAT NUMARASI': str}
    },
    {
        "filename": "etkin_madde_listesi.xlsx",
        "sheet_name": "Sheet1", # Bu dosyanın sayfa adı genellikle "Sheet1" olur
        "output_filename": "etkin_maddeler.jsonl",
        "header_row": 5,
        "column_map": {'ETKİN MADDE': 'etkin_madde_adi', 'KODU': 'basvuru_dosyasi_sayisi'}
    },
    {
        "filename": "skrs_erecete_listesi.xlsx",
        "sheet_name": "AKTİF ÜRÜNLER LİSTESİ",
        "output_filename": "skrs_aktif_urunler.jsonl",
        "header_row": 2,
        "column_map": {
            'İLAÇ ADI': 'urun_adi', 'BARKOD': 'barkod', 'ATC KODU': 'atc_kodu',
            'ATC ADI': 'atc_adi', 'FİRMA ADI': 'firma_adi', 'REÇETE TÜRÜ': 'recete_turu'
        },
        "dtype": {'BARKOD': str}
    },
    {
        "filename": "skrs_erecete_listesi.xlsx",
        "sheet_name": "PASİF ÜRÜNLER LİSTESİ",
        "output_filename": "skrs_pasif_urunler.jsonl",
        "header_row": 2,
        "column_map": {
            'İLAÇ ADI': 'urun_adi', 'BARKOD': 'barkod', 'ATC KODU': 'atc_kodu',
            'ATC ADI': 'atc_adi', 'FİRMA ADI': 'firma_adi', 'REÇETE TÜRÜ': 'recete_turu'
        },
        "dtype": {'BARKOD': str}
    },
    {
        "filename": "yurtdisi_etkin_madde_listesi.xlsx",
        # ❗️❗️ DİKKAT: Bu sayfa adını Excel dosyasını açıp kontrol ederek güncellemelisiniz. ❗️❗️
        "sheet_name": "YD-ETKIN MADDE LISTESI", # Örnek ad, gerçek ad farklı olabilir
        "output_filename": "yurtdisi_etkin_maddeler.jsonl",
        "header_row": 1,
        "column_map": {
            'ETKİN MADDE ADI': 'etkin_madde',
            'HASTALIK/TANI': 'hastalik_tani',
            'KISITLAMA': 'kisitlama'
        }
    }
]

def main():
    """Tüm veri temizleme işlemlerini yürüten ana fonksiyon."""
    logging.info("===== Veri Temizleme ve Standardizasyon Başlatıldı =====")
    
    # Tüm dosyaları konfigürasyon listesinden işliyoruz
    results = [process_generic_file(config) for config in FILES_TO_PROCESS]

    if all(results):
        logging.info("===== Tüm Dosyalar Başarıyla İşlendi =====")
    else:
        logging.error("!!! Bazı dosyalar işlenirken hatalar oluştu. Lütfen logları kontrol edin. !!!")
        sys.exit(1)

if __name__ == "__main__":
    main()
