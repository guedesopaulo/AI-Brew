"""Recipe domain TypedDicts."""

from typing import TypedDict


class Fermentable(TypedDict):
    name: str
    amount_kg: float
    color_ebc: float
    ppg: float


class Hop(TypedDict):
    name: str
    amount_g: float
    alpha_pct: float
    time_min: int
    use: str  # boil | whirlpool | dry-hop


class Yeast(TypedDict):
    name: str
    attenuation_pct: float
    min_temp_c: float
    max_temp_c: float


class CalculatedStats(TypedDict):
    og: float
    fg: float
    abv: float
    ibu: float
    srm: float


class Recipe(TypedDict):
    id: str
    name: str
    style: str
    batch_size_liters: float
    fermentables: list[Fermentable]
    hops: list[Hop]
    yeast: Yeast


class RecipePatch(TypedDict, total=False):
    name: str
    style: str
    batch_size_liters: float
    fermentables: list[Fermentable]
    hops: list[Hop]
    yeast: Yeast


class RecipeWithStats(Recipe):
    calculated: CalculatedStats


class SensoryProfile(TypedDict):
    aroma: str
    flavor: str
    mouthfeel: str
    appearance: str
