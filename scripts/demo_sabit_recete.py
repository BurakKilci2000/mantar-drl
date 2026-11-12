"""Duman testi: sabit reçeteyle bir üretim döngüsü çalıştırır, özeti yazdırır ve grafiği kaydeder.

Çalıştırma (proje kök klasöründen):  python -m scripts.demo_sabit_recete [istiridye|shiitake|aslan_yelesi]
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

from baselines.fixed_recipe import FixedRecipe
from mushroom_env.env import MushroomEnv


def gecici_parametreler(cfg: dict) -> list:
    return [k for k, v in cfg.items() if isinstance(v, dict) and v.get("tur") in ("gecici", "varsayim")]


def main(species: str = "istiridye", seed: int = 0) -> None:
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    env = MushroomEnv(cfg, species=species)
    policy = FixedRecipe(env)
    obs, info = env.reset(seed=seed)
    rows, total_reward, done = [], 0.0, False
    while not done:
        action = policy.act(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        g = info["gozlem"]
        rows.append({"gun": g["dongu_gunu"], "T": g["sicaklik_c"], "RH": g["bagil_nem"], "CO2": g["co2_ppm"],
                     "kol": g["kolonizasyon_gozlenen"], "kah": g["kahverengilesme_orani"], "biyo": g["biyokutle_orani"], "evre": info["evre"],
                     "kwh": info["enerji_kwh"]})
        done = terminated or truncated

    print(f"Tür: {species}  tohum: {seed}  toplam ödül: {total_reward:.1f}")
    for k, v in info["ozet"].items():
        print(f"  {k:22s} {v:.3f}" if isinstance(v, float) else f"  {k:22s} {v}")
    print("Not: şu parametre grupları varsayım/geçicidir:", ", ".join(gecici_parametreler(cfg)))

    os.makedirs("runs/demo", exist_ok=True)
    days = [r["gun"] for r in rows]
    fig, ax = plt.subplots(5, 1, figsize=(10, 11), sharex=True)
    ax[0].plot(days, [r["T"] for r in rows]); ax[0].set_ylabel("Sıcaklık (°C)")
    ax[1].plot(days, [r["RH"] for r in rows]); ax[1].set_ylabel("Bağıl nem (%)")
    ax[2].plot(days, [r["CO2"] for r in rows]); ax[2].set_ylabel("CO₂ (ppm)")
    ax[3].plot(days, [r["kol"] for r in rows], label="kolonizasyon (gözlenen)")
    if env.species_cfg.get("kahverengilesme"):
        ax[3].plot(days, [r["kah"] for r in rows], label="kahverengileşme")
    ax[3].plot(days, [r["biyo"] for r in rows], label="biyokütle / dalga kapasitesi")
    ax[3].legend(); ax[3].set_ylabel("Oran")
    ax[4].plot(days, [r["kwh"] for r in rows]); ax[4].set_ylabel("Enerji (kWh/adım)")
    ax[4].set_xlabel("Gün")
    fig.suptitle(f"Sabit reçete — {species}, tohum {seed}")
    fig.tight_layout()
    path = f"runs/demo/sabit_recete_{species}_{seed}.png"
    fig.savefig(path, dpi=120)
    print("Grafik:", path)


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "istiridye")
