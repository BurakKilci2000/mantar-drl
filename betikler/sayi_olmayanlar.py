"""
Hafta 6 - yardimci: Bir Excel/CSV dosyasinda sayiya cevrilemeyen degerlerin
neye benzedigini gosterir (repr ile; gizli karakterler de gorunur).

Kullanim:
    python betikler\\sayi_olmayanlar.py "D:\\...\\DS Temp - ESP8266.xlsx"
"""
import sys
from pathlib import Path

import pandas as pd


def calistir():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for yol in map(Path, sys.argv[1:]):
        df = pd.read_excel(yol) if yol.suffix == ".xlsx" else pd.read_csv(yol)
        print("=" * 80)
        print(yol.name, "| sutunlar:", [repr(c) for c in df.columns])
        print("ilk 5 satir (ham):")
        for _, satir in df.head(5).iterrows():
            print("   ", [repr(v) for v in satir.tolist()])
        for s in df.columns[1:]:
            ham = df[s]
            sayi = pd.to_numeric(ham.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")
            kotu = ham[sayi.isna()]
            print(f"\n[{s!r}] sayiya cevrilemeyen: {len(kotu)} / {len(ham)}"
                  f"  (bunlarin {int(kotu.isna().sum())} tanesi bos hucre)")
            dolu_kotu = kotu.dropna()
            if len(dolu_kotu):
                print("  en sik 10 deger:")
                for deger, adet in dolu_kotu.astype(str).value_counts().head(10).items():
                    print(f"    {adet:>8}  {deger!r}")
                ilk = df.loc[kotu.index[:1], df.columns[0]].tolist()
                son = df.loc[kotu.index[-1:], df.columns[0]].tolist()
                print("  ilk/son gorulme zamani:", ilk, son)
            negatif = sayi[sayi < 0]
            if len(negatif):
                print(f"  negatif deger: {len(negatif)} adet, ornek: {negatif.unique()[:5].tolist()}")


if __name__ == "__main__":
    calistir()