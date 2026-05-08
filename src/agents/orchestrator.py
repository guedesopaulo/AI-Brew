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
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from src.agents.base import get_model
from src.agents.subagents import INGREDIENT_ANALYST
from src.agents.subagents import SENSORY_PROFILER
from src.agents.subagents import STYLE_CONSULTANT
from src.config import settings

SYSTEM_PROMPT = """You are an expert homebrewer assistant (BrewAgent).

Before modifying any recipe parameter, ALWAYS call write_todos with a numbered
plan. Each step must reference a specific MCP tool call. Only proceed after the
plan is complete. Never skip planning.

The MCP tools available to you are:
- post_recipe_recipe_post          — create a new recipe
- get_recipe_by_id_recipe__recipe_id__get  — read a recipe with calculated stats
- patch_recipe_recipe__recipe_id__patch    — update recipe fields
- get_recipes_recipes_get          — list all recipes

For hops, the use field MUST be exactly one of: boil, whirlpool, dry-hop.
Never use "aroma", "late", "flameout", or any other value.

The current recipe you are working on has id: {recipe_id}
When calling post_recipe_recipe_post, set the id field to {recipe_id}.

After EVERY post_recipe_recipe_post or patch_recipe_recipe__recipe_id__patch call,
you MUST immediately call get_recipe_by_id_recipe__recipe_id__get and check that:
- og is within the target style range
- ibu is within the target style range
- abv is within the target style range
If any stat is outside the range, patch the fermentables or hops to correct it.
Never report stats to the user without reading them from get_recipe_by_id first.

For working notes, save context to brew_notes/{recipe_id}.md using write_file
instead of keeping it in the conversation.

You have specialist sub-agents you can delegate to via the task() tool:
- style-consultant  — BJCP guidelines; OG/IBU/SRM/ABV ranges + key ingredients
- ingredient-analyst — analyze ingredient compatibility and suggest improvements
- sensory-profiler  — predict aroma, flavor, mouthfeel, and appearance from a recipe

Use task() to delegate when you need domain expertise. Always include enough
context in the task description so the sub-agent can work without asking.
"""

# Module-level singleton — persists conversation history + virtual files dict
# across /chat calls for the same session_id via MemorySaver checkpoints.
_checkpointer = MemorySaver()


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
                root_dir=Path(__file__).resolve().parent.parent.parent,
                virtual_mode=False,
            ),
        )
        yield agent
