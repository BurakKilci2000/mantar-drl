"""MushroomEnv: alt modelleri birleştiren Gymnasium ortamı (K1).

Bir bölüm = bir üretim döngüsü (inokülasyondan son hasat dalgasına). Karar adımı Δt = 4 saat;
her karar adımında alt katman (PI denetleyiciler) 15 dakikalık iç adımlarla çalışır.

Eylem (hibrit, gymnasium.spaces.Dict):
    "ayar"  : Box(-1, 1, (3,))  → sıcaklık, bağıl nem ve CO2 ayar noktaları (alt katman PI ile izlenir)
    "karar" : MultiBinary(2)    → [meyvelenmeyi tetikleyen şok, hasat]

Ödül (öneri formu 3.2; yöntem dokümanı B.3):
    Δ(hasat edilmiş değer + bekleyen pazarlanabilir ürün değeri) − enerji maliyeti − su maliyeti
    − ihlal cezası − erken şok cezası; bölüm sonunda hasat edilmemiş ürün kaybedilir.
    Böylece ödül adım başına verilir (yoğun ödül) ama toplamı döngünün net kazancına eşittir.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .biology import BITTI, INKUBASYON, KAHVERENGILESME, STAGE_NAMES, Biology
from .climate import RoomClimate
from .resources import ResourceMeter
from .substrate import Substrate

SPECIES = ["istiridye", "shiitake", "aslan_yelesi"]
OPTIONAL_KEYS = {"co2_maks_ppm"}   # null olabilir: sınır yok demektir

# Gözlem vektörünün düzeni: politikalar bu adlarla okur (decode_observation).
OBS_KEYS = (
    ["sicaklik_c", "bagil_nem", "co2_ppm", "substrat_nemi", "kolonizasyon_gozlenen", "kahverengilesme_orani"]
    + [f"evre_{n}" for n in STAGE_NAMES]
    + ["dalga", "evre_gun", "meyve_yas_gun", "biyokutle_orani", "kalite", "dongu_gunu",
       "dis_sicaklik_c", "dis_bagil_nem"]
    + [f"tur_{s}" for s in SPECIES]
    + ["onceki_sicaklik_ayar", "onceki_nem_ayar", "onceki_co2_ayar", "onceki_sok", "onceki_hasat"]
)
_SCALE = {"co2_ppm": 1000.0, "sicaklik_c": 10.0, "bagil_nem": 100.0, "substrat_nemi": 100.0,
          "evre_gun": 10.0, "meyve_yas_gun": 10.0, "dongu_gunu": 200.0, "dis_sicaklik_c": 10.0,
          "dis_bagil_nem": 100.0}


def decode_observation(obs) -> dict:
    """Normalize gözlem vektörünü adlandırılmış ve birimli değerlere çevirir."""
    return {k: float(v) * _SCALE.get(k, 1.0) for k, v in zip(OBS_KEYS, obs)}


def check_species_config(config: dict, species: str) -> list:
    """Tür için eksik (null) parametrelerin listesini döndürür."""
    missing = []
    sp = config["turler"].get(species)
    for block in ["inkubasyon", "kahverengilesme", "meyvelenme", "biyoloji"]:
        values = None if sp is None else sp.get(block)
        if values is None:
            if block != "kahverengilesme":          # kahverengileşme evresi isteğe bağlı
                missing.append(f"turler.{species}.{block}")
            continue
        for key, value in values.items():
            if value is None and key not in OPTIONAL_KEYS:
                missing.append(f"turler.{species}.{block}.{key}")
    return missing


class MushroomEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config: dict, species: str = "istiridye"):
        missing = check_species_config(config, species)
        if missing:
            raise ValueError(f"'{species}' için eksik parametreler (config.yaml):\n  " + "\n  ".join(missing))
        self.cfg = config
        self.species = species
        self.species_cfg = config["turler"][species]
        sim = config["simulasyon"]
        self.dt_h = sim["adim_saat"]
        self.sub_dt_h = sim["alt_adim_dakika"] / 60.0
        self.n_sub = int(round(self.dt_h / self.sub_dt_h))
        self.max_steps = int(self.species_cfg["biyoloji"]["maks_gun"] * 24 / self.dt_h)
        self.area = config["oda"]["alan_m2"]

        lim = config["eylem_sinirlari"]
        self._t_rng = lim["sicaklik_c"]
        self._rh_rng = lim["bagil_nem"]
        self._co2_rng = lim["co2_ppm"]

        self.action_space = spaces.Dict({
            "ayar": spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32),
            "karar": spaces.MultiBinary(2),
        })
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(len(OBS_KEYS),), dtype=np.float32)

        self.climate = RoomClimate(config["oda"], config["pid"])
        self.substrate = Substrate(config["substrat"], self.species_cfg["inkubasyon"], self.area)
        self.biology = Biology(self.species_cfg, self.substrate.dry_kg, config["co2_buyume"],
                               config["dis_hava"]["co2_ppm"])
        self.meter = ResourceMeter()

    # ------------------------------------------------------------------ yardımcılar
    @staticmethod
    def _scale(x: float, rng) -> float:
        return float(rng[0] + (np.clip(x, -1.0, 1.0) + 1.0) / 2.0 * (rng[1] - rng[0]))

    def unscale_setpoints(self, ayar) -> tuple:
        return (self._scale(ayar[0], self._t_rng), self._scale(ayar[1], self._rh_rng),
                self._scale(ayar[2], self._co2_rng))

    def scale_setpoints(self, temp_c: float, rh: float, co2_ppm: float) -> np.ndarray:
        """Fiziksel ayar noktalarını [-1, 1] aralığına çevirir (karşılaştırma yöntemleri için)."""
        def inv(v, r):
            return 2.0 * (v - r[0]) / (r[1] - r[0]) - 1.0
        return np.clip(np.array([inv(temp_c, self._t_rng), inv(rh, self._rh_rng), inv(co2_ppm, self._co2_rng)],
                                dtype=np.float32), -1.0, 1.0)

    def _outside(self, hour: float) -> dict:
        d = self.cfg["dis_hava"]
        temp = (d["sicaklik_ort_c"] + d["sicaklik_gunluk_genlik_c"] * np.sin(2 * np.pi * (hour % 24 - 9) / 24)
                + self._weather_offset)
        return {"temp_c": float(temp), "rh": float(np.clip(d["bagil_nem"] + self._rh_offset, 5, 100)),
                "co2_ppm": d["co2_ppm"]}

    def _stage_targets(self) -> dict:
        """Mevcut evrenin uygun aralıkları (ihlal hesabı için)."""
        if self.biology.stage in (INKUBASYON, KAHVERENGILESME):
            inc = self.species_cfg["inkubasyon"]
            return {"t": inc["sicaklik_opt"], "t_tol": inc["sicaklik_tolerans"], "rh": None, "co2": None}
        fr = self.species_cfg["meyvelenme"]
        return {"t": fr["sicaklik_opt"], "t_tol": fr["sicaklik_tolerans"], "rh": fr["nem_opt"],
                "rh_tol": fr["nem_tolerans"], "co2": fr["co2_kalite_esigi_ppm"]}

    def _violation(self) -> bool:
        s, tg = self.climate.state, self._stage_targets()
        if not (tg["t"][0] - tg["t_tol"] <= s.temp_c <= tg["t"][1] + tg["t_tol"]):
            return True
        if tg["rh"] is not None and not (tg["rh"][0] - tg["rh_tol"] <= s.rh):
            return True
        if tg["co2"] is not None and s.co2_ppm > tg["co2"]:
            return True
        return False

    def _value_kg(self) -> float:
        return self.biology.harvested_value_kg + self.biology.marketable_kg()

    def _observe(self) -> np.ndarray:
        s, b = self.climate.state, self.biology
        out = self._outside(self.hour)
        stage = [1.0 if b.stage == i else 0.0 for i in range(len(STAGE_NAMES))]
        cap = b.capacity if b.capacity > 0 else 1.0
        values = ([s.temp_c, s.rh, s.co2_ppm, self.substrate.moisture,
                   self.substrate.observed_colonization(self.np_random), b.browning]
                  + stage
                  + [b.flush / b.n_flushes, b.stage_hours / 24.0, b.age_days, b.biomass / cap, b.quality(),
                     self.hour / 24.0, out["temp_c"], out["rh"]]
                  + [1.0 if self.species == sp else 0.0 for sp in SPECIES]
                  + list(self._prev_action))
        return np.array([v / _SCALE.get(k, 1.0) for k, v in zip(OBS_KEYS, values)], dtype=np.float32)

    # ------------------------------------------------------------------ Gymnasium arayüzü
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        d = self.cfg["dis_hava"]
        self._weather_offset = 0.0
        self._rh_offset = 0.0
        self.hour = 0.0
        self.steps = 0
        self._prev_action = np.zeros(5, dtype=np.float32)
        self.climate.reset(temp_c=d["sicaklik_ort_c"], rh=d["bagil_nem"], co2_ppm=d["co2_ppm"])
        self.substrate.reset(self.np_random)
        rnd = self.cfg["rastgelelik"]
        self.biology.reset(self.np_random, rnd["sus_kaymasi"], rnd["verimlilik_araligi"])
        self.meter = ResourceMeter()
        self.contaminations = 0
        self.violation_steps = 0
        obs = self._observe()
        return obs, {"gozlem": decode_observation(obs)}

    def step(self, action):
        ayar = np.asarray(action["ayar"], dtype=np.float32)
        karar = np.asarray(action["karar"]).astype(int)
        temp_sp, rh_sp, co2_sp = self.unscale_setpoints(ayar)
        ach_sum = 0.0
        econ, rw = self.cfg["ekonomi"], self.cfg["odul"]
        value_before = self._value_kg()
        energy_before, water_before = self.meter.energy_kwh, self.meter.water_l

        # --- kararlar adımın başında uygulanır
        early_shock = False
        if karar[0] == 1:
            early_shock = not self.biology.shock(self.substrate.colonization)
        if karar[1] == 1:
            self.biology.harvest()

        # --- dış hava: günlük yavaş değişen sapma
        d = self.cfg["dis_hava"]
        self._weather_offset = 0.9 * self._weather_offset + self.np_random.normal(0, d["sicaklik_gurultu_std_c"]) * 0.3
        self._rh_offset = 0.9 * self._rh_offset + self.np_random.normal(0, d["bagil_nem_gurultu_std"]) * 0.3

        # --- alt katman: iç adımlar
        for _ in range(self.n_sub):
            out = self._outside(self.hour)
            incubating = self.biology.stage == INKUBASYON
            in_bag = self.biology.stage in (INKUBASYON, KAHVERENGILESME)
            evap = self.substrate.evaporation_kg_h(self.climate.state.rh, self.area, in_bag)
            usage = self.climate.substep(self.sub_dt_h, temp_sp, rh_sp, co2_sp, out,
                                         self.substrate.heat_w(), self.substrate.co2_l_h(), evap)
            self.meter.add(usage)
            ach_sum += usage["ach"]
            s = self.climate.state
            self.substrate.substep(self.sub_dt_h, s.temp_c, s.co2_ppm, evap, incubating)
            self.biology.substep(self.sub_dt_h, s.temp_c, s.rh, s.co2_ppm, self.substrate.moisture_factor(),
                                 self.substrate.colonization)
            self.hour += self.sub_dt_h

        # --- kontaminasyon riski (günlük tehlike oranı → adım olasılığı)
        r, s = self.cfg["risk"], self.climate.state
        hazard = (r["temel_gunluk"]
                  + r["yuksek_nem_katsayi"] * max(0.0, s.rh - r["yuksek_nem_esigi"])
                  + r["yuksek_sicaklik_katsayi"] * max(0.0, s.temp_c - r["yuksek_sicaklik_esigi"]))
        contaminated = self.np_random.random() < 1.0 - np.exp(-hazard * self.dt_h / 24.0)
        if contaminated and self.biology.stage != BITTI:
            self.contaminations += 1
            self.biology.lose_capacity(r["kayip_orani"])

        violation = self._violation()
        self.violation_steps += int(violation)
        self.steps += 1

        terminated = self.biology.stage == BITTI
        truncated = (not terminated) and self.steps >= self.max_steps

        # --- ödül (TL / olcek)
        value_after = self._value_kg()
        if terminated or truncated:
            value_after = self.biology.harvested_value_kg          # hasat edilmeyen ürün kaybedilir
        energy = self.meter.energy_kwh - energy_before
        water = self.meter.water_l - water_before
        reward_tl = ((value_after - value_before) * econ["mantar_tl_kg"]
                     - energy * econ["elektrik_tl_kwh"] - water * econ["su_tl_litre"])
        reward = (reward_tl / rw["olcek_tl"] - rw["ihlal_ceza"] * int(violation)
                  - rw["erken_sok_ceza"] * int(early_shock))

        self._prev_action = np.array([ayar[0], ayar[1], ayar[2], karar[0], karar[1]], dtype=np.float32)
        obs = self._observe()
        info = {
            "gozlem": decode_observation(obs),
            "evre": STAGE_NAMES[self.biology.stage],
            "enerji_kwh": energy, "su_l": water, "ihlal": bool(violation),
            "erken_sok": early_shock, "kontaminasyon": bool(contaminated),
            "ayar_noktalari": {"sicaklik_c": temp_sp, "bagil_nem": rh_sp, "co2_ppm": co2_sp},
            "ortalama_ach": ach_sum / self.n_sub,
            "odul_tl": reward_tl,
        }
        if terminated or truncated:
            info["ozet"] = self.summary()
        return obs, float(reward), terminated, truncated, info

    def summary(self) -> dict:
        b, m = self.biology, self.meter
        kg = b.harvested_kg
        return {
            "tur": self.species,
            "gun": self.hour / 24.0,
            "hasat_kg": kg,
            "kg_m2": kg / self.area,
            "biyolojik_verimlilik": kg / self.substrate.dry_kg,
            "ortalama_kalite": (b.harvested_value_kg / kg) if kg > 0 else 0.0,
            "curuyen_kg": b.spoiled_kg,
            "tamamlanan_dalga": b.flush,
            "enerji_kwh": m.energy_kwh,
            "kwh_kg": (m.energy_kwh / kg) if kg > 0 else float("inf"),
            "su_l": m.water_l,
            "ihlal_orani": self.violation_steps / max(1, self.steps),
            "kontaminasyon": self.contaminations,
            "sus_sicaklik_kaymasi_c": b.temp_shift,      # ajan görmez; analiz için
            "potansiyel_bv": b.be,
        }
