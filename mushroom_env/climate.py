"""Oda iklimi alt modeli: sıcaklık, bağıl nem ve CO2.

Oda tek bir karışık hacim olarak ele alınır. Her iç adımda (varsayılan 15 dk):
  - ısı dengesi: duvar kaybı + taze hava + ısıtma/soğutma + miselin ürettiği ısı
  - su buharı dengesi: nemlendirici + substrattan buharlaşma − taze havayla çıkan nem
  - CO2 dengesi: miselin ürettiği CO2 − taze havayla seyrelme
Isıtıcı/soğutucu, nemlendirici ve taze hava fanı, ajanın verdiği sıcaklık, nem ve CO2 ayar noktalarını
PI denetleyicilerle izler (hiyerarşik yapı: öneri formu 3.4). Ajan 4 saatte bir ayar noktası verir;
denetleyiciler 15 dakikada bir çalışır.
"""

import math
from dataclasses import dataclass

AIR_DENSITY = 1.2          # kg/m³
AIR_CP = 1005.0            # J/(kg·K)
LATENT_HEAT = 2.45e6       # J/kg, suyun buharlaşma gizli ısısı


def saturation_vapor_density(temp_c: float) -> float:
    """Doymuş su buharı yoğunluğu (kg/m³), Magnus yaklaşımı."""
    e_s = 611.2 * math.exp(17.62 * temp_c / (243.12 + temp_c))   # Pa
    return e_s / (461.5 * (temp_c + 273.15))


def rh_to_vapor_density(rh: float, temp_c: float) -> float:
    return rh / 100.0 * saturation_vapor_density(temp_c)


@dataclass
class ClimateState:
    temp_c: float
    rh: float
    co2_ppm: float


class RoomClimate:
    def __init__(self, room_cfg: dict, pid_cfg: dict):
        self.cfg = room_cfg
        self.pid = pid_cfg
        self.volume = room_cfg["alan_m2"] * room_cfg["yukseklik_m"]
        self.heat_capacity = self.volume * AIR_DENSITY * AIR_CP * room_cfg["isil_kutle_carpani"]  # J/K
        self.state = None
        self._temp_integral = 0.0
        self._rh_integral = 0.0
        self._co2_integral = 0.0

    def reset(self, temp_c: float, rh: float, co2_ppm: float) -> None:
        self.state = ClimateState(temp_c, rh, co2_ppm)
        self._temp_integral = 0.0
        self._rh_integral = 0.0
        self._co2_integral = 0.0

    def substep(self, dt_h: float, temp_sp: float, rh_sp: float, co2_sp: float,
                outside: dict, bio_heat_w: float, bio_co2_l_h: float, evaporation_kg_h: float) -> dict:
        """Odayı dt_h saat ilerletir; bu iç adımdaki tüketimleri döndürür."""
        s, c, p = self.state, self.cfg, self.pid
        dt_s = dt_h * 3600.0

        # --- Taze hava: CO2 ayar noktasını izleyen PI denetleyici (ACH, saatte hava değişimi)
        error_c = (s.co2_ppm - co2_sp) / 1000.0
        ach_min, ach_max = c["taze_hava_min_ach"], c["taze_hava_maks_ach"]
        ach = ach_min + p["co2_kp_ach"] * error_c + p["co2_ki_ach_h"] * self._co2_integral
        if ach_min < ach < ach_max or (ach <= ach_min and error_c > 0) or (ach >= ach_max and error_c < 0):
            self._co2_integral = max(0.0, self._co2_integral + error_c * dt_h)
        ach = max(ach_min, min(ach_max, ach))

        # --- Sıcaklık: PI denetleyici, ısıtma (+) ya da soğutma (−) gücü
        error_t = temp_sp - s.temp_c
        hvac_w = p["sicaklik_kp_w_k"] * error_t + p["sicaklik_ki_w_kh"] * self._temp_integral
        hvac_max = c["isitma_maks_kw"] * 1000.0
        cool_max = c["sogutma_maks_kw"] * 1000.0
        if -cool_max < hvac_w < hvac_max:          # doygunlukta integrali büyütme (anti-windup)
            self._temp_integral += error_t * dt_h
        hvac_w = max(-cool_max, min(hvac_max, hvac_w))

        air_flow_m3_h = ach * self.volume
        vent_w_k = air_flow_m3_h / 3600.0 * AIR_DENSITY * AIR_CP
        heat_w = (c["isi_kayip_w_k"] * (outside["temp_c"] - s.temp_c)
                  + vent_w_k * (outside["temp_c"] - s.temp_c)
                  + hvac_w + bio_heat_w)
        new_temp = s.temp_c + heat_w * dt_s / self.heat_capacity

        # --- Nem: PI denetleyici, nemlendirici debisi (kg/h, yalnızca ekleyebilir)
        error_rh = rh_sp - s.rh
        humid_kg_h = p["nem_kp_kg_saat_yuzde"] * error_rh + p["nem_ki_kg_saat2_yuzde"] * self._rh_integral
        humid_max = c["nemlendirici_maks_kg_saat"]
        if 0.0 < humid_kg_h < humid_max:
            self._rh_integral += error_rh * dt_h
        elif humid_kg_h <= 0.0 and error_rh < 0:
            self._rh_integral = max(0.0, self._rh_integral + error_rh * dt_h)
        humid_kg_h = max(0.0, min(humid_max, humid_kg_h))

        vapor = rh_to_vapor_density(s.rh, s.temp_c) * self.volume                 # kg
        vapor_out = rh_to_vapor_density(outside["rh"], outside["temp_c"])        # kg/m³
        # soğutma bataryasında yoğuşma: soğutma gücünün bir kısmı nem almaya gider (gizli ısı)
        dehumid_kg_h = max(0.0, -hvac_w) * c["sogutma_nem_alma_orani"] * 3600.0 / LATENT_HEAT
        vapor += (humid_kg_h + evaporation_kg_h - dehumid_kg_h) * dt_h
        vapor -= air_flow_m3_h * dt_h * (vapor / self.volume - vapor_out)
        vapor = max(0.0, vapor)
        sat = saturation_vapor_density(new_temp) * self.volume
        new_rh = min(100.0, 100.0 * vapor / sat)                                 # %100'ün üstü yoğuşur

        # --- CO2 (ppm): 1 L CO2 / 1 m³ hava = 1000 ppm
        dco2 = bio_co2_l_h * 1000.0 / self.volume - ach * (s.co2_ppm - outside["co2_ppm"])
        new_co2 = max(outside["co2_ppm"], s.co2_ppm + dco2 * dt_h)

        self.state = ClimateState(new_temp, new_rh, new_co2)

        energy_kwh = (abs(hvac_w) / c["isi_pompasi_cop"] / 1000.0 * dt_h
                      + humid_kg_h * dt_h * c["nemlendirici_kwh_kg"]
                      + air_flow_m3_h * dt_h * c["fan_kwh_m3"])
        return {"enerji_kwh": energy_kwh, "su_l": humid_kg_h * dt_h, "ach": ach,
                "isitma_kwh": max(0.0, hvac_w) / 1000.0 * dt_h,
                "sogutma_kwh": max(0.0, -hvac_w) / 1000.0 * dt_h}
