"""
Hafta 6 - Adim 1: Duman vd. (2024) istiridye serasi sensor verisini tanima.

Her Excel dosyasini okur, deger sutununu sayiya cevirir ve dosya basina
bir ozet basar: satir sayisi, baslangic/bitis, tipik kayit araligi,
sayiya cevrilemeyen satir, tekrar eden zaman damgasi, min/ortalama/max.

Kullanim (proje kok klasorunden):
    python kod\\veri\\veri_tanima.py kaynaklar\\veri\\duman2024_oyster\\"Sensor Data"

Gerekli paketler: pandas, openpyxl
    pip install pandas openpyxl
"""
import sys
from pathlib import Path

import pandas as pd


SAYI_DESENI = r"^\s*(-?\d+(?:[.,]\d+)?)"


def deger_temizle(seri: pd.Series) -> pd.Series:
    """Metnin basindaki sayiyi alir; cevrilemeyenler NaN olur.

    Ornekler: '707.92\\n\\n' -> 707.92
              '17.44_x000D_\\n_x000D_\\n' -> 17.44   (_x000D_ = Excel'in \\r kodu)
              '-127.00_x000D_\\n' -> -127.0          (DS18B20 hata kodu; temizlemede atilacak)
    """
    if pd.api.types.is_numeric_dtype(seri):
        return seri.astype(float)
    sayi = seri.astype(str).str.extract(SAYI_DESENI, expand=False)
    return pd.to_numeric(sayi.str.replace(",", ".", regex=False), errors="coerce")


def dosya_oku(yol: Path) -> pd.DataFrame:
    df = pd.read_excel(yol)
    df.columns = [str(c).strip() for c in df.columns]
    zaman_sutunu = df.columns[0]          # 'created_at'
    deger_sutunlari = df.columns[1:]
    df[zaman_sutunu] = pd.to_datetime(df[zaman_sutunu], errors="coerce", utc=True)
    df[zaman_sutunu] = df[zaman_sutunu].dt.tz_convert("Europe/Istanbul")
    for s in deger_sutunlari:
        df[s] = deger_temizle(df[s])
    return df.rename(columns={zaman_sutunu: "zaman"})


def ozet(yol: Path, df: pd.DataFrame) -> list[dict]:
    satirlar = []
    zaman = df["zaman"].dropna().sort_values()
    aralik = zaman.diff().dt.total_seconds().median() if len(zaman) > 1 else float("nan")
    for s in df.columns[1:]:
        d = df[s]
        satirlar.append({
            "dosya": yol.parent.name + "/" + yol.name,
            "sutun": s,
            "satir": len(df),
            "baslangic": zaman.iloc[0].strftime("%Y-%m-%d %H:%M") if len(zaman) else "-",
            "bitis": zaman.iloc[-1].strftime("%Y-%m-%d %H:%M") if len(zaman) else "-",
            "aralik_sn": round(aralik, 1),
            "bos_zaman": int(df["zaman"].isna().sum()),
            "sayi_degil": int(d.isna().sum()),
            "tekrar_zaman": int(df["zaman"].duplicated().sum()),
            "min": round(d.min(), 2),
            "ort": round(d.mean(), 2),
            "max": round(d.max(), 2),
        })
    return satirlar


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    kok = Path(sys.argv[1])
    # Betiklerin kendi ciktilarini (islenmis/, *ozet*.csv, kesintiler) okuma
    def ham_mi(p: Path) -> bool:
        return "islenmis" not in p.parts and "ozet" not in p.stem and "kesinti" not in p.stem
    dosyalar = [p for p in sorted(kok.rglob("*.xlsx")) + sorted(kok.rglob("*.csv")) if ham_mi(p)]
    if not dosyalar:
        print("Dosya bulunamadi:", kok.resolve())
        sys.exit(1)

    tum = []
    for yol in dosyalar:
        print("okunuyor:", yol)
        try:
            if yol.suffix == ".csv":
                df = pd.read_csv(yol)
                df.columns = [str(c).strip() for c in df.columns]
                df = df.rename(columns={df.columns[0]: "zaman"})
                df["zaman"] = pd.to_datetime(df["zaman"], errors="coerce", utc=True).dt.tz_convert("Europe/Istanbul")
                for s in df.columns[1:]:
                    df[s] = deger_temizle(df[s])
            else:
                df = dosya_oku(yol)
            tum.extend(ozet(yol, df))
        except Exception as e:
            print("  HATA:", e)

    tablo = pd.DataFrame(tum)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)
    print()
    print(tablo.to_string(index=False))
    cikti = kok / "veri_ozeti.csv"
    tablo.to_csv(cikti, index=False, encoding="utf-8-sig")
    print("\nOzet kaydedildi:", cikti)


if __name__ == "__main__":
    main()