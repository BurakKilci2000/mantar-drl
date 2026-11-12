"""MantarOrtami: alt modelleri birleştiren Gymnasium ortamı (K1).

Bir bölüm = bir üretim döngüsü (inokülasyondan son hasat dalgasına). Karar adımı Δt = 4 saat;
her karar adımında alt katman (PI denetleyiciler) 15 dakikalık iç adımlarla çalışır.

Eylem (hibrit, gymnasium.spaces.Dict):
    "ayar"  : Box(-1, 1, (3,))  → sıcaklık, bağıl nem ve CO2 ayar noktaları (alt katman PI ile izlenir)
    "karar" : MultiBinary(2)    → [meyvelenmeyi tetikleyen şok, hasat]

Ödül (öneri formu 3.2; yöntem dokümanı B.3):
    Δ(hasat edilmiş değer + bekleyen pazarlanabilir ürün değeri) − enerji maliyeti − su maliyeti
    − ihlal cezası − erken şok cezası; bölüm sonunda hasat edilmemiş ürün kaybedilir.
    Böylece ödül adım başına verilir (yoğun ödül) ama toplamı döngünün net kazancına eşittir.

Not: reset, step, action_space, observation_space, metadata ve np_random adları Gymnasium
arayüzünün parçasıdır; kütüphane bu adlarla çağırdığı için İngilizce kalır.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .biyoloji import BITTI, INKUBASYON, KAHVERENGILESME, EVRE_ADLARI, Biyoloji
from .iklim import OdaIklimi
from .kaynaklar import KaynakSayaci
from .substrat import Substrat

TURLER = ["istiridye", "shiitake", "aslan_yelesi"]
ISTEGE_BAGLI_ANAHTARLAR = {"co2_maks_ppm"}   # null olabilir: sınır yok demektir

# Gözlem vektörünün düzeni: politikalar bu adlarla okur (gozlemi_coz).
GOZLEM_ANAHTARLARI = (
    ["sicaklik_c", "bagil_nem", "co2_ppm", "substrat_nemi", "kolonizasyon_gozlenen", "kahverengilesme_orani"]
    + [f"evre_{n}" for n in EVRE_ADLARI]
    + ["dalga", "evre_gun", "meyve_yas_gun", "biyokutle_orani", "kalite", "dongu_gunu",
       "dis_sicaklik_c", "dis_bagil_nem"]
    + [f"tur_{t}" for t in TURLER]
    + ["onceki_sicaklik_ayar", "onceki_nem_ayar", "onceki_co2_ayar", "onceki_sok", "onceki_hasat"]
)
_OLCEK = {"co2_ppm": 1000.0, "sicaklik_c": 10.0, "bagil_nem": 100.0, "substrat_nemi": 100.0,
          "evre_gun": 10.0, "meyve_yas_gun": 10.0, "dongu_gunu": 200.0, "dis_sicaklik_c": 10.0,
          "dis_bagil_nem": 100.0}


def gozlemi_coz(gozlem) -> dict:
    """Normalize gözlem vektörünü adlandırılmış ve birimli değerlere çevirir."""
    return {k: float(v) * _OLCEK.get(k, 1.0) for k, v in zip(GOZLEM_ANAHTARLARI, gozlem)}


def tur_ayarini_denetle(ayarlar: dict, tur: str) -> list:
    """Tür için eksik (null) parametrelerin listesini döndürür."""
    eksikler = []
    ta = ayarlar["turler"].get(tur)
    for blok in ["inkubasyon", "kahverengilesme", "meyvelenme", "biyoloji"]:
        degerler = None if ta is None else ta.get(blok)
        if degerler is None:
            if blok != "kahverengilesme":          # kahverengileşme evresi isteğe bağlı
                eksikler.append(f"turler.{tur}.{blok}")
            continue
        for anahtar, deger in degerler.items():
            if deger is None and anahtar not in ISTEGE_BAGLI_ANAHTARLAR:
                eksikler.append(f"turler.{tur}.{blok}.{anahtar}")
    return eksikler


class MantarOrtami(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, ayarlar: dict, tur: str = "istiridye"):
        eksikler = tur_ayarini_denetle(ayarlar, tur)
        if eksikler:
            raise ValueError(f"'{tur}' için eksik parametreler (config.yaml):\n  " + "\n  ".join(eksikler))
        self.ayarlar = ayarlar
        self.tur = tur
        self.tur_ayarlari = ayarlar["turler"][tur]
        sim = ayarlar["simulasyon"]
        self.adim_saat = sim["adim_saat"]
        self.alt_adim_saat = sim["alt_adim_dakika"] / 60.0
        self.alt_adim_sayisi = int(round(self.adim_saat / self.alt_adim_saat))
        self.maks_adim = int(self.tur_ayarlari["biyoloji"]["maks_gun"] * 24 / self.adim_saat)
        self.alan = ayarlar["oda"]["alan_m2"]

        sinir = ayarlar["eylem_sinirlari"]
        self._t_aralik = sinir["sicaklik_c"]
        self._bn_aralik = sinir["bagil_nem"]
        self._co2_aralik = sinir["co2_ppm"]

        self.action_space = spaces.Dict({
            "ayar": spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32),
            "karar": spaces.MultiBinary(2),
        })
        self.observation_space = spaces.Box(-np.inf, np.inf, shape=(len(GOZLEM_ANAHTARLARI),), dtype=np.float32)

        self.iklim = OdaIklimi(ayarlar["oda"], ayarlar["pid"])
        self.substrat = Substrat(ayarlar["substrat"], self.tur_ayarlari["inkubasyon"], self.alan)
        self.biyoloji = Biyoloji(self.tur_ayarlari, self.substrat.kuru_kg, ayarlar["co2_buyume"],
                                 ayarlar["dis_hava"]["co2_ppm"])
        self.sayac = KaynakSayaci()

    # ------------------------------------------------------------------ yardımcılar
    @staticmethod
    def _olcekle(x: float, aralik) -> float:
        return float(aralik[0] + (np.clip(x, -1.0, 1.0) + 1.0) / 2.0 * (aralik[1] - aralik[0]))

    def ayar_noktalarina_cevir(self, ayar) -> tuple:
        """[-1, 1] aralığındaki eylemi fiziksel ayar noktalarına (°C, %, ppm) çevirir."""
        return (self._olcekle(ayar[0], self._t_aralik), self._olcekle(ayar[1], self._bn_aralik),
                self._olcekle(ayar[2], self._co2_aralik))

    def ayar_noktalarini_olcekle(self, sicaklik_c: float, bagil_nem: float, co2_ppm: float) -> np.ndarray:
        """Fiziksel ayar noktalarını [-1, 1] aralığına çevirir (karşılaştırma yöntemleri için)."""
        def ters(v, r):
            return 2.0 * (v - r[0]) / (r[1] - r[0]) - 1.0
        return np.clip(np.array([ters(sicaklik_c, self._t_aralik), ters(bagil_nem, self._bn_aralik),
                                 ters(co2_ppm, self._co2_aralik)], dtype=np.float32), -1.0, 1.0)

    def _dis_hava(self, saat: float) -> dict:
        d = self.ayarlar["dis_hava"]
        sicaklik = (d["sicaklik_ort_c"] + d["sicaklik_gunluk_genlik_c"] * np.sin(2 * np.pi * (saat % 24 - 9) / 24)
                    + self._hava_sapmasi)
        return {"sicaklik_c": float(sicaklik),
                "bagil_nem": float(np.clip(d["bagil_nem"] + self._nem_sapmasi, 5, 100)),
                "co2_ppm": d["co2_ppm"]}

    def _evre_hedefleri(self) -> dict:
        """Mevcut evrenin uygun aralıkları (ihlal hesabı için)."""
        if self.biyoloji.evre in (INKUBASYON, KAHVERENGILESME):
            ink = self.tur_ayarlari["inkubasyon"]
            return {"t": ink["sicaklik_opt"], "t_tol": ink["sicaklik_tolerans"], "bn": None, "co2": None}
        m = self.tur_ayarlari["meyvelenme"]
        return {"t": m["sicaklik_opt"], "t_tol": m["sicaklik_tolerans"], "bn": m["nem_opt"],
                "bn_tol": m["nem_tolerans"], "co2": m["co2_kalite_esigi_ppm"]}

    def _ihlal_var_mi(self) -> bool:
        d, h = self.iklim.durum, self._evre_hedefleri()
        if not (h["t"][0] - h["t_tol"] <= d.sicaklik_c <= h["t"][1] + h["t_tol"]):
            return True
        if h["bn"] is not None and not (h["bn"][0] - h["bn_tol"] <= d.bagil_nem):
            return True
        if h["co2"] is not None and d.co2_ppm > h["co2"]:
            return True
        return False

    def _deger_kg(self) -> float:
        return self.biyoloji.hasat_deger_kg + self.biyoloji.pazarlanabilir_kg()

    def _gozlem(self) -> np.ndarray:
        d, b = self.iklim.durum, self.biyoloji
        dis = self._dis_hava(self.saat)
        evre = [1.0 if b.evre == i else 0.0 for i in range(len(EVRE_ADLARI))]
        kap = b.kapasite if b.kapasite > 0 else 1.0
        degerler = ([d.sicaklik_c, d.bagil_nem, d.co2_ppm, self.substrat.nem,
                     self.substrat.gozlenen_kolonizasyon(self.np_random), b.kahverengilesme]
                    + evre
                    + [b.dalga / b.dalga_sayisi, b.evre_saat / 24.0, b.yas_gun, b.biyokutle / kap, b.kalite(),
                       self.saat / 24.0, dis["sicaklik_c"], dis["bagil_nem"]]
                    + [1.0 if self.tur == t else 0.0 for t in TURLER]
                    + list(self._onceki_eylem))
        return np.array([v / _OLCEK.get(k, 1.0) for k, v in zip(GOZLEM_ANAHTARLARI, degerler)], dtype=np.float32)

    # ------------------------------------------------------------------ Gymnasium arayüzü
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        d = self.ayarlar["dis_hava"]
        self._hava_sapmasi = 0.0
        self._nem_sapmasi = 0.0
        self.saat = 0.0
        self.adim_sayisi = 0
        self._onceki_eylem = np.zeros(5, dtype=np.float32)
        self.iklim.sifirla(sicaklik_c=d["sicaklik_ort_c"], bagil_nem=d["bagil_nem"], co2_ppm=d["co2_ppm"])
        self.substrat.sifirla(self.np_random)
        rst = self.ayarlar["rastgelelik"]
        self.biyoloji.sifirla(self.np_random, rst["sus_kaymasi"], rst["verimlilik_araligi"])
        self.sayac = KaynakSayaci()
        self.kontaminasyon_sayisi = 0
        self.ihlal_adimi = 0
        gozlem = self._gozlem()
        return gozlem, {"gozlem": gozlemi_coz(gozlem)}

    def step(self, action):
        ayar = np.asarray(action["ayar"], dtype=np.float32)
        karar = np.asarray(action["karar"]).astype(int)
        t_ayar, bn_ayar, co2_ayar = self.ayar_noktalarina_cevir(ayar)
        ach_toplam = 0.0
        eko, od = self.ayarlar["ekonomi"], self.ayarlar["odul"]
        deger_once = self._deger_kg()
        enerji_once, su_once = self.sayac.enerji_kwh, self.sayac.su_l

        # --- kararlar adımın başında uygulanır
        erken_sok = False
        if karar[0] == 1:
            erken_sok = not self.biyoloji.sok(self.substrat.kolonizasyon)
        if karar[1] == 1:
            self.biyoloji.hasat()

        # --- dış hava: günlük yavaş değişen sapma
        d = self.ayarlar["dis_hava"]
        self._hava_sapmasi = 0.9 * self._hava_sapmasi + self.np_random.normal(0, d["sicaklik_gurultu_std_c"]) * 0.3
        self._nem_sapmasi = 0.9 * self._nem_sapmasi + self.np_random.normal(0, d["bagil_nem_gurultu_std"]) * 0.3

        # --- alt katman: iç adımlar
        for _ in range(self.alt_adim_sayisi):
            dis = self._dis_hava(self.saat)
            inkubasyonda = self.biyoloji.evre == INKUBASYON
            torbada = self.biyoloji.evre in (INKUBASYON, KAHVERENGILESME)
            buhar = self.substrat.buharlasma_kg_saat(self.iklim.durum.bagil_nem, self.alan, torbada)
            tuketim = self.iklim.alt_adim(self.alt_adim_saat, t_ayar, bn_ayar, co2_ayar, dis,
                                          self.substrat.isi_w(), self.substrat.co2_l_saat(), buhar)
            self.sayac.ekle(tuketim)
            ach_toplam += tuketim["ach"]
            s = self.iklim.durum
            self.substrat.alt_adim(self.alt_adim_saat, s.sicaklik_c, s.co2_ppm, buhar, inkubasyonda)
            self.biyoloji.alt_adim(self.alt_adim_saat, s.sicaklik_c, s.bagil_nem, s.co2_ppm,
                                   self.substrat.nem_carpani(), self.substrat.kolonizasyon)
            self.saat += self.alt_adim_saat

        # --- kontaminasyon riski (günlük tehlike oranı → adım olasılığı)
        r, s = self.ayarlar["risk"], self.iklim.durum
        tehlike = (r["temel_gunluk"]
                   + r["yuksek_nem_katsayi"] * max(0.0, s.bagil_nem - r["yuksek_nem_esigi"])
                   + r["yuksek_sicaklik_katsayi"] * max(0.0, s.sicaklik_c - r["yuksek_sicaklik_esigi"]))
        kontamine = self.np_random.random() < 1.0 - np.exp(-tehlike * self.adim_saat / 24.0)
        if kontamine and self.biyoloji.evre != BITTI:
            self.kontaminasyon_sayisi += 1
            self.biyoloji.kapasite_kaybet(r["kayip_orani"])

        ihlal = self._ihlal_var_mi()
        self.ihlal_adimi += int(ihlal)
        self.adim_sayisi += 1

        terminated = self.biyoloji.evre == BITTI                      # Gymnasium: doğal bitiş
        truncated = (not terminated) and self.adim_sayisi >= self.maks_adim   # Gymnasium: süre sınırı

        # --- ödül (TL / olcek)
        deger_sonra = self._deger_kg()
        if terminated or truncated:
            deger_sonra = self.biyoloji.hasat_deger_kg              # hasat edilmeyen ürün kaybedilir
        enerji = self.sayac.enerji_kwh - enerji_once
        su = self.sayac.su_l - su_once
        odul_tl = ((deger_sonra - deger_once) * eko["mantar_tl_kg"]
                   - enerji * eko["elektrik_tl_kwh"] - su * eko["su_tl_litre"])
        odul = (odul_tl / od["olcek_tl"] - od["ihlal_ceza"] * int(ihlal)
                - od["erken_sok_ceza"] * int(erken_sok))

        self._onceki_eylem = np.array([ayar[0], ayar[1], ayar[2], karar[0], karar[1]], dtype=np.float32)
        gozlem = self._gozlem()
        bilgi = {
            "gozlem": gozlemi_coz(gozlem),
            "evre": EVRE_ADLARI[self.biyoloji.evre],
            "enerji_kwh": enerji, "su_l": su, "ihlal": bool(ihlal),
            "erken_sok": erken_sok, "kontaminasyon": bool(kontamine),
            "ayar_noktalari": {"sicaklik_c": t_ayar, "bagil_nem": bn_ayar, "co2_ppm": co2_ayar},
            "ortalama_ach": ach_toplam / self.alt_adim_sayisi,
            "odul_tl": odul_tl,
        }
        if terminated or truncated:
            bilgi["ozet"] = self.ozet()
        return gozlem, float(odul), terminated, truncated, bilgi

    def ozet(self) -> dict:
        b, m = self.biyoloji, self.sayac
        kg = b.hasat_kg
        return {
            "tur": self.tur,
            "gun": self.saat / 24.0,
            "hasat_kg": kg,
            "kg_m2": kg / self.alan,
            "biyolojik_verimlilik": kg / self.substrat.kuru_kg,
            "ortalama_kalite": (b.hasat_deger_kg / kg) if kg > 0 else 0.0,
            "curuyen_kg": b.curuyen_kg,
            "tamamlanan_dalga": b.dalga,
            "enerji_kwh": m.enerji_kwh,
            "kwh_kg": (m.enerji_kwh / kg) if kg > 0 else float("inf"),
            "su_l": m.su_l,
            "ihlal_orani": self.ihlal_adimi / max(1, self.adim_sayisi),
            "kontaminasyon": self.kontaminasyon_sayisi,
            "sus_sicaklik_kaymasi_c": b.sicaklik_kaymasi,      # ajan görmez; analiz için
            "potansiyel_bv": b.bv,
        }
