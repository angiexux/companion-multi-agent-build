"""Quick smoke test: run LoreAgent on Dracula and print the result."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.lore_agent import run_lore_agent
from character.manager import save_bio

DRACULA_PROMPT = """
Count Dracula — ancient Romanian vampire lord, aristocratic and predatory, 500+ years old.
Originally Vlad Dracul III of Transylvania. Speaks with Victorian formal gravitas.
Obsessed with immortal dominion and worthy prey. Fears sunlight, sacred symbols, and mirrors.
Craves worthy adversaries and has an aching fear of being the last of his kind.
Impeccably dressed, moves with preternatural stillness. Commands loyalty through terror and fascination.
"""


async def main():
    print("Running LoreAgent on Dracula prompt...\n")
    profile = await run_lore_agent(DRACULA_PROMPT)
    print(json.dumps(profile.model_dump(), indent=2))
    path = save_bio(profile)
    print(f"\nSaved to: {path}")


if __name__ == "__main__":
    asyncio.run(main())
