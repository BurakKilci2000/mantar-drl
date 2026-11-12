"""Stres çarpanları: bir değişkenin uygun aralıkta olup olmadığını 0–1 arasında bir sayıya çevirir.

Aralığın içinde çarpan 1'dir; aralığın dışına çıkıldıkça Gauss biçiminde azalır.
Büyüme, bu çarpanların çarpımıyla modellenir (öneri formu, 3.1):
    dB/dt = mu_max · f(T) · g(RH) · h(CO2) · k(substrat nemi) · ...
"""

import math


def band(x: float, low: float, high: float, tolerance: float) -> float:
    """x, [low, high] aralığındaysa 1; dışındaysa uzaklığa göre Gauss biçiminde azalır.

    tolerance: aralığın dışında çarpanın yaklaşık 0,61'e düştüğü uzaklık (1 standart sapma).
    """
    if low <= x <= high:
        return 1.0
    distance = (low - x) if x < low else (x - high)
    return math.exp(-0.5 * (distance / tolerance) ** 2)


def upper_limit(x: float, limit: float, tolerance: float) -> float:
    """x, limitin altındaysa 1; üstüne çıktıkça Gauss biçiminde azalır (ör. CO2)."""
    if x <= limit:
        return 1.0
    return math.exp(-0.5 * ((x - limit) / tolerance) ** 2)


def piecewise_quality(co2_ppm: float, good_max: float, quality_threshold: float, deform: float) -> float:
    """CO2'ye bağlı kalite katsayısı (meyvelenme evresi).

    good_max altında 1; quality_threshold'da 0,5; deform (şekil bozulması) ve üstünde 0,1.
    Ara değerler doğrusal olarak hesaplanır.
    """
    if co2_ppm <= good_max:
        return 1.0
    if co2_ppm <= quality_threshold:
        return 1.0 - 0.5 * (co2_ppm - good_max) / (quality_threshold - good_max)
    if co2_ppm <= deform:
        return 0.5 - 0.4 * (co2_ppm - quality_threshold) / (deform - quality_threshold)
    return 0.1


def co2_growth(co2_ppm: float, outside_ppm: float, good_max: float, early_effect: float) -> float:
    """CO2'nin büyümeye etkisi.

    Dış hava düzeyinden good_max'a kadar doğrusal olarak (1 − early_effect)'e iner;
    good_max'ın üstünde Gauss biçiminde hızla düşer. Zhang vd. 2023: CO2 %0,04'ten %0,31'e
    çıkarken bile şapka küçülüyor.
    """
    if co2_ppm <= outside_ppm:
        return 1.0
    if co2_ppm <= good_max:
        return 1.0 - early_effect * (co2_ppm - outside_ppm) / (good_max - outside_ppm)
    return (1.0 - early_effect) * math.exp(-0.5 * ((co2_ppm - good_max) / good_max) ** 2)
