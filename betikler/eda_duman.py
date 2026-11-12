"""
Hafta 6 - Adim 4: Duman 2024 istiridye serasi verisi icin kesifsel veri analizi (EDA).

Girdi : Sensor Data\\temiz\\cycle1_5dk.csv, cycle2_5dk.csv  (temizle_duman.py ciktisi)
Cikti : Sensor Data\\temiz\\grafikler\\*.png  ve  eda_ozet.csv

Kullanim (mantar-drl klasorunden):
    python betikler\\eda_duman.py "D:\\...\\duman2024_oyster\\Sensor Data"

Gerekli paket: matplotlib  (pip install matplotlib)
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

# Birlesik ("ana") seri icin kaynak onceligi: ilk dolu olan kullanilir.
ONCELIK = {
    "Cycle I": {
        "ortam_t": ["ortam_t__esp32_02", "ortam_t__esp32_01", "ortam_t__esp8266"],
        "ortam_rh": ["ortam_rh__esp32_02", "ortam_rh__esp32_01", "ortam_rh__esp8266"],
        "torba_t": ["torba_t__esp32_02", "torba_t__esp32_01", "torba_t__esp8266"],
    },
    "Cycle II": {
        "ortam_t": ["ortam_t__esp3", "ortam_t__esp1_2"],          # SHT once, DHT yedek
        "ortam_rh": ["ortam_rh__esp3", "ortam_rh__esp1_2"],
        "torba_t": ["torba_t__esp1_2_3"],
    },
}
DOSYA = {"Cycle I": "cycle1_5dk.csv", "Cycle II": "cycle2_5dk.csv"}

# Istiridye meyvelenme bandi: config.yaml'daki istiridye degerleriyle ESITLE.
BANT_T = (12.0, 20.0)
BANT_RH = (85.0, 95.0)


def oku(yol: Path) -> pd.DataFrame:
    df = pd.read_csv(yol, encoding="utf-8-sig", parse_dates=["zaman"], index_col="zaman")
    return df


def ana_seri(df: pd.DataFrame, adaylar: list[str]) -> pd.Series:
    s = pd.Series(index=df.index, dtype=float)
    for a in adaylar:
        if a in df.columns:
            s = s.combine_first(df[a])
    return s


def kesinti_golgele(ax, df: pd.DataFrame):
    for k in [c for c in df.columns if c.startswith("kesinti__")]:
        bayrak = df[k].astype(str).str.lower().eq("true")
        if not bayrak.any():
            continue
        grup = (bayrak != bayrak.shift()).cumsum()
        for _, parca in df[bayrak].groupby(grup[bayrak]):
            ax.axvspan(parca.index[0], parca.index[-1], color="grey", alpha=0.15, lw=0)


def zaman_serisi_ciz(df: pd.DataFrame, dongu: str, klasor: Path):
    paneller = [
        ("Sıcaklık (°C)", [c for c in df.columns if (c.startswith("ortam_t__") or c.startswith("torba_t__")) and not c.endswith("__n")]),
        ("Bağıl nem (%)", [c for c in df.columns if c.startswith("ortam_rh__") and not c.endswith("__n")]),
        ("Substrat nemi (ham ADC)", [c for c in df.columns if c.startswith("substrat_nem") and not c.endswith("__n")]),
        ("eCO₂ (ppm, tahmini)", [c for c in df.columns if c.startswith("eco2_") and not c.endswith("__n")]),
    ]
    paneller = [p for p in paneller if p[1]]
    fig, eksenler = plt.subplots(len(paneller), 1, figsize=(14, 3.2 * len(paneller)), sharex=True)
    if len(paneller) == 1:
        eksenler = [eksenler]
    for ax, (baslik, sutunlar) in zip(eksenler, paneller):
        saatlik = df[sutunlar].resample("1h").mean()
        for s in sutunlar:
            ax.plot(saatlik.index, saatlik[s], lw=0.8, label=s)
        kesinti_golgele(ax, df)
        ax.set_ylabel(baslik)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, ncol=3, loc="upper left")
    eksenler[0].set_title(f"{dongu} — saatlik ortalamalar (gri alan: bildirilen kesinti)")
    eksenler[-1].xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    fig.tight_layout()
    yol = klasor / f"{dongu.replace(' ', '').lower()}_zaman_serisi.png"
    fig.savefig(yol, dpi=130)
    plt.close(fig)
    print("  grafik:", yol.name)


def calistir():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    temiz = Path(sys.argv[1]) / "temiz"
    klasor = temiz / "grafikler"
    klasor.mkdir(exist_ok=True)

    ozet, profiller, farklar = [], {}, {}
    for dongu, dosya in DOSYA.items():
        yol = temiz / dosya
        if not yol.exists():
            print("bulunamadi:", yol)
            continue
        print(f"\n=== {dongu} ===")
        df = oku(yol)
        zaman_serisi_ciz(df, dongu, klasor)

        ana = pd.DataFrame({ad: ana_seri(df, adaylar) for ad, adaylar in ONCELIK[dongu].items()})
        ana["fark_torba_ortam"] = ana["torba_t"] - ana["ortam_t"]
        profiller[dongu] = ana.groupby(ana.index.hour).agg(["mean", "std"])
        farklar[dongu] = ana["fark_torba_ortam"].resample("1D").mean()

        gun = (df.index[-1] - df.index[0]).total_seconds() / 86400
        for s in ana.columns:
            x = ana[s].dropna()
            satir = {"dongu": dongu, "seri": s, "gun": round(gun, 1),
                     "dolu_yuzde": round(100 * len(x) / len(ana), 1),
                     "ort": round(x.mean(), 2), "std": round(x.std(), 2),
                     "p05": round(x.quantile(0.05), 2), "medyan": round(x.median(), 2),
                     "p95": round(x.quantile(0.95), 2)}
            if s == "ortam_t":
                satir["bantta_yuzde"] = round(100 * x.between(*BANT_T).mean(), 1)
            if s == "ortam_rh":
                satir["bantta_yuzde"] = round(100 * x.between(*BANT_RH).mean(), 1)
            ozet.append(satir)

        # Cycle II'de iki ortam sensoru ayni anda var: aralarindaki fark (sensor uyumu)
        if {"ortam_t__esp3", "ortam_t__esp1_2"} <= set(df.columns):
            d = (df["ortam_t__esp1_2"] - df["ortam_t__esp3"]).dropna()
            print(f"  DHT - SHT sicaklik farki: ort {d.mean():.2f} °C, std {d.std():.2f}")
        if {"ortam_rh__esp3", "ortam_rh__esp1_2"} <= set(df.columns):
            d = (df["ortam_rh__esp1_2"] - df["ortam_rh__esp3"]).dropna()
            print(f"  DHT - SHT nem farki    : ort {d.mean():.2f} puan, std {d.std():.2f}")

    # Gunluk (saat) profili
    fig, eksenler = plt.subplots(1, 3, figsize=(15, 4))
    for ax, s, etiket in zip(eksenler, ["ortam_t", "torba_t", "ortam_rh"],
                             ["Ortam sıcaklığı (°C)", "Torba sıcaklığı (°C)", "Ortam nemi (%)"]):
        for dongu, p in profiller.items():
            if s in p.columns.get_level_values(0):
                ort, std = p[(s, "mean")], p[(s, "std")]
                ax.plot(ort.index, ort, marker="o", ms=3, label=dongu)
                ax.fill_between(ort.index, ort - std, ort + std, alpha=0.15)
        ax.set_xlabel("Saat")
        ax.set_title(etiket)
        ax.set_xticks(range(0, 24, 3))
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("Günlük profil (saat başına ortalama ± std)")
    fig.tight_layout()
    fig.savefig(klasor / "gunluk_profil.png", dpi=130)
    plt.close(fig)
    print("\n  grafik: gunluk_profil.png")

    # Torba - ortam farki (misel isisi)
    fig, ax = plt.subplots(figsize=(12, 3.5))
    for dongu, f in farklar.items():
        gun_no = (f.index - f.index[0]).days
        ax.plot(gun_no, f.values, marker=".", label=dongu)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Döngünün günü")
    ax.set_ylabel("Torba − ortam (°C)")
    ax.set_title("Günlük ortalama torba–ortam sıcaklık farkı (misel ısısı göstergesi)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(klasor / "torba_ortam_farki.png", dpi=130)
    plt.close(fig)
    print("  grafik: torba_ortam_farki.png")

    tablo = pd.DataFrame(ozet)
    tablo.to_csv(temiz / "eda_ozet.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)
    print("\nEDA ozeti (ana seriler):")
    print(tablo.to_string(index=False))
    print(f"\nMeyvelenme bandi varsayimi: T {BANT_T} °C, RH {BANT_RH} % (config.yaml ile kontrol et)")
    print("Grafikler:", klasor)


if __name__ == "__main__":
    calistir()