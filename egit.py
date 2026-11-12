"""Eğitim betiği (K2): bir tür ve tohum için PPO ajanını eğitir.

Çalıştırma (proje kök klasöründen):
    python egit.py --tur istiridye --tohum 0
    python egit.py --tur istiridye --tohum 0 --adim 50000     # kısa deneme

Ayarlar config.yaml → egitim bölümünden okunur; --adim verilirse toplam_adim'in yerine geçer.
Kayıtlar: runs/ppo/<tür>/<tohum>/  (model.zip, izleme.monitor.csv, egitim_egrisi.png, ayarlar.yaml)
Tohum aralıkları ayrıdır: eğitim ortamı 10000 + tohum ile başlar; ayarlanmış kural 100–109
doğrulama tohumlarında ayarlanır; bütün yöntemler seeds.txt'deki test tohumlarında (0–4) karşılaştırılır.
"""

import argparse
import os
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from stable_baselines3 import PPO  # noqa: E402
from stable_baselines3.common.monitor import Monitor  # noqa: E402

from ajanlar.sarmalayici import DuzEylem  # noqa: E402
from mantar_ortami.ortam import MantarOrtami  # noqa: E402


def egitim_egrisi_ciz(izleme_csv: Path, cikti: Path, tur: str) -> None:
    df = pd.read_csv(izleme_csv, skiprows=1)
    if df.empty:
        return
    df["adim"] = df["l"].cumsum()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["adim"], df["r"], alpha=0.3, label="bölüm ödülü")
    ax.plot(df["adim"], df["r"].rolling(20, min_periods=1).mean(), label="20 bölümlük ortalama")
    ax.set_xlabel("Eğitim adımı"); ax.set_ylabel("Bölüm ödülü"); ax.legend()
    ax.set_title(f"PPO eğitim eğrisi — {tur}")
    fig.tight_layout(); fig.savefig(cikti, dpi=120); plt.close(fig)


def egit(tur: str, tohum: int, adim: int | None = None) -> Path:
    with open("config.yaml", encoding="utf-8") as f:
        ayarlar = yaml.safe_load(f)
    e = ayarlar["egitim"]
    toplam_adim = adim or e["toplam_adim"]
    klasor = Path(os.environ.get("MANTAR_RUNS_DIR", "runs")) / "ppo" / tur / str(tohum)
    klasor.mkdir(parents=True, exist_ok=True)

    ortam = Monitor(DuzEylem(MantarOrtami(ayarlar, tur=tur)), str(klasor / "izleme"))
    ortam.reset(seed=10_000 + tohum)
    model = PPO("MlpPolicy", ortam, learning_rate=e["ogrenme_orani"], n_steps=e["n_steps"],
                batch_size=e["batch_size"], n_epochs=e["n_epochs"], gamma=e["gamma"],
                gae_lambda=e["gae_lambda"], clip_range=e["clip_eps"], ent_coef=e["ent_coef"],
                seed=tohum, device=os.environ.get("MANTAR_DEVICE", "cpu"), verbose=0)
    t0 = time.time()
    model.learn(total_timesteps=toplam_adim, progress_bar=False)
    sure = time.time() - t0
    model.save(klasor / "model")
    with open(klasor / "ayarlar.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump({"tur": tur, "tohum": tohum, "toplam_adim": toplam_adim, "sure_s": round(sure, 1),
                        "egitim": e}, f, allow_unicode=True, sort_keys=False)
    egitim_egrisi_ciz(klasor / "izleme.monitor.csv", klasor / "egitim_egrisi.png", tur)
    print(f"{tur} tohum {tohum}: {toplam_adim} adım, {sure:.0f} s → {klasor / 'model.zip'}")
    return klasor / "model.zip"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="PPO eğitimi")
    ap.add_argument("--tur", default="istiridye", choices=["istiridye", "shiitake", "aslan_yelesi"])
    ap.add_argument("--tohum", type=int, default=0)
    ap.add_argument("--adim", type=int, default=None, help="toplam eğitim adımı (varsayılan: config.yaml)")
    a = ap.parse_args()
    egit(a.tur, a.tohum, a.adim)
