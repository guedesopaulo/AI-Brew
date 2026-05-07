"""Sub-agent definitions for BrewAgent task delegation."""

from deepagents import SubAgent

from src.models.recipe import SensoryProfile

STYLE_CONSULTANT: SubAgent = {
    "name": "style-consultant",
    "description": (
        "Consult BJCP guidelines for a given beer style. "
        "Returns JSON with OG/IBU/SRM/ABV ranges and key ingredient recommendations."
    ),
    "system_prompt": (
        "You are a BJCP-certified style consultant.\n"
        "Read the bjcp-styles/SKILL.md file first.\n"
        "Return ONLY this JSON — no prose, no explanation:\n"
        '{"og_range":[min,max],"ibu_range":[min,max],"srm_range":[min,max],'
        '"abv_range":[min,max],"key_malts":[...],"key_hops":[...],"yeast_notes":"..."}'
    ),
    "tools": [],
    "skills": ["data/skills/bjcp-styles/"],
}

INGREDIENT_ANALYST: SubAgent = {
    "name": "ingredient-analyst",
    "description": (
        "Analyze ingredient compatibility and suggest improvements for a given recipe. "
        "Given fermentables, hops, and yeast; returns flavor profile and suggestions."
    ),
    "system_prompt": (
        "You are a brewing ingredient specialist.\n"
        "Read hop-pairing/SKILL.md and yeast-profiles/SKILL.md first.\n"
        "Return ONLY this JSON — no prose:\n"
        '{"flavor_profile":[...],"balance_notes":"...",'
        '"suggested_additions":[{"ingredient":"...","reason":"..."}],"warnings":[...]}'
    ),
    "tools": [],
    "skills": [
        "data/skills/hop-pairing/",
        "data/skills/yeast-profiles/",
        "data/skills/ingredient-substitutions/",
    ],
}

SENSORY_PROFILER: SubAgent = {
    "name": "sensory-profiler",
    "description": (
        "Predict the sensory profile (aroma, flavor, mouthfeel, appearance) "
        "of a beer given its recipe ingredients and calculated stats."
    ),
    "system_prompt": (
        "You are a sensory evaluation specialist.\n"
        "Read hop-pairing/SKILL.md and yeast-profiles/SKILL.md.\n"
        "Given recipe ingredients and calculated stats, produce a sensory prediction."
    ),
    "tools": [],
    "skills": ["data/skills/hop-pairing/", "data/skills/yeast-profiles/"],
    "response_format": SensoryProfile,
}
