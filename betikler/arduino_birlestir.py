"""
Hafta 6 - Adim 1b: Cycle I 'Arduino IoT Cloud Data' zip'lerini birlestirme.

Klasordeki butun ESP32-xx-historic-data-*.zip dosyalarini ACMADAN okur.
Her zip'in icindeki CSV'leri (ESP32_02-Hum_DHT21.csv gibi) kart + sensor
adina gore toplar, zamana gore siralar ve tekrar eden satirlari siler.
Sonuclari 'islenmis' klasorune yazar:
    islenmis/arduino_ESP32_02_Hum_DHT21.csv  ...
    islenmis/kesintiler_cycle1.csv          (Notes & drops.txt'teki kesintiler)
    islenmis/arduino_ozet.csv               (dosya basina ozet)

Kullanim (mantar-drl klasorunden):
    python betikler\\arduino_birlestir.py "D:\\...\\Sensor Data\\Cycle I\\Arduino IoT Cloud Data"
"""
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

# Notes & drops.txt'ten elle aktarildi (saatler UTC). bitis bos = belirtilmemis.
KESINTILER = [
    ("ESP32-01", "2023-01-10T21:55:24Z", None, "belirtilmemis"),
    ("ESP32-01", "2023-01-14T22:55:01Z", "2023-01-17T00:00:00Z", "belirtilmemis (yalniz gun verilmis)"),
    ("ESP32-01", "2023-01-20T14:50:25Z", "2023-01-21T18:23:03Z", "belirtilmemis"),
    ("ESP32-01", "2023-01-22T09:35:49Z", "2023-01-25T15:20:56Z", "belirtilmemis"),
    ("ESP32-01,ESP32-02", "2023-01-26T15:08:03Z", "2023-01-27T06:59:00Z", "elektrik"),
    ("ESP32-01,ESP32-02", "2023-02-01T10:26:58Z", "2023-02-03T10:15:18Z", "internet"),
    ("ESP32-01", "2023-02-17T08:07:29Z", None, "bakim"),
]
DONGU_SONU_UTC = "2023-03-02T08:33:51Z"


def deger_temizle(seri: pd.Series) -> pd.Series:
    """Metnin basindaki sayiyi alir ('17.44_x000D_\\n' -> 17.44)."""
    if pd.api.types.is_numeric_dtype(seri):
        return seri.astype(float)
    sayi = seri.astype(str).str.extract(r"^\s*(-?\d+(?:[.,]\d+)?)", expand=False)
    return pd.to_numeric(sayi.str.replace(",", ".", regex=False), errors="coerce")


def csv_oku(ham: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(ham), sep=None, engine="python")
    df.columns = [str(c).strip() for c in df.columns]
    zaman = df.columns[0]
    df[zaman] = pd.to_datetime(df[zaman], errors="coerce", utc=True)
    df = df.rename(columns={zaman: "zaman_utc"})
    for s in df.columns[1:]:
        df[s] = deger_temizle(df[s])
    return df


def calistir():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    kok = Path(sys.argv[1])
    ziplar = sorted(kok.glob("*.zip"))
    print(f"{len(ziplar)} zip bulundu: {kok}")
    cikti = kok / "islenmis"
    cikti.mkdir(exist_ok=True)

    parcalar: dict[str, list[pd.DataFrame]] = {}
    ilk_gosterildi = False
    for z in ziplar:
        try:
            with zipfile.ZipFile(z) as arsiv:
                for ad in arsiv.namelist():
                    if not ad.lower().endswith(".csv"):
                        continue
                    df = csv_oku(arsiv.read(ad))
                    if not ilk_gosterildi:
                        print("\nOrnek dosya:", z.name, "->", ad)
                        print(df.head(3).to_string(index=False), "\n")
                        ilk_gosterildi = True
                    anahtar = re.sub(r"[^A-Za-z0-9]+", "_", Path(ad).stem).strip("_")
                    parcalar.setdefault(anahtar, []).append(df)
        except zipfile.BadZipFile:
            print("  bozuk zip, atlandi:", z.name)

    ozet = []
    for anahtar, liste in sorted(parcalar.items()):
        df = pd.concat(liste, ignore_index=True)
        once = len(df)
        df = df.dropna(subset=["zaman_utc"]).drop_duplicates(subset=["zaman_utc"]).sort_values("zaman_utc")
        df.insert(1, "zaman_tr", df["zaman_utc"].dt.tz_convert("Europe/Istanbul"))
        df.to_csv(cikti / f"arduino_{anahtar}.csv", index=False, encoding="utf-8-sig")
        d = df[df.columns[2]]
        aralik = df["zaman_utc"].diff().dt.total_seconds().median()
        ozet.append({
            "dosya": anahtar, "zip_sayisi": len(liste), "ham_satir": once,
            "tekrarsiz_satir": len(df), "silinen_tekrar": once - len(df),
            "baslangic_tr": df["zaman_tr"].iloc[0].strftime("%Y-%m-%d %H:%M") if len(df) else "-",
            "bitis_tr": df["zaman_tr"].iloc[-1].strftime("%Y-%m-%d %H:%M") if len(df) else "-",
            "aralik_sn": round(aralik, 1) if pd.notna(aralik) else None,
            "sayi_degil": int(d.isna().sum()),
            "min": round(d.min(), 2), "ort": round(d.mean(), 2), "max": round(d.max(), 2),
        })

    kes = pd.DataFrame(KESINTILER, columns=["kart", "baslangic_utc", "bitis_utc", "neden"])
    for s in ["baslangic_utc", "bitis_utc"]:
        kes[s] = pd.to_datetime(kes[s], utc=True)
    kes.to_csv(cikti / "kesintiler_cycle1.csv", index=False, encoding="utf-8-sig")

    tablo = pd.DataFrame(ozet)
    tablo.to_csv(cikti / "arduino_ozet.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)
    print(tablo.to_string(index=False))
    print("\nDongu sonu (TR):", pd.Timestamp(DONGU_SONU_UTC).tz_convert("Europe/Istanbul"))
    print("Ciktilar:", cikti)


if __name__ == "__main__":
    calistir()