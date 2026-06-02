"""Unit tests for recipe calculation functions."""

import pytest

from src.models.recipe import Fermentable
from src.models.recipe import GrainInput
from src.models.recipe import Hop
from src.models.recipe import HopAdditionInput
from src.models.recipe import Recipe
from src.models.recipe import Yeast
from src.service.recipe import calc_abv
from src.service.recipe import calc_fg
from src.service.recipe import calc_ibu_tinseth
from src.service.recipe import calc_og
from src.service.recipe import calc_srm_morey
from src.service.recipe import calculate_grain_bill
from src.service.recipe import calculate_hop_schedule
from src.service.recipe import calculate_stats

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PALE_MALT: Fermentable = {
    "name": "Pale Malt (2-Row)",
    "amount_kg": 4.0,
    "color_ebc": 5,
    "ppg": 37,
}
CRYSTAL_60: Fermentable = {
    "name": "Crystal 60L",
    "amount_kg": 0.5,
    "color_ebc": 120,
    "ppg": 33,
}
CASCADE_BOIL: Hop = {
    "name": "Cascade",
    "amount_g": 30,
    "alpha_pct": 5.5,
    "time_min": 60,
    "use": "boil",
}
CASCADE_DRY: Hop = {
    "name": "Cascade",
    "amount_g": 30,
    "alpha_pct": 5.5,
    "time_min": 0,
    "use": "dry-hop",
}
AMERICAN_ALE_YEAST: Yeast = {
    "name": "SafAle US-05",
    "attenuation_pct": 78,
    "min_temp_c": 15,
    "max_temp_c": 24,
}


# ---------------------------------------------------------------------------
# calc_og
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fermentables", "batch_liters", "expected"),
    [
        ([PALE_MALT], 20.0, 1.0463),
        ([PALE_MALT, CRYSTAL_60], 20.0, 1.0515),
        ([PALE_MALT], 40.0, 1.0232),
    ],
)
def test_calc_og(
    fermentables: list[Fermentable], batch_liters: float, expected: float
) -> None:
    result = calc_og(fermentables, batch_liters)
    assert abs(result - expected) < 0.001


def test_calc_og_empty_fermentables() -> None:
    assert calc_og([], 20.0) == 1.0


def test_calc_og_higher_efficiency_raises_og() -> None:
    og_75 = calc_og([PALE_MALT], 20.0, efficiency_pct=75.0)
    og_80 = calc_og([PALE_MALT], 20.0, efficiency_pct=80.0)
    assert og_80 > og_75


# ---------------------------------------------------------------------------
# calc_ibu_tinseth
# ---------------------------------------------------------------------------


def test_calc_ibu_boil_only() -> None:
    # 30 g Cascade @ 5.5% AA, 60 min, OG 1.050, 20 L → ~19 IBU per Tinseth
    ibu = calc_ibu_tinseth([CASCADE_BOIL], og=1.050, batch_liters=20.0)
    assert 15 < ibu < 25


def test_calc_ibu_dry_hop_excluded() -> None:
    ibu_boil = calc_ibu_tinseth([CASCADE_BOIL], og=1.050, batch_liters=20.0)
    ibu_both = calc_ibu_tinseth(
        [CASCADE_BOIL, CASCADE_DRY], og=1.050, batch_liters=20.0
    )
    assert ibu_boil == ibu_both


def test_calc_ibu_no_hops() -> None:
    assert calc_ibu_tinseth([], og=1.050, batch_liters=20.0) == 0.0


def test_calc_ibu_higher_og_lower_utilization() -> None:
    ibu_low = calc_ibu_tinseth([CASCADE_BOIL], og=1.040, batch_liters=20.0)
    ibu_high = calc_ibu_tinseth([CASCADE_BOIL], og=1.080, batch_liters=20.0)
    assert ibu_low > ibu_high


def test_calc_ibu_longer_boil_higher_ibu() -> None:
    hop_60: Hop = {**CASCADE_BOIL, "time_min": 60}
    hop_15: Hop = {**CASCADE_BOIL, "time_min": 15}
    assert calc_ibu_tinseth([hop_60], og=1.050, batch_liters=20.0) > calc_ibu_tinseth(
        [hop_15], og=1.050, batch_liters=20.0
    )


# ---------------------------------------------------------------------------
# calc_srm_morey
# ---------------------------------------------------------------------------


def test_calc_srm_pale_beer() -> None:
    srm = calc_srm_morey([PALE_MALT], batch_liters=20.0)
    assert 2 <= srm <= 6  # pale golden range


def test_calc_srm_darker_with_crystal() -> None:
    srm_pale = calc_srm_morey([PALE_MALT], batch_liters=20.0)
    srm_amber = calc_srm_morey([PALE_MALT, CRYSTAL_60], batch_liters=20.0)
    assert srm_amber > srm_pale


def test_calc_srm_no_fermentables() -> None:
    assert calc_srm_morey([], batch_liters=20.0) == 0.0


# ---------------------------------------------------------------------------
# calc_fg
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("og", "attenuation_pct", "expected"),
    [
        (1.050, 75, 1.0125),
        (1.060, 80, 1.012),
        (1.040, 70, 1.012),
    ],
)
def test_calc_fg(og: float, attenuation_pct: float, expected: float) -> None:
    result = calc_fg(og, attenuation_pct)
    assert abs(result - expected) < 0.001


# ---------------------------------------------------------------------------
# calc_abv
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("og", "fg", "expected_approx"),
    [
        (1.050, 1.010, 5.25),
        (1.060, 1.012, 6.3),
        (1.040, 1.010, 3.94),
    ],
)
def test_calc_abv(og: float, fg: float, expected_approx: float) -> None:
    result = calc_abv(og, fg)
    assert abs(result - expected_approx) < 0.1


# ---------------------------------------------------------------------------
# calculate_stats (integration)
# ---------------------------------------------------------------------------

SIMPLE_RECIPE: Recipe = {
    "id": "test-1",
    "name": "Test Pale Ale",
    "style": "American Pale Ale",
    "batch_size_liters": 20.0,
    "fermentables": [PALE_MALT],
    "hops": [CASCADE_BOIL],
    "yeast": AMERICAN_ALE_YEAST,
}


def test_calculate_stats_returns_all_fields() -> None:
    stats = calculate_stats(SIMPLE_RECIPE)
    assert set(stats.keys()) == {"og", "fg", "abv", "ibu", "srm", "bu_gu"}


def test_calculate_stats_og_fg_abv_consistent() -> None:
    stats = calculate_stats(SIMPLE_RECIPE)
    assert stats["og"] > stats["fg"]
    assert stats["abv"] > 0
    # cross-check ABV
    expected_abv = round((stats["og"] - stats["fg"]) * 131.25, 2)
    assert stats["abv"] == expected_abv


def test_calculate_stats_ibu_positive() -> None:
    stats = calculate_stats(SIMPLE_RECIPE)
    assert stats["ibu"] > 0


def test_calculate_stats_respects_custom_efficiency() -> None:
    stats_75 = calculate_stats(SIMPLE_RECIPE, efficiency_pct=75.0)
    stats_68 = calculate_stats(SIMPLE_RECIPE, efficiency_pct=68.0)
    assert stats_68["og"] < stats_75["og"]
    assert stats_68["abv"] < stats_75["abv"]


def test_calculate_stats_srm_positive() -> None:
    stats = calculate_stats(SIMPLE_RECIPE)
    assert stats["srm"] > 0


def test_calculate_stats_bu_gu_known_value() -> None:
    # SIMPLE_RECIPE: 4kg Pale Malt 20L + 30g Cascade 5.5% 60min → OG ~1.046, IBU ~19
    # BU/GU = 19 / ((1.046 - 1) * 1000) = 19 / 46 ≈ 0.41
    stats = calculate_stats(SIMPLE_RECIPE)
    assert stats["bu_gu"] == pytest.approx(0.41, abs=0.05)
    assert 0.2 < stats["bu_gu"] < 0.7  # reasonable pale ale range


def test_calculate_stats_bu_gu_zero_when_no_og() -> None:
    no_grain_recipe: Recipe = {**SIMPLE_RECIPE, "fermentables": []}
    stats = calculate_stats(no_grain_recipe)
    assert stats["og"] == 1.0
    assert stats["bu_gu"] == 0.0


# ---------------------------------------------------------------------------
# calculate_grain_bill
# ---------------------------------------------------------------------------

_GUINNESS_GRAIN_INPUTS: list[GrainInput] = [
    {"name": "Pale Malt", "ppg": 37, "color_ebc": 5.0, "pct": 91.0},
    {"name": "Roasted Barley", "ppg": 25, "color_ebc": 1400.0, "pct": 5.0},
    {"name": "Black Malt", "ppg": 25, "color_ebc": 1300.0, "pct": 4.0},
]


def test_calculate_grain_bill_guinness_target_og() -> None:
    # 4.2% ABV, 78% attenuation → OG = 1 + 4.2 / (0.78 * 131.25) = 1.0410
    result = calculate_grain_bill(
        target_abv=4.2,
        batch_liters=40.0,
        efficiency_pct=70.0,
        yeast_attenuation_pct=78.0,
        grain_inputs=_GUINNESS_GRAIN_INPUTS,
    )
    assert abs(result["target_og"] - 1.041) < 0.001
    assert abs(result["target_og_points"] - 41.0) < 0.5


def test_calculate_grain_bill_guinness_total_grain() -> None:
    result = calculate_grain_bill(
        target_abv=4.2,
        batch_liters=40.0,
        efficiency_pct=70.0,
        yeast_attenuation_pct=78.0,
        grain_inputs=_GUINNESS_GRAIN_INPUTS,
    )
    # Verify grain bill rounds back to the correct OG via calc_og
    fermentables: list[Fermentable] = [
        {
            "name": g["name"],
            "amount_kg": g["amount_kg"],
            "color_ebc": g["color_ebc"],
            "ppg": gi["ppg"],
        }
        for g, gi in zip(result["fermentables"], _GUINNESS_GRAIN_INPUTS, strict=True)
    ]
    computed_og = calc_og(fermentables, batch_liters=40.0, efficiency_pct=70.0)
    assert abs(computed_og - result["target_og"]) < 0.002


def test_calculate_grain_bill_pcts_sum_reflected_in_amounts() -> None:
    result = calculate_grain_bill(
        target_abv=4.2,
        batch_liters=40.0,
        efficiency_pct=70.0,
        yeast_attenuation_pct=78.0,
        grain_inputs=_GUINNESS_GRAIN_INPUTS,
    )
    total = sum(f["amount_kg"] for f in result["fermentables"])
    assert abs(total - result["total_grain_kg"]) < 0.1


def test_calculate_grain_bill_higher_efficiency_less_grain() -> None:
    single_malt: list[GrainInput] = [
        {"name": "Pale Malt", "ppg": 37, "color_ebc": 5.0, "pct": 100.0}
    ]
    low = calculate_grain_bill(
        target_abv=4.2,
        batch_liters=20.0,
        efficiency_pct=65.0,
        yeast_attenuation_pct=75.0,
        grain_inputs=single_malt,
    )
    high = calculate_grain_bill(
        target_abv=4.2,
        batch_liters=20.0,
        efficiency_pct=80.0,
        yeast_attenuation_pct=75.0,
        grain_inputs=single_malt,
    )
    assert low["total_grain_kg"] > high["total_grain_kg"]


def test_calculate_grain_bill_color_ebc_passed_through() -> None:
    # color_ebc from grain_inputs must appear in the output fermentables
    inputs: list[GrainInput] = [
        {"name": "Pale Malt", "ppg": 37, "color_ebc": 5.0, "pct": 90.0},
        {"name": "Crystal 60L", "ppg": 33, "color_ebc": 120.0, "pct": 10.0},
    ]
    result = calculate_grain_bill(
        batch_liters=20.0,
        efficiency_pct=75.0,
        yeast_attenuation_pct=75.0,
        grain_inputs=inputs,
        target_abv=5.0,
    )
    colors = {f["name"]: f["color_ebc"] for f in result["fermentables"]}
    assert colors["Pale Malt"] == pytest.approx(5.0)
    assert colors["Crystal 60L"] == pytest.approx(120.0)


def test_calculate_grain_bill_target_og_direct() -> None:
    # target_og=1.040 must give same result as the equivalent ABV for 75% attenuation
    # ABV equivalent: (1.040 - 1) * 75/100 * 131.25 = 3.938% → round-trip should match
    single_malt: list[GrainInput] = [
        {"name": "Pale Malt", "ppg": 37, "color_ebc": 5.0, "pct": 100.0}
    ]
    result = calculate_grain_bill(
        batch_liters=20.0,
        efficiency_pct=75.0,
        yeast_attenuation_pct=75.0,
        grain_inputs=single_malt,
        target_og=1.040,
    )
    assert result["target_og"] == pytest.approx(1.040, abs=0.001)
    assert result["target_og_points"] == pytest.approx(40.0, abs=0.5)
    # Verify grain amounts match the forward calc_og
    fermentables: list[Fermentable] = [
        {
            "name": "Pale Malt",
            "amount_kg": result["fermentables"][0]["amount_kg"],
            "color_ebc": 5.0,
            "ppg": 37,
        }
    ]
    assert abs(calc_og(fermentables, 20.0, 75.0) - 1.040) < 0.002


def test_calculate_grain_bill_target_fg_matches_equivalent_og() -> None:
    # target_fg=1.010 at 75% attenuation → OG = 1 + 0.010/0.25 = 1.040
    # Must give identical result to target_og=1.040
    single_malt: list[GrainInput] = [
        {"name": "Pale Malt", "ppg": 37, "color_ebc": 5.0, "pct": 100.0}
    ]
    by_fg = calculate_grain_bill(
        batch_liters=20.0,
        efficiency_pct=75.0,
        yeast_attenuation_pct=75.0,
        grain_inputs=single_malt,
        target_fg=1.010,
    )
    by_og = calculate_grain_bill(
        batch_liters=20.0,
        efficiency_pct=75.0,
        yeast_attenuation_pct=75.0,
        grain_inputs=single_malt,
        target_og=1.040,
    )
    assert by_fg["target_og"] == pytest.approx(by_og["target_og"], abs=0.0005)
    assert by_fg["total_grain_kg"] == pytest.approx(by_og["total_grain_kg"], abs=0.01)


def test_calculate_grain_bill_no_target_raises() -> None:
    single_malt: list[GrainInput] = [
        {"name": "Pale Malt", "ppg": 37, "color_ebc": 5.0, "pct": 100.0}
    ]
    with pytest.raises(ValueError, match="Exactly one"):
        calculate_grain_bill(
            batch_liters=20.0,
            efficiency_pct=75.0,
            yeast_attenuation_pct=75.0,
            grain_inputs=single_malt,
        )


def test_calculate_grain_bill_multiple_targets_raises() -> None:
    single_malt: list[GrainInput] = [
        {"name": "Pale Malt", "ppg": 37, "color_ebc": 5.0, "pct": 100.0}
    ]
    with pytest.raises(ValueError, match="Exactly one"):
        calculate_grain_bill(
            batch_liters=20.0,
            efficiency_pct=75.0,
            yeast_attenuation_pct=75.0,
            grain_inputs=single_malt,
            target_abv=5.0,
            target_og=1.050,
        )


def test_calculate_grain_bill_full_attenuation_with_target_fg_raises() -> None:
    with pytest.raises(ValueError, match="less than 100"):
        calculate_grain_bill(
            batch_liters=20.0,
            efficiency_pct=75.0,
            yeast_attenuation_pct=100.0,
            grain_inputs=[
                {"name": "Pale Malt", "ppg": 37, "color_ebc": 5.0, "pct": 100.0}
            ],
            target_fg=1.010,
        )


# ---------------------------------------------------------------------------
# calculate_hop_schedule
# ---------------------------------------------------------------------------


def test_calculate_hop_schedule_single_boil_hit_target_ibu() -> None:
    # EKG 5% / 60 min / OG 1.035 / 40 L / target 30 IBU → verified ~91 g
    ekg: list[HopAdditionInput] = [
        {
            "name": "EKG",
            "alpha_pct": 5.0,
            "time_min": 60,
            "use": "boil",
            "ibu_pct": 100.0,
        },
    ]
    result = calculate_hop_schedule(
        target_ibu=30.0,
        og=1.035,
        batch_liters=40.0,
        hop_inputs=ekg,
    )
    assert abs(result["total_ibu"] - 30.0) < 0.5
    assert len(result["hops"]) == 1
    assert abs(result["hops"][0]["amount_g"] - 90.9) < 2.0


def test_calculate_hop_schedule_total_ibu_matches_forward_tinseth() -> None:
    # Two boil additions split 60/40 across Cascade and Centennial.
    hops: list[HopAdditionInput] = [
        {
            "name": "Cascade",
            "alpha_pct": 5.5,
            "time_min": 60,
            "use": "boil",
            "ibu_pct": 60.0,
        },
        {
            "name": "Centennial",
            "alpha_pct": 10.0,
            "time_min": 15,
            "use": "boil",
            "ibu_pct": 40.0,
        },
    ]
    result = calculate_hop_schedule(
        target_ibu=40.0,
        og=1.050,
        batch_liters=20.0,
        hop_inputs=hops,
    )
    assert abs(result["total_ibu"] - 40.0) < 1.0
    assert len(result["hops"]) == 2


def test_calculate_hop_schedule_non_boil_passes_through() -> None:
    # Dry-hop should not contribute IBU; amount defaults to 20 g.
    hops: list[HopAdditionInput] = [
        {
            "name": "Cascade",
            "alpha_pct": 5.5,
            "time_min": 60,
            "use": "boil",
            "ibu_pct": 100.0,
        },
        {
            "name": "Citra",
            "alpha_pct": 12.0,
            "time_min": 0,
            "use": "dry-hop",
            "ibu_pct": 0.0,
        },
    ]
    result = calculate_hop_schedule(
        target_ibu=25.0,
        og=1.045,
        batch_liters=20.0,
        hop_inputs=hops,
    )
    dry_hop = next(h for h in result["hops"] if h["use"] == "dry-hop")
    assert dry_hop["amount_g"] == pytest.approx(20.0)
    # total_ibu should only reflect the boil hop
    assert abs(result["total_ibu"] - 25.0) < 1.0


def test_calculate_hop_schedule_zero_ibu_pct_gives_zero_grams() -> None:
    # A boil hop with ibu_pct=0 should result in 0g (LLM may send this pattern).
    hops: list[HopAdditionInput] = [
        {
            "name": "Magnum",
            "alpha_pct": 12.0,
            "time_min": 60,
            "use": "boil",
            "ibu_pct": 0.0,
        },
    ]
    result = calculate_hop_schedule(
        target_ibu=30.0,
        og=1.050,
        batch_liters=20.0,
        hop_inputs=hops,
    )
    assert result["hops"][0]["amount_g"] == pytest.approx(0.0)


def test_calculate_hop_schedule_non_boil_explicit_amount() -> None:
    hops: list[HopAdditionInput] = [
        {
            "name": "EKG",
            "alpha_pct": 5.0,
            "time_min": 60,
            "use": "boil",
            "ibu_pct": 100.0,
        },
        {
            "name": "Saaz",
            "alpha_pct": 3.5,
            "time_min": 0,
            "use": "dry-hop",
            "ibu_pct": 0.0,
            "amount_g": 50.0,
        },
    ]
    result = calculate_hop_schedule(
        target_ibu=20.0,
        og=1.040,
        batch_liters=20.0,
        hop_inputs=hops,
    )
    dry_hop = next(h for h in result["hops"] if h["use"] == "dry-hop")
    assert dry_hop["amount_g"] == pytest.approx(50.0)
