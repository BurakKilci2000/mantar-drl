# Ad değişiklikleri (İngilizce → Türkçe)

Kodun okunabilirliği için projeye ait bütün klasör, modül, sınıf, fonksiyon ve değişken adları Türkçeye çevrildi
(ASCII harflerle). Hesaplar değişmedi: eski ve yeni kod üç tür × iki tohumda birebir aynı sonuçları veriyor.

İngilizce kalanlar: Gymnasium arayüzü (`reset`, `step`, `action_space`, `observation_space`, `metadata`,
`np_random`, `terminated`, `truncated`, `seed`, `options`) ve kütüphane adları (numpy, yaml, matplotlib).

## Klasörler ve dosyalar

| Eski | Yeni |
|---|---|
| mushroom_env/ | mantar_ortami/ |
| mushroom_env/env.py | mantar_ortami/ortam.py |
| mushroom_env/biology.py | mantar_ortami/biyoloji.py |
| mushroom_env/climate.py | mantar_ortami/iklim.py |
| mushroom_env/substrate.py | mantar_ortami/substrat.py |
| mushroom_env/stress.py | mantar_ortami/stres.py |
| mushroom_env/resources.py | mantar_ortami/kaynaklar.py |
| baselines/ | rakipler/ |
| baselines/fixed_recipe.py | rakipler/sabit_recete.py |
| baselines/policy.py | rakipler/politika.py |
| agents/ | ajanlar/ |
| reporting/ | raporlama/ |
| app/ | arayuz/ |
| data/ | veri/ |
| scripts/ | betikler/ |
| docs/ | belgeler/ |
| train.py | egit.py |
| evaluate.py | degerlendir.py |

## Sınıflar

| Eski | Yeni |
|---|---|
| MushroomEnv | MantarOrtami |
| Biology | Biyoloji |
| RoomClimate | OdaIklimi |
| ClimateState | IklimDurumu |
| Substrate | Substrat |
| ResourceMeter | KaynakSayaci |
| Policy | Politika |
| FixedRecipe | SabitRecete |

## Fonksiyonlar ve sabitler

| Eski | Yeni |
|---|---|
| decode_observation | gozlemi_coz |
| check_species_config | tur_ayarini_denetle |
| band | bant |
| upper_limit | ust_sinir |
| piecewise_quality | parcali_kalite |
| co2_growth | co2_buyume |
| saturation_vapor_density | doymus_buhar_yogunlugu |
| rh_to_vapor_density | nemden_buhar_yogunlugu |
| SPECIES | TURLER |
| OBS_KEYS | GOZLEM_ANAHTARLARI |
| OPTIONAL_KEYS | ISTEGE_BAGLI_ANAHTARLAR |
| STAGE_NAMES | EVRE_ADLARI |
| AIR_DENSITY / AIR_CP / LATENT_HEAT | HAVA_YOGUNLUGU / HAVA_OZGUL_ISI / GIZLI_ISI |
| main() (betiklerde) | calistir() |

## Yöntemler

| Sınıf | Eski | Yeni |
|---|---|---|
| hepsi | reset (alt modellerde) | sifirla |
| hepsi | substep | alt_adim |
| MantarOrtami | summary | ozet |
| MantarOrtami | unscale_setpoints | ayar_noktalarina_cevir |
| MantarOrtami | scale_setpoints | ayar_noktalarini_olcekle |
| MantarOrtami | _outside / _stage_targets / _violation | _dis_hava / _evre_hedefleri / _ihlal_var_mi |
| MantarOrtami | _observe / _value_kg / _scale | _gozlem / _deger_kg / _olcekle |
| Biyoloji | shock / harvest | sok / hasat |
| Biyoloji | quality / marketable_kg | kalite / pazarlanabilir_kg |
| Biyoloji | lose_capacity / _end_flush / _enter | kapasite_kaybet / _dalgayi_bitir / _gec |
| Substrat | moisture_factor / evaporation_kg_h | nem_carpani / buharlasma_kg_saat |
| Substrat | heat_w / co2_l_h / observed_colonization | isi_w / co2_l_saat / gozlenen_kolonizasyon |
| KaynakSayaci | add | ekle |
| Politika | act | eylem_sec |

## Öznitelikler (seçme)

| Eski | Yeni |
|---|---|
| env.cfg / species / species_cfg | ortam.ayarlar / tur / tur_ayarlari |
| env.climate / substrate / biology / meter | ortam.iklim / substrat / biyoloji / sayac |
| climate.state (temp_c, rh, co2_ppm) | iklim.durum (sicaklik_c, bagil_nem, co2_ppm) |
| biology.stage / flush / biomass / capacity | biyoloji.evre / dalga / biyokutle / kapasite |
| biology.harvested_kg / spoiled_kg / be / temp_shift | biyoloji.hasat_kg / curuyen_kg / bv / sicaklik_kaymasi |
| substrate.moisture / colonization / dry_kg | substrat.nem / kolonizasyon / kuru_kg |
| meter.energy_kwh / water_l | sayac.enerji_kwh / su_l |
| Policy.name | Politika.ad |

config.yaml anahtarları zaten Türkçeydi; değişmedi.
