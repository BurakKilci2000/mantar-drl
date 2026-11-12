"""Substrat alt modeli: blok nemi ve kolonizasyon oranı.

Kolonizasyon lojistik büyümeyle modellenir. Büyüme hızı, literatürdeki inkübasyon süresinden
türetilir: uygun koşullarda kolonizasyon %5'ten %95'e "sure_gun" günde ulaşır.
Gerçek kolonizasyon yalnızca yüzeyden kısmen gözlenebilir (kısmi gözlem; öneri formu 3.2).
"""

import math

from .stres import bant, ust_sinir

X0, X1 = 0.05, 0.95


class Substrat:
    def __init__(self, substrat_ayar: dict, inkubasyon_ayar: dict, alan_m2: float):
        self.ayar = substrat_ayar
        self.ink = inkubasyon_ayar
        self.islak_kg = substrat_ayar["kg_m2_islak"] * alan_m2
        # lojistik hız (1/saat): X0'dan X1'e sure_gun günde
        self.hiz_saat = math.log((X1 * (1 - X0)) / (X0 * (1 - X1))) / (inkubasyon_ayar["sure_gun"] * 24.0)
        self.nem = None
        self.kolonizasyon = None

    def sifirla(self, rng) -> None:
        self.nem = self.ayar["baslangic_nemi_yuzde"]
        self.kolonizasyon = X0

    @property
    def kuru_kg(self) -> float:
        return self.islak_kg * (1.0 - self.ayar["baslangic_nemi_yuzde"] / 100.0)

    def nem_carpani(self) -> float:
        alt, ust = self.ayar["nem_opt"]
        return bant(self.nem, alt, ust, self.ayar["nem_tolerans"])

    def buharlasma_kg_saat(self, oda_bn: float, alan_m2: float, inkubasyonda: bool) -> float:
        hiz = self.ayar["buharlasma_kg_m2_saat"] * alan_m2 * max(0.0, 1.0 - oda_bn / 100.0)
        if inkubasyonda:
            hiz *= self.ayar["inkubasyon_buharlasma_carpani"]
        return hiz

    def alt_adim(self, dt_saat: float, sicaklik_c: float, co2_ppm: float, buharlasma_kg_saat: float,
                 inkubasyonda: bool) -> None:
        # nem kaybı: substrattaki su kütlesi azalır
        su = self.islak_kg * self.nem / 100.0 - buharlasma_kg_saat * dt_saat
        kuru = self.kuru_kg
        self.nem = max(0.0, 100.0 * su / (su + kuru))

        if inkubasyonda and self.kolonizasyon < 1.0:
            alt, ust = self.ink["sicaklik_opt"]
            f_t = bant(sicaklik_c, alt, ust, self.ink["sicaklik_tolerans"])
            co2_maks = self.ink.get("co2_maks_ppm")
            h_co2 = ust_sinir(co2_ppm, co2_maks, co2_maks) if co2_maks else 1.0
            x = self.kolonizasyon
            self.kolonizasyon = min(1.0, x + self.hiz_saat * f_t * h_co2 * self.nem_carpani() * x * (1 - x) * dt_saat)

    def isi_w(self) -> float:
        return self.ayar["misel_isi_w_kg"] * self.islak_kg * self.kolonizasyon

    def co2_l_saat(self) -> float:
        return self.ayar["misel_co2_l_kg_saat"] * self.islak_kg * self.kolonizasyon

    def gozlenen_kolonizasyon(self, rng, gurultu_std: float = 0.03) -> float:
        """Yüzeyden yapılan gözlem: gerçek değer + gürültü (kısmi gözlem)."""
        return float(min(1.0, max(0.0, self.kolonizasyon + rng.normal(0.0, gurultu_std))))
