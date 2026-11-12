"""Biyoloji alt modeli: gelişim evresi, hasat dalgası, biyokütle ve kalite.

Evreler:
    INKUBASYON       misel substratı sarıyor
    KAHVERENGILESME  (yalnızca shiitake) misel tamamlanınca kendiliğinden başlar; yüzey kahverengileşir
    PIN              şoktan sonra taslakların (primordia) oluşması
    BUYUME           meyve gövdelerinin büyümesi; ajan hasat kararını verir
    DINLENME         hasattan sonra bir sonraki dalgaya kadar bekleme; sonra yeniden şok gerekir
    BITTI            son dalga hasat edildi ya da süre doldu

Şok, ajanın ayrık bir kararıdır. Gerçek üretimde tetikleme sıcaklık şokuyla (Kim vd. 2020)
ya da su şokuyla (Rocha vd. 2025) yapılır; model bu yöntemleri tek bir "tetikle" kararıyla temsil eder.

Suş farkı: her bölümün başında meyvelenme sıcaklık aralığı rastgele kaydırılır ve biyolojik
verimlilik literatürdeki aralıktan örneklenir (config.yaml → rastgelelik). Ajan bu değerleri görmez.
"""

import math

from .stress import band, co2_growth, piecewise_quality

INKUBASYON, KAHVERENGILESME, PIN, BUYUME, DINLENME, BITTI = range(6)
STAGE_NAMES = ["inkubasyon", "kahverengilesme", "pin", "buyume", "dinlenme", "bitti"]


class Biology:
    def __init__(self, species_cfg: dict, dry_substrate_kg: float, co2_cfg: dict, outside_co2: float):
        self.inc = species_cfg["inkubasyon"]
        self.brown = species_cfg.get("kahverengilesme")
        self.fr = species_cfg["meyvelenme"]
        self.bio = species_cfg["biyoloji"]
        self.co2_cfg = co2_cfg
        self.outside_co2 = outside_co2
        self.dry_kg = dry_substrate_kg
        g = self.bio["buyume_gun"] * 24.0
        self.growth_rate_per_h = math.log((0.95 * 0.99) / (0.01 * 0.05)) / g   # %1 → %95, buyume_gun günde

    def reset(self, rng, randomize_strain: bool, randomize_yield: bool) -> None:
        shift = self.fr.get("sus_sicaklik_kaymasi_c") or 0.0
        self.temp_shift = float(rng.uniform(-shift, shift)) if randomize_strain else 0.0
        be_low, be_high = self.bio["biyolojik_verimlilik"]
        self.be = float(rng.uniform(be_low, be_high)) if randomize_yield else (be_low + be_high) / 2
        total_yield = self.be * self.dry_kg
        self.flush_capacity = [share * total_yield for share in self.bio["dalga_paylari"]]

        self.stage = INKUBASYON
        self.flush = 0                 # tamamlanan hasat dalgası sayısı
        self.stage_hours = 0.0
        self.browning = 0.0            # kahverengileşme ilerlemesi (0–1)
        self.age_days = 0.0            # meyve gövdesi yaşı (BUYUME evresinde)
        self.biomass = 0.0             # mevcut dalgadaki taze mantar (kg)
        self.capacity = 0.0            # mevcut dalganın kapasitesi (kg)
        self.co2_quality = 1.0
        self.harvested_kg = 0.0
        self.harvested_value_kg = 0.0  # kaliteyle ağırlıklandırılmış hasat (kg eşdeğeri)
        self.spoiled_kg = 0.0

    @property
    def n_flushes(self) -> int:
        return len(self.flush_capacity)

    @property
    def fruiting_temp_band(self) -> tuple:
        low, high = self.fr["sicaklik_opt"]
        return low + self.temp_shift, high + self.temp_shift

    def quality(self) -> float:
        over = max(0.0, self.age_days - self.bio["hasat_opt_yas_gun"])
        return max(0.0, self.co2_quality * (1.0 - self.bio["kalite_dusus_gun"] * over))

    def marketable_kg(self) -> float:
        return self.biomass * self.quality()

    # --- kararlar
    def shock(self, colonization: float) -> bool:
        """Meyvelenmeyi tetikleme. Etkiliyse True döner."""
        if self.brown is None:
            ready_first = self.stage == INKUBASYON and colonization >= self.inc["kolonizasyon_esigi"]
        else:
            ready_first = self.stage == KAHVERENGILESME and self.browning >= self.brown["esik"]
        ready_next = self.stage == DINLENME and self.stage_hours >= self.bio["dinlenme_gun"] * 24.0
        if ready_first or ready_next:
            self._enter(PIN)
            return True
        return False

    def harvest(self) -> float:
        """Hasat. Pazarlanabilir kg eşdeğerini döndürür (BUYUME dışında 0)."""
        if self.stage != BUYUME or self.biomass <= 0.0:
            return 0.0
        value = self.marketable_kg()
        self.harvested_kg += self.biomass
        self.harvested_value_kg += value
        self._end_flush()
        return value

    # --- zaman ilerlemesi
    def substep(self, dt_h: float, temp_c: float, rh: float, co2_ppm: float,
                moisture_factor: float, colonization: float) -> None:
        self.stage_hours += dt_h

        if self.stage == INKUBASYON and self.brown is not None and colonization >= self.inc["kolonizasyon_esigi"]:
            self._enter(KAHVERENGILESME)                         # misel tamamlanınca kendiliğinden
        elif self.stage == KAHVERENGILESME:
            low, high = self.inc["sicaklik_opt"]                 # kahverengileşme inkübasyon koşullarında sürer
            f_t = band(temp_c, low, high, self.inc["sicaklik_tolerans"])
            self.browning = min(1.0, self.browning + f_t * dt_h / (self.brown["sure_gun"] * 24.0))
        elif self.stage == PIN and self.stage_hours >= self.bio["pin_gun"] * 24.0:
            self._enter(BUYUME)
            self.capacity = self.flush_capacity[self.flush]
            self.biomass = 0.01 * self.capacity
            self.co2_quality = 1.0
            self.age_days = 0.0
        elif self.stage == BUYUME:
            self.age_days += dt_h / 24.0
            f = self.fr
            low, high = self.fruiting_temp_band
            f_t = band(temp_c, low, high, f["sicaklik_tolerans"])
            g_rh = band(rh, f["nem_opt"][0], f["nem_opt"][1], f["nem_tolerans"])
            h_co2 = co2_growth(co2_ppm, self.outside_co2, f["co2_iyi_maks_ppm"], self.co2_cfg["erken_etki"])
            rate = self.growth_rate_per_h * f_t * g_rh * h_co2 * moisture_factor
            if self.capacity > 0:
                self.biomass += rate * self.biomass * (1.0 - self.biomass / self.capacity) * dt_h
            q = piecewise_quality(co2_ppm, f["co2_iyi_maks_ppm"], f["co2_kalite_esigi_ppm"], f["co2_sekil_bozulma_ppm"])
            self.co2_quality = min(self.co2_quality, q)
            if self.age_days >= self.bio["curume_yas_gun"]:      # hasat edilmezse ürün kaybolur
                self.spoiled_kg += self.biomass
                self._end_flush()

    def lose_capacity(self, fraction: float) -> None:
        """Kontaminasyon: kalan kapasitenin bir kısmı ve mevcut ürünün kalitesi kaybolur."""
        for i in range(self.flush, self.n_flushes):
            self.flush_capacity[i] *= (1.0 - fraction)
        if self.stage == BUYUME:
            self.capacity *= (1.0 - fraction)
            self.biomass = min(self.biomass, self.capacity)
            self.co2_quality *= (1.0 - fraction)

    def _end_flush(self) -> None:
        self.biomass = 0.0
        self.capacity = 0.0
        self.age_days = 0.0
        self.flush += 1
        self._enter(BITTI if self.flush >= self.n_flushes else DINLENME)

    def _enter(self, stage: int) -> None:
        self.stage = stage
        self.stage_hours = 0.0
