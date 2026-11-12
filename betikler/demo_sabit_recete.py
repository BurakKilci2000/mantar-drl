"""Duman testi: sabit reçeteyle bir üretim döngüsü çalıştırır, özeti yazdırır ve grafiği kaydeder.

Çalıştırma (proje kök klasöründen):  python -m betikler.demo_sabit_recete [istiridye|shiitake|aslan_yelesi]
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import yaml  # noqa: E402

from mantar_ortami.ortam import MantarOrtami  # noqa: E402
from rakipler.sabit_recete import SabitRecete  # noqa: E402


def gecici_parametreler(ayarlar: dict) -> list:
    return [k for k, v in ayarlar.items() if isinstance(v, dict) and v.get("tur") in ("gecici", "varsayim")]


def calistir(tur: str = "istiridye", tohum: int = 0) -> None:
    with open("config.yaml", encoding="utf-8") as f:
        ayarlar = yaml.safe_load(f)
    ortam = MantarOrtami(ayarlar, tur=tur)
    politika = SabitRecete(ortam)
    gozlem, bilgi = ortam.reset(seed=tohum)
    satirlar, toplam_odul, bitti = [], 0.0, False
    while not bitti:
        eylem = politika.eylem_sec(gozlem)
        gozlem, odul, terminated, truncated, bilgi = ortam.step(eylem)
        toplam_odul += odul
        g = bilgi["gozlem"]
        satirlar.append({"gun": g["dongu_gunu"], "T": g["sicaklik_c"], "BN": g["bagil_nem"], "CO2": g["co2_ppm"],
                         "kol": g["kolonizasyon_gozlenen"], "kah": g["kahverengilesme_orani"],
                         "biyo": g["biyokutle_orani"], "evre": bilgi["evre"], "kwh": bilgi["enerji_kwh"]})
        bitti = terminated or truncated

    print(f"Tür: {tur}  tohum: {tohum}  toplam ödül: {toplam_odul:.1f}")
    for k, v in bilgi["ozet"].items():
        print(f"  {k:22s} {v:.3f}" if isinstance(v, float) else f"  {k:22s} {v}")
    print("Not: şu parametre grupları varsayım/geçicidir:", ", ".join(gecici_parametreler(ayarlar)))

    os.makedirs("runs/demo", exist_ok=True)
    gunler = [s["gun"] for s in satirlar]
    fig, ax = plt.subplots(5, 1, figsize=(10, 11), sharex=True)
    ax[0].plot(gunler, [s["T"] for s in satirlar]); ax[0].set_ylabel("Sıcaklık (°C)")
    ax[1].plot(gunler, [s["BN"] for s in satirlar]); ax[1].set_ylabel("Bağıl nem (%)")
    ax[2].plot(gunler, [s["CO2"] for s in satirlar]); ax[2].set_ylabel("CO₂ (ppm)")
    ax[3].plot(gunler, [s["kol"] for s in satirlar], label="kolonizasyon (gözlenen)")
    if ortam.tur_ayarlari.get("kahverengilesme"):
        ax[3].plot(gunler, [s["kah"] for s in satirlar], label="kahverengileşme")
    ax[3].plot(gunler, [s["biyo"] for s in satirlar], label="biyokütle / dalga kapasitesi")
    ax[3].legend(); ax[3].set_ylabel("Oran")
    ax[4].plot(gunler, [s["kwh"] for s in satirlar]); ax[4].set_ylabel("Enerji (kWh/adım)")
    ax[4].set_xlabel("Gün")
    fig.suptitle(f"Sabit reçete — {tur}, tohum {tohum}")
    fig.tight_layout()
    yol = f"runs/demo/sabit_recete_{tur}_{tohum}.png"
    fig.savefig(yol, dpi=120)
    print("Grafik:", yol)


if __name__ == "__main__":
    import sys
    calistir(sys.argv[1] if len(sys.argv) > 1 else "istiridye")
