"""Kural tabanlı kontrolcü (K3, yöntem dokümanı B.6).

Sabit reçeteden farkı: ayar noktasını her adımda gözlenen duruma göre kurallarla seçer.
Uygun aralığın içindeyken iklime dokunmaz (ölü bant), dışına çıkınca en yakın sınıra çeker.
Böylece gereksiz ısıtma, soğutma, nemlendirme ve havalandırma yapılmaz.

Kurallar (her karar adımında, gözlem vektöründen):
  Sıcaklık : ayar = gözlenen sıcaklık, ölü banda kırpılmış. Ölü bant uygun aralığın
             t_daralma kadar daraltılmış hâlidir: 0 → aralığın tamamı, 1 → yalnızca orta nokta
             (1 olunca sıcaklık kuralı sabit reçeteye eşitlenir)
  Nem      : meyvelenmede aynı kural, bn_daralma ile; torbalı evrelerde nem kontrolü yok
  CO2      : ayar = co2_orani × türün sınırı (bu düzeyin altında havalandırma en azda kalır)
  Şok      : sabit reçeteyle aynı eşikler
  Hasat    : biyokütle dalga kapasitesinin hasat_esigi kadarına ulaşınca ya da meyve optimum yaşa
             gelince (hangisi önce olursa)

Ajanla aynı gözlemi kullanır; suş kaymasını bilmez, literatürdeki aralıkları kullanır.
Dört parametresi ayarlanmis_kural.py'de doğrulama tohumlarında ayarlanır.
"""

import numpy as np

from mantar_ortami.ortam import gozlemi_coz
from .politika import Politika

VARSAYILAN = {"t_daralma": 0.0, "bn_daralma": 0.0, "co2_orani": 0.9, "hasat_esigi": 0.95}


class KuralTabanli(Politika):
    ad = "kural_tabanli"

    def __init__(self, ortam, parametreler: dict | None = None):
        self.ortam = ortam
        ta = ortam.tur_ayarlari
        self.ink, self.meyve, self.biyo = ta["inkubasyon"], ta["meyvelenme"], ta["biyoloji"]
        self.kahve = ta.get("kahverengilesme")
        self.p = {**VARSAYILAN, **(parametreler or {})}

    @staticmethod
    def _olu_bant(deger: float, aralik, daralma: float) -> float:
        """Değeri, daralma oranında daraltılmış [alt, üst] aralığına kırpar."""
        alt, ust = aralik
        yari = (ust - alt) / 2 * daralma
        return min(max(deger, alt + yari), ust - yari)

    def eylem_sec(self, gozlem):
        g, p = gozlemi_coz(gozlem), self.p
        inkubasyonda = g["evre_inkubasyon"] > 0.5
        kahverengilesmede = g["evre_kahverengilesme"] > 0.5
        torbada = inkubasyonda or kahverengilesmede

        aralik = self.ink if torbada else self.meyve
        sicaklik = self._olu_bant(g["sicaklik_c"], aralik["sicaklik_opt"], p["t_daralma"])

        if torbada:
            bn = self.ortam.ayarlar["dis_hava"]["bagil_nem"]
            sinir = self.ink.get("co2_maks_ppm")
            co2 = p["co2_orani"] * sinir if sinir else self.ortam.ayarlar["eylem_sinirlari"]["co2_ppm"][1]
        else:
            bn = self._olu_bant(g["bagil_nem"], self.meyve["nem_opt"], p["bn_daralma"])
            co2 = p["co2_orani"] * self.meyve["co2_iyi_maks_ppm"]

        if self.kahve is None:
            ilk_hazir = inkubasyonda and g["kolonizasyon_gozlenen"] >= self.ink["kolonizasyon_esigi"]
        else:
            ilk_hazir = kahverengilesmede and g["kahverengilesme_orani"] >= self.kahve["esik"]
        sok = int(ilk_hazir or (g["evre_dinlenme"] > 0.5 and g["evre_gun"] >= self.biyo["dinlenme_gun"]))
        buyumede = g["evre_buyume"] > 0.5
        hasat = int(buyumede and (g["biyokutle_orani"] >= p["hasat_esigi"]
                                  or g["meyve_yas_gun"] >= self.biyo["hasat_opt_yas_gun"]))
        return {"ayar": self.ortam.ayar_noktalarini_olcekle(sicaklik, bn, co2), "karar": np.array([sok, hasat])}
