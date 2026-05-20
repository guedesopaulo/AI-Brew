"""Recipe CRUD endpoints."""

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Response
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage

from src.agents.orchestrator import get_checkpointer
from src.agents.orchestrator import recipe_agent_context
from src.config import settings
from src.models.chat import HistoryMessage
from src.models.equipment import EquipmentProfile
from src.models.recipe import BrewNotes
from src.models.recipe import GrainBillRequest
from src.models.recipe import GrainBillResult
from src.models.recipe import Recipe
from src.models.recipe import RecipePatch
from src.models.recipe import RecipeWithStats
from src.models.recipe import SensoryProfile
from src.models.recipe import Style
from src.resources.equipment import get_equipment_profile
from src.resources.equipment import get_equipment_profiles_by_ids
from src.resources.recipe import clone_recipe
from src.resources.recipe import create_recipe
from src.resources.recipe import delete_recipe
from src.resources.recipe import get_recipe
from src.resources.recipe import list_recipes
from src.resources.recipe import update_recipe
from src.service.recipe import DEFAULT_EFFICIENCY_PCT
from src.service.recipe import calculate_grain_bill
from src.service.recipe import calculate_stats

router = APIRouter(prefix="/recipe", tags=["recipe"])

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_STYLES: list[Style] = json.loads(
    (_REPO_ROOT / "src" / "data" / "styles.json").read_text()
)


async def _resolve_efficiency(recipe: Recipe) -> float:
    """Return brewhouse efficiency from the recipe's linked equipment profile."""
    if equip_id := recipe.get("equipment_id"):
        profile: EquipmentProfile | None = await get_equipment_profile(
            equip_id, settings.DB_PATH
        )
        if profile:
            return profile["brewhouse_efficiency_pct"]
    return DEFAULT_EFFICIENCY_PCT


@router.post("/grain-bill", operation_id="calculate_grain_bill")
async def calculate_grain_bill_endpoint(body: GrainBillRequest) -> GrainBillResult:
    """Calculate exact grain amounts for a target ABV."""
    return calculate_grain_bill(
        target_abv=body["target_abv"],
        batch_liters=body["batch_liters"],
        efficiency_pct=body["efficiency_pct"],
        yeast_attenuation_pct=body["yeast_attenuation_pct"],
        grain_inputs=body["grain_inputs"],
    )


@router.post("", status_code=201)
async def post_recipe(recipe: Recipe) -> dict[str, str]:
    recipe_id = await create_recipe(recipe, settings.DB_PATH)
    return {"id": recipe_id}


@router.get("/{recipe_id}")
async def get_recipe_by_id(recipe_id: str) -> RecipeWithStats:
    recipe = await get_recipe(recipe_id, settings.DB_PATH)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    eff = await _resolve_efficiency(recipe)
    return {**recipe, "calculated": calculate_stats(recipe, eff)}


@router.patch("/{recipe_id}")
async def patch_recipe(recipe_id: str, patch: RecipePatch) -> RecipeWithStats:
    updated = await update_recipe(recipe_id, patch, settings.DB_PATH)
    if updated is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    eff = await _resolve_efficiency(updated)
    return {**updated, "calculated": calculate_stats(updated, eff)}


@router.post("/{recipe_id}/clone", status_code=201)
async def clone_recipe_by_id(recipe_id: str) -> dict[str, str]:
    new_id = await clone_recipe(recipe_id, settings.DB_PATH)
    if new_id is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"id": new_id}


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe_by_id(recipe_id: str) -> Response:
    deleted = await delete_recipe(recipe_id, settings.DB_PATH)
    if not deleted:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return Response(status_code=204)


@router.get("s")
async def get_recipes() -> list[RecipeWithStats]:
    recipes = await list_recipes(settings.DB_PATH)
    # Batch-fetch equipment profiles to avoid N+1 queries.
    equip_ids = [r["equipment_id"] for r in recipes if r.get("equipment_id")]
    profiles = await get_equipment_profiles_by_ids(equip_ids, settings.DB_PATH)
    result: list[RecipeWithStats] = []
    for r in recipes:
        eff = DEFAULT_EFFICIENCY_PCT
        if (eid := r.get("equipment_id")) and eid in profiles:
            eff = profiles[eid]["brewhouse_efficiency_pct"]
        result.append({**r, "calculated": calculate_stats(r, eff)})
    return result


@router.get("/{recipe_id}/notes")
async def get_recipe_notes(recipe_id: str) -> BrewNotes:
    path = _REPO_ROOT / "brew_notes" / f"{recipe_id}.md"
    return {"content": path.read_text() if path.exists() else ""}


@router.get("s/styles")
async def get_styles() -> list[Style]:
    return _STYLES


@router.get("/{recipe_id}/history")
async def get_recipe_history(recipe_id: str, session_id: str) -> list[HistoryMessage]:
    if await get_recipe(recipe_id, settings.DB_PATH) is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    cp = get_checkpointer()
    tup = await cp.aget_tuple({"configurable": {"thread_id": session_id}})
    if tup is None:
        return []
    messages = tup.checkpoint.get("channel_values", {}).get("messages", [])
    result: list[HistoryMessage] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": str(msg.content)})
        elif isinstance(msg, AIMessage):
            raw = msg.content
            if isinstance(raw, str):
                text: str | None = raw
            else:
                text = next(
                    (
                        b.get("text")
                        for b in raw
                        if isinstance(b, dict) and b.get("type") == "text"
                    ),
                    None,
                )
            if text and text.strip():
                result.append({"role": "assistant", "content": text})
    return result


@router.get("/{recipe_id}/profile")
async def get_recipe_profile(recipe_id: str) -> SensoryProfile:
    recipe = await get_recipe(recipe_id, settings.DB_PATH)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    eff = await _resolve_efficiency(recipe)
    stats = calculate_stats(recipe, eff)
    prompt = (
        f"Generate a sensory profile for recipe {recipe_id}. "
        f"Fermentables: {recipe['fermentables']}. "
        f"Hops: {recipe['hops']}. "
        f"Yeast: {recipe['yeast']}. "
        f"Calculated stats: OG={stats['og']:.3f}, IBU={stats['ibu']:.1f}, "
        f"SRM={stats['srm']:.1f}, ABV={stats['abv']:.1f}%. "
        "Delegate to the sensory-profiler sub-agent."
    )
    async with recipe_agent_context(recipe_id) as agent:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=prompt)]},
            config={"configurable": {"thread_id": f"profile-{recipe_id}"}},
        )
    # Scan messages in reverse: the JSON lives in a ToolMessage from the
    # task() call, not necessarily the final AIMessage (which may be empty
    # when the orchestrator considers its job done after delegation).
    profile_keys = {"aroma", "flavor", "mouthfeel", "appearance"}
    for msg in reversed(result["messages"]):
        raw = msg.content
        if isinstance(raw, str):
            text: str | None = raw
        else:
            text = next(
                (b.get("text") for b in raw if b.get("type") == "text"),
                None,
            )
        if not text:
            continue
        try:
            data = json.loads(text)
            if profile_keys.issubset(data.keys()):
                return data
        except (json.JSONDecodeError, AttributeError):
            continue
    raise HTTPException(
        status_code=422, detail="Agent did not return a sensory profile"
    )
