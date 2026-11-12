"""Eğitilmiş PPO modelini, karşılaştırma yöntemleriyle aynı Politika arayüzünden çağırır."""

from pathlib import Path

from stable_baselines3 import PPO

from rakipler.politika import Politika
from .sarmalayici import duz_eylemi_coz


class PPOAjani(Politika):
    """belirlenimci=False varsayılandır: şok ve hasat kararları sürekli bir çıktının eşiklenmesiyle
    verildiği için, dağılımın ortalaması (belirlenimci eylem) eşiği hiç geçmeyebilir. 7. hafta ön
    denemesinde bir tohumun belirlenimci politikası hiç hasat etmedi; örneklemeli politika etti.
    Kalıcı çözüm: ayrık kararlar için Bernoulli/MultiDiscrete çıktı (bkz. sarmalayici.py)."""
    ad = "ppo"

    def __init__(self, model_yolu: str | Path, belirlenimci: bool = False):
        self.model = PPO.load(str(model_yolu), device="cpu")
        self.belirlenimci = belirlenimci

    def eylem_sec(self, gozlem):
        eylem, _ = self.model.predict(gozlem, deterministic=self.belirlenimci)
        return duz_eylemi_coz(eylem)
