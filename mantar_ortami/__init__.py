"""K1 · Kapalı mantar yetiştirme odası simülasyonu (Gymnasium ortamı).

Alt modeller:
    iklim.py      oda iklimi: sıcaklık, bağıl nem, CO2 (enerji–kütle dengesi)
    substrat.py   substrat: blok nemi, sıcaklığı, kolonizasyon oranı
    biyoloji.py   biyoloji: gelişim evresi, pin sayısı, biyokütle, hasat dalgası, kalite
    kaynaklar.py  kaynak tüketimi: enerji ve su
    stres.py      stres çarpanları (uygun aralığa uzaklık → 0–1)
    ortam.py      MantarOrtami: alt modelleri birleştiren Gymnasium ortamı
"""
