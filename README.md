# mantar-drl

**Kapalı Ortam Mantar Üretiminde Derin Pekiştirmeli Öğrenme ile Türe Duyarlı İklim Reçetesi ve Hasat Zamanlaması Optimizasyonu**

Burak Kılcı (230202111) · Danışman: Doç. Dr. Alpaslan Burak İNNER
Kocaeli Üniversitesi, Bilgisayar Mühendisliği · BLM403 Araştırma Problemleri / BLM402 Bitirme Çalışması · 2026–2027

## Proje özeti

Kapalı bir mantar yetiştirme odasının simülasyonunda (dijital ikiz), tür kimliğiyle koşullanmış tek bir PPO politikası;
oda ikliminin ayar noktalarını (sıcaklık, nem, CO₂, taze hava) ve meyvelenmeyi tetikleme ile hasat kararlarını
istiridye, shiitake ve aslan yelesi mantarları için verim, kalite ve enerji maliyetini birlikte gözeterek belirler.
Ajan; sabit reçete + PID, kural tabanlı kontrolcü ve eşikleri validation senaryolarında ayarlanmış kural ile karşılaştırılır.

## Klasör yapısı

```
mantar-drl/
├── 04_Kurulum/        Kurulum adımları (README.md) ve sürümleri sabitlenmiş requirements.txt
├── mantar_ortami/     K1 · Simülasyon ortamı (Gymnasium): oda iklimi, substrat, biyoloji, kaynak alt modelleri
├── ajanlar/           K2 · PPO (ve hedeflenen SAC) ajanı
├── rakipler/          K3 · Sabit reçete + PID, kural tabanlı ve ayarlanmış kural kontrolcüleri
├── raporlama/         K4 · Kayıtlardan grafik ve özet tablo üreten betikler
├── arayuz/            K5 · Streamlit arayüzü
├── veri/              Gerçek veri setlerini okuyan ve temizleyen modüller (Duman 2024)
├── betikler/          Tek seferlik çalıştırılan betikler (veri temizleme, EDA, demo)
├── belgeler/          Literatür özeti, yöntem dokümanı ve raporlar
├── config.yaml        Tüm parametreler ve kaynakları (kodda sabit değer bulunmaz)
├── seeds.txt          Deneylerde kullanılan rastgele tohumlar
├── egit.py            Eğitim betiği
└── degerlendir.py     Değerlendirme betiği
```

Kodda sınıf, fonksiyon ve değişken adları Türkçedir (ASCII harflerle: ı→i, ş→s, ğ→g, ü→u, ö→o, ç→c).
Gymnasium arayüzünün parçası olan `reset`, `step`, `action_space`, `observation_space`, `metadata`,
`np_random`, `terminated`, `truncated` adları kütüphane tarafından çağrıldığı için İngilizce kalır.

Eğitim ve değerlendirme kayıtları `runs/` klasörüne yazılır; bu klasör depoya eklenmez.

## Kurulum ve çalıştırma

Ayrıntılı adımlar için: [04_Kurulum/README.md](04_Kurulum/README.md)

## Durum

- [~] K1 · Simülasyon ortamı (sürüm 0.2: üç tür; parametre kaynakları belgeler/parametre_kaynaklari.md)
- [ ] K2 · Eğitim ve değerlendirme hattı
- [~] K3 · Karşılaştırma modülü (sabit reçete hazır)
- [ ] K4 · Raporlama modülü
- [ ] K5 · Etkileşimli arayüz
