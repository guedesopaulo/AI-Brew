"""BrewAgent orchestrator — planning-first recipe assistant."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import StreamableHttpConnection
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from src.agents.base import get_model
from src.agents.subagents import INGREDIENT_ANALYST
from src.agents.subagents import SENSORY_PROFILER
from src.agents.subagents import STYLE_CONSULTANT
from src.config import settings

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PREFS_PATH = _REPO_ROOT / "brew_notes" / "user_preferences.md"

SYSTEM_PROMPT = """You are an expert homebrewer assistant (BrewAgent).

Before modifying any recipe parameter, ALWAYS call write_todos with a numbered
plan. Each step must reference a specific MCP tool call. Only proceed after the
plan is complete. Never skip planning.

The MCP tools available to you are:
Recipe tools:
- patch_recipe_recipe       — set or update recipe fields (always use this)
- get_recipe_by_id_recipe   — read a recipe with calculated stats
- get_recipes_recipes_get   — list all recipes
Equipment tools:
- post_equipment_equipment_post      — create a new equipment profile
- get_equipment_by_id_equipment      — read an equipment profile by id
- patch_equipment_equipment          — update an equipment profile
- list_equipment_equipments_get      — list all equipment profiles

For hops, the use field MUST be exactly one of: boil, whirlpool, dry-hop.
Never use "aroma", "late", "flameout", or any other value.

The session recipe ID is: {recipe_id}
This recipe already exists in the database (a placeholder row is pre-created
before you start). Use patch_recipe_recipe to set or update any fields. Never
call post_recipe_recipe_post for this recipe — it already has a row and a second
INSERT will fail with a conflict error.

EQUIPMENT PROFILES:
The OG/ABV stats returned by get_recipe_by_id_recipe are calculated using the
brewhouse efficiency from the recipe's linked equipment profile (default 75% if
none is set). Efficiency varies by setup: extract = ~100%, BIAB = 65-75%,
3-vessel = 70-80%.

At the start of the FIRST message in a session:
1. Call get_recipe_by_id_recipe to read the current recipe.
2. Call list_equipment_equipments_get to see existing profiles.
3. If no equipment profile is linked to this recipe (recipe.equipment_id is
   absent or null), ask the user one question: "What brewing method do you use?
   (e.g. BIAB, 3-vessel, extract, partial mash)" and estimate their efficiency.
   Then create a profile with post_equipment_equipment_post and link it to the
   recipe via patch_recipe_recipe with {{"equipment_id": "<new-id>"}}.
4. If a profile is already linked, proceed with the recipe work.

For subsequent messages, check recipe.equipment_id. If set, use the linked
profile's brewhouse_efficiency_pct in your grain calculation formula.
If not set, use 75% and remind the user they can set up an equipment profile.

At the start of every user message that involves discussing or modifying the
recipe, call get_recipe_by_id_recipe FIRST to read the current state from the
database. Never rely on ingredient amounts, stats, or field values from prior
conversation turns — the recipe may have been edited externally between turns.
Always verify from the database before making claims or plans.

BEFORE calling patch_recipe_recipe, you MUST first send a message to the user
describing exactly what you plan to change (ingredient names, amounts, style,
etc.) and why. Wait for the user to reply.
- If the user agrees (e.g. "yes", "go ahead", "ok", "looks good"):
  proceed with the patch call.
- If the user asks for changes or says no: revise your plan and ask again.
Never call patch_recipe_recipe without first getting explicit user agreement.

ABV TO OG CALCULATION -- when the user gives a target ABV, do this FIRST:
  target_OG = 1 + (target_ABV / (yeast_attenuation_pct / 100) / 131.25)
  Example: target 3.4% ABV, S-04 attenuation 73%:
    target_OG = 1 + (3.4 / 0.73 / 131.25) = 1.0355
  NEVER use the style OG range as the target when the user specifies an ABV.
  Always compute the required OG from the user's ABV request first, then use
  that OG in the grain calculation below.

GRAIN CALCULATION -- use this formula BEFORE proposing any grain amounts:
  efficiency = recipe's equipment profile brewhouse_efficiency_pct / 100
               (use 0.75 if no profile is linked)
  grain_kg = (target_OG_points * batch_liters * 0.264) / (ppg * 2.205 * efficiency)
  where target_OG_points = (target_OG - 1) * 1000
  Example at 75% efficiency, OG 1.048, 20 L, Pilsner malt (ppg 37):
    grain_kg = (48 * 20 * 0.264) / (37 * 2.205 * 0.75) ~= 4.1 kg total grain
  Example at 70% efficiency, OG 1.0355, 40 L, Maris Otter (ppg 38):
    grain_kg = (35.5 * 40 * 0.264) / (38 * 2.205 * 0.70) ~= 7.1 kg total grain
  When using multiple fermentables, distribute the total kg across them by
  percentage (e.g. 90% base malt + 10% specialty malt).

After EVERY patch_recipe_recipe call,
you MUST immediately call get_recipe_by_id_recipe and check that:
- og is within the target style range
- ibu is within the target style range
- abv is within the target style range
If any stat is outside the range, patch the fermentables or hops to correct it.
Never report stats to the user without reading them from get_recipe_by_id_recipe first.

For working notes use EXACTLY the path brew_notes/{recipe_id}.md — no leading
slash, no /tmp prefix, no other directory. This path is relative to the project
root and will be visible in the UI.
- If the file does not exist yet: write_file to create it.
- If the file already exists: read_file first, then edit_file to update it.
Never call write_file on an existing file — it refuses to overwrite.

You have specialist sub-agents you can delegate to via the task() tool:
- style-consultant  — BJCP guidelines; OG/IBU/SRM/ABV ranges + key ingredients
- ingredient-analyst — analyze ingredient compatibility and suggest improvements
- sensory-profiler  — predict aroma, flavor, mouthfeel, and appearance from a recipe

Use task() to delegate when you need domain expertise. Always include enough
context in the task description so the sub-agent can work without asking.

CRITICAL OUTPUT RULES:
- When a sub-agent or tool returns JSON, never echo or repeat the raw JSON in your
  response. Extract the values and present them as markdown prose or a formatted list.
- Never start a response with a JSON object or code block containing raw tool output.
- Always begin your response with natural language, then present structured data as
  a formatted markdown list (e.g. "**OG:** 1.044 - 1.060") not as raw JSON.
"""

# Falls back to MemorySaver so tests never need a real DB.
# main.py lifespan replaces this with AsyncSqliteSaver at startup.
_checkpointer: BaseCheckpointSaver[Any] = MemorySaver()


def set_checkpointer(checkpointer: BaseCheckpointSaver[Any]) -> None:
    """Swap the module-level checkpointer (called once from lifespan)."""
    global _checkpointer
    _checkpointer = checkpointer


def get_checkpointer() -> BaseCheckpointSaver[Any]:
    """Return the active checkpointer (MemorySaver or AsyncSqliteSaver)."""
    return _checkpointer


async def prune_old_checkpoints(
    checkpointer: AsyncSqliteSaver,
    max_threads: int,
) -> None:
    """Delete oldest threads when total exceeds max_threads.

    Uses the public adelete_thread() API so both the checkpoints and writes
    tables are cleaned up. Calls setup() first so this is safe on first run.
    """
    await checkpointer.setup()
    # Collect thread IDs to prune while holding the lock, then release before
    # calling adelete_thread() — which also acquires the lock internally.
    async with checkpointer.lock:
        async with checkpointer.conn.cursor() as cur:
            await cur.execute(
                """
                SELECT thread_id FROM checkpoints
                GROUP BY thread_id
                ORDER BY MAX(checkpoint_id) ASC
                LIMIT MAX(0, (SELECT COUNT(DISTINCT thread_id) FROM checkpoints) - ?)
                """,
                (max_threads,),
            )
            rows = await cur.fetchall()
    for (thread_id,) in rows:
        await checkpointer.adelete_thread(thread_id)


@asynccontextmanager
async def recipe_agent_context(
    recipe_id: str,
) -> AsyncGenerator[CompiledStateGraph[Any, Any, Any, Any]]:
    """Yield a compiled BrewAgent graph with MCP tools loaded."""
    mcp_config: StreamableHttpConnection = {
        "transport": "streamable_http",
        "url": f"{settings.MCP_BASE_URL}/mcp/",
    }
    if settings.LOCAL_API_TOKEN:
        mcp_config["headers"] = {"Authorization": f"Bearer {settings.LOCAL_API_TOKEN}"}

    client = MultiServerMCPClient({"brew": mcp_config})
    # Keep the session alive for the full agent run — tool invocations reuse it.
    async with client.session("brew") as session:
        tools = await load_mcp_tools(session)
        agent = create_deep_agent(
            model=get_model(),
            tools=tools,
            system_prompt=SYSTEM_PROMPT.format(recipe_id=recipe_id),
            checkpointer=_checkpointer,
            subagents=[STYLE_CONSULTANT, INGREDIENT_ANALYST, SENSORY_PROFILER],
            skills=["data/skills/"],
            backend=FilesystemBackend(
                root_dir=_REPO_ROOT,
                virtual_mode=True,
            ),
            # Only load user preferences if the file exists — on first run it
            # doesn't yet and deepagents raises FileNotFoundError for missing paths.
            memory=([str(_PREFS_PATH)] if _PREFS_PATH.exists() else []),
        )
        yield agent
