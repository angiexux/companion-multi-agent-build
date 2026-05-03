"""
Smoke test: LoreAgent → DialogueStyleAgent pipeline.
Generates bio.json + style_guide.md for Dracula and prints both.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.lore_agent import run_lore_agent
from agents.dialogue_agent import run_dialogue_agent
from character.manager import save_bio, save_style_guide

DRACULA_PROMPT = """
Count Dracula — ancient Romanian vampire lord, aristocratic and predatory, 500+ years old.
Originally Vlad Dracul III of Transylvania. Speaks with Victorian formal gravitas.
Obsessed with immortal dominion and worthy prey. Fears sunlight, sacred symbols, and mirrors.
Craves worthy adversaries and has an aching fear of being the last of his kind.
Impeccably dressed, moves with preternatural stillness. Commands loyalty through terror and fascination.
"""


async def main():
    print("=== LoreAgent ===")
    profile = await run_lore_agent(DRACULA_PROMPT)
    bio_path = save_bio(profile)
    print(json.dumps(profile.model_dump(), indent=2))
    print(f"\nSaved → {bio_path}")

    print("\n=== DialogueStyleAgent ===")
    output, style_md = await run_dialogue_agent(profile)
    style_path = save_style_guide(profile.id, style_md)
    print(f"\nIntroduction text:\n  {output.introduction_text}")
    print(f"\nStyle guide saved → {style_path}")
    print(f"\n--- style_guide.md preview ---\n{style_md[:600]}...")


if __name__ == "__main__":
    asyncio.run(main())
