"""Değerlendirme betiği (K2, K3): bütün yöntemleri aynı test senaryolarında çalıştırır.

Çalıştırma (proje kök klasöründen):
    python degerlendir.py                              # bütün yöntemler, üç tür
    python degerlendir.py --turler istiridye           # tek tür
    python degerlendir.py --yontemler sabit_recete kural_tabanli

Yöntemler: sabit_recete, kural_tabanli, ayarlanmis_kural, ppo
  ayarlanmis_kural için önce:  python -m rakipler.ayarlanmis_kural
  ppo için önce:               python egit.py --tur <tür> --tohum <n>   (runs/ppo/<tür>/<n>/model.zip)
  Eksik olan yöntem uyarıyla atlanır.

Test tohumları seeds.txt'den okunur. Her test tohumu aynı dış hava, suş kayması, verimlilik ve
kontaminasyon rastgeleliğini üretir; yani bütün yöntemler aynı senaryolarla karşılaşır.

Çıktılar (runs/degerlendirme/):
    sonuclar.csv   her yöntem × tür × (eğitim tohumu) × test tohumu için bir satır
    ozet.csv       yöntem × tür için ortalama ve standart sapma
    ozet.md        rapora konacak tablo
    karsilastirma.png
"""

import argparse
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

from mantar_ortami.ortam import TURLER, MantarOrtami  # noqa: E402
from rakipler.kural_tabanli import KuralTabanli  # noqa: E402
from rakipler.sabit_recete import SabitRecete  # noqa: E402

YONTEMLER = ["sabit_recete", "kural_tabanli", "ayarlanmis_kural", "ppo"]
OLCUTLER = {   # sütun → tablodaki başlık
    "net_kazanc_tl": "Net kazanç (TL)",
    "hasat_kg": "Hasat (kg)",
    "biyolojik_verimlilik": "BV",
    "ortalama_kalite": "Kalite",
    "kwh_kg": "kWh/kg",
    "su_l_kg": "Su (L/kg)",
    "ihlal_orani": "İhlal oranı",
    "gun": "Döngü (gün)",
}


def bolum_calistir(ortam, politika, tohum: int) -> dict:
    politika.sifirla(tohum)
    gozlem, _ = ortam.reset(seed=tohum)
    odul, kazanc, bitti = 0.0, 0.0, False
    while not bitti:
        gozlem, r, terminated, truncated, bilgi = ortam.step(politika.eylem_sec(gozlem))
        odul += r
        kazanc += bilgi["odul_tl"]
        bitti = terminated or truncated
    z = bilgi["ozet"]
    hasat_var = z["hasat_kg"] > 0
    return {**z, "odul": odul, "net_kazanc_tl": kazanc,
            "kwh_kg": z["kwh_kg"] if hasat_var else float("nan"),        # hasat yoksa tanımsız
            "su_l_kg": z["su_l"] / z["hasat_kg"] if hasat_var else float("nan"),
            "hasatsiz": not hasat_var, "kesildi": bool(truncated)}


def politikalar(yontem: str, ortam, tur: str, kayit_kok: Path):
    """(eğitim tohumu, politika) çiftleri üretir; öğrenmeyen yöntemlerde eğitim tohumu -1'dir."""
    if yontem == "sabit_recete":
        yield -1, SabitRecete(ortam)
    elif yontem == "kural_tabanli":
        yield -1, KuralTabanli(ortam)
    elif yontem == "ayarlanmis_kural":
        from rakipler.ayarlanmis_kural import parametreleri_oku
        p = parametreleri_oku()[tur]
        yield -1, KuralTabanli(ortam, {k: v for k, v in p.items() if k != "dogrulama_odulu"})
    elif yontem == "ppo":
        from ajanlar.ppo_ajani import PPOAjani
        modeller = sorted((kayit_kok / "ppo" / tur).glob("*/model.zip"))
        if not modeller:
            raise FileNotFoundError(f"runs/ppo/{tur}/ altında model yok")
        for m in modeller:
            yield int(m.parent.name), PPOAjani(m)


def ozetle(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["tur", "yontem"], sort=False)[list(OLCUTLER)]
    ozet = g.mean().add_suffix("_ort").join(g.std(ddof=1).add_suffix("_std"))
    ozet["bolum"] = g.size()
    ozet["hasatsiz_bolum"] = df.groupby(["tur", "yontem"], sort=False)["hasatsiz"].sum()
    return ozet.reset_index()


def markdown_tablo(ozet: pd.DataFrame) -> str:
    satirlar = ["| Tür | Yöntem | " + " | ".join(OLCUTLER.values()) + " | n |",
                "|---|---|" + "---|" * (len(OLCUTLER) + 1)]
    for _, r in ozet.iterrows():
        hucre = []
        for k in OLCUTLER:
            ort, std = r[f"{k}_ort"], r[f"{k}_std"]
            basamak = 0 if abs(ort) >= 100 else (2 if abs(ort) < 10 else 1)
            hucre.append(f"{ort:.{basamak}f} ± {0 if np.isnan(std) else std:.{basamak}f}")
        satirlar.append(f"| {r['tur']} | {r['yontem']} | " + " | ".join(hucre) + f" | {int(r['bolum'])} |")
    satirlar.append("\nOrtalama ± standart sapma; n = bölüm sayısı (ppo için eğitim tohumu × test tohumu).")
    for _, r in ozet[ozet["hasatsiz_bolum"] > 0].iterrows():
        satirlar.append(f"{r['tur']} / {r['yontem']}: {int(r['hasatsiz_bolum'])} bölümde hiç hasat yok "
                        "(kWh/kg ve L/kg bu bölümler dışarıda bırakılarak hesaplandı).")
    return "\n".join(satirlar)


def grafik(ozet: pd.DataFrame, yol: Path) -> None:
    olcutler = ["net_kazanc_tl", "hasat_kg", "kwh_kg", "su_l_kg"]
    yontemler = list(dict.fromkeys(ozet["yontem"]))
    turler = list(dict.fromkeys(ozet["tur"]))
    fig, eksenler = plt.subplots(1, len(olcutler), figsize=(4.2 * len(olcutler), 4))
    genislik = 0.8 / len(yontemler)
    for ax, o in zip(eksenler, olcutler):
        for i, y in enumerate(yontemler):
            alt = ozet[ozet["yontem"] == y].set_index("tur").reindex(turler)
            ax.bar(np.arange(len(turler)) + i * genislik, alt[f"{o}_ort"], genislik,
                   yerr=alt[f"{o}_std"].fillna(0), capsize=2, label=y)
        ax.set_xticks(np.arange(len(turler)) + genislik * (len(yontemler) - 1) / 2, turler, rotation=15)
        ax.set_title(OLCUTLER[o])
    eksenler[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(yol, dpi=130); plt.close(fig)


def calistir(yontemler, turler) -> pd.DataFrame:
    with open("config.yaml", encoding="utf-8") as f:
        ayarlar = yaml.safe_load(f)
    with open("seeds.txt", encoding="utf-8") as f:
        test_tohumlari = [int(s) for s in f.read().split()]
    kayit_kok = Path(os.environ.get("MANTAR_RUNS_DIR", "runs"))
    cikti = kayit_kok / "degerlendirme"
    cikti.mkdir(parents=True, exist_ok=True)

    satirlar = []
    for tur in turler:
        ortam = MantarOrtami(ayarlar, tur=tur)
        for yontem in yontemler:
            try:
                for egitim_tohumu, politika in politikalar(yontem, ortam, tur, kayit_kok):
                    for t in test_tohumlari:
                        satirlar.append({"yontem": yontem, "tur": tur, "egitim_tohumu": egitim_tohumu,
                                         "test_tohumu": t, **bolum_calistir(ortam, politika, t)})
            except FileNotFoundError as hata:
                print(f"  atlandı: {yontem} / {tur} ({hata})")
    df = pd.DataFrame(satirlar)
    df.to_csv(cikti / "sonuclar.csv", index=False, encoding="utf-8-sig")
    ozet = ozetle(df)
    ozet.to_csv(cikti / "ozet.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
    tablo = markdown_tablo(ozet)
    (cikti / "ozet.md").write_text(tablo + "\n", encoding="utf-8")
    grafik(ozet, cikti / "karsilastirma.png")
    print(tablo)
    print("\nKayıtlar:", cikti)
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Yöntemleri test tohumlarında karşılaştırır")
    ap.add_argument("--yontemler", nargs="+", default=YONTEMLER, choices=YONTEMLER)
    ap.add_argument("--turler", nargs="+", default=TURLER, choices=TURLER)
    a = ap.parse_args()
    calistir(a.yontemler, a.turler)
