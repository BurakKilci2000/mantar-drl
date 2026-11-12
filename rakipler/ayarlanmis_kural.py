"""Ayarlanmış kural (K3): kural tabanlı kontrolcünün parametreleri doğrulama tohumlarında ızgara
aramasıyla her tür için ayrı ayarlanır.

Ayar ve test tohumları ayrıdır: ayar DOGRULAMA_TOHUMLARI üzerinde yapılır, karşılaştırma
seeds.txt'deki test tohumlarında. Böylece rakip, test senaryolarını görmeden ayarlanmış olur.

Çalıştırma (proje kök klasöründen):  python -m rakipler.ayarlanmis_kural
Çıktı: rakipler/ayarlanmis_parametreler.yaml (degerlendir.py buradan okur)
"""

import itertools
import time
from pathlib import Path

import numpy as np
import yaml

from mantar_ortami.ortam import TURLER, MantarOrtami
from .kural_tabanli import KuralTabanli

DOGRULAMA_TOHUMLARI = list(range(100, 110))
IZGARA = {
    "t_daralma": [0.0, 0.5, 0.75, 1.0],      # 1.0: sıcaklıkta sabit reçeteyle aynı (orta nokta)
    "bn_daralma": [0.0, 0.5, 1.0],
    "co2_orani": [0.6, 0.8, 1.0],
    "hasat_esigi": [0.9, 0.95, 1.01],         # 1.01: biyokütleye bakma, yalnızca yaşa göre hasat et
}
PARAMETRE_DOSYASI = Path(__file__).with_name("ayarlanmis_parametreler.yaml")


def bolum_odulu(ortam, politika, tohum: int) -> float:
    gozlem, _ = ortam.reset(seed=tohum)
    toplam, bitti = 0.0, False
    while not bitti:
        gozlem, odul, terminated, truncated, _ = ortam.step(politika.eylem_sec(gozlem))
        toplam += odul
        bitti = terminated or truncated
    return toplam


def ayarla(ayarlar: dict, tur: str, tohumlar=DOGRULAMA_TOHUMLARI) -> tuple[dict, float]:
    ortam = MantarOrtami(ayarlar, tur=tur)
    en_iyi, en_iyi_puan = None, -np.inf
    for degerler in itertools.product(*IZGARA.values()):
        p = dict(zip(IZGARA.keys(), degerler))
        puan = float(np.mean([bolum_odulu(ortam, KuralTabanli(ortam, p), t) for t in tohumlar]))
        if puan > en_iyi_puan:
            en_iyi, en_iyi_puan = p, puan
    return en_iyi, en_iyi_puan


def parametreleri_oku() -> dict:
    if not PARAMETRE_DOSYASI.exists():
        raise FileNotFoundError("Önce ayarı çalıştırın: python -m rakipler.ayarlanmis_kural")
    with open(PARAMETRE_DOSYASI, encoding="utf-8") as f:
        return yaml.safe_load(f)["turler"]


def calistir() -> None:
    with open("config.yaml", encoding="utf-8") as f:
        ayarlar = yaml.safe_load(f)
    sonuc = {}
    for tur in TURLER:
        t0 = time.time()
        p, puan = ayarla(ayarlar, tur)
        sonuc[tur] = {**p, "dogrulama_odulu": round(puan, 3)}
        print(f"{tur:13s} {p}  doğrulama ödülü {puan:.1f}  ({time.time() - t0:.0f} s)")
    kayit = {
        "aciklama": "Kural tabanlı kontrolcünün doğrulama tohumlarında ızgara aramasıyla bulunan parametreleri",
        "dogrulama_tohumlari": f"{DOGRULAMA_TOHUMLARI[0]}-{DOGRULAMA_TOHUMLARI[-1]}",
        "izgara": IZGARA,
        "turler": sonuc,
    }
    with open(PARAMETRE_DOSYASI, "w", encoding="utf-8") as f:
        yaml.safe_dump(kayit, f, allow_unicode=True, sort_keys=False)
    print("Kaydedildi:", PARAMETRE_DOSYASI)


if __name__ == "__main__":
    calistir()
