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

HAVA_YOGUNLUGU = 1.2       # kg/m³
HAVA_OZGUL_ISI = 1005.0    # J/(kg·K)
GIZLI_ISI = 2.45e6         # J/kg, suyun buharlaşma gizli ısısı


def doymus_buhar_yogunlugu(sicaklik_c: float) -> float:
    """Doymuş su buharı yoğunluğu (kg/m³), Magnus yaklaşımı."""
    e_s = 611.2 * math.exp(17.62 * sicaklik_c / (243.12 + sicaklik_c))   # Pa
    return e_s / (461.5 * (sicaklik_c + 273.15))


def nemden_buhar_yogunlugu(bagil_nem: float, sicaklik_c: float) -> float:
    return bagil_nem / 100.0 * doymus_buhar_yogunlugu(sicaklik_c)


@dataclass
class IklimDurumu:
    sicaklik_c: float
    bagil_nem: float
    co2_ppm: float


class OdaIklimi:
    def __init__(self, oda_ayar: dict, pid_ayar: dict):
        self.ayar = oda_ayar
        self.pid = pid_ayar
        self.hacim = oda_ayar["alan_m2"] * oda_ayar["yukseklik_m"]
        self.isi_sigasi = self.hacim * HAVA_YOGUNLUGU * HAVA_OZGUL_ISI * oda_ayar["isil_kutle_carpani"]  # J/K
        self.durum = None
        self._t_integral = 0.0
        self._bn_integral = 0.0
        self._co2_integral = 0.0

    def sifirla(self, sicaklik_c: float, bagil_nem: float, co2_ppm: float) -> None:
        self.durum = IklimDurumu(sicaklik_c, bagil_nem, co2_ppm)
        self._t_integral = 0.0
        self._bn_integral = 0.0
        self._co2_integral = 0.0

    def alt_adim(self, dt_saat: float, t_ayar: float, bn_ayar: float, co2_ayar: float,
                 dis: dict, misel_isi_w: float, misel_co2_l_saat: float, buharlasma_kg_saat: float) -> dict:
        """Odayı dt_saat saat ilerletir; bu iç adımdaki tüketimleri döndürür."""
        d, a, p = self.durum, self.ayar, self.pid
        dt_s = dt_saat * 3600.0

        # --- Taze hava: CO2 ayar noktasını izleyen PI denetleyici (ACH, saatte hava değişimi)
        hata_co2 = (d.co2_ppm - co2_ayar) / 1000.0
        ach_min, ach_maks = a["taze_hava_min_ach"], a["taze_hava_maks_ach"]
        ach = ach_min + p["co2_kp_ach"] * hata_co2 + p["co2_ki_ach_h"] * self._co2_integral
        if (ach_min < ach < ach_maks or (ach <= ach_min and hata_co2 > 0)
                or (ach >= ach_maks and hata_co2 < 0)):
            self._co2_integral = max(0.0, self._co2_integral + hata_co2 * dt_saat)
        ach = max(ach_min, min(ach_maks, ach))

        # --- Sıcaklık: PI denetleyici, ısıtma (+) ya da soğutma (−) gücü
        hata_t = t_ayar - d.sicaklik_c
        iklimlendirme_w = p["sicaklik_kp_w_k"] * hata_t + p["sicaklik_ki_w_kh"] * self._t_integral
        isitma_maks = a["isitma_maks_kw"] * 1000.0
        sogutma_maks = a["sogutma_maks_kw"] * 1000.0
        if -sogutma_maks < iklimlendirme_w < isitma_maks:   # doygunlukta integrali büyütme (anti-windup)
            self._t_integral += hata_t * dt_saat
        iklimlendirme_w = max(-sogutma_maks, min(isitma_maks, iklimlendirme_w))

        hava_debisi_m3_saat = ach * self.hacim
        havalandirma_w_k = hava_debisi_m3_saat / 3600.0 * HAVA_YOGUNLUGU * HAVA_OZGUL_ISI
        isi_w = (a["isi_kayip_w_k"] * (dis["sicaklik_c"] - d.sicaklik_c)
                 + havalandirma_w_k * (dis["sicaklik_c"] - d.sicaklik_c)
                 + iklimlendirme_w + misel_isi_w)
        yeni_sicaklik = d.sicaklik_c + isi_w * dt_s / self.isi_sigasi

        # --- Nem: PI denetleyici, nemlendirici debisi (kg/saat, yalnızca ekleyebilir)
        hata_bn = bn_ayar - d.bagil_nem
        nemlendirme_kg_saat = p["nem_kp_kg_saat_yuzde"] * hata_bn + p["nem_ki_kg_saat2_yuzde"] * self._bn_integral
        nemlendirici_maks = a["nemlendirici_maks_kg_saat"]
        if 0.0 < nemlendirme_kg_saat < nemlendirici_maks:
            self._bn_integral += hata_bn * dt_saat
        elif nemlendirme_kg_saat <= 0.0 and hata_bn < 0:
            self._bn_integral = max(0.0, self._bn_integral + hata_bn * dt_saat)
        nemlendirme_kg_saat = max(0.0, min(nemlendirici_maks, nemlendirme_kg_saat))

        buhar = nemden_buhar_yogunlugu(d.bagil_nem, d.sicaklik_c) * self.hacim         # kg
        dis_buhar = nemden_buhar_yogunlugu(dis["bagil_nem"], dis["sicaklik_c"])        # kg/m³
        # soğutma bataryasında yoğuşma: soğutma gücünün bir kısmı nem almaya gider (gizli ısı)
        nem_alma_kg_saat = max(0.0, -iklimlendirme_w) * a["sogutma_nem_alma_orani"] * 3600.0 / GIZLI_ISI
        buhar += (nemlendirme_kg_saat + buharlasma_kg_saat - nem_alma_kg_saat) * dt_saat
        buhar -= hava_debisi_m3_saat * dt_saat * (buhar / self.hacim - dis_buhar)
        buhar = max(0.0, buhar)
        doygun = doymus_buhar_yogunlugu(yeni_sicaklik) * self.hacim
        yeni_bn = min(100.0, 100.0 * buhar / doygun)                                     # %100'ün üstü yoğuşur

        # --- CO2 (ppm): 1 L CO2 / 1 m³ hava = 1000 ppm
        dco2 = misel_co2_l_saat * 1000.0 / self.hacim - ach * (d.co2_ppm - dis["co2_ppm"])
        yeni_co2 = max(dis["co2_ppm"], d.co2_ppm + dco2 * dt_saat)

        self.durum = IklimDurumu(yeni_sicaklik, yeni_bn, yeni_co2)

        enerji_kwh = (abs(iklimlendirme_w) / a["isi_pompasi_cop"] / 1000.0 * dt_saat
                      + nemlendirme_kg_saat * dt_saat * a["nemlendirici_kwh_kg"]
                      + hava_debisi_m3_saat * dt_saat * a["fan_kwh_m3"])
        return {"enerji_kwh": enerji_kwh, "su_l": nemlendirme_kg_saat * dt_saat, "ach": ach,
                "isitma_kwh": max(0.0, iklimlendirme_w) / 1000.0 * dt_saat,
                "sogutma_kwh": max(0.0, -iklimlendirme_w) / 1000.0 * dt_saat}
