"""Hafta 7: istiridye simülasyonunu Duman vd. (2024) Cycle II'de ölçülen sürelerle karşılaştırır.

Gerçek seradaki ortalama iklim, sabit ayar noktası olarak simülasyona verilir; sonra simülasyonun
ürettiği süreler (kolonizasyon, şoktan hasada, dalgalar arası) gerçek değerlerle yan yana yazılır.
Suş kayması ve verim rastgeleliği kapatılır; böylece yalnızca modelin süre yapısı sınanır.

Senaryolar:
  A  Cycle II ortamı     : inkübasyon 20,1 °C (oda), meyvelenme 15,2 °C / %89,7
  B  torba sıcaklığı     : inkübasyon 26,6 °C (Duman'da torba içi ortalaması), meyvelenme aynı
  C  kış (Cycle I gibi)  : inkübasyon 20,1 °C, meyvelenme 7 °C (Cycle I'de ortam 3–10 °C)

Çalıştırma (proje kök klasöründen):  python -m betikler.duman_karsilastir
Çıktı: runs/duman_karsilastirma.csv ve ekrana tablo
"""

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from mantar_ortami.biyoloji import BUYUME, DINLENME, INKUBASYON, PIN
from mantar_ortami.ortam import MantarOrtami

SENARYOLAR = {
    "A · Cycle II ortamı": {"ink_t": 20.1, "meyve_t": 15.2, "meyve_bn": 89.7},
    "B · torba sıcaklığı": {"ink_t": 26.6, "meyve_t": 15.2, "meyve_bn": 89.7},
    "C · kış (7 °C)": {"ink_t": 20.1, "meyve_t": 7.0, "meyve_bn": 89.7},
}
# Duman 2024'ten (tez notları 12.5–12.6)
GERCEK = {
    "kolonizasyon_gun": "≈17 (oda ≈20 °C)",
    "soktan_ilk_hasada_gun": "≈9 ilk olgun, ≈14 yarısı olgun (15 °C)",
    "taslaktan_hasat_sonuna_gun": "≈13 (15 °C) · ≈17–18 (3–10 °C)",
    "hasattan_hasada_gun": "≈30 (Cycle I, 3–10 °C)",
}


def senaryo_calistir(ayarlar: dict, s: dict, tohum: int = 0) -> dict:
    a = copy.deepcopy(ayarlar)
    a["rastgelelik"] = {"sus_kaymasi": False, "verimlilik_araligi": False}
    ortam = MantarOrtami(a, tur="istiridye")
    b = ortam.biyoloji
    ink = a["turler"]["istiridye"]["inkubasyon"]
    biyo = a["turler"]["istiridye"]["biyoloji"]
    gozlem, _ = ortam.reset(seed=tohum)
    olaylar = {"sok": [], "pin_sonu": [], "hasat": []}
    onceki_evre, bitti = b.evre, False
    while not bitti:
        gun = ortam.saat / 24.0
        if b.evre == INKUBASYON:
            t, bn, co2 = s["ink_t"], a["dis_hava"]["bagil_nem"], 5000.0
        else:
            t, bn, co2 = s["meyve_t"], s["meyve_bn"], 2400.0
        sok = int((b.evre == INKUBASYON and ortam.substrat.kolonizasyon >= ink["kolonizasyon_esigi"])
                  or (b.evre == DINLENME and b.evre_saat >= biyo["dinlenme_gun"] * 24))
        hasat = int(b.evre == BUYUME and b.yas_gun >= biyo["hasat_opt_yas_gun"])
        if sok:
            olaylar["sok"].append(gun)
        if hasat:
            olaylar["hasat"].append(gun)
        eylem = {"ayar": ortam.ayar_noktalarini_olcekle(t, bn, co2), "karar": np.array([sok, hasat])}
        gozlem, _, terminated, truncated, bilgi = ortam.step(eylem)
        if onceki_evre == PIN and b.evre == BUYUME:
            olaylar["pin_sonu"].append(ortam.saat / 24.0)
        onceki_evre, bitti = b.evre, terminated or truncated
    z = bilgi["ozet"]
    sok, hasat = olaylar["sok"], olaylar["hasat"]
    return {
        "kolonizasyon_gun": sok[0] if sok else np.nan,
        "soktan_ilk_hasada_gun": hasat[0] - sok[0] if sok and hasat else np.nan,
        "taslaktan_hasat_sonuna_gun": (hasat[0] - olaylar["pin_sonu"][0]) if hasat and olaylar["pin_sonu"] else np.nan,
        "hasattan_hasada_gun": hasat[1] - hasat[0] if len(hasat) > 1 else np.nan,
        "dalga": z["tamamlanan_dalga"], "hasat_kg": z["hasat_kg"], "curuyen_kg": z["curuyen_kg"],
        "dongu_gun": z["gun"],
    }


def calistir() -> None:
    with open("config.yaml", encoding="utf-8") as f:
        ayarlar = yaml.safe_load(f)
    sonuc = pd.DataFrame({ad: senaryo_calistir(ayarlar, s) for ad, s in SENARYOLAR.items()}).T
    Path("runs").mkdir(exist_ok=True)
    sonuc.to_csv("runs/duman_karsilastirma.csv", encoding="utf-8-sig", float_format="%.2f")
    pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
    print(sonuc.round(1))
    print("\nGerçek (Duman 2024):")
    for k, v in GERCEK.items():
        print(f"  {k:28s} {v}")


if __name__ == "__main__":
    calistir()
