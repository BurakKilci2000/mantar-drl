"""Kaynak tüketimi alt modeli: enerji (kWh) ve su (L) sayaçları."""

from dataclasses import dataclass, field


@dataclass
class ResourceMeter:
    energy_kwh: float = 0.0
    water_l: float = 0.0
    heating_kwh: float = 0.0
    cooling_kwh: float = 0.0
    breakdown: dict = field(default_factory=dict)

    def add(self, usage: dict) -> None:
        self.energy_kwh += usage["enerji_kwh"]
        self.water_l += usage["su_l"]
        self.heating_kwh += usage["isitma_kwh"]
        self.cooling_kwh += usage["sogutma_kwh"]
