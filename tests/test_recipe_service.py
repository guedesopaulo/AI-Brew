"""Unit tests for recipe calculation functions."""

import pytest

from src.models.recipe import Fermentable
from src.models.recipe import Hop
from src.models.recipe import Recipe
from src.models.recipe import Yeast
from src.service.recipe import calc_abv
from src.service.recipe import calc_fg
from src.service.recipe import calc_ibu_tinseth
from src.service.recipe import calc_og
from src.service.recipe import calc_srm_morey
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
        ([PALE_MALT], 20.0, 1.0618),
        ([PALE_MALT, CRYSTAL_60], 20.0, 1.0686),
        ([PALE_MALT], 40.0, 1.0309),
    ],
)
def test_calc_og(
    fermentables: list[Fermentable], batch_liters: float, expected: float
) -> None:
    result = calc_og(fermentables, batch_liters)
    assert abs(result - expected) < 0.001


def test_calc_og_empty_fermentables() -> None:
    assert calc_og([], 20.0) == 1.0


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
    assert set(stats.keys()) == {"og", "fg", "abv", "ibu", "srm"}


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


def test_calculate_stats_srm_positive() -> None:
    stats = calculate_stats(SIMPLE_RECIPE)
    assert stats["srm"] > 0
