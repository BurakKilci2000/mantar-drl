# Parametre kaynakları

config.yaml'daki tür parametrelerinin kaynakları. Taramalar Scopus'ta 16–17.10.2026 tarihlerinde yapılmıştır.
Her değerin yanında config.yaml'da kaynak kodu ve sayfa numarası bulunur.

| Kod | Künye | Kullanıldığı yer |
|---|---|---|
| [12] | C. Sánchez, "Cultivation of Pleurotus ostreatus and other edible mushrooms," *Appl. Microbiol. Biotechnol.*, c. 85, ss. 1321–1337, 2010, doi:10.1007/s00253-009-2343-7 | İstiridye inkübasyonu (25 °C, 12–14 gün), meyvelenme nemi |
| [13] | Y. Zhang vd., "Cauliflower-shaped Pleurotus ostreatus cultivated in an atmosphere with high environmental carbon dioxide concentration," *Mycologia*, c. 115, no. 1, ss. 153–163, 2023, doi:10.1080/00275514.2022.2149013 | CO2 ≥ %1'de şekil bozulması; CO2'nin büyümeye kademeli etkisi; suş farkı (20–25 °C'de meyvelenme) |
| [14] | K.-Y. Jang vd., "Characterization of Fruitbody Morphology on Various Environmental Conditions in Pleurotus ostreatus," *Mycobiology*, c. 31, no. 3, ss. 145–150, 2003, doi:10.4489/MYCO.2003.31.3.145 | İstiridye meyvelenme sıcaklığı (13–16 °C), nemi (≥ %80), CO2 eşikleri (%0,3 / %0,5) |
| [S1] | Y. Sakamoto, "Influences of environmental factors on fruiting body induction, development and maturation in mushroom-forming fungi," *Fungal Biology Reviews*, c. 32, ss. 236–248, 2018 | Şok mekanizması, türler arası CO2 duyarlılığı, ışık varsayımı, aşırı olgunlaşmada kalite kaybı |
| [S2] | J.-H. Kim vd., "Characteristics of Newly Bred Lentinula edodes Cultivar 'Hwadam' for Sawdust Cultivation," *Korean J. Mycol.*, c. 48, no. 2, ss. 125–133, 2020, doi:10.4489/KJM.20200014 | Shiitake reçetesi: inkübasyon 20 °C / ≤ 5000 ppm, kahverengileşme 84 gün, meyvelenme 13–16 °C / ≤ 1000 ppm, dalga verimleri |
| [S3] | B. de S. Rocha vd., "Impact of Substrate Amount and Fruiting Induction Methods in Lentinula edodes Cultivation," *Horticulturae*, c. 11, 915, 2025 | Shiitake meyvelenme odası 19 ± 4 °C, %85 ± 15 nem, 850 ± 500 ppm; 20 günlük dalgalar; su şoku |
| [S4] | R. Ángeles-Argáiz vd., "Warm-tolerant shiitake cultivation on alternative subtropical substrates," *J. Appl. Microbiol.*, c. 136, no. 12, lxaf298, 2025, doi:10.1093/jambio/lxaf298 (yalnızca ek dosya okundu) | Shiitake BV aralığı (meşede %65–107); suş × sıcaklık etkileşimi |
| [H1] | F. Atila, Y. Tüzel, A. Pekşen, A. Faz Cano, J. A. Fernández, "The effect of different fruiting temperatures on the yield and nutritional parameters of some wild and hybrid Hericium isolates," *Scientia Horticulturae*, c. 280, 109915, 2021, doi:10.1016/j.scienta.2021.109915 | Aslan yelesi: inkübasyon 25 °C; meyvelenme 15/20/25 °C, %85–90 nem, CO2 < 1000 ppm; BV |
| [H2] | D. Gonkhom vd., "Cultivation and Nutrient Compositions of Medicinal Mushroom, Hericium erinaceus in Thailand," *Chiang Mai J. Sci.*, c. 51, no. 2, e2024028, 2024, doi:10.12982/CMJS.2024.028 | Aslan yelesi: inkübasyon 30–40 gün; meyvelenme 18–24 °C, %90–95; pin 17–28 gün, gelişim 7–10 gün |
| [H3] | 'Chuanhougu 1' (2021) ve 'Chuanhougu 2' (2020), *Mycosystema* (yalnızca özetler) | Aslan yelesi meyvelenme 12–20 °C; BV %83–85 |

## Varsayımlar ve kalibrasyon
- Oda fiziği, PI kazançları, kontaminasyon riski, ekonomi ve ödül katsayıları varsayımdır (`tur: varsayim / gecici`).
- Miselin CO2 üretimi (0,1 L/kg/saat), literatürdeki ticari CO2 ayar noktalarının (≤ 1000 ppm) makul havalandırmayla
  sağlanabileceği şekilde kalibre edilmiştir.
- Işık ajanın kararı değildir; meyvelenme ve kahverengileşme evrelerinde sabit aydınlatma programı varsayılır ([S1], [S2]).
- Şok soyut bir ayrık karardır; gerçekte sıcaklık şoku ([S2]) ya da su şoku ([S3]) olabilir.
- Suş farkı: meyvelenme sıcaklık aralığı her bölümde ±3 °C kaydırılır; BV literatür aralığından örneklenir.
