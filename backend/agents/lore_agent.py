import os
import re
from pathlib import Path
from datetime import datetime, timezone

from google import genai
from google.genai import types
from dotenv import load_dotenv

from models import CharacterProfile

load_dotenv()

_SYSTEM_PROMPT = (Path(__file__).parent.parent / "prompts" / "lore_system.txt").read_text()

_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])


def _make_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"{slug}_001"


async def run_lore_agent(prompt: str) -> CharacterProfile:
    """Generate a CharacterProfile from a free-text character description."""
    response = _client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Create a character profile for:\n\n{prompt}",
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=CharacterProfile,
            temperature=0.85,
        ),
    )

    profile = CharacterProfile.model_validate_json(response.text)

    # Ensure id and created_at are set correctly regardless of what the model wrote
    name_slug = _make_id(profile.name)
    profile = profile.model_copy(update={
        "id": name_slug,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return profile
