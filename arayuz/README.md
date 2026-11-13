# K5 · Streamlit arayüzü

```
streamlit run arayuz/uygulama.py
```
Tarayıcıda http://localhost:8501 açılır. Simülasyon arayüzün içinde çalışır (bir döngü < 1 s).

Sekmeler:
- **Döngüyü izle**: tür, senaryo (tohum) ve yöntem seçilir; oda iklimi, ayar noktaları, evreler, şok ve hasat
  kararları, kolonizasyon ve biyokütle grafikte; zaman kaydırıcısı ve ▶ Oynat ile adım adım izlenir.
- **Yöntemleri karşılaştır**: aynı senaryoda seçilen yöntemlerin özet tablosu, sabit reçeteye göre fark,
  birikimli hasat ve kazanç eğrileri.
- **Test sonuçları**: `degerlendir.py`'nin 5 test tohumluk özeti (runs/degerlendirme varsa oradan,
  yoksa belgeler/hafta07'den).
- **Model hakkında**: türün parametreleri ve kaynakları.

PPO seçeneği `runs/ppo/<tür>/<tohum>/model.zip` varsa görünür (`python egit.py --tur istiridye --tohum 0`).
