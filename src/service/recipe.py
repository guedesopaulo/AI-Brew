"""Pure recipe calculation functions — no I/O."""

import math

from src.models.recipe import CalculatedStats
from src.models.recipe import Fermentable
from src.models.recipe import GrainBillResult
from src.models.recipe import GrainInput
from src.models.recipe import GrainOutput
from src.models.recipe import Hop
from src.models.recipe import HopAdditionInput
from src.models.recipe import HopAdditionOutput
from src.models.recipe import HopScheduleResult
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


def calculate_grain_bill(
    batch_liters: float,
    efficiency_pct: float,
    yeast_attenuation_pct: float,
    grain_inputs: list[GrainInput],
    target_abv: float | None = None,
    target_og: float | None = None,
    target_fg: float | None = None,
) -> GrainBillResult:
    """Return exact grain amounts for a target ABV, OG, or FG.

    Exactly one of target_abv, target_og, or target_fg must be provided.
    Offloads arithmetic from the LLM to prevent order-of-operations errors.
    """
    targets = [t for t in (target_abv, target_og, target_fg) if t is not None and t > 0]
    if len(targets) != 1:
        raise ValueError(
            "Exactly one of target_abv, target_og, or target_fg must be provided "
            "(pass only the one you need; omit or leave out the others)"
        )
    attenuation = yeast_attenuation_pct / 100
    if target_abv is not None and target_abv > 0:
        resolved_og = 1 + target_abv / (attenuation * 131.25)
    elif target_fg is not None and target_fg > 0:
        if attenuation >= 1.0:
            raise ValueError("yeast_attenuation_pct must be less than 100")
        resolved_og = 1 + (target_fg - 1) / (1 - attenuation)
    else:
        assert target_og is not None  # validated above: exactly one target is set
        resolved_og = target_og
    target_og_points = (resolved_og - 1) * 1000
    weighted_ppg = sum(g["ppg"] * g["pct"] / 100 for g in grain_inputs)
    batch_gallons = batch_liters * _LITERS_TO_GALLONS
    efficiency = efficiency_pct / 100
    total_grain_kg = (
        target_og_points * batch_gallons / (weighted_ppg * _KG_TO_LBS * efficiency)
    )
    fermentables: list[GrainOutput] = [
        {
            "name": g["name"],
            "ppg": g["ppg"],
            "amount_kg": round(total_grain_kg * g["pct"] / 100, 2),
            "color_ebc": g["color_ebc"],
        }
        for g in grain_inputs
    ]
    return {
        "target_og": round(resolved_og, 4),
        "target_og_points": round(target_og_points, 1),
        "total_grain_kg": round(total_grain_kg, 2),
        "fermentables": fermentables,
    }


def calculate_hop_schedule(
    target_ibu: float,
    og: float,
    batch_liters: float,
    hop_inputs: list[HopAdditionInput],
) -> HopScheduleResult:
    """Return exact gram amounts for a target IBU using inverse Tinseth.

    Boil hops: amount computed via inverse Tinseth from ibu_pct share.
    Non-boil hops: pass through with provided amount_g (default 20 g).
    total_ibu is verified by running forward Tinseth on the result.
    """
    batch_gallons = batch_liters * _LITERS_TO_GALLONS
    bigness = 1.65 * (0.000125 ** (og - 1))
    hops_out: list[HopAdditionOutput] = []
    for h in hop_inputs:
        if h["use"] == "boil":
            boil_factor = (1 - math.exp(-0.04 * h["time_min"])) / 4.15
            utilization = bigness * boil_factor
            if utilization == 0 or h["alpha_pct"] == 0:
                raise ValueError(
                    f"Hop '{h['name']}': time_min > 0 and alpha_pct > 0 "
                    "required for boil additions"
                )
            ibu_share = target_ibu * h["ibu_pct"] / 100
            amount_g = (
                ibu_share
                * batch_gallons
                / (utilization * h["alpha_pct"] * 74.89 * _G_TO_OZ)
            )
            hops_out.append(
                {
                    "name": h["name"],
                    "amount_g": round(amount_g, 1),
                    "alpha_pct": h["alpha_pct"],
                    "time_min": h["time_min"],
                    "use": "boil",
                }
            )
        else:
            hops_out.append(
                {
                    "name": h["name"],
                    "amount_g": h.get("amount_g", 20.0),
                    "alpha_pct": h["alpha_pct"],
                    "time_min": h["time_min"],
                    "use": h["use"],
                }
            )
    hop_list: list[Hop] = [
        {
            "name": h["name"],
            "amount_g": h["amount_g"],
            "alpha_pct": h["alpha_pct"],
            "time_min": h["time_min"],
            "use": h["use"],
        }
        for h in hops_out
    ]
    total_ibu = calc_ibu_tinseth(hop_list, og=og, batch_liters=batch_liters)
    return {"total_ibu": total_ibu, "hops": hops_out}


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
