"""Biyoloji alt modeli: gelişim evresi, hasat dalgası, biyokütle ve kalite.

Evreler:
    INKUBASYON       misel substratı sarıyor
    KAHVERENGILESME  (yalnızca shiitake) misel tamamlanınca kendiliğinden başlar; yüzey kahverengileşir
    PIN              şoktan sonra taslakların (primordia) oluşması
    BUYUME           meyve gövdelerinin büyümesi; ajan hasat kararını verir
    DINLENME         hasattan sonra bir sonraki dalgaya kadar bekleme; sonra yeniden şok gerekir
    BITTI            son dalga hasat edildi ya da süre doldu

Şok, ajanın ayrık bir kararıdır. Gerçek üretimde tetikleme sıcaklık şokuyla (Kim vd. 2020)
ya da su şokuyla (Rocha vd. 2025) yapılır; model bu yöntemleri tek bir "tetikle" kararıyla temsil eder.

Suş farkı: her bölümün başında meyvelenme sıcaklık aralığı rastgele kaydırılır ve biyolojik
verimlilik literatürdeki aralıktan örneklenir (config.yaml → rastgelelik). Ajan bu değerleri görmez.
"""

import math

from .stres import bant, co2_buyume, parcali_kalite

INKUBASYON, KAHVERENGILESME, PIN, BUYUME, DINLENME, BITTI = range(6)
EVRE_ADLARI = ["inkubasyon", "kahverengilesme", "pin", "buyume", "dinlenme", "bitti"]


class Biyoloji:
    def __init__(self, tur_ayarlari: dict, kuru_substrat_kg: float, co2_ayar: dict, dis_co2: float):
        self.ink = tur_ayarlari["inkubasyon"]
        self.kahve = tur_ayarlari.get("kahverengilesme")
        self.meyve = tur_ayarlari["meyvelenme"]
        self.biyo = tur_ayarlari["biyoloji"]
        self.co2_ayar = co2_ayar
        self.dis_co2 = dis_co2
        self.kuru_kg = kuru_substrat_kg
        g = self.biyo["buyume_gun"] * 24.0
        self.buyume_hizi_saat = math.log((0.95 * 0.99) / (0.01 * 0.05)) / g   # %1 → %95, buyume_gun günde

    def sifirla(self, rng, sus_rastgele: bool, verim_rastgele: bool) -> None:
        kayma = self.meyve.get("sus_sicaklik_kaymasi_c") or 0.0
        self.sicaklik_kaymasi = float(rng.uniform(-kayma, kayma)) if sus_rastgele else 0.0
        bv_alt, bv_ust = self.biyo["biyolojik_verimlilik"]
        self.bv = float(rng.uniform(bv_alt, bv_ust)) if verim_rastgele else (bv_alt + bv_ust) / 2
        toplam_verim = self.bv * self.kuru_kg
        self.dalga_kapasiteleri = [pay * toplam_verim for pay in self.biyo["dalga_paylari"]]

        self.evre = INKUBASYON
        self.dalga = 0                 # tamamlanan hasat dalgası sayısı
        self.evre_saat = 0.0
        self.kahverengilesme = 0.0     # kahverengileşme ilerlemesi (0–1)
        self.yas_gun = 0.0             # meyve gövdesi yaşı (BUYUME evresinde)
        self.biyokutle = 0.0           # mevcut dalgadaki taze mantar (kg)
        self.kapasite = 0.0            # mevcut dalganın kapasitesi (kg)
        self.co2_kalitesi = 1.0
        self.hasat_kg = 0.0
        self.hasat_deger_kg = 0.0      # kaliteyle ağırlıklandırılmış hasat (kg eşdeğeri)
        self.curuyen_kg = 0.0

    @property
    def dalga_sayisi(self) -> int:
        return len(self.dalga_kapasiteleri)

    @property
    def meyvelenme_sicaklik_bandi(self) -> tuple:
        alt, ust = self.meyve["sicaklik_opt"]
        return alt + self.sicaklik_kaymasi, ust + self.sicaklik_kaymasi

    def kalite(self) -> float:
        gecikme = max(0.0, self.yas_gun - self.biyo["hasat_opt_yas_gun"])
        return max(0.0, self.co2_kalitesi * (1.0 - self.biyo["kalite_dusus_gun"] * gecikme))

    def pazarlanabilir_kg(self) -> float:
        return self.biyokutle * self.kalite()

    # --- kararlar
    def sok(self, kolonizasyon: float) -> bool:
        """Meyvelenmeyi tetikleme. Etkiliyse True döner."""
        if self.kahve is None:
            ilk_hazir = self.evre == INKUBASYON and kolonizasyon >= self.ink["kolonizasyon_esigi"]
        else:
            ilk_hazir = self.evre == KAHVERENGILESME and self.kahverengilesme >= self.kahve["esik"]
        sonraki_hazir = self.evre == DINLENME and self.evre_saat >= self.biyo["dinlenme_gun"] * 24.0
        if ilk_hazir or sonraki_hazir:
            self._gec(PIN)
            return True
        return False

    def hasat(self) -> float:
        """Hasat. Pazarlanabilir kg eşdeğerini döndürür (BUYUME dışında 0)."""
        if self.evre != BUYUME or self.biyokutle <= 0.0:
            return 0.0
        deger = self.pazarlanabilir_kg()
        self.hasat_kg += self.biyokutle
        self.hasat_deger_kg += deger
        self._dalgayi_bitir()
        return deger

    # --- zaman ilerlemesi
    def alt_adim(self, dt_saat: float, sicaklik_c: float, bagil_nem: float, co2_ppm: float,
                 nem_carpani: float, kolonizasyon: float) -> None:
        self.evre_saat += dt_saat

        if self.evre == INKUBASYON and self.kahve is not None and kolonizasyon >= self.ink["kolonizasyon_esigi"]:
            self._gec(KAHVERENGILESME)                           # misel tamamlanınca kendiliğinden
        elif self.evre == KAHVERENGILESME:
            alt, ust = self.ink["sicaklik_opt"]                  # kahverengileşme inkübasyon koşullarında sürer
            f_t = bant(sicaklik_c, alt, ust, self.ink["sicaklik_tolerans"])
            self.kahverengilesme = min(1.0, self.kahverengilesme + f_t * dt_saat / (self.kahve["sure_gun"] * 24.0))
        elif self.evre == PIN and self.evre_saat >= self.biyo["pin_gun"] * 24.0:
            self._gec(BUYUME)
            self.kapasite = self.dalga_kapasiteleri[self.dalga]
            self.biyokutle = 0.01 * self.kapasite
            self.co2_kalitesi = 1.0
            self.yas_gun = 0.0
        elif self.evre == BUYUME:
            self.yas_gun += dt_saat / 24.0
            m = self.meyve
            alt, ust = self.meyvelenme_sicaklik_bandi
            f_t = bant(sicaklik_c, alt, ust, m["sicaklik_tolerans"])
            g_bn = bant(bagil_nem, m["nem_opt"][0], m["nem_opt"][1], m["nem_tolerans"])
            h_co2 = co2_buyume(co2_ppm, self.dis_co2, m["co2_iyi_maks_ppm"], self.co2_ayar["erken_etki"])
            hiz = self.buyume_hizi_saat * f_t * g_bn * h_co2 * nem_carpani
            if self.kapasite > 0:
                self.biyokutle += hiz * self.biyokutle * (1.0 - self.biyokutle / self.kapasite) * dt_saat
            q = parcali_kalite(co2_ppm, m["co2_iyi_maks_ppm"], m["co2_kalite_esigi_ppm"], m["co2_sekil_bozulma_ppm"])
            self.co2_kalitesi = min(self.co2_kalitesi, q)
            if self.yas_gun >= self.biyo["curume_yas_gun"]:      # hasat edilmezse ürün kaybolur
                self.curuyen_kg += self.biyokutle
                self._dalgayi_bitir()

    def kapasite_kaybet(self, oran: float) -> None:
        """Kontaminasyon: kalan kapasitenin bir kısmı ve mevcut ürünün kalitesi kaybolur."""
        for i in range(self.dalga, self.dalga_sayisi):
            self.dalga_kapasiteleri[i] *= (1.0 - oran)
        if self.evre == BUYUME:
            self.kapasite *= (1.0 - oran)
            self.biyokutle = min(self.biyokutle, self.kapasite)
            self.co2_kalitesi *= (1.0 - oran)

    def _dalgayi_bitir(self) -> None:
        self.biyokutle = 0.0
        self.kapasite = 0.0
        self.yas_gun = 0.0
        self.dalga += 1
        self._gec(BITTI if self.dalga >= self.dalga_sayisi else DINLENME)

    def _gec(self, evre: int) -> None:
        self.evre = evre
        self.evre_saat = 0.0
