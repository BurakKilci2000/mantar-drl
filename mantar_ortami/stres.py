"""Stres çarpanları: bir değişkenin uygun aralıkta olup olmadığını 0–1 arasında bir sayıya çevirir.

Aralığın içinde çarpan 1'dir; aralığın dışına çıkıldıkça Gauss biçiminde azalır.
Büyüme, bu çarpanların çarpımıyla modellenir (öneri formu, 3.1):
    dB/dt = mu_max · f(T) · g(RH) · h(CO2) · k(substrat nemi) · ...
"""

import math


def bant(x: float, alt: float, ust: float, tolerans: float) -> float:
    """x, [alt, ust] aralığındaysa 1; dışındaysa uzaklığa göre Gauss biçiminde azalır.

    tolerans: aralığın dışında çarpanın yaklaşık 0,61'e düştüğü uzaklık (1 standart sapma).
    """
    if alt <= x <= ust:
        return 1.0
    uzaklik = (alt - x) if x < alt else (x - ust)
    return math.exp(-0.5 * (uzaklik / tolerans) ** 2)


def ust_sinir(x: float, sinir: float, tolerans: float) -> float:
    """x, sınırın altındaysa 1; üstüne çıktıkça Gauss biçiminde azalır (ör. CO2)."""
    if x <= sinir:
        return 1.0
    return math.exp(-0.5 * ((x - sinir) / tolerans) ** 2)


def parcali_kalite(co2_ppm: float, iyi_maks: float, kalite_esigi: float, sekil_bozulma: float) -> float:
    """CO2'ye bağlı kalite katsayısı (meyvelenme evresi).

    iyi_maks altında 1; kalite_esigi'nde 0,5; sekil_bozulma ve üstünde 0,1.
    Ara değerler doğrusal olarak hesaplanır.
    """
    if co2_ppm <= iyi_maks:
        return 1.0
    if co2_ppm <= kalite_esigi:
        return 1.0 - 0.5 * (co2_ppm - iyi_maks) / (kalite_esigi - iyi_maks)
    if co2_ppm <= sekil_bozulma:
        return 0.5 - 0.4 * (co2_ppm - kalite_esigi) / (sekil_bozulma - kalite_esigi)
    return 0.1


def co2_buyume(co2_ppm: float, dis_ppm: float, iyi_maks: float, erken_etki: float) -> float:
    """CO2'nin büyümeye etkisi.

    Dış hava düzeyinden iyi_maks'a kadar doğrusal olarak (1 − erken_etki)'ye iner;
    iyi_maks'ın üstünde Gauss biçiminde hızla düşer. Zhang vd. 2023: CO2 %0,04'ten %0,31'e
    çıkarken bile şapka küçülüyor.
    """
    if co2_ppm <= dis_ppm:
        return 1.0
    if co2_ppm <= iyi_maks:
        return 1.0 - erken_etki * (co2_ppm - dis_ppm) / (iyi_maks - dis_ppm)
    return (1.0 - erken_etki) * math.exp(-0.5 * ((co2_ppm - iyi_maks) / iyi_maks) ** 2)
