"""
Hafta 6 - Adim 2: Duman 2024 sensor verisini temizler ve 5 dakikalik tabloya indirir.

Once arduino_birlestir.py calistirilmis olmali (Cycle I icin islenmis/ klasoru).

Kullanim (mantar-drl klasorunden):
    python betikler\\temizle_duman.py "D:\\...\\duman2024_oyster\\Sensor Data"

Ciktilar (Sensor Data\\temiz\\ klasorune):
    cycle1_5dk.csv, cycle2_5dk.csv   temiz, 5 dakikalik tablolar
    temizlik_raporu.csv              her seride hangi adimda kac deger atildi
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # mantar-drl kok klasoru
from veri.duman2024 import donguyu_temizle  # noqa: E402

DONGULER = {
    "Cycle I": {"cikti": "cycle1_5dk.csv", "bitis": "2023-03-02T08:33:51Z"},  # Notes & drops.txt
    "Cycle II": {"cikti": "cycle2_5dk.csv", "bitis": None},
}


def calistir():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    kok = Path(sys.argv[1])
    cikti = kok / "temiz"
    cikti.mkdir(exist_ok=True)

    tum_rapor = []
    for dongu, ayar in DONGULER.items():
        print(f"\n=== {dongu} ===")
        tablo, rapor = donguyu_temizle(kok, dongu, bitis=ayar["bitis"])
        tablo.to_csv(cikti / ayar["cikti"], encoding="utf-8-sig", date_format="%Y-%m-%d %H:%M",
                     float_format="%.3f", index_label="zaman")
        print(f"  -> {ayar['cikti']}: {len(tablo)} satir ({tablo.index[0]:%Y-%m-%d} - {tablo.index[-1]:%Y-%m-%d}),"
              f" {sum(not c.endswith('__n') and not c.startswith('kesinti') for c in tablo.columns)} seri")
        tum_rapor.append(rapor)

    rapor = pd.concat(tum_rapor, ignore_index=True)
    rapor.to_csv(cikti / "temizlik_raporu.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)
    print("\nTemizlik raporu:")
    print(rapor.drop(columns=["dosya"]).to_string(index=False))
    print("\nCiktilar:", cikti)


if __name__ == "__main__":
    calistir()