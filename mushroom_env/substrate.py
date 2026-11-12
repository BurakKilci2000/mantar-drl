"""Substrat alt modeli: blok nemi ve kolonizasyon oranı.

Kolonizasyon lojistik büyümeyle modellenir. Büyüme hızı, literatürdeki inkübasyon süresinden
türetilir: uygun koşullarda kolonizasyon %5'ten %95'e "sure_gun" günde ulaşır.
Gerçek kolonizasyon yalnızca yüzeyden kısmen gözlenebilir (kısmi gözlem; öneri formu 3.2).
"""

import math

from .stress import band, upper_limit

X0, X1 = 0.05, 0.95


class Substrate:
    def __init__(self, substrate_cfg: dict, incubation_cfg: dict, area_m2: float):
        self.cfg = substrate_cfg
        self.inc = incubation_cfg
        self.wet_kg = substrate_cfg["kg_m2_islak"] * area_m2
        # lojistik hız (1/saat): X0'dan X1'e sure_gun günde
        self.rate_per_h = math.log((X1 * (1 - X0)) / (X0 * (1 - X1))) / (incubation_cfg["sure_gun"] * 24.0)
        self.moisture = None
        self.colonization = None

    def reset(self, rng) -> None:
        self.moisture = self.cfg["baslangic_nemi_yuzde"]
        self.colonization = X0

    @property
    def dry_kg(self) -> float:
        return self.wet_kg * (1.0 - self.cfg["baslangic_nemi_yuzde"] / 100.0)

    def moisture_factor(self) -> float:
        low, high = self.cfg["nem_opt"]
        return band(self.moisture, low, high, self.cfg["nem_tolerans"])

    def evaporation_kg_h(self, room_rh: float, area_m2: float, incubating: bool) -> float:
        rate = self.cfg["buharlasma_kg_m2_saat"] * area_m2 * max(0.0, 1.0 - room_rh / 100.0)
        if incubating:
            rate *= self.cfg["inkubasyon_buharlasma_carpani"]
        return rate

    def substep(self, dt_h: float, temp_c: float, co2_ppm: float, evaporation_kg_h: float, incubating: bool) -> None:
        # nem kaybı: substrattaki su kütlesi azalır
        water = self.wet_kg * self.moisture / 100.0 - evaporation_kg_h * dt_h
        dry = self.dry_kg
        self.moisture = max(0.0, 100.0 * water / (water + dry))

        if incubating and self.colonization < 1.0:
            low, high = self.inc["sicaklik_opt"]
            f_t = band(temp_c, low, high, self.inc["sicaklik_tolerans"])
            co2_max = self.inc.get("co2_maks_ppm")
            h_co2 = upper_limit(co2_ppm, co2_max, co2_max) if co2_max else 1.0
            x = self.colonization
            self.colonization = min(1.0, x + self.rate_per_h * f_t * h_co2 * self.moisture_factor() * x * (1 - x) * dt_h)

    def heat_w(self) -> float:
        return self.cfg["misel_isi_w_kg"] * self.wet_kg * self.colonization

    def co2_l_h(self) -> float:
        return self.cfg["misel_co2_l_kg_saat"] * self.wet_kg * self.colonization

    def observed_colonization(self, rng, noise_std: float = 0.03) -> float:
        """Yüzeyden yapılan gözlem: gerçek değer + gürültü (kısmi gözlem)."""
        return float(min(1.0, max(0.0, self.colonization + rng.normal(0.0, noise_std))))
