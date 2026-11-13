"""K5 · Streamlit arayüzü: bir üretim döngüsünü izleme ve yöntemleri karşılaştırma.

Çalıştırma (proje kök klasöründen):  streamlit run arayuz/uygulama.py
Tarayıcıda http://localhost:8501 açılır.

Sekmeler:
  Döngüyü izle          tek bir yöntemle bir döngü: iklim, evre, kararlar, biyokütle, zaman kaydırıcısı
  Yöntemleri karşılaştır aynı senaryoda (aynı tohum) seçilen yöntemler yan yana
  Test sonuçları        degerlendir.py'nin ürettiği 5 test tohumluk özet tablo
  Model hakkında        türün parametreleri, kaynakları ve varsayımlar
"""

import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
import streamlit.components.v1 as bilesenler  # noqa: E402
import yaml  # noqa: E402

from mantar_ortami.ortam import TURLER, MantarOrtami  # noqa: E402
from raporlama.bolum_kaydi import bolum_kaydi  # noqa: E402
from rakipler.kural_tabanli import KuralTabanli  # noqa: E402
from rakipler.sabit_recete import SabitRecete  # noqa: E402

TUR_ADLARI = {"istiridye": "İstiridye (Pleurotus ostreatus)",
              "shiitake": "Shiitake (Lentinula edodes)",
              "aslan_yelesi": "Aslan yelesi (Hericium erinaceus)"}
YONTEM_ADLARI = {"sabit_recete": "Sabit reçete + PID", "kural_tabanli": "Kural tabanlı",
                 "ayarlanmis_kural": "Ayarlanmış kural", "ppo": "PPO ajanı"}
YONTEM_RENK = {"sabit_recete": "#1F77B4", "kural_tabanli": "#FF7F0E",
               "ayarlanmis_kural": "#2CA02C", "ppo": "#D62728"}
EVRE_ADLARI_TR = {"inkubasyon": "İnkübasyon", "kahverengilesme": "Kahverengileşme", "pin": "Taslak (pin)",
                  "buyume": "Büyüme", "dinlenme": "Dinlenme", "bitti": "Bitti"}
EVRE_RENK = {"inkubasyon": "#EADBC4", "kahverengilesme": "#D3B08C", "pin": "#D7E8CF",
             "buyume": "#A9D2A5", "dinlenme": "#E6E6E6", "bitti": "#FFFFFF"}

st.set_page_config(page_title="Mantar odası · DRL", page_icon="🍄", layout="wide")

# Streamlit sayfayı İngilizce (lang="en") işaretliyor; Chrome bu yüzden sayfayı "çevirmeyi" öneriyor.
# Çeviri, React'in güncellediği yazıları dondurur (göstergeler eski değerde kalır). Sayfayı Türkçe ve
# "çevrilmez" olarak işaretliyoruz.
bilesenler.html("""<script>
const d = window.parent.document;
d.documentElement.lang = "tr";
d.documentElement.setAttribute("translate", "no");
d.documentElement.classList.add("notranslate");
if (!d.querySelector('meta[name="google"]')) {
  const m = d.createElement("meta"); m.name = "google"; m.content = "notranslate"; d.head.appendChild(m);
}
</script>""", height=0)


# ---------------------------------------------------------------- veri ve simülasyon
@st.cache_data
def ayarlari_oku() -> dict:
    with open(KOK / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ppo_modelleri(tur: str) -> list[Path]:
    return sorted((KOK / "runs" / "ppo" / tur).glob("*/model.zip"))


def kullanilabilir_yontemler(tur: str) -> list[str]:
    y = ["sabit_recete", "kural_tabanli"]
    if (KOK / "rakipler" / "ayarlanmis_parametreler.yaml").exists():
        y.append("ayarlanmis_kural")
    if ppo_modelleri(tur):
        y.append("ppo")
    return y


def politika_kur(yontem: str, ortam, tur: str):
    if yontem == "sabit_recete":
        return SabitRecete(ortam)
    if yontem == "kural_tabanli":
        return KuralTabanli(ortam)
    if yontem == "ayarlanmis_kural":
        from rakipler.ayarlanmis_kural import parametreleri_oku
        p = parametreleri_oku()[tur]
        return KuralTabanli(ortam, {k: v for k, v in p.items() if k != "dogrulama_odulu"})
    from ajanlar.ppo_ajani import PPOAjani
    return PPOAjani(ppo_modelleri(tur)[0])


@st.cache_data(show_spinner="Simülasyon çalışıyor…")
def simule(tur: str, yontem: str, tohum: int) -> tuple[pd.DataFrame, dict]:
    ortam = MantarOrtami(ayarlari_oku(), tur=tur)
    return bolum_kaydi(ortam, politika_kur(yontem, ortam, tur), tohum)


def evre_araliklari(df: pd.DataFrame) -> list[tuple[str, float, float]]:
    """Ardışık aynı evredeki adımları (evre, başlangıç günü, bitiş günü) aralıklarına çevirir."""
    araliklar, bas, onceki = [], 0.0, df["evre"].iloc[0]
    onceki_gun = 0.0
    for gun, evre in zip(df["gun"], df["evre"]):
        if evre != onceki:
            araliklar.append((onceki, bas, onceki_gun))
            bas, onceki = onceki_gun, evre
        onceki_gun = gun
    araliklar.append((onceki, bas, df["gun"].iloc[-1]))
    return araliklar


# ---------------------------------------------------------------- grafikler
def dongu_grafigi(df: pd.DataFrame, tur_ayar: dict, imlec_gun: float | None = None):
    """2 × 2 panel: sıcaklık, bağıl nem, CO2, gelişim (kolonizasyon, biyokütle, şok, hasat)."""
    fig, eksen = plt.subplots(2, 2, figsize=(14, 4.4), sharex=True)
    ax = [eksen[0, 0], eksen[0, 1], eksen[1, 0], eksen[1, 1]]
    for a in ax:
        for evre, bas, bit in evre_araliklari(df):
            a.axvspan(bas, bit, color=EVRE_RENK[evre], alpha=0.55, lw=0)
        if imlec_gun is not None:
            a.axvline(imlec_gun, color="#333", lw=1.2, ls="--")
        a.grid(alpha=0.25)
        a.tick_params(labelsize=8)

    ink, mey = tur_ayar["inkubasyon"], tur_ayar["meyvelenme"]
    ax[0].plot(df["gun"], df["dis_sicaklik_c"], color="#999", lw=0.7, label="dış hava")
    ax[0].plot(df["gun"], df["sicaklik_ayar"], color="#E8A86B", lw=1.2, ls=":", label="ayar noktası")
    ax[0].plot(df["gun"], df["sicaklik_c"], color="#A85A22", lw=1.6, label="oda")
    ax[0].axhspan(*ink["sicaklik_opt"], color="#A85A22", alpha=0.06)
    ax[0].axhspan(*mey["sicaklik_opt"], color="#2C7A3F", alpha=0.08)
    ax[0].set_title("Sıcaklık (°C)", fontsize=10, loc="left"); ax[0].legend(loc="upper right", fontsize=7, ncol=3)

    ax[1].plot(df["gun"], df["nem_ayar"], color="#7FB3D5", lw=1.2, ls=":", label="ayar noktası")
    ax[1].plot(df["gun"], df["bagil_nem"], color="#1F5F8B", lw=1.6, label="oda")
    ax[1].axhspan(*mey["nem_opt"], color="#1F5F8B", alpha=0.08)
    ax[1].set_title("Bağıl nem (%)", fontsize=10, loc="left"); ax[1].legend(loc="lower right", fontsize=7)

    ax[2].plot(df["gun"], df["co2_ayar"], color="#BBB", lw=1.2, ls=":", label="ayar noktası")
    ax[2].plot(df["gun"], df["co2_ppm"], color="#555", lw=1.6, label="oda")
    ax[2].axhline(mey["co2_iyi_maks_ppm"], color="#C0392B", lw=0.8, ls="--", label="meyvelenme sınırı")
    ax[2].set_title("CO₂ (ppm)", fontsize=10, loc="left"); ax[2].legend(loc="upper right", fontsize=7, ncol=3)
    ax[2].set_xlabel("Gün", fontsize=9)

    ax[3].plot(df["gun"], df["kolonizasyon"], color="#8E6C3A", lw=1.4, label="kolonizasyon")
    if tur_ayar.get("kahverengilesme"):
        ax[3].plot(df["gun"], df["kahverengilesme"], color="#5B3A1E", lw=1.4, label="kahverengileşme")
    kap = df["kapasite_kg"].where(df["kapasite_kg"] > 0)
    ax[3].plot(df["gun"], (df["biyokutle_kg"] / kap).fillna(0), color="#2C7A3F", lw=1.6,
               label="mantar büyüklüğü")
    soklar = df[df["sok"] == 1]
    hasatlar = df[df["hasat_kg"] > 0]
    ax[3].scatter(soklar["gun"], [1.07] * len(soklar), marker="v", color="#1F5F8B", s=36, label="şok", zorder=3)
    ax[3].scatter(hasatlar["gun"], [1.07] * len(hasatlar), marker="*", color="#C0392B", s=100, label="hasat", zorder=3)
    ax[3].set_ylim(0, 1.17)
    ax[3].set_title("Gelişim (0–1 oran)", fontsize=10, loc="left"); ax[3].set_xlabel("Gün", fontsize=9)
    ax[3].legend(loc="center left", fontsize=7, ncol=2)
    fig.tight_layout()
    return fig


def karsilastirma_grafigi(kayitlar: dict):
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    for y, (df, _) in kayitlar.items():
        r = YONTEM_RENK[y]
        ax[0].plot(df["gun"], df["sicaklik_c"], color=r, lw=1.1, label=YONTEM_ADLARI[y])
        ax[1].plot(df["gun"], df["toplam_hasat_kg"], color=r, lw=1.6, label=YONTEM_ADLARI[y])
        ax[2].plot(df["gun"], df["kazanc_tl"], color=r, lw=1.6, label=YONTEM_ADLARI[y])
    for a, baslik in zip(ax, ["Oda sıcaklığı (°C)", "Birikimli hasat (kg)", "Birikimli net kazanç (TL)"]):
        a.set_title(baslik, fontsize=11); a.set_xlabel("Gün"); a.grid(alpha=0.25)
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    return fig


def ozet_satiri(yontem: str, z: dict) -> dict:
    kg = z["hasat_kg"]
    return {"Yöntem": YONTEM_ADLARI[yontem], "Net kazanç (TL)": round(z["net_kazanc_tl"]),
            "Hasat (kg)": round(kg, 1), "Kalite": round(z["ortalama_kalite"], 2),
            "kWh/kg": round(z["kwh_kg"], 2) if kg > 0 else None,
            "Su (L)": round(z["su_l"], 1), "İhlal oranı": round(z["ihlal_orani"], 3),
            "Dalga": z["tamamlanan_dalga"], "Döngü (gün)": round(z["gun"], 1),
            "Çürüyen (kg)": round(z["curuyen_kg"], 1)}


# ---------------------------------------------------------------- yan çubuk
ayarlar = ayarlari_oku()
with st.sidebar:
    st.header("Senaryo")
    tur = st.selectbox("Mantar türü", TURLER, format_func=TUR_ADLARI.get)
    tohum = st.number_input("Senaryo (test tohumu)", min_value=0, max_value=9999, value=0, step=1,
                            help="Aynı tohum aynı dış havayı, suş farkını ve verim potansiyelini üretir. "
                                 "Test tohumları: 0–4 (seeds.txt).")
    mevcut = kullanilabilir_yontemler(tur)
    secili = st.multiselect("Yöntemler", mevcut, default=mevcut, format_func=YONTEM_ADLARI.get)
    if "ppo" not in mevcut:
        st.caption(f"PPO modeli yok. Eğitmek için: `python egit.py --tur {tur} --tohum 0`")
    st.divider()
    st.caption("Karar adımı 4 saat; ayar noktalarını alt katmanda PI denetleyiciler 15 dakikada bir izler. "
               "Ajan suş farkını görmez.")

st.markdown("""<style>
.block-container {padding-top: 1.6rem; padding-bottom: 1rem;}
div[data-testid="stMetricValue"] {font-size: 1.7rem;}
</style>""", unsafe_allow_html=True)
st.markdown("## 🍄 Kapalı mantar odası: iklim reçetesi ve hasat zamanlaması")
st.caption("Burak Kılcı · BLM403 Araştırma Problemleri · Danışman: Doç. Dr. Alpaslan Burak İNNER · "
           "simülasyon (dijital ikiz) üzerinde DRL ve rakip yöntemler")

if not secili:
    st.info("Soldan en az bir yöntem seçin.")
    st.stop()

sekme_izle, sekme_kars, sekme_test, sekme_model = st.tabs(
    ["Döngüyü izle", "Yöntemleri karşılaştır", "Test sonuçları", "Model hakkında"])

# ---------------------------------------------------------------- 1) döngüyü izle
with sekme_izle:
    ust = st.columns([2.2, 4, 1])
    with ust[0]:
        yontem = st.selectbox("Yöntem", secili, format_func=YONTEM_ADLARI.get)
    df, z = simule(tur, yontem, int(tohum))
    tur_ayar = ayarlar["turler"][tur]

    son_gun = float(df["gun"].iloc[-1])
    with ust[1]:
        gun = st.slider("Zaman (gün)", 0.0, son_gun, son_gun, step=1 / 6, format="%.1f")
    with ust[2]:
        st.write("")
        oynat = st.button("▶ Oynat", use_container_width=True)

    def anlik_gostergeler(yer, satir):
        with yer.container():
            k = st.columns(6)
            k[0].metric(f"Gün {satir['gun']:.1f} · evre", EVRE_ADLARI_TR[satir["evre"]])
            k[1].metric(f"Sıcaklık · ayar {satir['sicaklik_ayar']:.1f}", f"{satir['sicaklik_c']:.1f} °C")
            k[2].metric(f"Bağıl nem · ayar {satir['nem_ayar']:.0f}", f"%{satir['bagil_nem']:.0f}")
            k[3].metric(f"CO₂ · ayar {satir['co2_ayar']:.0f}", f"{satir['co2_ppm']:.0f} ppm")
            k[4].metric(f"Toplam hasat · dalga {int(satir['dalga'])}", f"{satir['toplam_hasat_kg']:.0f} kg")
            k[5].metric("Net kazanç", f"{satir['kazanc_tl']:,.0f} TL".replace(",", "."))
            st.caption(f"Kolonizasyon %{100 * satir['kolonizasyon']:.0f} (gözlenen %{100 * satir['kolonizasyon_gozlenen']:.0f})"
                       f" · Odadaki mantar {satir['biyokutle_kg']:.1f} kg · Enerji {satir['enerji_kwh']:.0f} kWh"
                       f" · Su {satir['su_l']:.0f} L")

    gosterge_yeri, grafik_yeri = st.empty(), st.empty()
    if oynat:
        adim = max(1, len(df) // 60)
        for i in list(range(0, len(df), adim)) + [len(df) - 1]:
            anlik_gostergeler(gosterge_yeri, df.iloc[i])
            fig = dongu_grafigi(df, tur_ayar, float(df["gun"].iloc[i]))
            grafik_yeri.pyplot(fig); plt.close(fig)
            time.sleep(0.05)
    else:
        i = int((df["gun"] - gun).abs().idxmin())
        anlik_gostergeler(gosterge_yeri, df.iloc[i])
        fig = dongu_grafigi(df, tur_ayar, gun)
        grafik_yeri.pyplot(fig); plt.close(fig)

    with st.expander("Bu ekran ne gösteriyor?"):
        st.markdown(
            "Bu, 100 m²'lik sanal bir mantar odası. Seçilen yöntem **4 saatte bir** odanın hedef sıcaklığını, "
            "nemini ve CO₂'sini belirler; ayrıca mantarları meyveye geçirmek için **şok** verip vermeyeceğine ve "
            "**hasat** edip etmeyeceğine karar verir. Isıtıcı, nemlendirici ve fan bu hedefleri izler; simülasyon "
            "odanın ve mantarın bundan nasıl etkilendiğini hesaplar.\n\n"
            "- **Sıcaklık / Bağıl nem / CO₂:** düz çizgi odanın gerçek değeri, noktalı çizgi yöntemin istediği "
            "değer (ayar noktası), gri çizgi dış hava. Açık renkli yatay bantlar literatürdeki uygun aralık.\n"
            "- **Gelişim:** kahverengi çizgi miselin bloğu ne kadar sardığı (kolonizasyon), yeşil çizgi o dalgadaki "
            "mantarların ne kadar büyüdüğü. ▼ şok kararı, ★ hasat.\n"
            "- **Arka plan rengi** evreyi gösterir: bej inkübasyon, açık yeşil taslak (pin), yeşil büyüme, gri "
            "dinlenme. Bir döngüde bu sıra her dalga için tekrarlanır.\n"
            "- **Zaman** kaydırıcısı ya da **▶ Oynat** ile döngüyü gün gün izleyebilirsiniz; üstteki göstergeler "
            "seçilen andaki değerlerdir.")

    st.caption("Arka plan renkleri evreyi gösterir: "
               + " · ".join(f"{EVRE_ADLARI_TR[e]}" for e in EVRE_RENK if e in set(df["evre"]))
               + ". Kahverengi/yeşil yatay bantlar türün inkübasyon/meyvelenme aralıkları (literatür).")

    olaylar = []
    for _, r in df[df["sok"] == 1].iterrows():
        olaylar.append({"Gün": round(r["gun"], 1), "Olay": "Şok (meyvelenmeyi tetikle)", "Ayrıntı": ""})
    for _, r in df[df["hasat_kg"] > 0].iterrows():
        olaylar.append({"Gün": round(r["gun"], 1), "Olay": f"Hasat · dalga {int(r['dalga'])}",
                        "Ayrıntı": f"{r['hasat_kg']:.1f} kg"})
    for _, r in df[df["kontaminasyon"]].iterrows():
        olaylar.append({"Gün": round(r["gun"], 1), "Olay": "Kontaminasyon", "Ayrıntı": "kalan kapasitenin %30'u kayıp"})
    with st.expander(f"Olaylar ({len(olaylar)})", expanded=False):
        st.dataframe(pd.DataFrame(olaylar).sort_values("Gün"), hide_index=True, use_container_width=True)
    with st.expander("Döngü özeti"):
        st.dataframe(pd.DataFrame([ozet_satiri(yontem, z)]), hide_index=True, use_container_width=True)
    st.download_button("Adım tablosunu indir (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"dongu_{tur}_{yontem}_{tohum}.csv", mime="text/csv")

# ---------------------------------------------------------------- 2) karşılaştırma
with sekme_kars:
    st.subheader(f"{TUR_ADLARI[tur]} · senaryo {tohum}")
    st.caption("Bütün yöntemler aynı senaryoyla karşılaşır: aynı dış hava, aynı suş farkı, aynı verim potansiyeli.")
    kayitlar = {y: simule(tur, y, int(tohum)) for y in secili}
    tablo = pd.DataFrame([ozet_satiri(y, z) for y, (_, z) in kayitlar.items()])
    st.dataframe(tablo, hide_index=True, use_container_width=True)
    referans = "sabit_recete" if "sabit_recete" in kayitlar else None
    if referans and len(kayitlar) > 1:
        ref = kayitlar[referans][1]["net_kazanc_tl"]
        k = st.columns(len(kayitlar) - 1)
        for kol, (y, (_, zz)) in zip(k, [(y, v) for y, v in kayitlar.items() if y != referans]):
            kol.metric(YONTEM_ADLARI[y], f"{zz['net_kazanc_tl']:,.0f} TL".replace(",", "."),
                       f"{100 * (zz['net_kazanc_tl'] - ref) / abs(ref):+.1f}% sabit reçeteye göre")
    fig = karsilastirma_grafigi(kayitlar)
    st.pyplot(fig); plt.close(fig)
    st.caption("Birikimli net kazanç, ödülün toplamıdır: hasat edilen değer + henüz hasat edilmemiş pazarlanabilir "
               "ürün − enerji ve su maliyeti. Bu yüzden ürün büyürken yükselir; hasat edilmeyen ürün bölüm sonunda düşülür.")

# ---------------------------------------------------------------- 3) test sonuçları
with sekme_test:
    yeni = KOK / "runs" / "degerlendirme"
    kayitli = KOK / "belgeler" / "hafta07"
    klasor = yeni if (yeni / "ozet.csv").exists() else kayitli
    if (klasor / "ozet.csv").exists():
        st.caption(f"Kaynak: `{klasor.relative_to(KOK)}` · 5 test tohumu (seeds.txt), ortalama ± std. "
                   "Yenilemek için: `python degerlendir.py`")
        o = pd.read_csv(klasor / "ozet.csv")
        o = o[o["tur"] == tur]
        goster = pd.DataFrame({
            "Yöntem": o["yontem"].map(YONTEM_ADLARI),
            "Net kazanç (TL)": [f"{a:,.0f} ± {b:,.0f}".replace(",", ".") for a, b in zip(o["net_kazanc_tl_ort"], o["net_kazanc_tl_std"].fillna(0))],
            "Hasat (kg)": [f"{a:.0f} ± {b:.0f}" for a, b in zip(o["hasat_kg_ort"], o["hasat_kg_std"].fillna(0))],
            "Kalite": o["ortalama_kalite_ort"].round(2),
            "kWh/kg": o["kwh_kg_ort"].round(2),
            "Döngü (gün)": o["gun_ort"].round(1),
            "n": o["bolum"],
        })
        st.dataframe(goster, hide_index=True, use_container_width=True)
        if (klasor / "karsilastirma.png").exists():
            st.image(str(klasor / "karsilastirma.png"), caption="Üç tür, bütün yöntemler")
    else:
        st.info("Henüz değerlendirme yok. Çalıştırmak için: `python degerlendir.py`")

# ---------------------------------------------------------------- 4) model hakkında
with sekme_model:
    ta = ayarlar["turler"][tur]
    st.markdown(
        "**Ortam.** Oda tek bir karışık hacimdir (100 m², 3 m). Isı, su buharı ve CO₂ dengeleri 15 dakikalık "
        "iç adımlarla çözülür. Ajan 4 saatte bir sıcaklık, nem ve CO₂ ayar noktası verir; ısıtıcı/soğutucu, "
        "nemlendirici ve taze hava fanı bu noktaları PI denetleyicilerle izler. Ayrıca iki ayrık karar verir: "
        "meyvelenmeyi tetikleyen **şok** ve **hasat**.\n\n"
        "**Ödül.** Hasat edilen ürünün kaliteyle ağırlıklı değeri − enerji ve su maliyeti − iklim ihlali cezası "
        "− erken şok cezası. Hasat edilmeyen ürün bölüm sonunda kaybedilir.\n\n"
        "**Belirsizlik.** Her bölümde meyvelenme sıcaklık aralığı ±3 °C kaydırılır (suş farkı) ve biyolojik "
        "verimlilik literatür aralığından örneklenir. Ajan bunları görmez; kolonizasyonu da gürültülü gözler.")
    satirlar = []
    for blok in ["inkubasyon", "kahverengilesme", "meyvelenme", "biyoloji"]:
        for k, v in (ta.get(blok) or {}).items():
            if k not in ("kaynak", "tur"):
                satirlar.append({"Blok": blok, "Parametre": k, "Değer": str(v)})
    st.dataframe(pd.DataFrame(satirlar), hide_index=True, use_container_width=True, height=420)
    kaynaklar = [f"- **{b}**: {ta[b]['kaynak']}" for b in ["inkubasyon", "kahverengilesme", "meyvelenme"]
                 if ta.get(b) and ta[b].get("kaynak")]
    st.markdown("**Kaynaklar** (ayrıntı: belgeler/parametre_kaynaklari.md)\n" + "\n".join(kaynaklar))