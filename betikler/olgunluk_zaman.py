"""
Hafta 6 - Adim 3b: Olgunluk etiketlerinden hasat zamanlamasi.

COCO Format klasorundeki her JSON bir goruntuye ait; dosya adi goruntunun cekildigi an
(Unix zamani, milisaniye: 1673327431124 -> 2023-01-10 08:10 TR). Her goruntu icin
olgun ve olgun olmayan mantar sayisini cikarir, zamana dizer, gunluk ozet ve grafik uretir.

Kullanim (mantar-drl klasorunden):
    python betikler\\olgunluk_zaman.py "D:\\...\\duman2024_oyster"

Ciktilar (Sensor Data\\temiz\\ klasorune):
    olgunluk_goruntu.csv   goruntu basina sayimlar
    olgunluk_gunluk.csv    gunluk toplamlar
    grafikler\\olgunluk_zaman.png
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

SAAT_DILIMI = "Europe/Istanbul"
# Dongu sinirlari (sensor verisinden): Cycle I sonu 02.03.2023, Cycle II basi 11.03.2023
CYCLE2_BASI = pd.Timestamp("2023-03-05", tz=SAAT_DILIMI)


def sinif_adi(ad: str) -> str:
    a = ad.lower().replace("_", " ").replace("-", " ")
    if "immature" in a or "unripe" in a or "olgun degil" in a:
        return "olgun_degil"
    if "mature" in a or "ripe" in a or "olgun" in a:
        return "olgun"
    return "diger:" + ad


ETIKET_ANAHTARLARI = ("label", "labels", "rectanglelabels", "polygonlabels", "class", "class_name",
                      "category", "category_name", "name", "title")


def etiketleri_topla(dugum, cikti: list):
    """JSON agacini gezer; etiket anahtarlarindaki (label, rectanglelabels ...) adlari toplar.
    Liste ya da sozluk olmasi fark etmez (Label Studio, CVAT, COCO ...)."""
    if isinstance(dugum, dict):
        for k, v in dugum.items():
            if k in ETIKET_ANAHTARLARI:
                if isinstance(v, str):
                    cikti.append(v)
                    continue
                if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
                    cikti.extend(v)
                    continue
            etiketleri_topla(v, cikti)
    elif isinstance(dugum, list):
        for x in dugum:
            etiketleri_topla(x, cikti)


def json_say(yol: Path) -> tuple[dict, list]:
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    # Standart COCO: kategori id'leri -> ad
    if isinstance(veri, dict) and "categories" in veri and "annotations" in veri:
        kategoriler = {k["id"]: k["name"] for k in veri["categories"]}
        adlar = [kategoriler.get(a.get("category_id"), str(a.get("category_id"))) for a in veri["annotations"]]
    else:
        adlar = []
        etiketleri_topla(veri, adlar)
    sayim = {"olgun": 0, "olgun_degil": 0}
    for ad in adlar:
        s = sinif_adi(ad)
        sayim[s] = sayim.get(s, 0) + 1
    return sayim, adlar


def calistir():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    kok = Path(sys.argv[1])
    coco = kok / "Maturity Labelled Images and Annotation Files" / "COCO Format"
    temiz = kok / "Sensor Data" / "temiz"
    (temiz / "grafikler").mkdir(parents=True, exist_ok=True)

    dosyalar = sorted(coco.glob("*.json"))
    print(f"{len(dosyalar)} JSON bulundu")
    satirlar, ilk = [], True
    for yol in dosyalar:
        try:
            ms = int(yol.stem)
        except ValueError:
            print("  adi zaman degil, atlandi:", yol.name)
            continue
        sayim, adlar = json_say(yol)
        if ilk:
            with open(yol, encoding="utf-8") as f:
                print("Ornek dosya:", yol.name, "| ilk 600 karakter:\n", f.read()[:600], "\n")
            print("Bulunan etiket adlari:", sorted(set(adlar)), "->", sayim, "\n")
            ilk = False
        zaman = pd.Timestamp(ms, unit="ms", tz="UTC").tz_convert(SAAT_DILIMI)
        satirlar.append({"zaman": zaman, "dosya": yol.name, **sayim})

    df = pd.DataFrame(satirlar).fillna(0).sort_values("zaman").set_index("zaman")
    df["toplam"] = df["olgun"] + df["olgun_degil"]
    df["olgun_orani"] = (df["olgun"] / df["toplam"]).where(df["toplam"] > 0)
    df["dongu"] = ["Cycle II" if z >= CYCLE2_BASI else "Cycle I" for z in df.index]
    df.to_csv(temiz / "olgunluk_goruntu.csv", encoding="utf-8-sig", date_format="%Y-%m-%d %H:%M")

    gunluk = df.groupby(["dongu", pd.Grouper(freq="1D")]).agg(
        goruntu=("dosya", "count"), olgun=("olgun", "sum"), olgun_degil=("olgun_degil", "sum"))
    gunluk["olgun_orani"] = (gunluk["olgun"] / (gunluk["olgun"] + gunluk["olgun_degil"])).round(2)
    gunluk.to_csv(temiz / "olgunluk_gunluk.csv", encoding="utf-8-sig", date_format="%Y-%m-%d")

    print("\nDongu ozeti:")
    for dongu, d in df.groupby("dongu"):
        ilk_mantar = d.index[d["toplam"] > 0].min()
        ilk_olgun = d.index[d["olgun"] > 0].min()
        print(f"  {dongu}: {len(d)} goruntu, {d.index.min():%d.%m.%Y} - {d.index.max():%d.%m.%Y}")
        print(f"    toplam etiket: olgun {int(d['olgun'].sum())}, olgun degil {int(d['olgun_degil'].sum())}")
        if pd.notna(ilk_mantar):
            print(f"    ilk mantar gorulen goruntu : {ilk_mantar:%d.%m.%Y %H:%M}")
        if pd.notna(ilk_olgun):
            print(f"    ilk olgun mantar           : {ilk_olgun:%d.%m.%Y %H:%M}"
                  f"  (ilk mantardan {(ilk_olgun - ilk_mantar).total_seconds() / 86400:.1f} gun sonra)")

    pd.set_option("display.width", 200)
    print("\nGunluk tablo:")
    print(gunluk.to_string())

    fig, eksenler = plt.subplots(2, 1, figsize=(14, 7), sharex=False)
    for ax, (dongu, d) in zip(eksenler, gunluk.groupby(level=0)):
        d = d.droplevel(0)
        ax.bar(d.index, d["olgun_degil"], color="tab:green", label="olgun değil")
        ax.bar(d.index, d["olgun"], bottom=d["olgun_degil"], color="tab:orange", label="olgun")
        ax2 = ax.twinx()
        ax2.plot(d.index, d["olgun_orani"], "k.-", lw=1, label="olgun oranı")
        ax2.set_ylim(0, 1.05)
        ax2.set_ylabel("Olgun oranı")
        ax.set_ylabel("Etiketli mantar (adet/gün)")
        ax.set_title(f"{dongu} — günlük olgunluk etiketleri")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        ax.grid(alpha=0.3)
        ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(temiz / "grafikler" / "olgunluk_zaman.png", dpi=130)
    print("\ngrafik: olgunluk_zaman.png\nCiktilar:", temiz)


if __name__ == "__main__":
    calistir()