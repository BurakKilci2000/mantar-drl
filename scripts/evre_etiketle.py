"""
Hafta 6 - Adim 3a: Uretim evrelerini (kolonizasyon / sok / meyvelenme) etiketleme.

Kurallar gunluk ortalamalar uzerinden, seffaf ve elle dogrulanabilir sekilde:
  1. Kolonizasyon tepe gunu : torba-ortam farkinin (misel isisi) en buyuk oldugu gun
  2. Sok baslangici         : tepe gununden sonra, ortam sicakliginin kolonizasyon ortalamasindan
                              en az SOK_DUSUS °C asagi indigi ilk gun
  3. Meyvelenme baslangici  : soktan sonra, fark < MEYVE_FARK ve nem >= MEYVE_RH olan
                              art arda 2 gunun ilki
Otomatik tarihler yanlis gorunurse asagidaki ELLE sozlugune tarih yazilarak degistirilebilir.

Kullanim (mantar-drl klasorunden):
    python scripts\\evre_etiketle.py "D:\\...\\duman2024_oyster\\Sensor Data"

Ciktilar (temiz\\ klasorune):
    evreler.csv             her dongu icin evre baslangic/bitis tarihleri
    cycle2_etiketli.csv     5 dk'lik tablo + 'evre' sutunu
    gunluk_tablo_cycle2.csv karar icin kullanilan gunluk degerler
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.duman2024 import ana_seriler, temiz_oku  # noqa: E402

SOK_DUSUS = 4.0     # °C
MEYVE_FARK = 2.0    # °C
MEYVE_RH = 85.0     # %

# Otomatik bulunan tarihi degistirmek icin: {"sok": "2023-03-27", "meyvelenme": "2023-04-01"}
ELLE: dict[str, str] = {"sok": "2023-03-28", "meyvelenme": "2023-04-02"}

def gunluk_tablo(ana: pd.DataFrame) -> pd.DataFrame:
    g = pd.DataFrame({
        "ortam_t": ana["ortam_t"].resample("1D").mean(),
        "ortam_t_min": ana["ortam_t"].resample("1D").min(),
        "ortam_rh": ana["ortam_rh"].resample("1D").mean(),
        "torba_t": ana["torba_t"].resample("1D").mean(),
        "fark": ana["fark"].resample("1D").mean(),
    })
    g.insert(0, "gun", range(len(g)))
    return g.round(2)


def evreleri_bul(g: pd.DataFrame) -> dict[str, pd.Timestamp]:
    gecerli = g.dropna(subset=["fark", "ortam_t"])
    tepe = gecerli["fark"].idxmax()
    kol_ort = gecerli.loc[:tepe, "ortam_t"].mean()

    sonrasi = gecerli.loc[tepe:]
    aday = sonrasi[sonrasi["ortam_t"] <= kol_ort - SOK_DUSUS]
    sok = aday.index[0] if len(aday) else None

    meyve = None
    if sok is not None:
        s = gecerli.loc[sok:]
        uygun = (s["fark"] < MEYVE_FARK) & (s["ortam_rh"] >= MEYVE_RH)
        iki_gun = uygun & uygun.shift(-1, fill_value=False)
        if iki_gun.any():
            meyve = iki_gun[iki_gun].index[0]

    bulunan = {"kolonizasyon_tepe": tepe, "sok": sok, "meyvelenme": meyve}
    for k, v in ELLE.items():
        bulunan[k] = pd.Timestamp(v)
    print(f"  kolonizasyon donemi ortam ortalamasi: {kol_ort:.1f} °C (sok esigi {kol_ort - SOK_DUSUS:.1f} °C)")
    return bulunan


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    temiz = Path(sys.argv[1]) / "temiz"

    df = temiz_oku(temiz / "cycle2_5dk.csv")
    ana = ana_seriler(df, "Cycle II")
    g = gunluk_tablo(ana)
    g.to_csv(temiz / "gunluk_tablo_cycle2.csv", encoding="utf-8-sig", date_format="%Y-%m-%d")

    print("=== Cycle II ===")
    t = evreleri_bul(g)
    for k, v in t.items():
        print(f"  {k:<18}: {v:%Y-%m-%d} (gun {g.loc[v, 'gun']})" if v is not None else f"  {k:<18}: bulunamadi")

    bas, son = df.index[0], df.index[-1]
    sinirlar = [("kolonizasyon", bas, t["sok"]),
                ("sok", t["sok"], t["meyvelenme"]),
                ("meyvelenme", t["meyvelenme"], son + pd.Timedelta("5min"))]
    evre = pd.Series("bilinmiyor", index=df.index)
    satirlar = []
    for ad, b, s in sinirlar:
        if b is None or s is None:
            continue
        evre[(df.index >= b) & (df.index < s)] = ad
        satirlar.append({"dongu": "Cycle II", "evre": ad, "baslangic": b, "bitis": s,
                         "sure_gun": round((s - b).total_seconds() / 86400, 1)})
    satirlar.append({"dongu": "Cycle I", "evre": "bilinmiyor", "baslangic": None, "bitis": None,
                     "sure_gun": None})   # torba sensoru 13. gunde basladi; goruntulerle belirlenecek

    pd.DataFrame(satirlar).to_csv(temiz / "evreler.csv", index=False, encoding="utf-8-sig")
    df.assign(evre=evre).to_csv(temiz / "cycle2_etiketli.csv", encoding="utf-8-sig",
                                date_format="%Y-%m-%d %H:%M", float_format="%.3f", index_label="zaman")

    # Evre bazinda ozet: simulasyon kalibrasyonu icin hedef degerler
    ozet = ana.assign(evre=evre).groupby("evre")[["ortam_t", "ortam_rh", "torba_t", "fark"]].agg(["mean", "std"]).round(2)
    pd.set_option("display.width", 250)
    print("\nKarar icin gunluk tablo (gun 0-25):")
    print(g.head(26).to_string())
    print("\nEvre bazinda ortalama ± std:")
    print(ozet.to_string())
    print("\nCiktilar:", temiz)


if __name__ == "__main__":
    main()