"""Eylem sarmalayıcısı: Stable-Baselines3 için hibrit eylemi tek bir sürekli vektöre çevirir.

Ortamın eylemi bir Dict'tir ("ayar": Box(3), "karar": MultiBinary(2)). SB3'ün PPO'su Dict eylem
uzayını desteklemediği için ajan 5 boyutlu bir Box(-1, 1) üretir:
    ilk 3 değer → ayar noktaları (olduğu gibi)
    son 2 değer → şok ve hasat kararları (0'dan büyükse 1)
Bu eşikleme, ayrık kararları sürekli politikayla öğrenmenin basit bir yoludur; ileride
MultiDiscrete ya da hibrit (parametreli) eylem uzaylarıyla karşılaştırılabilir.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces


def duz_eylemi_coz(eylem) -> dict:
    eylem = np.asarray(eylem, dtype=np.float32)
    return {"ayar": np.clip(eylem[:3], -1.0, 1.0), "karar": (eylem[3:5] > 0.0).astype(int)}


class DuzEylem(gym.ActionWrapper):
    def __init__(self, ortam):
        super().__init__(ortam)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(5,), dtype=np.float32)

    def action(self, action):          # Gymnasium ActionWrapper arayüzü
        return duz_eylemi_coz(action)
