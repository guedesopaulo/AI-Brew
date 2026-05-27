"""Recipe domain TypedDicts."""

from typing import NotRequired
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
    use: str  # MUST be one of: boil | whirlpool | dry-hop


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
    equipment_id: NotRequired[str]


class RecipePatch(TypedDict, total=False):
    name: str
    style: str
    batch_size_liters: float
    fermentables: list[Fermentable]
    hops: list[Hop]
    yeast: Yeast
    equipment_id: str


class RecipeWithStats(Recipe):
    calculated: CalculatedStats


class SensoryProfile(TypedDict):
    aroma: str
    flavor: str
    mouthfeel: str
    appearance: str


class BrewNotes(TypedDict):
    content: str


class Style(TypedDict):
    name: str
    category: str
    og_min: float
    og_max: float
    fg_min: float
    fg_max: float
    ibu_min: float
    ibu_max: float
    srm_min: float
    srm_max: float
    abv_min: float
    abv_max: float
    description: str


class GrainInput(TypedDict):
    name: str
    ppg: int
    pct: float  # share of total grain bill; all pct values must sum to 100


class GrainOutput(TypedDict):
    name: str
    amount_kg: float


class GrainBillRequest(TypedDict):
    target_abv: float
    batch_liters: float
    efficiency_pct: float
    yeast_attenuation_pct: float
    grain_inputs: list[GrainInput]


class GrainBillResult(TypedDict):
    target_og: float
    target_og_points: float
    total_grain_kg: float
    fermentables: list[GrainOutput]


class HopAdditionInput(TypedDict):
    name: str
    alpha_pct: float
    time_min: int
    use: str  # "boil" | "whirlpool" | "dry-hop"
    ibu_pct: float  # share of total IBU; sum to 100 across boil hops; 0 for non-boil
    amount_g: NotRequired[float]  # non-boil hops only; boil hops use inverse Tinseth


class HopAdditionOutput(TypedDict):
    name: str
    amount_g: float
    alpha_pct: float
    time_min: int
    use: str


class HopAdditionRequest(TypedDict):
    target_ibu: float
    og: float
    batch_liters: float
    hop_inputs: list[HopAdditionInput]


class HopScheduleResult(TypedDict):
    total_ibu: float
    hops: list[HopAdditionOutput]
