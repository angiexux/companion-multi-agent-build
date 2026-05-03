"""
Full pipeline smoke test: Lore → Dialogue → Visual + Voice (parallel).
Generates all 4 artifacts for Dracula.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.lore_agent import run_lore_agent
from agents.dialogue_agent import run_dialogue_agent
from agents.visual_agent import run_visual_agent
from agents.voice_agent import run_voice_agent
from character.manager import save_bio, save_style_guide, save_voice_config

DRACULA_PROMPT = """
Count Dracula — ancient Romanian vampire lord, aristocratic and predatory, 500+ years old.
Originally Vlad Dracul III of Transylvania. Speaks with Victorian formal gravitas.
Obsessed with immortal dominion and worthy prey. Fears sunlight, sacred symbols, and mirrors.
Craves worthy adversaries and has an aching fear of being the last of his kind.
Impeccably dressed, moves with preternatural stillness. Commands loyalty through terror and fascination.
"""


async def main():
    print("=== [1/4] LoreAgent ===")
    profile = await run_lore_agent(DRACULA_PROMPT)
    save_bio(profile)
    print(f"  {profile.name} ({profile.archetype})")
    print(f"  bio.json saved")

    print("\n=== [2/4] DialogueStyleAgent ===")
    dialogue_output, style_md = await run_dialogue_agent(profile)
    save_style_guide(profile.id, style_md)
    print(f"  style_guide.md saved")
    print(f"  Intro: {dialogue_output.introduction_text[:80]}...")

    print("\n=== [3+4/4] VisualAgent + VoiceAgent (parallel) ===")
    visual_task = run_visual_agent(profile)
    voice_task = run_voice_agent(profile, dialogue_output)

    (visual_prompt, portrait_path), (voice_config, voice_path) = await asyncio.gather(
        visual_task, voice_task
    )
    save_voice_config(profile.id, voice_config)

    print(f"  portrait.png saved → {portrait_path}")
    print(f"  voice_sample.mp3 saved → {voice_path}")
    print(f"  Voice: {voice_config.voice_name} (stability={voice_config.stability})")
    print(f"  Reason: {voice_config.reasoning}")

    print(f"\n=== Done ===")
    print(f"  All artifacts in: characters/{profile.id}/")


if __name__ == "__main__":
    asyncio.run(main())
