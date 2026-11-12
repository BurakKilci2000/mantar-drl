"""
Duman vd. (2024) istiridye mantari serasi sensor verisi: okuma ve temizleme.

Veri: Mendeley Data, doi:10.17632/hf55tkx489.1 (CC BY 4.0)
Makale: Duman, S. vd. (2024). Data in Brief, 57, 111074.

Temizleme sirasi (her seri icin):
  1. Sayiya cevirme  : '17.44_x000D_\\n' -> 17.44
  2. Hata kodlari    : sensorun bilinen hata degerleri -> NaN (DS18B20 -127 ve 85, CCS811 65535 ...)
  3. Fiziksel aralik : sensorun / seranin gercekte alamayacagi degerler -> NaN
  4. Sicrama         : 15 dakikalik kayan medyandan cok sapan tekil degerler -> NaN
  5. 5 dakikalik ortalama (yeniden ornekleme); her bin icin kac olcum dustugu da tutulur
Hicbir boslugu doldurmuyoruz (interpolasyon yok); bu karar sonraki adimlara birakildi.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SAAT_DILIMI = "Europe/Istanbul"
SAYI_DESENI = r"^\s*(-?\d+(?:[.,]\d+)?)"


@dataclass(frozen=True)
class Kural:
    degisken: str            # cikti sutun adinin ilk kismi
    birim: str
    hata_kodlari: tuple      # tam esit oldugunda atilacak degerler
    alt: float               # gecerli aralik (dahil)
    ust: float
    sicrama: float | None    # kayan medyandan izin verilen en buyuk sapma (None = kontrol yok)


# Dosya adindaki ifade -> kural. Sira onemli: ilk eslesen kullanilir.
KURALLAR: list[tuple[str, Kural]] = [
    (r"DS ?Temp|Temp_DS1820", Kural("torba_t", "°C", (-127.0, 85.0), -5, 40, 3.0)),
    (r"DHT ?Temp|Temp_DHT21", Kural("ortam_t", "°C", (-50.0, 149.9), -5, 40, 3.0)),
    (r"SHT ?Temp",            Kural("ortam_t", "°C", (), -5, 40, 3.0)),
    (r"DHT ?Hum|Hum_DHT21",   Kural("ortam_rh", "%", (0.0,), 1, 100, 15.0)),
    (r"SHT ?Hum",             Kural("ortam_rh", "%", (0.0,), 1, 100, 15.0)),
    (r"Res ?Moist|Moist_res", Kural("substrat_nem_res_ham", "ADC", (0.0, 4095.0), 1, 4094, None)),
    (r"Cap ?Moist|Moist_cap", Kural("substrat_nem_cap_ham", "ADC", (0.0, 4095.0), 1, 4094, None)),
    (r"CSS ?ECO2",            Kural("eco2_css", "ppm", (0.0, 65535.0), 400, 8192, None)),
    (r"CSS ?TVOC",            Kural("tvoc_css", "ppb", (65535.0,), 0, 1187, None)),
    # SGP30 eCO2, H2/etanoldan tahmin edilir; temizlik/hasat gunlerinde 50 000 ppm'e siciyor.
    # Oda havasinda CO2 pratikte 10 000 ppm'i asmaz -> ust sinir 10 000.
    (r"SGP ?ECO2",            Kural("eco2_sgp", "ppm", (60000.0,), 400, 10000, None)),
    (r"SGP ?TVOC",            Kural("tvoc_sgp", "ppb", (60000.0,), 0, 59999, None)),
]


def kural_bul(ad: str) -> Kural | None:
    for desen, kural in KURALLAR:
        if re.search(desen, ad, flags=re.IGNORECASE):
            return kural
    return None


def kaynak_adi(dosya: Path) -> str:
    """'DHT Temp - ESP1-2.xlsx' -> 'esp1_2' ; 'arduino_ESP32_02_Hum_DHT21.csv' -> 'esp32_02'"""
    m = re.search(r"ESP32_(\d+)", dosya.stem, flags=re.IGNORECASE)
    if m:
        return f"esp32_{m.group(1)}"
    m = re.search(r"-\s*(ESP[\w-]+)$", dosya.stem, flags=re.IGNORECASE)
    if m:
        return m.group(1).lower().replace("-", "_")
    return "bilinmiyor"


def sayiya_cevir(seri: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(seri):
        return seri.astype(float)
    sayi = seri.astype(str).str.extract(SAYI_DESENI, expand=False)
    return pd.to_numeric(sayi.str.replace(",", ".", regex=False), errors="coerce")


def ham_oku(dosya: Path) -> pd.Series:
    """Tek dosyayi zaman indeksli bir seri olarak okur (zaman: TR saati, tz bilgili)."""
    if dosya.suffix.lower() == ".xlsx":
        df = pd.read_excel(dosya)
    else:
        df = pd.read_csv(dosya)
    df.columns = [str(c).strip() for c in df.columns]
    zaman_sutunu = "zaman_utc" if "zaman_utc" in df.columns else df.columns[0]
    deger_sutunu = [c for c in df.columns if c not in (zaman_sutunu, "zaman_tr")][0]
    zaman = pd.to_datetime(df[zaman_sutunu], errors="coerce", utc=True).dt.tz_convert(SAAT_DILIMI)
    seri = pd.Series(sayiya_cevir(df[deger_sutunu]).to_numpy(), index=zaman)
    seri = seri[seri.index.notna()].sort_index()
    return seri[~seri.index.duplicated(keep="first")]


def temizle(seri: pd.Series, kural: Kural) -> tuple[pd.Series, dict]:
    """Kurallari sirayla uygular; her adimda kac deger atildigini raporlar."""
    s = seri.copy()
    rapor = {"ham": int(s.notna().sum())}

    hata = s.isin(kural.hata_kodlari)
    s[hata] = np.nan
    rapor["hata_kodu"] = int(hata.sum())

    disari = s.notna() & ((s < kural.alt) | (s > kural.ust))
    s[disari] = np.nan
    rapor["aralik_disi"] = int(disari.sum())

    sicrama_adet = 0
    if kural.sicrama is not None and s.notna().sum() > 10:
        medyan = s.rolling("15min", center=True, min_periods=3).median()
        sicrama = s.notna() & medyan.notna() & ((s - medyan).abs() > kural.sicrama)
        s[sicrama] = np.nan
        sicrama_adet = int(sicrama.sum())
    rapor["sicrama"] = sicrama_adet

    rapor["kalan"] = int(s.notna().sum())
    rapor["kalan_yuzde"] = round(100 * rapor["kalan"] / max(rapor["ham"], 1), 1)
    return s, rapor


def yeniden_ornekle(seri: pd.Series, adim: str = "5min") -> pd.DataFrame:
    """Ortalama + o bine dusen gecerli olcum sayisi (n). n=0 ise ortalama NaN kalir."""
    gruplar = seri.resample(adim)
    return pd.DataFrame({"ort": gruplar.mean(), "n": gruplar.count()})


# Her donguyu tek serilerle ozetlemek icin kaynak onceligi (EDA'da secildi):
# Cycle I'de ESP32-02 en saglam kart; Cycle II'de SHT (ESP3), DHT'den daha guvenilir.
ONCELIK = {
    "Cycle I": {
        "ortam_t": ["ortam_t__esp32_02", "ortam_t__esp32_01", "ortam_t__esp8266"],
        "ortam_rh": ["ortam_rh__esp32_02", "ortam_rh__esp32_01", "ortam_rh__esp8266"],
        "torba_t": ["torba_t__esp32_02", "torba_t__esp32_01", "torba_t__esp8266"],
    },
    "Cycle II": {
        "ortam_t": ["ortam_t__esp3", "ortam_t__esp1_2"],
        "ortam_rh": ["ortam_rh__esp3", "ortam_rh__esp1_2"],
        "torba_t": ["torba_t__esp1_2_3"],
    },
}


def ana_seriler(df: pd.DataFrame, dongu: str) -> pd.DataFrame:
    """Oncelik sirasina gore birlestirilmis ortam_t, ortam_rh, torba_t ve torba-ortam farki."""
    cikti = {}
    for ad, adaylar in ONCELIK[dongu].items():
        s = pd.Series(index=df.index, dtype=float)
        for a in adaylar:
            if a in df.columns:
                s = s.combine_first(df[a])
        cikti[ad] = s
    ana = pd.DataFrame(cikti)
    ana["fark"] = ana["torba_t"] - ana["ortam_t"]
    return ana


def temiz_oku(yol: Path) -> pd.DataFrame:
    """temizle_duman.py'nin yazdigi 5 dk'lik tabloyu okur."""
    return pd.read_csv(yol, encoding="utf-8-sig", parse_dates=["zaman"], index_col="zaman")


def dongu_dosyalari(sensor_kok: Path, dongu: str) -> list[Path]:
    """Bir donguye ait ham dosyalar: xlsx'ler + (varsa) islenmis Arduino CSV'leri."""
    klasor = sensor_kok / dongu
    dosyalar = sorted(klasor.glob("*.xlsx"))
    islenmis = klasor / "Arduino IoT Cloud Data" / "islenmis"
    if islenmis.exists():
        dosyalar += sorted(islenmis.glob("arduino_ESP32_*.csv"))
    return dosyalar


def kesintileri_oku(sensor_kok: Path, dongu: str) -> pd.DataFrame | None:
    yol = sensor_kok / dongu / "Arduino IoT Cloud Data" / "islenmis" / "kesintiler_cycle1.csv"
    if not yol.exists():
        return None
    k = pd.read_csv(yol)
    for s in ("baslangic_utc", "bitis_utc"):
        k[s] = pd.to_datetime(k[s], utc=True).dt.tz_convert(SAAT_DILIMI)
    return k


def donguyu_temizle(sensor_kok: Path, dongu: str, adim: str = "5min",
                    bitis: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bir dongunun butun serilerini temizler ve ortak 5 dk'lik tabloda birlestirir.

    Donus: (tablo, rapor). Tablo sutunlari '<degisken>__<kaynak>' ve '<...>__n'.
    """
    sutunlar, raporlar = {}, []
    for dosya in dongu_dosyalari(sensor_kok, dongu):
        kural = kural_bul(dosya.stem)
        if kural is None:
            print("  kural yok, atlandi:", dosya.name)
            continue
        print("  okunuyor:", dosya.name)
        ham = ham_oku(dosya)
        temiz, rapor = temizle(ham, kural)
        ad = f"{kural.degisken}__{kaynak_adi(dosya)}"
        if ad in sutunlar:            # ayni degisken + kaynak iki kez gelirse
            ad += "_2"
        bin_ = yeniden_ornekle(temiz, adim)
        sutunlar[ad] = bin_["ort"]
        sutunlar[ad + "__n"] = bin_["n"]
        raporlar.append({"dongu": dongu, "seri": ad, "birim": kural.birim, "dosya": dosya.name, **rapor})

    tablo = pd.DataFrame(sutunlar).sort_index()
    if bitis is not None:
        tablo = tablo[tablo.index <= pd.Timestamp(bitis).tz_convert(SAAT_DILIMI)]

    kes = kesintileri_oku(sensor_kok, dongu)
    if kes is not None:
        for kart in ("ESP32-01", "ESP32-02"):
            bayrak = pd.Series(False, index=tablo.index)
            for _, r in kes[kes["kart"].str.contains(kart)].iterrows():
                son = r["bitis_utc"]
                if pd.isna(son):      # bitis yazilmamis: kartin veri gondermeye dondugu ilk an
                    n_sutun = f"ortam_t__{kart.lower().replace('-', '_')}__n"
                    sonraki = tablo.index[(tablo.index > r["baslangic_utc"]) & (tablo.get(n_sutun, 0) > 0)]
                    son = sonraki[0] if len(sonraki) else tablo.index[-1]
                bayrak |= (tablo.index >= r["baslangic_utc"]) & (tablo.index <= son)
            tablo[f"kesinti__{kart.lower().replace('-', '_')}"] = bayrak

    return tablo, pd.DataFrame(raporlar)