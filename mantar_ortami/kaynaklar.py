"""Kaynak tüketimi alt modeli: enerji (kWh) ve su (L) sayaçları."""

from dataclasses import dataclass, field


@dataclass
class KaynakSayaci:
    enerji_kwh: float = 0.0
    su_l: float = 0.0
    isitma_kwh: float = 0.0
    sogutma_kwh: float = 0.0
    dokum: dict = field(default_factory=dict)

    def ekle(self, tuketim: dict) -> None:
        self.enerji_kwh += tuketim["enerji_kwh"]
        self.su_l += tuketim["su_l"]
        self.isitma_kwh += tuketim["isitma_kwh"]
        self.sogutma_kwh += tuketim["sogutma_kwh"]
