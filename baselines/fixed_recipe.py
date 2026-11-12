"""Sabit ticari reçete + PID (K3, yöntem dokümanı B.6).

Her evrede literatürdeki uygun aralığın ortasını sıcaklık ve nem ayar noktası olarak kullanır.
CO2 ayar noktası meyvelenmede türün iyi kabul edilen sınırının %80'i, inkübasyonda varsa misel sınırının
%80'idir (yoksa 5000 ppm). Ayar noktalarını alt katmandaki PI denetleyiciler izler.
Şoku gözlenen kolonizasyon (shiitake: kahverengileşme) eşiği geçince, hasadı meyve gövdesi optimum yaşa
gelince verir.
Ajanla aynı gözlem vektörünü kullanır (decode_observation); gerçek iç duruma erişmez.
"""

import numpy as np

from mushroom_env.env import decode_observation
from .policy import Policy


class FixedRecipe(Policy):
    name = "sabit_recete"

    def __init__(self, env, co2_ratio: float = 0.8, co2_incubation_default: float = 5000.0):
        self.env = env
        sp = env.species_cfg
        self.inc, self.fr, self.bio = sp["inkubasyon"], sp["meyvelenme"], sp["biyoloji"]
        self.brown = sp.get("kahverengilesme")
        self.co2_ratio = co2_ratio
        self.co2_incubation_default = co2_incubation_default

    def act(self, observation):
        g = decode_observation(observation)
        incubating = g["evre_inkubasyon"] > 0.5
        browning = g["evre_kahverengilesme"] > 0.5
        if incubating or browning:
            temp = sum(self.inc["sicaklik_opt"]) / 2
            rh = self.env.cfg["dis_hava"]["bagil_nem"]          # torbalar kapalı: nem kontrolü yok
            limit = self.inc.get("co2_maks_ppm")
            co2 = self.co2_ratio * limit if limit else self.co2_incubation_default
        else:
            temp = sum(self.fr["sicaklik_opt"]) / 2
            rh = sum(self.fr["nem_opt"]) / 2
            co2 = self.co2_ratio * self.fr["co2_iyi_maks_ppm"]
        if self.brown is None:
            first_ready = incubating and g["kolonizasyon_gozlenen"] >= self.inc["kolonizasyon_esigi"]
        else:
            first_ready = browning and g["kahverengilesme_orani"] >= self.brown["esik"]
        shock = int(first_ready or (g["evre_dinlenme"] > 0.5 and g["evre_gun"] >= self.bio["dinlenme_gun"]))
        harvest = int(g["evre_buyume"] > 0.5 and g["meyve_yas_gun"] >= self.bio["hasat_opt_yas_gun"])
        return {"ayar": self.env.scale_setpoints(temp, rh, co2), "karar": np.array([shock, harvest])}
