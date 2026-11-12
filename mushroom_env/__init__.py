"""K1 · Kapalı mantar yetiştirme odası simülasyonu (Gymnasium ortamı).

Alt modeller:
    climate.py    oda iklimi: sıcaklık, bağıl nem, CO2 (enerji–kütle dengesi)
    substrate.py  substrat: blok nemi, sıcaklığı, kolonizasyon oranı
    biology.py    biyoloji: gelişim evresi, pin sayısı, biyokütle, hasat dalgası, kalite
    resources.py  kaynak tüketimi: enerji ve su
    env.py        MushroomEnv: alt modelleri birleştiren Gymnasium ortamı
"""
