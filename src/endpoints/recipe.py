"""Recipe CRUD endpoints."""

import json
from pathlib import Path

from fastapi import APIRouter
from fastapi import HTTPException
from langchain_core.messages import HumanMessage

from src.agents.orchestrator import recipe_agent_context
from src.config import settings
from src.models.recipe import BrewNotes
from src.models.recipe import Recipe
from src.models.recipe import RecipePatch
from src.models.recipe import RecipeWithStats
from src.models.recipe import SensoryProfile
from src.models.recipe import Style
from src.resources.recipe import create_recipe
from src.resources.recipe import get_recipe
from src.resources.recipe import list_recipes
from src.resources.recipe import update_recipe
from src.service.recipe import calculate_stats

router = APIRouter(prefix="/recipe", tags=["recipe"])

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_STYLES: list[Style] = json.loads(
    (_REPO_ROOT / "src" / "data" / "styles.json").read_text()
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
    return {**recipe, "calculated": calculate_stats(recipe)}


@router.patch("/{recipe_id}")
async def patch_recipe(recipe_id: str, patch: RecipePatch) -> RecipeWithStats:
    updated = await update_recipe(recipe_id, patch, settings.DB_PATH)
    if updated is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {**updated, "calculated": calculate_stats(updated)}


@router.get("s")
async def get_recipes() -> list[RecipeWithStats]:
    recipes = await list_recipes(settings.DB_PATH)
    return [{**r, "calculated": calculate_stats(r)} for r in recipes]


@router.get("/{recipe_id}/notes")
async def get_recipe_notes(recipe_id: str) -> BrewNotes:
    path = _REPO_ROOT / "brew_notes" / f"{recipe_id}.md"
    return {"content": path.read_text() if path.exists() else ""}


@router.get("s/styles")
async def get_styles() -> list[Style]:
    return _STYLES


@router.get("/{recipe_id}/profile")
async def get_recipe_profile(recipe_id: str) -> SensoryProfile:
    recipe = await get_recipe(recipe_id, settings.DB_PATH)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    stats = calculate_stats(recipe)
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
