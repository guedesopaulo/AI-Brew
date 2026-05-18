"""Pure recipe calculation functions — no I/O."""

import math

from src.models.recipe import CalculatedStats
from src.models.recipe import Fermentable
from src.models.recipe import Hop
from src.models.recipe import Recipe

_KG_TO_LBS = 2.20462
_G_TO_OZ = 0.035274
_LITERS_TO_GALLONS = 0.264172
_EBC_TO_LOVIBOND = 0.508  # Lovibond = EBC * 0.508 (inverse of EBC = L * 1.97)
DEFAULT_EFFICIENCY_PCT = 75.0


def calc_og(
    fermentables: list[Fermentable],
    batch_liters: float,
    efficiency_pct: float = DEFAULT_EFFICIENCY_PCT,
) -> float:
    """Original gravity via malt extract (PPG) formula."""
    batch_gallons = batch_liters * _LITERS_TO_GALLONS
    total_points = sum(f["amount_kg"] * _KG_TO_LBS * f["ppg"] for f in fermentables)
    return round(1 + total_points * (efficiency_pct / 100) / batch_gallons / 1000, 4)


def calc_ibu_tinseth(hops: list[Hop], og: float, batch_liters: float) -> float:
    """IBU via Tinseth formula (boil additions only)."""
    batch_gallons = batch_liters * _LITERS_TO_GALLONS
    total_ibu = 0.0
    for hop in hops:
        if hop["use"] != "boil":
            continue
        bigness = 1.65 * (0.000125 ** (og - 1))
        boil_factor = (1 - math.exp(-0.04 * hop["time_min"])) / 4.15
        utilization = bigness * boil_factor
        oz = hop["amount_g"] * _G_TO_OZ
        total_ibu += utilization * hop["alpha_pct"] * oz * 74.89 / batch_gallons
    return round(total_ibu, 1)


def calc_srm_morey(fermentables: list[Fermentable], batch_liters: float) -> float:
    """SRM color via Morey formula."""
    batch_gallons = batch_liters * _LITERS_TO_GALLONS
    mcu = (
        sum(
            f["amount_kg"] * _KG_TO_LBS * f["color_ebc"] * _EBC_TO_LOVIBOND
            for f in fermentables
        )
        / batch_gallons
    )
    return round(1.4922 * (mcu**0.6859), 1)


def calc_fg(og: float, attenuation_pct: float) -> float:
    """Final gravity from OG and yeast attenuation."""
    return round(1 + (og - 1) * (1 - attenuation_pct / 100), 4)


def calc_abv(og: float, fg: float) -> float:
    """Alcohol by volume (%)."""
    return round((og - fg) * 131.25, 2)


def calculate_stats(
    recipe: Recipe, efficiency_pct: float = DEFAULT_EFFICIENCY_PCT
) -> CalculatedStats:
    """Derive all calculated stats from a recipe."""
    og = calc_og(recipe["fermentables"], recipe["batch_size_liters"], efficiency_pct)
    fg = calc_fg(og, recipe["yeast"]["attenuation_pct"])
    return {
        "og": og,
        "fg": fg,
        "abv": calc_abv(og, fg),
        "ibu": calc_ibu_tinseth(recipe["hops"], og, recipe["batch_size_liters"]),
        "srm": calc_srm_morey(recipe["fermentables"], recipe["batch_size_liters"]),
    }
