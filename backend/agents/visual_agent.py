import os
import httpx
from pathlib import Path

import fal_client
from google import genai
from google.genai import types
from dotenv import load_dotenv

from models import CharacterProfile, VisualPrompt
from character.manager import character_dir

load_dotenv()

_SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "visual_system.txt").read_text()

_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def _profile_to_prompt(profile: CharacterProfile) -> str:
    return f"""CharacterProfile:
Name: {profile.name}
Archetype: {profile.archetype}
Age: {profile.age}
Origin: {profile.origin}
Appearance: {profile.appearance}
Personality: {', '.join(profile.personality)}
Backstory: {profile.backstory}

Generate an image generation prompt for this character's portrait."""


async def _write_image_prompt(profile: CharacterProfile) -> VisualPrompt:
    response = _client.models.generate_content(
        model="gemini-2.0-flash",
        contents=_profile_to_prompt(profile),
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=VisualPrompt,
            temperature=0.7,
        ),
    )
    return VisualPrompt.model_validate_json(response.text)


async def _generate_image(visual_prompt: VisualPrompt, character_id: str) -> Path:
    result = fal_client.subscribe(
        "fal-ai/flux/dev",
        arguments={
            "prompt": visual_prompt.prompt,
            "negative_prompt": visual_prompt.negative_prompt,
            "image_size": "square_hd",
            "num_images": 1,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
        },
    )

    image_url = result["images"][0]["url"]

    async with httpx.AsyncClient() as http:
        r = await http.get(image_url)
        r.raise_for_status()

    out_path = character_dir(character_id) / "portrait.png"
    out_path.write_bytes(r.content)
    return out_path


async def run_visual_agent(profile: CharacterProfile) -> tuple[VisualPrompt, Path]:
    """Returns (VisualPrompt used, path to saved portrait.png)."""
    visual_prompt = await _write_image_prompt(profile)
    portrait_path = await _generate_image(visual_prompt, profile.id)
    return visual_prompt, portrait_path
