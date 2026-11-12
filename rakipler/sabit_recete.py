"""Sabit ticari reçete + PID (K3, yöntem dokümanı B.6).

Her evrede literatürdeki uygun aralığın ortasını sıcaklık ve nem ayar noktası olarak kullanır.
CO2 ayar noktası meyvelenmede türün iyi kabul edilen sınırının %80'i, inkübasyonda varsa misel sınırının
%80'idir (yoksa 5000 ppm). Ayar noktalarını alt katmandaki PI denetleyiciler izler.
Şoku gözlenen kolonizasyon (shiitake: kahverengileşme) eşiği geçince, hasadı meyve gövdesi optimum yaşa
gelince verir.
Ajanla aynı gözlem vektörünü kullanır (gozlemi_coz); gerçek iç duruma erişmez.
"""

import numpy as np

from mantar_ortami.ortam import gozlemi_coz
from .politika import Politika


class SabitRecete(Politika):
    ad = "sabit_recete"

    def __init__(self, ortam, co2_orani: float = 0.8, inkubasyon_co2_varsayilan: float = 5000.0):
        self.ortam = ortam
        ta = ortam.tur_ayarlari
        self.ink, self.meyve, self.biyo = ta["inkubasyon"], ta["meyvelenme"], ta["biyoloji"]
        self.kahve = ta.get("kahverengilesme")
        self.co2_orani = co2_orani
        self.inkubasyon_co2_varsayilan = inkubasyon_co2_varsayilan

    def eylem_sec(self, gozlem):
        g = gozlemi_coz(gozlem)
        inkubasyonda = g["evre_inkubasyon"] > 0.5
        kahverengilesmede = g["evre_kahverengilesme"] > 0.5
        if inkubasyonda or kahverengilesmede:
            sicaklik = sum(self.ink["sicaklik_opt"]) / 2
            bn = self.ortam.ayarlar["dis_hava"]["bagil_nem"]      # torbalar kapalı: nem kontrolü yok
            sinir = self.ink.get("co2_maks_ppm")
            co2 = self.co2_orani * sinir if sinir else self.inkubasyon_co2_varsayilan
        else:
            sicaklik = sum(self.meyve["sicaklik_opt"]) / 2
            bn = sum(self.meyve["nem_opt"]) / 2
            co2 = self.co2_orani * self.meyve["co2_iyi_maks_ppm"]
        if self.kahve is None:
            ilk_hazir = inkubasyonda and g["kolonizasyon_gozlenen"] >= self.ink["kolonizasyon_esigi"]
        else:
            ilk_hazir = kahverengilesmede and g["kahverengilesme_orani"] >= self.kahve["esik"]
        sok = int(ilk_hazir or (g["evre_dinlenme"] > 0.5 and g["evre_gun"] >= self.biyo["dinlenme_gun"]))
        hasat = int(g["evre_buyume"] > 0.5 and g["meyve_yas_gun"] >= self.biyo["hasat_opt_yas_gun"])
        return {"ayar": self.ortam.ayar_noktalarini_olcekle(sicaklik, bn, co2), "karar": np.array([sok, hasat])}
