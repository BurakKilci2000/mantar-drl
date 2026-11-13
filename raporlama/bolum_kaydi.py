"""Bir üretim döngüsünü adım adım kaydeder (K4). Arayüz ve grafikler bu tabloyu kullanır.

Her satır bir karar adımıdır (4 saat): iklim, ayar noktaları, evre, kararlar, biyokütle,
hasat edilen miktar ve birikimli enerji/su/kazanç.
"""

import pandas as pd

from mantar_ortami.ortam import EVRE_ADLARI


def bolum_kaydi(ortam, politika, tohum: int) -> tuple[pd.DataFrame, dict]:
    """Bölümü çalıştırır; (adım tablosu, bölüm özeti) döndürür."""
    politika.sifirla(tohum)
    gozlem, _ = ortam.reset(seed=tohum)
    b, sayac = ortam.biyoloji, ortam.sayac
    satirlar, kazanc, bitti = [], 0.0, False
    while not bitti:
        eylem = politika.eylem_sec(gozlem)
        hasat_once = b.hasat_kg
        gozlem, odul, terminated, truncated, bilgi = ortam.step(eylem)
        kazanc += bilgi["odul_tl"]
        d, ay = ortam.iklim.durum, bilgi["ayar_noktalari"]
        satirlar.append({
            "gun": ortam.saat / 24.0,
            "sicaklik_c": d.sicaklik_c, "bagil_nem": d.bagil_nem, "co2_ppm": d.co2_ppm,
            "sicaklik_ayar": ay["sicaklik_c"], "nem_ayar": ay["bagil_nem"], "co2_ayar": ay["co2_ppm"],
            "dis_sicaklik_c": bilgi["gozlem"]["dis_sicaklik_c"],
            "evre": bilgi["evre"], "evre_no": EVRE_ADLARI.index(bilgi["evre"]),
            "sok": int(eylem["karar"][0]), "hasat_karari": int(eylem["karar"][1]),
            "kolonizasyon": ortam.substrat.kolonizasyon,
            "kolonizasyon_gozlenen": bilgi["gozlem"]["kolonizasyon_gozlenen"],
            "kahverengilesme": b.kahverengilesme,
            "biyokutle_kg": b.biyokutle, "kapasite_kg": b.kapasite, "kalite": b.kalite(),
            "dalga": b.dalga, "hasat_kg": b.hasat_kg - hasat_once, "toplam_hasat_kg": b.hasat_kg,
            "enerji_kwh": sayac.enerji_kwh, "su_l": sayac.su_l, "kazanc_tl": kazanc,
            "ach": bilgi["ortalama_ach"], "ihlal": bilgi["ihlal"], "kontaminasyon": bilgi["kontaminasyon"],
        })
        bitti = terminated or truncated
    ozet = {**bilgi["ozet"], "net_kazanc_tl": kazanc}
    return pd.DataFrame(satirlar), ozet
