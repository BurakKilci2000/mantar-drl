# Kurulum

Aşağıdaki adımlar projeyi bağımsız bir Windows bilgisayarda çalıştırmak içindir.
12. haftada Docker ile kurulum (compose.yaml) eklenecektir.

## Gereksinimler

- Python 3.11
- Git
- (İsteğe bağlı) NVIDIA ekran kartı ve CUDA sürücüsü

## Adımlar

```
git clone https://github.com/BurakKilci2000/mantar-drl.git
cd mantar-drl

python -m venv .venv
.venv\Scripts\activate

pip install -r 04_Kurulum/requirements.txt
```

Linux veya macOS'ta sanal ortamı etkinleştirmek için `source .venv/bin/activate` kullanılır.

### Ekran kartıyla eğitim (isteğe bağlı)

requirements.txt içindeki PyTorch işlemci (CPU) sürümüdür. Eğitimi NVIDIA ekran kartıyla yapmak için
PyTorch'u resmî sitedeki (pytorch.org) yönergelere göre CUDA destekli olarak yeniden kurun.

### Ortam değişkenleri

```
copy .env.example .env
```

Ardından `.env` dosyasındaki değerleri gerekirse düzenleyin. `.env` depoya eklenmez.

## Çalıştırma

Bu bölüm modüller tamamlandıkça güncellenecektir.

```
python -m betikler.demo_sabit_recete shiitake   # duman testi (istiridye | shiitake | aslan_yelesi) + grafik (runs/demo/)
python egit.py                        # eğitim (yazılacak)
python degerlendir.py                 # değerlendirme (yazılacak)
```
